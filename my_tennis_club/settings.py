"""
Thuoc chuc nang nao: Cau hinh he thong cho toan bo backend Django va cac tich hop AI, signing, auth, media.
Vai tro backend: File nay dinh nghia app duoc nap, middleware, ket noi Postgres, JWT, CORS, social login, logging, duong dan media/static, cau hinh AI/OCR, cau hinh preview tai lieu va remote HSM cho ky so.
Vai tro cua no trong frontend: Frontend khong goi truc tiep file nay, nhung moi man dang nhap, dashboard, tro ly AI, danh sach tai lieu, preview PDF, ky so, thong bao va admin deu phu thuoc vao tham so backend duoc chot o day.
Moi lien he voi nhung ham / source khac: Duoc `asgi.py`, `wsgi.py` va `manage.py` nap khi khoi dong; route tong nam o `my_tennis_club.urls`; app runtime bao gom `accounts`, `ai_engine`, `document_templates`, `documents`, `signing`, `prompts`, `api`.
Tac dung: Dong vai tro nguon cau hinh trung tam de tat ca module backend cung van hanh tren mot bo quy tac va thong so thong nhat.
"""

from pathlib import Path
import json
import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

DEFAULT_ALLOWED_HOSTS = [
    'localhost',
    '127.0.0.1',
    'host.docker.internal',
    '.ngrok-free.app',
    '.ngrok-free.dev',
]

DEFAULT_CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://host.docker.internal',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
    'http://host.docker.internal:8000',
    'http://host.docker.internal:8888',
    'https://*.ngrok-free.app',
    'https://*.ngrok-free.dev',
]

DEFAULT_CORS_ALLOWED_ORIGINS = [
    'http://localhost:3000',
    'http://localhost:8080',
    'http://127.0.0.1:8080',
]

def _env_csv_list(name, default=()):
    """
    Thuoc chuc nang nao: Doc cau hinh ENV dang chuoi CSV cho cac tham so allowlist.
    Vai tro backend: Ham nay lay gia tri tu bien moi truong, tach theo dau phay, loai bo khoang trang va hop nhat voi gia tri mac dinh de host/origin quan trong khong bi bo sot khi deploy qua Nginx hay ngrok.
    Vai tro cua no trong frontend: Frontend web huong loi gian tiep vi same-origin login, refresh token, admin va media van duoc backend chap nhan tren cac host public da chot.
    Moi lien he voi nhung ham / source khac: Duoc dung cho `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` va `CORS_ALLOWED_ORIGINS`; bo sung cho cac helper doc JSON ben duoi.
    Tac dung: Chuyen allowlist tu ENV thanh danh sach on dinh, khong con phai hardcode `*` trong source.
    """
    raw = (os.getenv(name, '') or '').strip()
    extra_values = [item.strip() for item in raw.split(',') if item.strip()]
    merged_values = []
    for item in [*default, *extra_values]:
        if item and item not in merged_values:
            merged_values.append(item)
    return merged_values

def _env_json_list(name):
    """
    Thuoc chuc nang nao: Doc cau hinh JSON tu bien moi truong cho cac tham so dang danh sach.
    Vai tro backend: Ham nay lay gia tri ENV, parse JSON va chi chap nhan ket qua kieu list; neu bien rong hoac parse loi thi tra ve danh sach rong de backend khoi dong an toan.
    Vai tro cua no trong frontend: Frontend huong loi gian tiep vi cac tinh nang nhu trusted certificate PEM list hay danh sach thong so mo rong luon co gia tri backend hop le thay vi lam API loi luc khoi dong.
    Moi lien he voi nhung ham / source khac: Duoc goi o cuoi file de nap `SIGNING_PKI_TRUSTED_CA_PEMS` va `SIGNING_PKI_INTERMEDIATE_CA_PEMS`; dong cap voi `_env_json_dict` de xu ly cac bien ENV dang JSON.
    Tac dung: Chuan hoa du lieu list tu moi truong thanh dau vao an toan cho cau hinh he thong.
    """
    raw = (os.getenv(name, '') or '').strip()
    if not raw:
        return []
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return [raw]
    return value if isinstance(value, list) else []

