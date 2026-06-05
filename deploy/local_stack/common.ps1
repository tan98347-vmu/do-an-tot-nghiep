$script:StackConfig = & (Join-Path $PSScriptRoot 'stack_config.ps1')

function Get-StackConfig {
    $script:StackConfig
}

function Set-StackWindowTitle {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Title
    )

    try {
        $host.UI.RawUI.WindowTitle = $Title
    } catch {
    }
}

function Ensure-PathExists {
    param(
        [Parameter(Mandatory = $true)]
        [string]$LiteralPath,
        [Parameter(Mandatory = $true)]
        [string]$Label
    )

    if (-not (Test-Path -LiteralPath $LiteralPath)) {
        throw "$Label not found: $LiteralPath"
    }
}

function Use-RepoRoot {
    $config = Get-StackConfig
    Set-Location $config.RepoRoot
}

function Invoke-NativeCommand {
    param(
        [Parameter(Mandatory = $true)]
        [string]$FilePath,
        [string[]]$Arguments = @(),
        [string]$Description = $FilePath
    )

    & $FilePath @Arguments
    if ($LASTEXITCODE -ne 0) {
        throw "$Description failed with exit code $LASTEXITCODE."
    }
}

function Set-BackendEnvironment {
    $config = Get-StackConfig

    $env:WORD_AI_LOCAL_AGENT_TOKEN = $config.WordAgentToken
    $env:MANUAL_EDIT_PROVIDER = $config.ManualEditProvider
    $env:COLLABORA_PUBLIC_URL = $config.PublicUrl
    $env:COLLABORA_EDITOR_PATH = $config.CollaboraEditorPath
    $env:MANUAL_EDIT_WOPI_SRC_BASE_URL = $config.ManualEditWopiSrcBaseUrl
    $env:MANUAL_EDIT_SESSION_TTL_SECONDS = $config.ManualEditSessionTtlSeconds
}

function Set-WordWorkerEnvironment {
    $config = Get-StackConfig

    $env:WORD_AI_LOCAL_AGENT_TOKEN = $config.WordAgentToken
    $env:WORD_AI_BACKEND_BASE_URL = $config.BackendBaseUrl
    $env:WORD_AI_PROFILE = 'production'
    $env:WORD_AI_MAX_WORKER_SLOTS = '1'
    $env:WORD_AI_ENABLED_WORKER_SLOTS = '1'
    $env:WORD_AI_ENABLE_SLOT2_IN_TEST = '0'
    $env:WORD_AI_PRESERVE_JOB_WORKSPACES = '0'
}

function Get-CollaboraExtraParams {
    $config = Get-StackConfig
    if ($config.CollaboraSslTermination) {
        return '--o:ssl.enable=false --o:ssl.termination=true'
    }
    return '--o:ssl.enable=false --o:ssl.termination=false'
}

function Wait-ForDocker {
    param(
        [int]$TimeoutSeconds = 180
    )

    $config = Get-StackConfig
    $dockerCommand = Get-Command docker -ErrorAction SilentlyContinue
    if (-not $dockerCommand) {
        throw 'docker command not found in PATH.'
    }

    if ($config.DockerDesktopPath -and (Test-Path -LiteralPath $config.DockerDesktopPath)) {
        Start-Process -FilePath $config.DockerDesktopPath | Out-Null
    }

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        & $dockerCommand.Source version *> $null
        if ($LASTEXITCODE -eq 0) {
            return
        }
        Start-Sleep -Seconds 3
    }

    throw "Docker engine did not become ready within $TimeoutSeconds seconds."
}

function Wait-ForTcpPort {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Host,
        [Parameter(Mandatory = $true)]
        [int]$Port,
        [int]$TimeoutSeconds = 120
    )

    $deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $deadline) {
        $client = [System.Net.Sockets.TcpClient]::new()
        try {
            $asyncResult = $client.BeginConnect($Host, $Port, $null, $null)
            if ($asyncResult.AsyncWaitHandle.WaitOne(1000, $false) -and $client.Connected) {
                $client.EndConnect($asyncResult)
                return
            }
        } catch {
        } finally {
            $client.Dispose()
        }
        Start-Sleep -Seconds 1
    }

    throw "Timed out waiting for TCP $Host`:$Port."
}

function Update-LiveNginxConfig {
    $config = Get-StackConfig

    Ensure-PathExists -LiteralPath $config.NginxTemplatePath -Label 'nginx template'
    $templateContent = Get-Content -LiteralPath $config.NginxTemplatePath -Raw
    $serverNameLine = "server_name $($config.PublicHost) localhost 127.0.0.1;"
    $liveContent = $templateContent -replace 'server_name\s+.*localhost 127\.0\.0\.1;', $serverNameLine

    Set-Content -LiteralPath $config.LiveNginxConfPath -Value $liveContent -Encoding ASCII
}

function Start-StackWindow {
    param(
        [Parameter(Mandatory = $true)]
        [string]$ScriptName,
        [string[]]$ScriptArguments = @()
    )

    $scriptPath = Join-Path $PSScriptRoot $ScriptName
    Ensure-PathExists -LiteralPath $scriptPath -Label 'launcher script'

    $invocation = "& '$scriptPath'"
    if ($ScriptArguments.Count -gt 0) {
        $invocation = "$invocation $([string]::Join(' ', $ScriptArguments))"
    }

    Start-Process `
        -FilePath 'powershell.exe' `
        -WorkingDirectory (Get-StackConfig).RepoRoot `
        -ArgumentList @('-NoExit', '-ExecutionPolicy', 'Bypass', '-Command', $invocation) | Out-Null
}
