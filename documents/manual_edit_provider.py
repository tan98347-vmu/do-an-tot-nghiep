import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlsplit
from urllib.request import Request, urlopen

from django.conf import settings
from django.urls import reverse
from django.utils import timezone


# class ManualEditProviderStatus (dataclass) là trạng thái sẵn sàng của provider sửa thủ công (Collabora): tên provider, is_ready, mã lỗi và chi tiết.
# vd: Collabora chưa cấu hình -> is_ready=False, code='collabora_public_url_missing'.
@dataclass(frozen=True)
class ManualEditProviderStatus:
    provider: str
    is_ready: bool
    code: str = ''
    detail: str = ''


# def manual_edit_provider_name trả tên provider trình soạn (mặc định 'collabora') từ settings.
# vd: -> 'collabora'.
def manual_edit_provider_name():
    return str(getattr(settings, 'MANUAL_EDIT_PROVIDER', 'collabora') or 'collabora').strip().lower()


# def get_manual_edit_provider_status kiểm tra provider có sẵn sàng không: đúng loại + có COLLABORA_PUBLIC_URL + (nếu cần) healthcheck OK; trả ManualEditProviderStatus.
# vd: Collabora đang chạy -> is_ready=True.
def get_manual_edit_provider_status():
    provider = manual_edit_provider_name()
    if provider != 'collabora':
        return ManualEditProviderStatus(
            provider=provider,
            is_ready=False,
            code='unsupported_provider',
            detail=f'Manual edit provider "{provider}" is not supported.',
        )
    public_url = str(getattr(settings, 'COLLABORA_PUBLIC_URL', '') or '').strip()
    if not public_url:
        return ManualEditProviderStatus(
            provider=provider,
            is_ready=False,
            code='collabora_public_url_missing',
            detail='COLLABORA_PUBLIC_URL is not configured.',
        )
    health_error = _check_collabora_runtime_health()
    if health_error:
        return ManualEditProviderStatus(
            provider=provider,
            is_ready=False,
            code='collabora_runtime_unreachable',
            detail=health_error,
        )
    return ManualEditProviderStatus(
        provider=provider,
        is_ready=True,
        code='ready',
        detail='Collabora manual edit provider is ready.',
    )


# def manual_edit_provider_is_configured trả True nếu provider đã sẵn sàng để dùng.
# vd: -> True khi Collabora đã cấu hình + chạy.
def manual_edit_provider_is_configured():
    return get_manual_edit_provider_status().is_ready


# def _collabora_public_url đọc COLLABORA_PUBLIC_URL từ settings (đã trim).
# vd: -> 'http://127.0.0.1:8888'.
def _collabora_public_url():
    return str(getattr(settings, 'COLLABORA_PUBLIC_URL', '') or '').strip()


# def _collabora_public_hostname trả hostname của COLLABORA_PUBLIC_URL (chữ thường).
# vd: -> '127.0.0.1'.
def _collabora_public_hostname():
    return (urlsplit(_collabora_public_url()).hostname or '').strip().lower()


# def _is_loopback_collabora_public_url cho biết Collabora có đang trỏ localhost/127.0.0.1 không.
# vd: host='localhost' -> True.
def _is_loopback_collabora_public_url():
    return _collabora_public_hostname() in {'127.0.0.1', 'localhost'}


# def _is_ngrok_public_url cho biết URL có phải domain ngrok không.
# vd: '...ngrok-free.app' -> True.
def _is_ngrok_public_url():
    host = _collabora_public_hostname()
    return host.endswith('.ngrok-free.app') or host.endswith('.ngrok-free.dev')


# def _manual_edit_local_proxy_port suy ra cổng proxy nội bộ (từ URL hoặc env, mặc định 8888).
# vd: -> 8888.
def _manual_edit_local_proxy_port():
    public_url = _collabora_public_url()
    parsed = urlsplit(public_url)
    if parsed.port:
        return parsed.port
    raw_port = (os.getenv('MANUAL_EDIT_LOCAL_PROXY_PORT', '') or '').strip()
    if raw_port:
        try:
            port = int(raw_port)
            if 1 <= port <= 65535:
                return port
        except ValueError:
            pass
    return 8888


