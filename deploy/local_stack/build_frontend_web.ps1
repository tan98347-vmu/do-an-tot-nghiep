param(
    [switch]$SkipPubGet
)

$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle 'Stack Frontend Build'
Ensure-PathExists -LiteralPath $config.FlutterPath -Label 'Flutter'
Ensure-PathExists -LiteralPath $config.FlutterProjectRoot -Label 'Flutter project'

Set-Location $config.FlutterProjectRoot

if (-not $SkipPubGet) {
    Invoke-NativeCommand -FilePath $config.FlutterPath -Arguments @('pub', 'get') -Description 'flutter pub get'
}

Invoke-NativeCommand -FilePath $config.FlutterPath -Arguments @('build', 'web') -Description 'flutter build web'
