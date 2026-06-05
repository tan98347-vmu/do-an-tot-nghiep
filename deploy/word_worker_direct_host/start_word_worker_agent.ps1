param(
    [string]$PythonPath = 'C:\Python314\python.exe',
    [string]$BackendBaseUrl = '',
    [string]$WorkerToken = ''
)

$ErrorActionPreference = 'Stop'

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runtimeRoot = Join-Path $repoRoot '.codex-runtime'
$workspaceRoot = Join-Path $runtimeRoot 'word-ai-agent-workspace'
$logRoot = Join-Path $runtimeRoot 'word-worker-agent'

function Set-EnvDefault {
    param(
        [string]$Name,
        [string]$Value
    )

    if ([string]::IsNullOrWhiteSpace((Get-Item -Path "Env:$Name" -ErrorAction SilentlyContinue).Value)) {
        Set-Item -Path "Env:$Name" -Value $Value
    }
}

New-Item -ItemType Directory -Force -Path $runtimeRoot | Out-Null
New-Item -ItemType Directory -Force -Path $workspaceRoot | Out-Null
New-Item -ItemType Directory -Force -Path $logRoot | Out-Null

if (-not (Test-Path -LiteralPath $PythonPath)) {
    throw "Python executable not found: $PythonPath"
}

if (-not $BackendBaseUrl) {
    $BackendBaseUrl = $env:WORD_AI_BACKEND_BASE_URL
}
if (-not $BackendBaseUrl) {
    $BackendBaseUrl = 'http://127.0.0.1:8000/api'
}

if (-not $WorkerToken) {
    $WorkerToken = $env:WORD_AI_LOCAL_AGENT_TOKEN
}
if (-not $WorkerToken) {
    throw 'WORD_AI_LOCAL_AGENT_TOKEN is required. Provide -WorkerToken or set the environment variable before starting the agent.'
}

$env:WORD_AI_BACKEND_BASE_URL = $BackendBaseUrl
$env:WORD_AI_LOCAL_AGENT_TOKEN = $WorkerToken
Set-EnvDefault -Name 'WORD_AI_PROFILE' -Value 'production'
Set-EnvDefault -Name 'WORD_AI_MAX_WORKER_SLOTS' -Value '1'
Set-EnvDefault -Name 'WORD_AI_ENABLED_WORKER_SLOTS' -Value '1'
Set-EnvDefault -Name 'WORD_AI_ENABLE_SLOT2_IN_TEST' -Value '0'
Set-EnvDefault -Name 'WORD_AI_WORKSPACE_ROOT' -Value $workspaceRoot
Set-EnvDefault -Name 'WORD_AI_PRESERVE_JOB_WORKSPACES' -Value '0'

Set-Location $repoRoot
& $PythonPath -m word_worker_agent
