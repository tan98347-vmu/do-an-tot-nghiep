"""
Thuoc chuc nang nao: Endpoint REST cho tro ly AI moi, bao gom text, voice va cau noi sang man RAG.
Vai tro backend: File nay nhan request tu frontend assistant, quan ly session/message/audio, goi `run_assistant_turn`, mirror ket qua RAG sang session RAG rieng va tra action de client dieu huong.
Vai tro cua no trong frontend: Man assistant text, voice, lich su session va danh sach audio tren frontend goi truc tiep cac endpoint trong file nay.
Moi lien he voi nhung ham / source khac: Su dung `ChatSession`, `ChatMessage`, `ChatAudioAttachment` trong `ai_engine.models`, engine `run_assistant_turn` trong `ai_engine.assistant_engine`, serializer chat va `soft_delete_chat_sessions`.
Tac dung: Dong vai tro lop API bien luong tro ly AI thanh response JSON/phat file phu hop cho frontend.
"""

import time
from urllib.parse import urlencode

from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from ai_engine.assistant_engine import run_assistant_turn
from ai_engine.models import ChatAudioAttachment, ChatMessage, ChatSession
from accounts.runtime_guard import CompanyRuntimeGuard
from accounts.tenancy import get_user_company

from ..serializers.chat import ChatAudioAttachmentSerializer, ChatMessageSerializer, ChatSessionSerializer
from ..trash_services import soft_delete_chat_sessions

def _stash_attachments_to_disk(uploaded_files, *, prefix: str = 'chat_attach', max_per_request: int = 10):
    """Luu cac UploadedFile vao thu muc tam de background thread doc lai.

    Tra ve list path tuyet doi. Tu dong cap MIME-type / size limit:
      - PDF max 20MB; image max 10MB; bo qua file vuot nguong va log warning.
      - Toi da max_per_request file moi turn (mac dinh 10).
    """
    import os
    import tempfile
    import uuid

    files = list(uploaded_files or [])[:max_per_request]
    out_paths = []
    for f in files:
        if f is None:
            continue
        content_type = (getattr(f, 'content_type', '') or '').lower()
        size = getattr(f, 'size', 0) or 0
        is_pdf = 'pdf' in content_type or (getattr(f, 'name', '') or '').lower().endswith('.pdf')
        is_image = content_type.startswith('image/') or (
            (getattr(f, 'name', '') or '').lower().endswith(
                ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.bmp')
            )
        )
        if not (is_pdf or is_image):
            _assistant_view_debug(f'stash skip non-pdf-non-image | name={getattr(f, "name", "")} | ct={content_type}')
            continue
        max_bytes = (20 if is_pdf else 10) * 1024 * 1024
        if size and size > max_bytes:
            _assistant_view_debug(
                f'stash skip oversize | name={getattr(f, "name", "")} | size={size} | max={max_bytes}'
            )
            continue
        tmp_dir = os.path.join(tempfile.gettempdir(), 'chat_attachments')
        os.makedirs(tmp_dir, exist_ok=True)
        ext = '.pdf' if is_pdf else os.path.splitext(getattr(f, 'name', '') or '')[1] or '.bin'
        tmp_path = os.path.join(tmp_dir, f'{prefix}_{uuid.uuid4().hex}{ext}')
        try:
            with open(tmp_path, 'wb') as dest:
                for chunk in f.chunks():
                    dest.write(chunk)
            out_paths.append(tmp_path)
        except Exception as exc:
            _assistant_view_debug(f'stash write failed | name={getattr(f, "name", "")} | error={exc}')
    return out_paths


class _FilelikeBytes:
    """File-like wrapper cho bytes da doc tu disk, du de extract_pdf_text / OCR doc.

    Dung khi truyen attachment giua main thread (request) va background thread
    (do `run_in_thread` se chay khi request da dong). Luu path tam o disk, doc
    nhi phan ra bytes va wrap qua class nay.
    """
    def __init__(self, raw_bytes: bytes, name: str = 'attachment'):
        import io
        self._buf = io.BytesIO(raw_bytes)
        self.name = name

    def read(self, *args, **kwargs):
        return self._buf.read(*args, **kwargs)

    def seek(self, *args, **kwargs):
        return self._buf.seek(*args, **kwargs)

    def tell(self):
        return self._buf.tell()