def _env_json_dict(name):
    """
    Thuoc chuc nang nao: Doc cau hinh JSON tu bien moi truong cho cac tham so dang dictionary.
    Vai tro backend: Ham nay parse mot bien ENV duoc ky vong la object JSON va chi tra ve ket qua khi dung kieu dict, tu do cau hinh nhu header bo sung cho remote HSM khong lam vo backend khi du lieu xau.
    Vai tro cua no trong frontend: Frontend phu thuoc gian tiep vao cac tich hop signing/AI duoc cau hinh dung; ham nay giup API ky so van tra loi on dinh ngay ca khi bien moi truong bi thieu hoac sai dinh dang.
    Moi lien he voi nhung ham / source khac: Duoc dung de nap `SIGNING_REMOTE_HSM['extra_headers']`; bo sung cho `_env_json_list` trong nhom helper doc cau hinh JSON.
    Tac dung: Chan cau hinh dict loi truoc khi no anh huong den cac service backend quan trong.
    """
    raw = (os.getenv(name, '') or '').strip()
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}

SECRET_KEY = os.getenv('SECRET_KEY', 'django-insecure-by1dy$5b6f#m4fk9gq5^#!t(hjwy4h3*me!^f66l*dq1j6o0wf')

DEBUG = os.getenv('DEBUG', 'True') == 'True'
LLM_DETECT_TRACE = os.getenv('LLM_DETECT_TRACE', 'True') == 'True'

ALLOWED_HOSTS = _env_csv_list('ALLOWED_HOSTS', DEFAULT_ALLOWED_HOSTS)

