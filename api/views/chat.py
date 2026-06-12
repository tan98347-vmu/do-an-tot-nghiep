"""
Thuoc chuc nang nao: Endpoint REST cho chat AI co dien, RAG query va lich su session lien quan.
Vai tro backend: File nay phuc vu luong chat AI tong quat, luong RAG template/document rieng, va quan ly session/message cua hai nhom do; dong thoi co kha nang re nhanh sang tao document neu cau hoi mang y dinh sinh van ban.
Vai tro cua no trong frontend: Man Chat AI cu, man RAG text va sidebar lich su cho hai man nay goi truc tiep cac endpoint trong file nay.
Moi lien he voi nhung ham / source khac: Dung `ChatSession`, `ChatMessage`, `KnowledgeBase` trong `ai_engine.models`, `ask_ai`/`rag_query` trong `ai_engine.rag_engine`, `is_document_creation_request`/`create_document_from_intent` trong `ai_engine.doc_creator`, va serializer chat.
Tac dung: Bien cac luong chat/RAG co dien thanh API JSON co session, lich su va phep xoa mem.
"""

import json
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from accounts.tenancy import get_user_company
from ai_engine.models import ChatSession, ChatMessage, KnowledgeBase
from ai_engine.rag_engine import ask_ai, rag_query
from ai_engine.doc_creator import is_document_creation_request, create_document_from_intent
from ..serializers.chat import ChatSessionSerializer, ChatMessageSerializer, KnowledgeBaseSerializer
from ..trash_services import soft_delete_chat_sessions

# Là gì: `chat_ai_model_info` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `chat ai model info` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `resolve_chat_ai_model` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_ai_model_info(request):
    """Tra ve model dang dung cho Tro ly Chat AI cua nguoi dung hien tai."""
    from accounts.tenancy import resolve_chat_ai_model
    model = resolve_chat_ai_model(user=request.user)
    return Response({
        'model': model,
        'display_name': model,
    })