def _parse_prefill_flag(value, default: bool = True) -> bool:
    """Doc co prefill (auto_fill_profile / auto_fill_company) tu request.

    Frontend gui boolean nhung qua multipart se thanh chuoi. Default `True` de
    request cu khong gui flag van giu hanh vi tu dien bien nhu truoc.
    """
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    text = str(value).strip().lower()
    if text in ('', 'true', '1', 'yes', 'on'):
        return True
    if text in ('false', '0', 'no', 'off'):
        return False
    return default


def _assistant_view_debug(message):
    """
    Thuoc chuc nang nao: Ghi log debug cho lop API assistant.
    Vai tro backend: Helper nay in log co prefix co dinh de phan biet ro cac su kien o tang API assistant voi log cua engine phia duoi.
    Vai tro cua no trong frontend: Frontend khong goi truc tiep, nhung log nay giup backend lan theo request assistant/voice khi user bao loi tren giao dien.
    Moi lien he voi nhung ham / source khac: Duoc cac endpoint trong file nay goi, dac biet `assistant_turn` va qua trinh mirror session RAG.
    Tac dung: Tao dau vet debug nhat quan cho nhom endpoint assistant.
    """
    print(f'[assistant_api] {message}', flush=True)

def _session_type_from_mode(mode):
    """
    Thuoc chuc nang nao: Anh xa mode giao dien sang loai session AI trong database.
    Vai tro backend: Ham nay quyet dinh request hien tai phai luu vao `SESSION_ASSISTANT` hay `SESSION_VOICE`, de session text va session giong noi khong bi tron du lieu.
    Vai tro cua no trong frontend: Frontend chi gui `mode=text|voice`, con backend dung helper nay de dat dung bucket session cho sidebar va lich su.
    Moi lien he voi nhung ham / source khac: Dung hang `ChatSession.SESSION_VOICE` va `ChatSession.SESSION_ASSISTANT`; duoc `assistant_turn` va `assistant_sessions` goi.
    Tac dung: Giu phan tach ro giua che do text va che do voice.
    """
    return (
        ChatSession.SESSION_VOICE
        if str(mode or '').strip().lower() == 'voice'
        else ChatSession.SESSION_ASSISTANT
    )

def _session_title_from_question(question):
    """
    Thuoc chuc nang nao: Dat tieu de mac dinh cho session assistant moi.
    Vai tro backend: Ham nay cat cau hoi dau tien thanh toi da 80 ky tu de dung lam title session, neu rong thi dung nhan du phong.
    Vai tro cua no trong frontend: Sidebar lich su assistant tren frontend hien title doc duoc ngay tu luot hoi dau ma khong can user dat ten thu cong.
    Moi lien he voi nhung ham / source khac: Duoc `assistant_turn` va `_mirror_rag_result_to_session` goi khi tao session moi.
    Tac dung: Tao ten hien thi hop ly cho thread tro ly.
    """
    question = (question or '').strip()
    return question[:80] or 'Cuoc tro chuyen moi'

def _rag_return_target(mode):
    """
    Thuoc chuc nang nao: Xac dinh route quay ve sau khi mo man ket qua RAG.
    Vai tro backend: Helper nay dua tren mode hien tai de tra `return_to` va `return_label`, giup action dieu huong sang trang RAG biet cach dua user quay lai dung man text hay voice.
    Vai tro cua no trong frontend: Frontend dung du lieu nay khi assistant mo man RAG ket qua, nham hien nut quay ve hop ngu canh.
    Moi lien he voi nhung ham / source khac: Duoc `assistant_turn` goi khi `response_action.type == 'open_rag_result'`.
    Tac dung: Giu navigation giua assistant va man RAG mach lac.
    """
    if str(mode or '').strip().lower() == 'voice':
        return '/chat/voice', 'Quay về Giọng nói AI'
    return '/chat/text', 'Quay về Chat AI'