CSRF_TRUSTED_ORIGINS = _env_csv_list(
    'CSRF_TRUSTED_ORIGINS',
    DEFAULT_CSRF_TRUSTED_ORIGINS,
)

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.postgres',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'accounts',
    'ai_engine',
    'document_templates.runtime_app.DocumentTemplatesRuntimeConfig',
    'documents',
    'signing',
    'prompts',
    'company_backups',
    'ai_tasks',
    'word_ai',
    'sharing',
    'my_tennis_club',
    'rest_framework',
    'corsheaders',
    'api',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'my_tennis_club.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'my_tennis_club.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'tennis_club_db'),
        'USER': os.getenv('DB_USER', 'postgres'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'localhost'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'vi'
TIME_ZONE = 'Asia/Ho_Chi_Minh'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATICFILES_DIRS = [BASE_DIR / 'static'] if (BASE_DIR / 'static').exists() else []
STATIC_ROOT = BASE_DIR / 'staticfiles'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

EXTRA_AI_MODELS = [
    'kimi-k2.6:cloud',
]

TESSERACT_CMD = os.getenv('TESSERACT_CMD', r'C:\Program Files\Tesseract-OCR\tesseract.exe')

OLLAMA_BASE_URL = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
DEFAULT_AI_MODEL = os.getenv('DEFAULT_AI_MODEL', 'kimi-k2.6:cloud')
DEFAULT_EMBEDDING_MODEL = os.getenv('DEFAULT_EMBEDDING_MODEL', 'mxbai-embed-large')
AI_REQUEST_TIMEOUT_SECONDS = max(
    int(os.getenv('AI_REQUEST_TIMEOUT_SECONDS', '1200') or '1200'),
    1200,
)
OCR_MODEL = os.getenv('OCR_MODEL', 'qwen3-vl:4b')
IMAGE_OCR_MODEL = os.getenv('IMAGE_OCR_MODEL', 'qwen3-vl:235b-cloud')
OCR_TIMEOUT_SECONDS = max(
    int(os.getenv('OCR_TIMEOUT_SECONDS', str(AI_REQUEST_TIMEOUT_SECONDS)) or str(AI_REQUEST_TIMEOUT_SECONDS)),
    AI_REQUEST_TIMEOUT_SECONDS,
)
LIBREOFFICE_BIN = os.getenv('LIBREOFFICE_BIN', 'soffice')
DOC_PREVIEW_TIMEOUT_SECONDS = max(
    int(os.getenv('DOC_PREVIEW_TIMEOUT_SECONDS', '45') or '45'),
    10,
)
WORD_AI_PROMPT_VERSION = os.getenv('WORD_AI_PROMPT_VERSION', 'word-ai-v1')
WORD_AI_DEFAULT_EDIT_MODE = os.getenv('WORD_AI_DEFAULT_EDIT_MODE', 'direct_addin_mcp')
WORD_AI_MCP_SCHEMA_VERSION = os.getenv('WORD_AI_MCP_SCHEMA_VERSION', 'word-ai-mcp-v1')
WORD_AI_LOCAL_AGENT_TOKEN = os.getenv('WORD_AI_LOCAL_AGENT_TOKEN', '')
WORD_AI_MAX_WORKER_SLOTS = max(int(os.getenv('WORD_AI_MAX_WORKER_SLOTS', '2') or '2'), 1)
WORD_AI_ENABLED_WORKER_SLOTS = min(
    max(int(os.getenv('WORD_AI_ENABLED_WORKER_SLOTS', '1') or '1'), 1),
    WORD_AI_MAX_WORKER_SLOTS,
)
WORD_AI_WORD_IDLE_CLOSE_SECONDS = max(int(os.getenv('WORD_AI_WORD_IDLE_CLOSE_SECONDS', '180') or '180'), 30)
WORD_AI_PAUSE_ALL_FREE_RAM_MB_LT = max(int(os.getenv('WORD_AI_PAUSE_ALL_FREE_RAM_MB_LT', '2000') or '2000'), 512)
WORD_AI_PAUSE_SLOT2_FREE_RAM_MB_LT = max(int(os.getenv('WORD_AI_PAUSE_SLOT2_FREE_RAM_MB_LT', '3500') or '3500'), 1024)
WORD_AI_MCP_AGENT_MAX_STEPS = max(int(os.getenv('WORD_AI_MCP_AGENT_MAX_STEPS', '12') or '12'), 4)
WORD_AI_ALLOWED_FORMAT_OPS = [
    item.strip()
    for item in (
        os.getenv(
            'WORD_AI_ALLOWED_FORMAT_OPS',
            'set_alignment,set_spacing,set_heading_style,set_font_name,set_font_size,set_font_color,set_bold,set_italic,set_table_style',
        ) or ''
    ).split(',')
    if item.strip()
]
WORD_AI_ALLOWED_MACRO_CAPABILITIES = [
    item.strip()
    for item in (
        os.getenv(
            'WORD_AI_ALLOWED_MACRO_CAPABILITIES',
            'replace_in_headers,replace_in_footers,set_track_revisions,replace_in_tables',
        ) or ''
    ).split(',')
    if item.strip()
]

MANUAL_EDIT_PROVIDER = os.getenv('MANUAL_EDIT_PROVIDER', 'collabora')
COLLABORA_BASE_URL = os.getenv('COLLABORA_BASE_URL', '')
COLLABORA_PUBLIC_URL = os.getenv('COLLABORA_PUBLIC_URL', COLLABORA_BASE_URL)
COLLABORA_EDITOR_PATH = os.getenv('COLLABORA_EDITOR_PATH', '/browser/dist/cool.html')
COLLABORA_WOPI_SECRET = os.getenv('COLLABORA_WOPI_SECRET', '')
COLLABORA_ALLOWED_ORIGINS = _env_csv_list('COLLABORA_ALLOWED_ORIGINS', ())
MANUAL_EDIT_WOPI_SRC_BASE_URL = os.getenv('MANUAL_EDIT_WOPI_SRC_BASE_URL', '')
MANUAL_EDIT_SESSION_TTL_SECONDS = max(int(os.getenv('MANUAL_EDIT_SESSION_TTL_SECONDS', '3600') or '3600'), 300)

SIGNING_DEFAULT_SIGNATURE_MODE = os.getenv('SIGNING_DEFAULT_SIGNATURE_MODE', 'pdf_pkcs7')
SIGNING_REMOTE_HSM = {
    'base_url': os.getenv('SIGNING_REMOTE_HSM_BASE_URL', ''),
    'healthcheck_url': os.getenv('SIGNING_REMOTE_HSM_HEALTHCHECK_URL', ''),
    'sign_url': os.getenv('SIGNING_REMOTE_HSM_SIGN_URL', ''),
    'api_key': os.getenv('SIGNING_REMOTE_HSM_API_KEY', ''),
    'timeout_seconds': float(os.getenv('SIGNING_REMOTE_HSM_TIMEOUT_SECONDS', '15') or '15'),
    'verify_ssl': os.getenv('SIGNING_REMOTE_HSM_VERIFY_SSL', 'True') == 'True',
}
SIGNING_REMOTE_HSM['extra_headers'] = _env_json_dict('SIGNING_REMOTE_HSM_EXTRA_HEADERS_JSON')

SIGNING_PKI_TRUSTED_CA_FILES = [item for item in os.getenv('SIGNING_PKI_TRUSTED_CA_FILES', '').split(os.pathsep) if item]
SIGNING_PKI_INTERMEDIATE_CA_FILES = [item for item in os.getenv('SIGNING_PKI_INTERMEDIATE_CA_FILES', '').split(os.pathsep) if item]
SIGNING_PKI_TRUSTED_CA_PEMS = _env_json_list('SIGNING_PKI_TRUSTED_CA_PEMS_JSON')
SIGNING_PKI_INTERMEDIATE_CA_PEMS = _env_json_list('SIGNING_PKI_INTERMEDIATE_CA_PEMS_JSON')

PGVECTOR_CONNECTION_STRING = (
    f"postgresql+psycopg2://{os.getenv('DB_USER', 'postgres')}:"
    f"{os.getenv('DB_PASSWORD', '')}@{os.getenv('DB_HOST', 'localhost')}:"
    f"{os.getenv('DB_PORT', '5432')}/{os.getenv('DB_NAME', 'tennis_club_db')}"
)

USE_X_FORWARDED_HOST  = True
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

from datetime import timedelta

CORS_ALLOWED_ORIGINS = _env_csv_list(
    'CORS_ALLOWED_ORIGINS',
    DEFAULT_CORS_ALLOWED_ORIGINS,
)
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_ALL_ORIGINS = False

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    'DEFAULT_RENDERER_CLASSES': [
        'rest_framework.renderers.JSONRenderer',
    ],
}

SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=12),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'AUTH_HEADER_TYPES': ('Bearer',),
    'UPDATE_LAST_LOGIN': True,
}

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
            'formatter': 'verbose',
        },
    },
    'formatters': {
        'verbose': {
            'format': '[{levelname}] {name}: {message}',
            'style': '{',
        },
    },
    'loggers': {
        'ai_engine': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'documents.preview_pdf': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'signing': {
            'handlers': ['console'],
            'level': 'DEBUG',
            'propagate': False,
        },
        'company_backups': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
        'api.views.company_backups': {
            'handlers': ['console'],
            'level': 'INFO',
            'propagate': False,
        },
    },
}
AUTHENTICATION_BACKENDS = [
    "accounts.auth_backends.EmployeeCodeOrUsernameBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# === BEGIN R5: backup encryption ===
import base64 as _r5_base64

_BACKUP_KEY_RAW = (os.getenv('BACKUP_ENCRYPTION_MASTER_KEY', '') or '').strip()
try:
    BACKUP_ENCRYPTION_MASTER_KEY = _r5_base64.b64decode(_BACKUP_KEY_RAW) if _BACKUP_KEY_RAW else None
except Exception:
    BACKUP_ENCRYPTION_MASTER_KEY = None
BACKUP_ENCRYPTION_REQUIRED = os.getenv('BACKUP_ENCRYPTION_REQUIRED', 'False').lower() in ('1', 'true', 'yes')

if BACKUP_ENCRYPTION_REQUIRED:
    if BACKUP_ENCRYPTION_MASTER_KEY is None:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'BACKUP_ENCRYPTION_REQUIRED=True nhung thieu BACKUP_ENCRYPTION_MASTER_KEY trong ENV. '
            'Sinh key bang: python -c "import os,base64;print(base64.b64encode(os.urandom(32)).decode())"'
        )
    if len(BACKUP_ENCRYPTION_MASTER_KEY) != 32:
        from django.core.exceptions import ImproperlyConfigured
        raise ImproperlyConfigured(
            'BACKUP_ENCRYPTION_MASTER_KEY phai la base64 cua dung 32 bytes (256-bit AES key).'
        )

_BACKUP_SIGNER_PRIVATE_KEY_PATH = (os.getenv('BACKUP_SIGNER_PRIVATE_KEY_PATH', '') or '').strip()
BACKUP_SIGNER_PRIVATE_KEY_PEM = None
if _BACKUP_SIGNER_PRIVATE_KEY_PATH:
    try:
        BACKUP_SIGNER_PRIVATE_KEY_PEM = Path(_BACKUP_SIGNER_PRIVATE_KEY_PATH).read_bytes()
    except OSError:
        BACKUP_SIGNER_PRIVATE_KEY_PEM = None

_BACKUP_SIGNER_PUBLIC_KEY_PATH = (os.getenv('BACKUP_SIGNER_PUBLIC_KEY_PATH', '') or '').strip()
BACKUP_SIGNER_PUBLIC_KEY_PEM = None
if _BACKUP_SIGNER_PUBLIC_KEY_PATH:
    try:
        BACKUP_SIGNER_PUBLIC_KEY_PEM = Path(_BACKUP_SIGNER_PUBLIC_KEY_PATH).read_bytes()
    except OSError:
        BACKUP_SIGNER_PUBLIC_KEY_PEM = None
# === END R5 ===