# def _derive_local_windows_wopi_src_base_url khi chạy Windows + Collabora loopback/ngrok -> dùng host.docker.internal:<port> làm base URL WOPI để container Collabora gọi ngược về host.
# vd: -> 'http://host.docker.internal:8888'.
def _derive_local_windows_wopi_src_base_url():
    if os.name != 'nt':
        return ''
    public_url = _collabora_public_url()
    if not public_url:
        return ''
    if not (_is_loopback_collabora_public_url() or _is_ngrok_public_url()):
        return ''
    return f'http://host.docker.internal:{_manual_edit_local_proxy_port()}'


# def _collabora_healthcheck_url dựng URL healthcheck (/hosting/discovery) của Collabora.
# vd: -> '<public_url>/hosting/discovery'.
def _collabora_healthcheck_url():
    public_url = _collabora_public_url().rstrip('/')
    if not public_url:
        return ''
    return f'{public_url}/hosting/discovery'


# def _should_check_collabora_runtime_health quyết định có cần kiểm tra Collabora còn sống không (mặc định kiểm khi chạy localhost, hoặc theo cờ COLLABORA_REQUIRE_HEALTHCHECK).
# vd: host localhost -> có kiểm tra health.
def _should_check_collabora_runtime_health():
    public_url = _collabora_public_url()
    if not public_url:
        return False
    host = (urlsplit(public_url).hostname or '').strip().lower()
    explicit = (getattr(settings, 'COLLABORA_REQUIRE_HEALTHCHECK', '') or '').strip().lower()
    if explicit in {'1', 'true', 'yes', 'on'}:
        return True
    if explicit in {'0', 'false', 'no', 'off'}:
        return False
    return host in {'127.0.0.1', 'localhost'}


# def _check_collabora_runtime_health gọi healthcheck Collabora; trả None nếu OK, ngược lại trả chuỗi mô tả lỗi (không kết nối được / HTTP lỗi).
# vd: Collabora chết -> 'Collabora editor is unreachable: ...'.
def _check_collabora_runtime_health():
    if not _should_check_collabora_runtime_health():
        return None
    healthcheck_url = _collabora_healthcheck_url()
    if not healthcheck_url:
        return 'COLLABORA_PUBLIC_URL is not configured.'
    request = Request(
        healthcheck_url,
        headers={'User-Agent': 'manual-edit-provider-check'},
        method='GET',
    )
    timeout_seconds = max(
        float(getattr(settings, 'COLLABORA_HEALTHCHECK_TIMEOUT_SECONDS', 1.5) or 1.5),
        0.5,
    )
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            status_code = getattr(response, 'status', 200)
            if 200 <= status_code < 400:
                return None
            return f'Collabora healthcheck returned HTTP {status_code}.'
    except HTTPError as exc:
        return f'Collabora healthcheck returned HTTP {exc.code}.'
    except (URLError, OSError) as exc:
        return f'Collabora editor is unreachable: {exc}'


# def manual_edit_postmessage_origin trả origin để Collabora postMessage về frame cha: dùng MANUAL_EDIT_POSTMESSAGE_ORIGIN nếu có, mặc định '*' (request WOPI là server-to-server nên không suy được origin trình duyệt từ đây).
# vd: chưa cấu hình -> '*'.
def manual_edit_postmessage_origin(request=None):
    """Origin ma Collabora dung lam targetOrigin khi postMessage ve frame cha.

    Collabora CHI gui cac message `App_LoadingStatus` / `Action_Save_Resp` ve host
    khi CheckFileInfo tra ve `PostMessageOrigin`. Thieu/sai field nay thi host
    (Flutter web) khong bao gio nhan duoc handshake -> bam "Luu & hoan tat" se bao
    "Trinh sua web chua san sang de nhan lenh luu".

    QUAN TRONG: request WOPI CheckFileInfo den tu SERVER Collabora (server-to-server),
    KHONG phai trinh duyet. Vi vay KHONG the suy ra origin cua trang nhung iframe tu
    header cua request nay - lam vay se ra origin noi bo (host.docker.internal /
    loopback / domain backend) khac voi origin that cua trinh duyet, khien Collabora
    postMessage sai dich -> handshake that bai.

    Vi vay mac dinh tra `*` (postMessage giao toi MOI parent origin -> luon toi noi).
    Dieu nay an toan vi host da xac thuc message theo iframe `event.source` chu khong
    dua vao chuoi origin. Chi pin origin cu the khi admin co tinh dat
    `MANUAL_EDIT_POSTMESSAGE_ORIGIN` (vd 'https://aiagentvmu.id.vn').
    """
    explicit = str(getattr(settings, 'MANUAL_EDIT_POSTMESSAGE_ORIGIN', '') or '').strip()
    if explicit:
        return explicit.rstrip('/')
    return '*'


