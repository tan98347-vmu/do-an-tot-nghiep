from word_ai.services.mcp_agent_loop_service import advance_mcp_agent


def advance_word_tool_loop(*, job, tool_transcript, latest_command, session_snapshot):
    return advance_mcp_agent(
        job=job,
        tool_transcript=tool_transcript,
        latest_command=latest_command,
        session_snapshot=session_snapshot,
    )
