$ErrorActionPreference = 'Stop'

. (Join-Path $PSScriptRoot 'common.ps1')

$config = Get-StackConfig
Set-StackWindowTitle "Stack Collabora - $($config.PublicHost)"

Use-RepoRoot
Wait-ForDocker

& docker rm -f $config.CollaboraContainerName *> $null

$dockerArgs = @(
    'run',
    '--rm',
    '--name', $config.CollaboraContainerName,
    '-p', "$($config.CollaboraPort):9980",
    '-e', "aliasgroup1=$($config.ManualEditWopiSrcBaseUrl)",
    '-e', "extra_params=$(Get-CollaboraExtraParams)",
    $config.CollaboraImage
)

Invoke-NativeCommand -FilePath 'docker' -Arguments $dockerArgs -Description 'Collabora container'
