from django.conf import settings

from accounts.tenancy import resolve_ai_config


def current_llm_snapshot(*, user=None):
    config = resolve_ai_config(user=user)
    return {
        'llm_model_name': config.ai_model,
        'llm_temperature': config.ai_temperature,
        'ollama_base_url': settings.OLLAMA_BASE_URL,
        'prompt_version': getattr(settings, 'WORD_AI_PROMPT_VERSION', 'word-ai-v1'),
        'allow_cloud_model': True,
    }


def allowed_format_ops():
    return list(getattr(settings, 'WORD_AI_ALLOWED_FORMAT_OPS', []))


def allowed_macro_capabilities():
    return list(getattr(settings, 'WORD_AI_ALLOWED_MACRO_CAPABILITIES', []))


def mcp_agent_max_steps():
    return int(getattr(settings, 'WORD_AI_MCP_AGENT_MAX_STEPS', 12))


def worker_token():
    return getattr(settings, 'WORD_AI_LOCAL_AGENT_TOKEN', '')
