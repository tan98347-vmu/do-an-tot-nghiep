from word_ai.services.mcp_contract_service import (
    build_direct_addin_execution_payload,
    mcp_schema_version,
)


def native_word_schema_version():
    return mcp_schema_version()


def build_native_word_execution_payload(job, plan_payload):
    return build_direct_addin_execution_payload(job, plan_payload)