# Là gì: `_do_chat_task` là helper nội bộ của module `chat.py`, phục vụ nhóm chat AI, hội thoại và phản hồi theo luồng.
# Chức năng backend: Hàm thực thi phần xử lý nội bộ của luồng hiện tại; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ giao diện ChatAI.
# Mối liên hệ: Hàm phối hợp với `User.objects.get`, `update_progress`, `check_cancel` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: hàm hỗ trợ tái sử dụng trong module; có side effect ghi cơ sở dữ liệu.
def _do_chat_task(task_id, user_id, session_id, question, prompt_system, prompt_rules, extra_context):
    """Background chat task with detailed stages + token streaming progress."""
    from django.contrib.auth.models import User
    from langchain_core.messages import HumanMessage, SystemMessage
    from ai_engine.rag_engine import get_llm
    from ai_tasks.services.task_runner import (
        update_progress, check_cancel, append_stream_chunk,
    )

    user = User.objects.get(pk=user_id)

    update_progress(task_id, 3, 'Khoi tao', 'Mo phien chat')
    check_cancel(task_id)
    session = ChatSession.objects.get(pk=session_id, user=user)

    update_progress(task_id, 8, 'Phan tich y dinh', question[:80])
    check_cancel(task_id)

    update_progress(task_id, 15, 'Doc lich su tro chuyen', f'Session #{session.id}')
    history_count = session.messages.count()
    check_cancel(task_id)

    if prompt_system or prompt_rules:
        update_progress(task_id, 20, 'Tai prompt template', 'Co he tu tuong + quy tac')
    else:
        update_progress(task_id, 20, 'Tai prompt mac dinh', '')
    check_cancel(task_id)

    update_progress(task_id, 25, 'Chuan bi cau prompt', f'{history_count} luot truoc')
    check_cancel(task_id)

    token_count = [0]
    expected_max = 500

    # Là gì: `on_token` là hàm cục bộ bên trong `_do_chat_task`, chỉ phục vụ bước xử lý nội bộ của nhóm chat AI, hội thoại và phản hồi theo luồng.
    # Chức năng backend: Hàm xử lý phần việc `on token` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
    # Vai trò với UI: Flutter không gọi trực tiếp hàm này; các endpoint cùng module dùng kết quả của nó để phục vụ giao diện ChatAI.
    # Mối liên hệ: Hàm phối hợp với `update_progress`, `append_stream_chunk` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
    # Bản chất và tác dụng: callback cục bộ chỉ có hiệu lực trong hàm bao ngoài; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu.
    def on_token(chunk):
        token_count[0] += 1
        c = token_count[0]
        pct = 30 + min(65, int(65 * c / expected_max))
        if c < 3:
            stage = 'Nhan token dau tien'
            detail = 'AI vua bat dau phan hoi'
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
        update_progress(task_id, pct, stage, detail)
        append_stream_chunk(task_id, chunk)

    from accounts.tenancy import resolve_chat_ai_model
    chat_model = resolve_chat_ai_model(user=user)
    update_progress(task_id, 28, 'Ket noi LLM Ollama', f'Mo ket noi toi {chat_model}')
    check_cancel(task_id)
    update_progress(task_id, 30, 'Gui prompt va cho phan hoi', f'Cho token dau tien tu {chat_model}')
    check_cancel(task_id)

    identity = (prompt_system or '').strip() or 'Ban la tro ly AI tieng Viet, tra loi ngan gon ro rang.'
    rules = (prompt_rules or '').strip()
    system_prompt = identity + ('\n\nQUY TAC:\n' + rules if rules else '')
    human_prompt = question
    if extra_context:
        human_prompt = f'NGU CANH:\n{extra_context}\n\nCAU HOI:\n{question}'

    llm = get_llm(user, model_override=chat_model, streaming_callback=on_token)
    resp = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt),
    ])
    answer = str(getattr(resp, 'content', '') or '').strip()

    update_progress(task_id, 95, 'Tong hop phan hoi', f'{len(answer)} ky tu cau tra loi')
    check_cancel(task_id)
    update_progress(task_id, 97, 'Luu lich su chat', f'Ghi vao session #{session.id}')
    ChatMessage.objects.create(session=session, role='assistant', content=answer)
    session.save(update_fields=['updated_at'])
    update_progress(task_id, 99, 'Don dep va dong ngu canh', 'Cap nhat trang thai phien')
    return {
        'answer': answer,
        'session_id': session.id,
        'token_count': token_count[0],
        'model': chat_model,
    }


# Là gì: `chat_message_async` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `chat message async` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `strip`, `request.data.get`, `get_accessible_prompts.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_message_async(request):
    from ai_tasks.models import TASK_TYPE_CHAT
    from ai_tasks.services.task_runner import create_task, run_in_thread

    question = (request.data.get('q') or '').strip()
    if not question:
        return Response({'error': 'Vui lòng nhập câu hỏi.'}, status=status.HTTP_400_BAD_REQUEST)

    session_id = request.data.get('session_id')
    prompt_id = request.data.get('prompt_id')
    extra_context = request.data.get('extra_context', '')

    prompt_system = None
    prompt_rules = None
    if prompt_id:
        from prompts.models import Prompt, PROMPT_STATUS_APPROVED
        from accounts.permissions import get_accessible_prompts
        try:
            p = get_accessible_prompts(request.user).get(pk=prompt_id, status=PROMPT_STATUS_APPROVED)
            prompt_system = p.system_content or None
            prompt_rules = p.rules_content or None
        except Prompt.DoesNotExist:
            pass

    company = get_user_company(request.user)
    session = None
    if session_id:
        try:
            session = ChatSession.objects.get(
                pk=session_id, user=request.user, company=company,
                session_type=ChatSession.SESSION_CHAT,
            )
        except ChatSession.DoesNotExist:
            session = None
    if not session:
        session = ChatSession.objects.create(user=request.user, company=company, title=question[:50])
    ChatMessage.objects.create(session=session, role='user', content=question)

    task = create_task(
        user=request.user,
        task_type=TASK_TYPE_CHAT,
        related_entity_type='chat_session',
        related_entity_id=session.id,
    )
    run_in_thread(
        task, _do_chat_task,
        request.user.pk, session.id, question,
        prompt_system, prompt_rules, extra_context,
    )
    return Response({
        'task_id': str(task.task_id),
        'polling_url': f'/api/ai-tasks/{task.task_id}/',
        'session_id': session.id,
        'status': 'queued',
    }, status=status.HTTP_202_ACCEPTED)


