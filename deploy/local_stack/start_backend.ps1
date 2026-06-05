param(
    [switch]$SkipMigrate,
    [switch]$SkipCollectstatic
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle "Stack Backend - $($config.PublicHost)"
Ensure-PathExists -LiteralPath $config.PythonPath -Label 'Python'

Use-RepoRoot
Set-BackendEnvironment

if ($config.RunMigrateOnLaunch -and -not $SkipMigrate) {
    Invoke-NativeCommand -FilePath $config.PythonPath -Arguments @('manage.py', 'migrate') -Description 'Django migrate'
}

if ($config.RunCollectstaticOnLaunch -and -not $SkipCollectstatic) {
    Invoke-NativeCommand -FilePath $config.PythonPath -Arguments @('manage.py', 'collectstatic', '--noinput') -Description 'Django collectstatic'
}

Invoke-NativeCommand `
    -FilePath $config.PythonPath `
    -Arguments @('manage.py', 'runserver', "$($config.DjangoHost):$($config.DjangoPort)") `
    -Description 'Django runserver'
