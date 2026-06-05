TOOL_SPECS = {
    'inspect_document': {
        'family': 'inspect',
        'description': 'Read whole-document metadata and text summary from Word.',
    },
    'inspect_selection': {
        'family': 'inspect',
        'description': 'Read the current Word selection state and text excerpt.',
    },
    'inspect_text_matches': {
        'family': 'inspect',
        'description': 'Count target and replacement text matches in the current document.',
    },
    'inspect_format_state': {
        'family': 'inspect',
        'description': 'Read font and paragraph formatting state from the document or current selection.',
    },
    'replace_text_matches': {
        'family': 'mutate_text',
        'description': 'Replace exact target text occurrences in the current document by removing the matched text and inserting the requested replacement text in the same place, while preserving existing formatting unless the user explicitly asks for a formatting change.',
        'verify_pair': 'verify_text_replacement',
    },
    'replace_selection_text': {
        'family': 'mutate_text',
        'description': 'Replace the current selection text only.',
        'verify_pair': 'verify_selection_text',
    },
    'normalize_case_whole_document': {
        'family': 'mutate_text',
        'description': 'Normalize the whole document text case.',
        'verify_pair': 'verify_document_case',
    },
    'normalize_case_selection': {
        'family': 'mutate_text',
        'description': 'Normalize the current selection text case.',
        'verify_pair': 'verify_selection_case',
    },
    'apply_format_whole_document': {
        'family': 'mutate_format',
        'description': 'Apply font formatting to the whole document.',
        'verify_pair': 'verify_document_format_coverage',
    },
    'apply_format_selection': {
        'family': 'mutate_format',
        'description': 'Apply font formatting to the current selection.',
        'verify_pair': 'verify_selection_format',
    },
    'clear_format_selection': {
        'family': 'mutate_format',
        'description': 'Clear direct formatting from the current selection.',
        'verify_pair': 'verify_selection_format',
    },
    'set_paragraph_alignment': {
        'family': 'mutate_layout',
        'description': 'Set paragraph alignment for the current selection paragraphs.',
        'verify_pair': 'verify_selection_format',
    },
    'set_line_spacing': {
        'family': 'mutate_layout',
        'description': 'Set paragraph line spacing for the current selection paragraphs.',
        'verify_pair': 'verify_selection_format',
    },
    'set_paragraph_spacing': {
        'family': 'mutate_layout',
        'description': 'Set paragraph spacing before and after for the current selection paragraphs.',
        'verify_pair': 'verify_selection_format',
    },
    'toggle_track_changes': {
        'family': 'review',
        'description': 'Enable or disable Track Changes in the active document.',
        'verify_pair': 'verify_track_changes_state',
    },
    'replace_in_headers': {
        'family': 'review',
        'description': 'Replace matching text inside Word headers.',
        'verify_pair': 'verify_header_replacement',
    },
    'replace_in_footers': {
        'family': 'review',
        'description': 'Replace matching text inside Word footers.',
        'verify_pair': 'verify_footer_replacement',
    },
    'replace_in_tables': {
        'family': 'review',
        'description': 'Replace matching text inside Word table cells.',
        'verify_pair': 'verify_table_replacement',
    },
    'insert_comment_selection': {
        'family': 'review',
        'description': 'Insert a review comment on the current selection.',
        'verify_pair': 'verify_comment_selection',
    },
    'verify_text_replacement': {
        'family': 'verify',
        'description': 'Verify that the requested target text was removed and the exact replacement text was inserted in the same document locations.',
    },
    'verify_document_case': {
        'family': 'verify',
        'description': 'Verify whole-document text case coverage.',
    },
    'verify_document_format_coverage': {
        'family': 'verify',
        'description': 'Verify whole-document format coverage.',
    },
    'verify_selection_text': {
        'family': 'verify',
        'description': 'Verify that the current selection text matches the expected value.',
    },
    'verify_selection_case': {
        'family': 'verify',
        'description': 'Verify case coverage inside the current selection only.',
    },
    'verify_selection_format': {
        'family': 'verify',
        'description': 'Verify formatting and layout state for the current selection.',
    },
    'verify_track_changes_state': {
        'family': 'verify',
        'description': 'Verify that Track Changes matches the expected state.',
    },
    'verify_header_replacement': {
        'family': 'verify',
        'description': 'Verify header replacement coverage inside Word headers only.',
    },
    'verify_footer_replacement': {
        'family': 'verify',
        'description': 'Verify footer replacement coverage inside Word footers only.',
    },
    'verify_table_replacement': {
        'family': 'verify',
        'description': 'Verify replacement coverage inside Word tables only.',
    },
    'verify_comment_selection': {
        'family': 'verify',
        'description': 'Verify that a comment exists on the current selection.',
    },
    'verify_export_artifact': {
        'family': 'verify',
        'description': 'Verify that the exported DOCX artifact exists and matches the expected checksum inputs.',
    },
    'export_document': {
        'family': 'export',
        'description': 'Save and export the active document for backend version commit.',
    },
}


LEGACY_CAPABILITY_TOOL_NAMES = {
    'replace_in_headers',
    'replace_in_footers',
    'replace_in_tables',
}


MUTATION_TOOL_NAMES = {
    tool_name
    for tool_name, spec in TOOL_SPECS.items()
    if spec['family'].startswith('mutate')
} | {'toggle_track_changes', 'replace_in_headers', 'replace_in_footers', 'replace_in_tables', 'insert_comment_selection'}


VERIFY_TOOL_NAMES = {
    tool_name
    for tool_name, spec in TOOL_SPECS.items()
    if spec['family'] == 'verify'
}


def allowed_native_word_tools():
    return list(TOOL_SPECS.keys())


def tool_prompt_specs():
    return {
        name: {
            'family': spec['family'],
            'description': spec['description'],
            'verify_pair': spec.get('verify_pair', ''),
        }
        for name, spec in TOOL_SPECS.items()
    }


def is_mutation_tool(tool_name):
    return str(tool_name or '').strip() in MUTATION_TOOL_NAMES


def is_verify_tool(tool_name):
    return str(tool_name or '').strip() in VERIFY_TOOL_NAMES


def verify_pair_for_tool(tool_name):
    spec = TOOL_SPECS.get(str(tool_name or '').strip(), {})
    return str(spec.get('verify_pair') or '').strip()