# Là gì: `chat_message` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `chat message` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `request.data.get.strip`, `request.data.get`, `get_accessible_prompts.get` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def chat_message(request):
    """
    Thuoc chuc nang nao: Endpoint gui mot tin nhan vao luong Chat AI co dien.
    Vai tro backend: Endpoint nay validate cau hoi, nap prompt bo sung neu user chon prompt, tim/tao session chat, luu user message, roi re nhanh sang `create_document_from_intent` neu day la yeu cau tao van ban; nguoc lai thi goi `ask_ai`.
    Vai tro cua no trong frontend: Man Chat AI goi truc tiep endpoint nay moi khi user gui noi dung; frontend nhan `answer` va `session_id` de cap nhat bong chat va sidebar.
    Moi lien he voi nhung ham / source khac: Goi `is_document_creation_request`, `create_document_from_intent`, `ask_ai`; doc prompt tu `prompts.models`; luu `ChatSession` va `ChatMessage`.
    Tac dung: Tao entrypoint chat tong quat co kha nang vua hoi dap vua tao document.
    """
    question = request.data.get('q', '').strip()
    if not question:
        return Response({'error': 'Vui lòng nhập câu hỏi.'}, status=status.HTTP_400_BAD_REQUEST)

    session_id = request.data.get('session_id')
    prompt_id = request.data.get('prompt_id')
    extra_context = request.data.get('extra_context', '')

    prompt_system = None
    prompt_rules = None
    if prompt_id:
        from prompts.models import Prompt, PROMPT_STATUS_APPROVED
        from accounts.permissions import get_accessible_prompts
        try:
            p = get_accessible_prompts(request.user).get(pk=prompt_id, status=PROMPT_STATUS_APPROVED)
            prompt_system = p.system_content or None
            prompt_rules = p.rules_content or None
        except Prompt.DoesNotExist:
            pass

    session = None
    company = get_user_company(request.user)
    if session_id:
        try:
            session = ChatSession.objects.get(
                pk=session_id,
                user=request.user,
                company=company,
                session_type=ChatSession.SESSION_CHAT,
            )
        except ChatSession.DoesNotExist:
            pass
    if not session:
        session = ChatSession.objects.create(user=request.user, company=company, title=question[:50])

    ChatMessage.objects.create(session=session, role='user', content=question)

    try:
        if is_document_creation_request(question):
            answer, _, _, _ = create_document_from_intent(
                question, request.user,
                system_ideology=prompt_system,
                user_extra_rules=prompt_rules,
                extra_context=extra_context,
            )
        else:
            answer, _ = ask_ai(
                question=question, user=request.user,
                extra_context=extra_context,
                prompt_system_ideology=prompt_system,
                prompt_rules_content=prompt_rules,
            )
        ChatMessage.objects.create(session=session, role='assistant', content=answer)
        session.save(update_fields=['updated_at'])
        return Response({'answer': answer, 'session_id': session.id})
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Là gì: `chat_sessions` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `chat sessions` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `request.data.get`, `soft_delete_chat_sessions`, `ChatSession.objects.filter` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def chat_sessions(request):
    """
    Thuoc chuc nang nao: Liet ke hoac xoa mem session Chat AI co dien.
    Vai tro backend: `GET` tra danh sach session `SESSION_CHAT` cua user; `DELETE` goi `soft_delete_chat_sessions` de xoa mem nhieu session chat mot luc.
    Vai tro cua no trong frontend: Sidebar lich su Chat AI va thao tac xoa nhieu thread tren giao dien su dung endpoint nay.
    Moi lien he voi nhung ham / source khac: Truy van `ChatSession`, serialize bang `ChatSessionSerializer`, va dung `soft_delete_chat_sessions` de dong bo logic xoa mem voi assistant/RAG.
    Tac dung: Cung cap API quan ly session cho luong chat AI cu.
    """
    if request.method == 'DELETE':
        session_ids = request.data.get('session_ids')
        if not session_ids:
            return Response({'detail': 'Danh sach session_ids khong hop le.'}, status=status.HTTP_400_BAD_REQUEST)
        payload = soft_delete_chat_sessions(
            request.user,
            session_ids,
            actor=request.user,
            session_types=[ChatSession.SESSION_CHAT],
        )
        return Response(payload)

    sessions = ChatSession.objects.filter(user=request.user, company=get_user_company(request.user), session_type=ChatSession.SESSION_CHAT)
    return Response(ChatSessionSerializer(sessions, many=True).data)

