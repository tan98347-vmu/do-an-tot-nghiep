param(
    [string]$AddinPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$defaultAddinPath = Join-Path $repoRoot '.codex-runtime\native-word-addin\WordAiNativeWorker.dotm'

if (-not $AddinPath) {
    $AddinPath = $defaultAddinPath
}

$resolvedAddinPath = [System.IO.Path]::GetFullPath($AddinPath)
if (-not (Test-Path -LiteralPath $resolvedAddinPath)) {
    throw "Native Word add-in not found: $resolvedAddinPath"
}

try {
    $word = New-Object -ComObject Word.Application
} catch {
    throw 'Could not start Word through COM. Ensure Microsoft Word is installed and available.'
}

$word.Visible = $true

try {
    foreach ($existingAddin in $word.AddIns) {
        if ([string]::Equals($existingAddin.Path, (Split-Path -Parent $resolvedAddinPath), [System.StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals($existingAddin.Name, (Split-Path -Leaf $resolvedAddinPath), [System.StringComparison]::OrdinalIgnoreCase)) {
            $existingAddin.Installed = $false
            $existingAddin.Installed = $true
            @{
                ok = $true
                addin_path = $resolvedAddinPath
                already_registered = $true
                reloaded_existing = $true
            } | ConvertTo-Json -Depth 6 -Compress
            exit 0
        }
    }

    $addin = $word.AddIns.Add($resolvedAddinPath, $true)
    $addin.Installed = $true

    @{
        ok = $true
        addin_path = $resolvedAddinPath
        already_registered = $false
    } | ConvertTo-Json -Depth 6 -Compress
}
finally {
    if ($null -ne $word) {
        $word.Quit()
    }
}
