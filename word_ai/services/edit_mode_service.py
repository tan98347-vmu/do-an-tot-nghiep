from django.conf import settings


DIRECT_EDIT_MODE = 'direct_edit'
DIRECT_ADDIN_MCP_MODE = 'direct_addin_mcp'

SUPPORTED_WORD_AI_EDIT_MODES = {
    DIRECT_EDIT_MODE,
    DIRECT_ADDIN_MCP_MODE,
}


def legacy_direct_edit_enabled():
    return False


def default_word_ai_edit_mode():
    raw_value = str(getattr(settings, 'WORD_AI_DEFAULT_EDIT_MODE', DIRECT_EDIT_MODE) or '').strip().lower()
    if raw_value in SUPPORTED_WORD_AI_EDIT_MODES:
        if raw_value == DIRECT_EDIT_MODE and not legacy_direct_edit_enabled():
            return DIRECT_ADDIN_MCP_MODE
        return raw_value
    return DIRECT_ADDIN_MCP_MODE


def normalize_word_ai_edit_mode(value):
    normalized = str(value or '').strip().lower()
    if not normalized:
        return default_word_ai_edit_mode()
    if normalized not in SUPPORTED_WORD_AI_EDIT_MODES:
        raise ValueError(f'Unsupported Word AI edit mode: {normalized}')
    if normalized == DIRECT_EDIT_MODE:
        raise ValueError('Unsupported Word AI edit mode: direct_edit has been removed from the production runtime.')
    return normalized


def is_direct_addin_mcp_mode(value):
    return normalize_word_ai_edit_mode(value) == DIRECT_ADDIN_MCP_MODE
