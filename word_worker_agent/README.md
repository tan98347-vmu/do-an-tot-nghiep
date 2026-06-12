# Word Worker Agent

This package is the direct-host native Word runtime for Word AI.

## Responsibilities
- poll backend worker endpoints
- keep slot state and host guardrails
- open the claimed DOCX in Word
- call typed native Word procedures through `Application.Run`
- collect structured tool results and verification evidence
- upload the exported DOCX back to Django

## Current scope
- configuration loader with required worker token
- slot state and failure policy
- backend client for claim, heartbeat, advance, complete, and fail
- native Word tool bridge
- macro bridge for deeper whitelisted capabilities
- workspace isolation and structured logging
- slot runner with hard verify gating before success

## No longer in scope
- Office.js task-pane runtime
- local HTTP control server
- MCP session polling inside the Word client
- whole-document direct-edit COM path
