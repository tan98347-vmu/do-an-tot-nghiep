$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle "Stack ngrok - $($config.PublicHost)"

Use-RepoRoot

$ngrokCommand = Get-Command $config.NgrokCommand -ErrorAction SilentlyContinue
if (-not $ngrokCommand) {
    throw "ngrok command not found: $($config.NgrokCommand)"
}

Invoke-NativeCommand `
    -FilePath $ngrokCommand.Source `
    -Arguments @('http', "127.0.0.1:$($config.NginxPort)", '--url', $config.PublicUrl) `
    -Description 'ngrok tunnel'
