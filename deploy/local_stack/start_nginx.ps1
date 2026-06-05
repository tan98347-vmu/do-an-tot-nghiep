$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle "Stack nginx - $($config.PublicHost)"
Ensure-PathExists -LiteralPath $config.NginxExecutablePath -Label 'nginx executable'
Ensure-PathExists -LiteralPath $config.NginxRoot -Label 'nginx root'

Use-RepoRoot
Update-LiveNginxConfig

& taskkill /IM nginx.exe /F *> $null

$nginxPrefix = "$($config.NginxRoot)\"
Invoke-NativeCommand -FilePath $config.NginxExecutablePath -Arguments @('-t', '-p', $nginxPrefix) -Description 'nginx config test'

Start-Process -FilePath $config.NginxExecutablePath -WorkingDirectory $config.NginxRoot | Out-Null
Write-Host "nginx started on http://127.0.0.1:$($config.NginxPort)"