# Là gì: `chat_session_messages` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `chat session messages` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `get_user_company`, `session.messages.order_by` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def chat_session_messages(request, session_id):
    """
    Thuoc chuc nang nao: Lay lich su message cua mot session Chat AI.
    Vai tro backend: Endpoint nay xac thuc session thuoc user hien tai, doc toan bo `messages` theo thu tu tao va tra ve cho client.
    Vai tro cua no trong frontend: Khi nguoi dung mo lai mot session Chat AI trong sidebar, frontend goi endpoint nay de do lai lich su hoi dap.
    Moi lien he voi nhung ham / source khac: Truy van `ChatSession` va `ChatMessage`, serialize bang `ChatMessageSerializer`.
    Tac dung: Cung cap endpoint phuc hoi lich su cho mot thread chat cu.
    """
    session = get_object_or_404(ChatSession, pk=session_id, user=request.user, company=get_user_company(request.user))
    msgs = session.messages.order_by('created_at')
    return Response(ChatMessageSerializer(msgs, many=True).data)

# Là gì: `rag_query_view` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `rag query view` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `request.data.get.strip`, `request.data.get`, `get_user_company` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; có side effect ghi cơ sở dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def rag_query_view(request):
    """
    Thuoc chuc nang nao: Endpoint hoi dap RAG theo nguon template hoac document.
    Vai tro backend: Endpoint nay nhan cau hoi, tim/tao session RAG, nap lich su message, goi `rag_query`, luu user/assistant message kem citations va tra session/message id cho client.
    Vai tro cua no trong frontend: Man RAG template/document goi endpoint nay de lay cau tra loi trich dan, cap nhat thread RAG va mo thang vao message vua tao.
    Moi lien he voi nhung ham / source khac: Goi `rag_query` trong `ai_engine.rag_engine`; luu `ChatSession` loai `SESSION_RAG` va `ChatMessage`.
    Tac dung: Dat luong hoi dap co trich dan vao mot endpoint rieng biet voi chat tong quat.
    """
    q = request.data.get('q', '').strip()
    if not q:
        return Response({'error': 'Vui lòng nhập câu hỏi.'}, status=status.HTTP_400_BAD_REQUEST)
    mode = request.data.get('mode', 'template')
    session_id = request.data.get('session_id')

    session = None
    company = get_user_company(request.user)
    if session_id:
        try:
            session = ChatSession.objects.get(
                pk=session_id,
                user=request.user,
                company=company,
                session_type=ChatSession.SESSION_RAG,
            )
        except ChatSession.DoesNotExist:
            pass
    if not session:
        session = ChatSession.objects.create(
            user=request.user, company=company, title=q[:60],
            session_type=ChatSession.SESSION_RAG, rag_mode=mode,
        )

    history = list(session.messages.order_by('created_at').values('role', 'content'))

    try:
        answer, citations = rag_query(q, request.user, mode=mode, history=history)
    except Exception as e:
        return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    ChatMessage.objects.create(session=session, role='user', content=q)
    assistant_message = ChatMessage.objects.create(
        session=session,
        role='assistant',
        content=answer,
        citations=citations or None,
    )
    session.save(update_fields=['updated_at'])

    return Response({
        'answer': answer,
        'citations': citations or [],
        'session_id': session.id,
        'message_id': assistant_message.id,
    })