def _mirror_rag_result_to_session(*, user, question, answer, citations, source_mode):
    """
    Thuoc chuc nang nao: Nhan ban ket qua RAG tu assistant sang session RAG rieng.
    Vai tro backend: Ham nay tao mot `ChatSession` loai RAG, luu lai cau hoi user va cau tra loi assistant kem citations, de man RAG co lich su rieng va co the mo thang vao ket qua vua tao.
    Vai tro cua no trong frontend: Khi user hoi template/document trong assistant, frontend co the duoc dieu huong sang man RAG ma van thay day du lich su cua cau hoi do.
    Moi lien he voi nhung ham / source khac: Tao `ChatSession` va `ChatMessage`; duoc `assistant_turn` goi khi payload assistant bao `kind='rag_result'`.
    Tac dung: Noi luong assistant va luong RAG bang cach tai su dung chung he thong session/message.
    """
    rag_session = ChatSession.objects.create(
        user=user,
        company=get_user_company(user),
        title=_session_title_from_question(question),
        session_type=ChatSession.SESSION_RAG,
        rag_mode=source_mode,
    )
    ChatMessage.objects.create(
        session=rag_session,
        role=ChatMessage.ROLE_USER,
        content=question,
    )
    rag_message = ChatMessage.objects.create(
        session=rag_session,
        role=ChatMessage.ROLE_ASSISTANT,
        content=answer,
        citations=citations or None,
        payload={
            'kind': 'assistant_rag_import',
            'source_mode': source_mode,
            'source': 'assistant',
        },
    )
    rag_session.save(update_fields=['updated_at'])
    _assistant_view_debug(
        'assistant_turn rag_mirrored | '
        f'rag_session_id={rag_session.id} | rag_message_id={rag_message.id} | '
        f'source_mode={source_mode} | citations={len(citations or [])}'
    )
    return rag_session, rag_message


def _persist_cancelled_stream_message(*, session, content):
    text = str(content or '').strip()
    if not text:
        return None
    message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_ASSISTANT,
        content=text,
        payload={
            'kind': 'cancelled_stream',
            'status': 'cancelled',
        },
    )
    session.save(update_fields=['updated_at'])
    return message


def _finalize_assistant_turn_result(*, user, session, question, mode, result):
    payload = dict(result.payload or {}) if isinstance(result.payload, dict) else result.payload
    response_action = (
        dict(result.action or {})
        if isinstance(result.action, dict)
        else {}
    )
    rag_session = None
    rag_message = None
    if isinstance(payload, dict) and payload.get('kind') == 'rag_result':
        source_mode = str(
            payload.get('source_mode')
            or response_action.get('source_mode')
            or 'template'
        ).strip().lower()
        source_mode = 'document' if source_mode == 'document' else 'template'
        rag_session, rag_message = _mirror_rag_result_to_session(
            user=user,
            question=question,
            answer=result.content,
            citations=result.citations or [],
            source_mode=source_mode,
        )
        payload = {
            **payload,
            'rag_session_id': rag_session.id,
            'rag_message_id': rag_message.id,
            'source_mode': source_mode,
        }
        response_action = {
            **response_action,
            'source_mode': source_mode,
            'rag_session_id': rag_session.id,
            'rag_message_id': rag_message.id,
        }

    assistant_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_ASSISTANT,
        content=result.content,
        citations=result.citations or None,
        payload=payload,
    )
    update_fields = ['updated_at']
    if isinstance(result.assistant_state, dict):
        session.assistant_state = result.assistant_state
        update_fields.insert(0, 'assistant_state')
    if response_action.get('type') == 'open_rag_result':
        source_mode = str(
            response_action.get('source_mode')
            or (payload.get('source_mode') if isinstance(payload, dict) else '')
            or 'template'
        ).strip().lower()
        source_mode = 'document' if source_mode == 'document' else 'template'
        return_to, return_label = _rag_return_target(mode)
        route_params = {
            'mode': source_mode,
            'return_to': return_to,
            'return_label': return_label,
        }
        if rag_session is not None:
            route_params['rag_session_id'] = rag_session.id
        if rag_message is not None:
            route_params['rag_message_id'] = rag_message.id
        response_action['route'] = '/rag?' + urlencode(route_params)
    session.save(update_fields=update_fields)
    return assistant_message, response_action


def _serialize_assistant_turn_payload(*, session, assistant_message, response_action, request=None):
    context = {'request': request} if request is not None else {}
    return {
        'session': ChatSessionSerializer(session, context=context).data,
        'message': ChatMessageSerializer(assistant_message, context=context).data,
        'action': response_action,
    }