# def browser_origin_from_request lấy origin THẬT của trình duyệt từ request (ưu tiên header Origin, rồi Referer) — dùng khi tạo phiên (request đến từ browser) để Collabora postMessage đúng đích.
# vd: Origin='https://app.vn' -> 'https://app.vn'.
def browser_origin_from_request(request):
    """Lay origin THAT cua trinh duyet tu request (chi dung khi request den TU trinh
    duyet, vd luc tao phien manual edit). Uu tien header `Origin`, sau do `Referer`.

    Khac voi manual_edit_postmessage_origin(): ham nay dung cho request browser->Django
    (co Origin/Referer), con CheckFileInfo la Collabora->Django (khong co).
    """
    if request is None:
        return ''
    origin = (request.META.get('HTTP_ORIGIN', '') or '').strip()
    if origin and origin.lower() != 'null':
        return origin.rstrip('/')
    referer = (request.META.get('HTTP_REFERER', '') or '').strip()
    if referer:
        parsed = urlsplit(referer)
        if parsed.scheme and parsed.netloc:
            return f'{parsed.scheme}://{parsed.netloc}'
    return ''


# def build_manual_edit_wopi_src dựng WOPISrc (URL endpoint WOPI) cho Collabora gọi vào: ưu tiên MANUAL_EDIT_WOPI_SRC_BASE_URL, rồi host.docker.internal (Windows), rồi forwarded host, cuối cùng URL tuyệt đối từ request.
# vd: -> 'http://host.docker.internal:8888/api/.../wopi/files/<id>'.
def build_manual_edit_wopi_src(
    session,
    request,
    *,
    wopi_route_name='api:document_manual_edit_wopi_file',
):
    wopi_path = reverse(wopi_route_name, args=[session.wopi_file_id]).rstrip('/')
    public_base_url = str(getattr(settings, 'MANUAL_EDIT_WOPI_SRC_BASE_URL', '') or '').strip().rstrip('/')
    if public_base_url:
        return f'{public_base_url}{wopi_path}'
    local_windows_base_url = _derive_local_windows_wopi_src_base_url()
    if local_windows_base_url:
        return f'{local_windows_base_url}{wopi_path}'
    forwarded_host = (request.META.get('HTTP_X_FORWARDED_HOST', '') or '').strip()
    if forwarded_host:
        forwarded_proto = (request.META.get('HTTP_X_FORWARDED_PROTO', '') or '').strip() or request.scheme
        return f'{forwarded_proto}://{forwarded_host}{wopi_path}'
    return request.build_absolute_uri(wopi_path).rstrip('/')


# def build_manual_edit_editor_url dựng URL nhúng editor Collabora (cool.html) kèm WOPISrc + access_token + ttl; trả None nếu provider chưa sẵn sàng.
# vd: -> '<collabora>/browser/dist/cool.html?WOPISrc=...&access_token=...'.
def build_manual_edit_editor_url(
    session,
    request,
    *,
    wopi_route_name='api:document_manual_edit_wopi_file',
):
    provider_status = get_manual_edit_provider_status()
    if not provider_status.is_ready:
        return None
    public_url = str(settings.COLLABORA_PUBLIC_URL or '').rstrip('/')
    editor_path = str(getattr(settings, 'COLLABORA_EDITOR_PATH', '/browser/dist/cool.html') or '/browser/dist/cool.html')
    if not editor_path.startswith('/'):
        editor_path = f'/{editor_path}'
    wopi_src = build_manual_edit_wopi_src(
        session,
        request,
        wopi_route_name=wopi_route_name,
    )
    ttl_ms = max(int((session.expires_at - timezone.now()).total_seconds() * 1000), 0)
    return (
        f'{public_url}{editor_path}'
        f'?WOPISrc={quote(wopi_src, safe="")}'
        f'&access_token={quote(session.access_token, safe="")}'
        f'&access_token_ttl={ttl_ms}'
    )