# Là gì: `rag_sessions` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `rag sessions` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `request.data.get`, `strip`, `soft_delete_chat_sessions` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET', 'DELETE'])
@permission_classes([IsAuthenticated])
def rag_sessions(request):
    """
    Thuoc chuc nang nao: Liet ke hoac xoa mem cac session RAG.
    Vai tro backend: `GET` tra danh sach session RAG cua user, co the loc them theo `mode=template|document`; `DELETE` xoa mem cac session da chon va co the gioi han theo `rag_mode`.
    Vai tro cua no trong frontend: Sidebar/man lich su RAG dung endpoint nay de hien va xoa thread hoi dap co trich dan.
    Moi lien he voi nhung ham / source khac: Truy van `ChatSession` loai `SESSION_RAG`, serialize bang `ChatSessionSerializer`, dung `soft_delete_chat_sessions`.
    Tac dung: Quan ly lifecycle session cho man RAG.
    """
    if request.method == 'DELETE':
        session_ids = request.data.get('session_ids')
        if not session_ids:
            return Response({'detail': 'Danh sach session_ids khong hop le.'}, status=status.HTTP_400_BAD_REQUEST)
        mode = (request.data.get('mode') or '').strip()
        rag_mode = mode if mode in {'template', 'document'} else None
        payload = soft_delete_chat_sessions(
            request.user,
            session_ids,
            actor=request.user,
            session_types=[ChatSession.SESSION_RAG],
            rag_mode=rag_mode,
        )
        return Response(payload)

    mode = (request.GET.get('mode') or '').strip()
    sessions = ChatSession.objects.filter(
        user=request.user,
        company=get_user_company(request.user),
        session_type=ChatSession.SESSION_RAG,
    )
    if mode in {'template', 'document'}:
        sessions = sessions.filter(rag_mode=mode)
    sessions = sessions.order_by('-updated_at', '-created_at')
    return Response(ChatSessionSerializer(sessions, many=True).data)

# Là gì: `rag_session_messages` là endpoint REST của nhóm chat AI, hội thoại và phản hồi theo luồng; nó là điểm nhận request từ client đã đi qua router và lớp permission.
# Chức năng backend: Hàm xử lý phần việc `rag session messages` theo dữ liệu và ngữ cảnh được truyền vào; đầu vào được kiểm tra hoặc chuẩn hóa trước khi tạo kết quả.
# Vai trò với UI: Kết quả được giao diện ChatAI sử dụng trực tiếp để hiển thị dữ liệu, tải tệp hoặc cập nhật trạng thái thao tác.
# Mối liên hệ: Hàm phối hợp với `get_object_or_404`, `get_user_company`, `session.messages.order_by` và trả dữ liệu về cho lớp gọi kế tiếp trong cùng luồng.
# Bản chất và tác dụng: view mỏng ở biên HTTP; chủ yếu đọc, kiểm tra hoặc biến đổi dữ liệu; chuyển kết quả thành HTTP response.
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def rag_session_messages(request, session_id):
    """
    Thuoc chuc nang nao: Lay lich su message cua mot session RAG cu the.
    Vai tro backend: Endpoint nay chi cho phep doc session `SESSION_RAG` cua user hien tai, sau do tra message theo thu tu tao de tai lai thread hoi dap co trich dan.
    Vai tro cua no trong frontend: Khi frontend mo lai mot session RAG cu, endpoint nay cung cap toan bo lich su Q&A kem citation da duoc luu.
    Moi lien he voi nhung ham / source khac: Truy van `ChatSession` va `ChatMessage`, serialize bang `ChatMessageSerializer`.
    Tac dung: Phuc hoi thread hoi dap RAG cho giao dien.
    """
    session = get_object_or_404(
        ChatSession,
        pk=session_id,
        user=request.user,
        company=get_user_company(request.user),
        session_type=ChatSession.SESSION_RAG,
    )
    msgs = session.messages.order_by('created_at')
    return Response(ChatMessageSerializer(msgs, many=True).data)