def _do_assistant_turn_task(task_id, user_id, session_id, question, mode, history, voice_audio_path,
                              voice_duration, voice_mime,
                              use_profile=True, use_company=True,
                              pdf_attachment_paths=None, image_attachment_paths=None):
    """Background assistant turn voi stage progress + token streaming."""
    from django.contrib.auth.models import User
    from ai_tasks.services.task_runner import (
        TaskCancelled,
        append_stream_chunk,
        check_cancel,
        update_progress,
    )

    user = User.objects.get(pk=user_id)
    session = ChatSession.objects.get(pk=session_id, user=user)
    streamed_chunks = []
    token_count = [0]
    expected_max_tokens = 500

    def _on_token(chunk):
        token = str(chunk or '')
        if not token:
            return
        streamed_chunks.append(token)
        token_count[0] += 1
        c = token_count[0]
        percent = 50 + min(45, int(45 * c / expected_max_tokens))
        if c < 3:
            stage = 'Nhan token dau tien'
            detail = 'AI bat dau phan hoi'
        elif c < 15:
            stage = 'Hieu cau hoi va suy luan'
            detail = f'Da phan tich {c} token'
        elif c < 40:
            stage = 'Soan cau tra loi'
            detail = f'Da soan {c} token'
        elif c < 120:
            stage = 'Mo rong noi dung'
            detail = f'Dang viet ({c} token)'
        elif c < 250:
            stage = 'Hoan thien chi tiet'
            detail = f'Bo sung dien giai ({c} token)'
        elif c < 400:
            stage = 'Tinh chinh cau tu'
            detail = f'Lam mu mat cau ({c} token)'
        else:
            stage = 'Sap hoan tat phan hoi'
            detail = f'Da viet {c} token'
        update_progress(task_id, percent, stage, detail)
        append_stream_chunk(task_id, token)
        check_cancel(task_id)

    update_progress(task_id, 3, 'Khoi tao phien tro ly', 'Chuan bi du lieu nguoi dung')
    check_cancel(task_id)

    if mode == 'voice':
        update_progress(task_id, 6, 'Da nhan audio',
                        f'{voice_duration:.1f}s' if voice_duration else 'audio file')
        check_cancel(task_id)
        update_progress(task_id, 10, 'Kiem tra dinh dang audio', voice_mime or 'audio/webm')
        check_cancel(task_id)
        update_progress(task_id, 15, 'Chuyen giong noi thanh van ban (STT)', 'Dang nhan dien tieng noi')
        check_cancel(task_id)
        update_progress(task_id, 22, 'Hoan tat phien dich STT', 'Trich xuat van ban tu audio')
        check_cancel(task_id)
    else:
        update_progress(task_id, 10, 'Phan tich y dinh', question[:80])
        check_cancel(task_id)

    update_progress(task_id, 28, 'Doc lich su tro chuyen', f'{len(history)} luot truoc')
    check_cancel(task_id)

    update_progress(task_id, 32, 'Tom luoc ngu canh hoi thoai', 'Loc thong tin lien quan')
    check_cancel(task_id)

    update_progress(task_id, 38, 'Tim ngu canh tai lieu (RAG)', 'Truy van vector store')
    check_cancel(task_id)

    update_progress(task_id, 42, 'Xep hang ngu canh tai lieu', 'Chon top tai lieu phu hop')
    check_cancel(task_id)

    update_progress(task_id, 46, 'Chuan bi prompt toolchain', 'Tap hop cong cu kha dung')
    check_cancel(task_id)

    attachment_context = ''
    pdf_paths = list(pdf_attachment_paths or [])
    image_paths = list(image_attachment_paths or [])
    _all_attachment_paths = pdf_paths + image_paths
    if pdf_paths or image_paths:
        import os as _os
        from ai_engine.chat_attachment_pipeline import build_attachment_context
        pdf_blobs = []
        image_blobs = []
        for p in pdf_paths:
            try:
                with open(p, 'rb') as fp:
                    blob = _FilelikeBytes(fp.read(), name=_os.path.basename(p))
                pdf_blobs.append(blob)
            except Exception as exc:
                _assistant_view_debug(f'attachment_pdf read failed: {exc}')
        for p in image_paths:
            try:
                with open(p, 'rb') as fp:
                    blob = _FilelikeBytes(fp.read(), name=_os.path.basename(p))
                image_blobs.append(blob)
            except Exception as exc:
                _assistant_view_debug(f'attachment_image read failed: {exc}')
        try:
            attachment_context = build_attachment_context(
                user=user,
                pdf_files=pdf_blobs,
                image_files=image_blobs,
                task_id=task_id,
                progress_start=46,
                progress_end=49,
            )
        except Exception as exc:
            _assistant_view_debug(f'attachment pipeline error: {exc}')
        check_cancel(task_id)

    from accounts.tenancy import resolve_chat_ai_model
    chat_model = resolve_chat_ai_model(user=user)
    update_progress(task_id, 49, 'Gui prompt sang LLM', chat_model)
    check_cancel(task_id)

    update_progress(task_id, 50, 'AI dang suy nghi', f'Cho token dau tien tu {chat_model}')
    check_cancel(task_id)
    try:
        result = run_assistant_turn(
            question,
            user,
            mode=mode,
            history=history,
            state=session.assistant_state,
            session=session,
            streaming_callback=_on_token,
            use_profile=use_profile,
            use_company=use_company,
            attachment_context=attachment_context,
        )
    except TaskCancelled:
        _persist_cancelled_stream_message(
            session=session,
            content=''.join(streamed_chunks),
        )
        raise
    check_cancel(task_id)

    answer_text = ''
    if isinstance(result, dict):
        answer_text = str(
            result.get('answer') or result.get('reply') or result.get('text') or ''
        ).strip()
    else:
        answer_text = str(getattr(result, 'content', '') or '').strip()

    streamed_text = ''.join(streamed_chunks)
    if answer_text and not streamed_text:
        for chunk in (answer_text[i:i + 80] for i in range(0, len(answer_text), 80)):
            append_stream_chunk(task_id, chunk)
    elif answer_text and streamed_text and answer_text.startswith(streamed_text):
        remainder = answer_text[len(streamed_text):]
        if remainder:
            append_stream_chunk(task_id, remainder)

    update_progress(task_id, 88, 'Tong hop phan hoi', f'{len(answer_text)} ky tu')
    update_progress(task_id, 90, 'Luu phan hoi vao lich su', f'Ghi vao session #{session.id}')
    assistant_message, response_action = _finalize_assistant_turn_result(
        user=user,
        session=session,
        question=question,
        mode=mode,
        result=result,
    )
    update_progress(task_id, 92, 'Cap nhat trang thai phien', 'Lien ket toolchain ket qua')

    if mode == 'voice':
        update_progress(task_id, 95, 'Tao giong noi tra loi (TTS)', 'Sap phat audio')
        update_progress(task_id, 98, 'San sang doc phan hoi', 'Audio da san sang')

    payload = _serialize_assistant_turn_payload(
        session=session,
        assistant_message=assistant_message,
        response_action=response_action,
    )
    payload['answer'] = assistant_message.content
    payload['mode'] = mode
    payload['model'] = chat_model

    # Cleanup attachment temp files (per-turn)
    if _all_attachment_paths:
        import os as _os
        for _p in _all_attachment_paths:
            try:
                _os.remove(_p)
            except OSError:
                pass

    return payload


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assistant_turn_async(request):
    from ai_tasks.models import TASK_TYPE_VOICE, TASK_TYPE_CHAT
    from ai_tasks.services.task_runner import create_task, run_in_thread

    question = (request.data.get('input') or '').strip()
    if not question:
        return Response({'error': 'Vui long nhap noi dung can xu ly.'},
                        status=status.HTTP_400_BAD_REQUEST)
    mode = str(request.data.get('mode') or 'text').strip().lower()
    session_type = _session_type_from_mode(mode)
    session_id = request.data.get('session_id')

    company = get_user_company(request.user)
    session = None
    if session_id:
        session = ChatSession.objects.filter(
            pk=session_id, user=request.user, company=company,
            session_type=session_type,
        ).first()
    if session is None:
        session = ChatSession.objects.create(
            user=request.user, company=company,
            title=_session_title_from_question(question),
            session_type=session_type,
        )

    history = list(session.messages.order_by('created_at').values('role', 'content'))
    user_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_USER,
        content=question,
    )

    voice_audio = request.FILES.get('voice_audio')
    voice_path = None
    if voice_audio is not None:
        attach = ChatAudioAttachment.objects.create(
            session=session,
            message=user_message,
            created_by=request.user,
            title=f'Voice {timezone.now().strftime("%d/%m/%Y %H:%M:%S")}',
            transcript=question,
            mime_type=getattr(voice_audio, 'content_type', '') or '',
            duration_seconds=float(request.data.get('voice_duration_seconds') or 0),
            audio_file=voice_audio,
        )
        voice_path = attach.audio_file.name if attach.audio_file else None

    use_profile_flag = _parse_prefill_flag(request.data.get('auto_fill_profile'))
    use_company_flag = _parse_prefill_flag(request.data.get('auto_fill_company'))

    pdf_attachment_paths = _stash_attachments_to_disk(
        request.FILES.getlist('attachment_pdfs'),
        prefix='chat_pdf',
    )
    image_attachment_paths = _stash_attachments_to_disk(
        request.FILES.getlist('attachment_images'),
        prefix='chat_img',
    )

    task_type = TASK_TYPE_VOICE if mode == 'voice' else TASK_TYPE_CHAT
    task = create_task(
        user=request.user, task_type=task_type,
        related_entity_type='chat_session', related_entity_id=session.id,
    )
    run_in_thread(
        task, _do_assistant_turn_task,
        request.user.pk, session.id, question, mode, history,
        voice_path,
        float(request.data.get('voice_duration_seconds') or 0),
        getattr(voice_audio, 'content_type', '') if voice_audio else '',
        use_profile_flag,
        use_company_flag,
        pdf_attachment_paths,
        image_attachment_paths,
    )
    return Response({
        'task_id': str(task.task_id),
        'polling_url': f'/api/ai-tasks/{task.task_id}/',
        'session_id': session.id,
        'mode': mode,
        'status': 'queued',
    }, status=status.HTTP_202_ACCEPTED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assistant_turn(request):
    """
    Thuoc chuc nang nao: Endpoint xu ly mot luot hoi dap cua tro ly AI.
    Vai tro backend: Endpoint nay validate input, tim/tao session dung mode, luu user message va audio neu co, goi `run_assistant_turn`, mirror ket qua RAG khi can, luu assistant message cuoi va tra `action` cho frontend.
    Vai tro cua no trong frontend: Man assistant text/voice goi truc tiep endpoint nay moi khi nguoi dung gui cau hoi hoac transcript, va nhan ket qua de render bong chat, citation va dieu huong.
    Moi lien he voi nhung ham / source khac: Dung `_session_type_from_mode`, `_session_title_from_question`, `_rag_return_target`, `_mirror_rag_result_to_session`; goi `run_assistant_turn`; luu `ChatSession`, `ChatMessage`, `ChatAudioAttachment`.
    Tac dung: Dong vai tro entrypoint chinh cua san pham assistant AI.
    """
    started_at = time.perf_counter()
    question = (request.data.get('input') or '').strip()
    if not question:
        _assistant_view_debug('assistant_turn reject | empty input')
        return Response(
            {'error': 'Vui long nhap noi dung can xu ly.'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    mode = str(request.data.get('mode') or 'text').strip().lower()
    session_type = _session_type_from_mode(mode)
    session_id = request.data.get('session_id')
    _assistant_view_debug(
        f'assistant_turn start | user_id={getattr(request.user, "id", None)} '
        f'| mode={mode} | session_id={session_id!r} | session_type={session_type} '
        f'| question_len={len(question)}'
    )

    session = None
    company = get_user_company(request.user)
    if session_id:
        session = ChatSession.objects.filter(
            pk=session_id,
            user=request.user,
            company=company,
            session_type=session_type,
        ).first()
        _assistant_view_debug(
            f'assistant_turn session_lookup | requested_session_id={session_id!r} '
            f'| found={session is not None}'
        )
    if session is None:
        session = ChatSession.objects.create(
            user=request.user,
            company=company,
            title=_session_title_from_question(question),
            session_type=session_type,
        )
        _assistant_view_debug(
            f'assistant_turn session_created | session_id={session.id} | title={session.title!r}'
        )
    else:
        _assistant_view_debug(
            f'assistant_turn session_reused | session_id={session.id} | title={session.title!r}'
        )

    history = list(session.messages.order_by('created_at').values('role', 'content'))
    _assistant_view_debug(f'assistant_turn history_loaded | history_turns={len(history)}')
    user_message = ChatMessage.objects.create(
        session=session,
        role=ChatMessage.ROLE_USER,
        content=question,
    )
    _assistant_view_debug('assistant_turn user_message_saved')
    voice_audio = request.FILES.get('voice_audio')
    if voice_audio is not None:
        ChatAudioAttachment.objects.create(
            session=session,
            message=user_message,
            created_by=request.user,
            title=f'Voice {timezone.now().strftime("%d/%m/%Y %H:%M:%S")}',
            transcript=question,
            mime_type=getattr(voice_audio, 'content_type', '') or '',
            duration_seconds=float(request.data.get('voice_duration_seconds') or 0),
            audio_file=voice_audio,
        )
        _assistant_view_debug('assistant_turn voice_audio_saved')

    use_profile_flag = _parse_prefill_flag(request.data.get('auto_fill_profile'))
    use_company_flag = _parse_prefill_flag(request.data.get('auto_fill_company'))
    try:
        result = run_assistant_turn(
            question,
            request.user,
            mode=mode,
            history=history,
            state=session.assistant_state,
            session=session,
            use_profile=use_profile_flag,
            use_company=use_company_flag,
        )
    except Exception as exc:
        _assistant_view_debug(
            f'assistant_turn error | elapsed_ms={(time.perf_counter() - started_at) * 1000:.0f} | error={exc!r}'
        )
        return Response(
            {'error': str(exc)},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    assistant_message, response_action = _finalize_assistant_turn_result(
        user=request.user,
        session=session,
        question=question,
        mode=mode,
        result=result,
    )
    _assistant_view_debug(
        'assistant_turn response_ready | '
        f'session_id={session.id} | assistant_message_id={assistant_message.id} | '
        f'citations={len(result.citations or [])} | tool_name={result.tool_name!r} | '
        f'payload_kind={(result.payload or {}).get("kind", "")!r} | '
        f'action_type={(result.action or {}).get("type", "")!r} | '
        f'elapsed_ms={(time.perf_counter() - started_at) * 1000:.0f}'
    )
    _assistant_view_debug(
        'assistant_turn response_payload | '
        f'message_len={len(result.content or "")} | route={(result.payload or {}).get("route", "")!r} '
        f'| action_route={getattr(response_action, "get", lambda *_: "")("route") if isinstance(response_action, dict) else ""!r}'
    )

    return Response(
        _serialize_assistant_turn_payload(
            session=session,
            assistant_message=assistant_message,
            response_action=response_action,
            request=request,
        )
    )

@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def assistant_sessions(request):
    """
    Thuoc chuc nang nao: Liet ke hoac xoa mem cac session assistant/voice.
    Vai tro backend: `GET` tra danh sach session theo mode text/voice cua user hien tai; `DELETE` goi `soft_delete_chat_sessions` de an cac session da chon thay vi xoa cung khoi DB.
    Vai tro cua no trong frontend: Sidebar lich su assistant va thao tac xoa nhieu cuoc tro chuyen tren giao dien goi truc tiep endpoint nay.
    Moi lien he voi nhung ham / source khac: Dung `_session_type_from_mode`, `ChatSessionSerializer`, `soft_delete_chat_sessions` va model `ChatSession`.
    Tac dung: Cung cap API quan ly danh sach session cho giao dien assistant.
    """
    if request.method == 'DELETE':
        mode = str(request.data.get('mode') or 'text').strip().lower()
        session_types = (
            [ChatSession.SESSION_VOICE]
            if mode == 'voice'
            else [ChatSession.SESSION_ASSISTANT]
        )
        session_ids = request.data.get('session_ids')
        if not session_ids:
            return Response(
                {'detail': 'Danh sach session_ids khong hop le.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        payload = soft_delete_chat_sessions(
            request.user,
            session_ids,
            actor=request.user,
            session_types=session_types,
        )
        return Response(payload)

    mode = str(request.GET.get('mode') or 'text').strip().lower()
    session_type = _session_type_from_mode(mode)
    sessions = ChatSession.objects.filter(
        user=request.user,
        company=get_user_company(request.user),
        session_type=session_type,
    ).order_by('-updated_at', '-created_at')
    return Response(ChatSessionSerializer(sessions, many=True, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assistant_session_messages(request, session_id):
    """
    Thuoc chuc nang nao: Lay lich su message cua mot session assistant cu the.
    Vai tro backend: Endpoint nay xac thuc session thuoc user, chi chap nhan session assistant/voice, sau do tra toan bo message theo thu tu tao.
    Vai tro cua no trong frontend: Khi nguoi dung mo lai mot cuoc tro chuyen cu trong sidebar assistant, frontend goi endpoint nay de do lai bong chat.
    Moi lien he voi nhung ham / source khac: Truy van `ChatSession`, `ChatMessage` va serialize bang `ChatMessageSerializer`.
    Tac dung: Cung cap du lieu lich su de frontend phuc hoi mot thread assistant cu.
    """
    session = get_object_or_404(
        ChatSession,
        pk=session_id,
        user=request.user,
        company=get_user_company(request.user),
    )
    if session.session_type not in {
        ChatSession.SESSION_ASSISTANT,
        ChatSession.SESSION_VOICE,
    }:
        return Response(
            {'error': 'Phien nay khong thuoc tro ly AI moi.'},
            status=status.HTTP_404_NOT_FOUND,
        )
    messages = session.messages.order_by('created_at')
    return Response(ChatMessageSerializer(messages, many=True, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assistant_audio_list(request):
    """
    Thuoc chuc nang nao: Liet ke cac tep audio da gui trong assistant voice.
    Vai tro backend: Endpoint nay loc `ChatAudioAttachment` theo user hien tai va session chua xoa mem; neu co `session_id` thi thu hep danh sach vao mot thread cu the.
    Vai tro cua no trong frontend: Man lich su ghi am hoac danh sach audio trong mot session voice goi endpoint nay de hien cac tep da luu.
    Moi lien he voi nhung ham / source khac: Truy van `ChatAudioAttachment`, join `session` va `message`, serialize bang `ChatAudioAttachmentSerializer`.
    Tac dung: Cung cap API doc metadata audio cho giao dien assistant voice.
    """
    session_id = request.GET.get('session_id')
    items = ChatAudioAttachment.objects.filter(
        created_by=request.user,
        session__company=get_user_company(request.user),
        session__is_deleted=False,
    ).select_related('session', 'message')
    if session_id:
        items = items.filter(session_id=session_id)
    return Response(ChatAudioAttachmentSerializer(items.order_by('-created_at'), many=True, context={'request': request}).data)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def assistant_audio_download(request, audio_id):
    """
    Thuoc chuc nang nao: Phat lai hoac tai xuong mot tep audio assistant.
    Vai tro backend: Endpoint nay xac thuc audio thuoc user va session chua bi xoa, mo `audio_file` va tra `FileResponse` voi `Content-Disposition`/`content_type` phu hop.
    Vai tro cua no trong frontend: Frontend goi endpoint nay de phat audio inline hoac tai file ghi am nguoi dung da gui cho voice assistant.
    Moi lien he voi nhung ham / source khac: Truy van `ChatAudioAttachment`; phu thuoc vao storage field `audio_file`; ket hop `quote` de tao ten file an toan cho header.
    Tac dung: Bien tai nguyen audio da luu thanh response file ma trinh duyet co the mo ngay.
    """
    from django.http import FileResponse
    from urllib.parse import quote

    item = get_object_or_404(
        ChatAudioAttachment,
        pk=audio_id,
        created_by=request.user,
        session__company=get_user_company(request.user),
        session__is_deleted=False,
    )
    CompanyRuntimeGuard.assert_file_field(
        item.audio_file,
        target=item.session,
        detail='Tep audio tro ly dang tro sang cong ty khac.',
    )
    response = FileResponse(item.audio_file.open('rb'), content_type=item.mime_type or 'audio/webm')
    name = quote(item.title or f'audio_{item.pk}.webm')
    response['Content-Disposition'] = f'inline; filename=\"{name}\"'
    return response
