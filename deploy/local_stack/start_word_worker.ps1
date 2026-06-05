param(
    [switch]$PrepareAddin
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle "Stack Word Worker - $($config.PublicHost)"
Ensure-PathExists -LiteralPath $config.PythonPath -Label 'Python'
Ensure-PathExists -LiteralPath $config.WordWorkerStartScriptPath -Label 'Word worker start script'

Use-RepoRoot
Wait-ForTcpPort -Host $config.DjangoHost -Port $config.DjangoPort -TimeoutSeconds 180
Set-WordWorkerEnvironment

if ($PrepareAddin) {
    Ensure-PathExists -LiteralPath $config.WordWorkerBuildScriptPath -Label 'Word add-in build script'
    Ensure-PathExists -LiteralPath $config.WordWorkerInstallScriptPath -Label 'Word add-in install script'

    & taskkill /IM WINWORD.EXE /F *> $null
    Invoke-NativeCommand `
        -FilePath 'powershell.exe' `
        -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $config.WordWorkerBuildScriptPath, '-Force') `
        -Description 'Word add-in build'
    Invoke-NativeCommand `
        -FilePath 'powershell.exe' `
        -Arguments @('-NoProfile', '-ExecutionPolicy', 'Bypass', '-File', $config.WordWorkerInstallScriptPath) `
        -Description 'Word add-in install'
}

Invoke-NativeCommand `
    -FilePath 'powershell.exe' `
    -Arguments @(
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-File', $config.WordWorkerStartScriptPath,
        '-PythonPath', $config.PythonPath,
        '-BackendBaseUrl', $config.BackendBaseUrl,
        '-WorkerToken', $config.WordAgentToken
    ) `
    -Description 'Word worker agent'
