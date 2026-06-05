param(
    [switch]$SkipFrontendBuild,
    [switch]$SkipWordWorker,
    [switch]$PrepareWordAddin
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle "Stack Launcher - $($config.PublicHost)"

$includeFrontendBuild = $config.IncludeFrontendBuildWindow -and -not $SkipFrontendBuild
$includeWordWorker = $config.IncludeWordWorkerWindow -and -not $SkipWordWorker
$launchPrepareWordAddin = $config.PrepareWordAddinBeforeStart -or $PrepareWordAddin

Start-StackWindow -ScriptName 'start_nginx.ps1'
Start-Sleep -Seconds 1

Start-StackWindow -ScriptName 'start_collabora.ps1'
Start-Sleep -Seconds 1

Start-StackWindow -ScriptName 'start_backend.ps1'
Start-Sleep -Seconds 1

if ($includeFrontendBuild) {
    Start-StackWindow -ScriptName 'build_frontend_web.ps1'
    Start-Sleep -Seconds 1
}

Start-StackWindow -ScriptName 'start_ngrok.ps1'
Start-Sleep -Seconds 1

if ($includeWordWorker) {
    $wordWorkerArguments = @()
    if ($launchPrepareWordAddin) {
        $wordWorkerArguments += '-PrepareAddin'
    }
    Start-StackWindow -ScriptName 'start_word_worker.ps1' -ScriptArguments $wordWorkerArguments
}

Write-Host "Stack launch requested for $($config.PublicUrl)"
Write-Host 'Edit deploy/local_stack/stack_config.ps1 to change domain, token, or default windows.'
