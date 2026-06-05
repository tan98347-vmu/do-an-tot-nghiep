param(
    [string]$OutputPath = '',
    [switch]$Force
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest

$repoRoot = Split-Path -Parent (Split-Path -Parent $PSScriptRoot)
$runtimeRoot = Join-Path $repoRoot '.codex-runtime'
$defaultOutputDir = Join-Path $runtimeRoot 'native-word-addin'

if (-not $OutputPath) {
    New-Item -ItemType Directory -Force -Path $defaultOutputDir | Out-Null
    $OutputPath = Join-Path $defaultOutputDir 'WordAiNativeWorker.dotm'
}

$modulePaths = @(
    (Join-Path $repoRoot 'word_addin\vba\WordAiMacroBridge.bas'),
    (Join-Path $repoRoot 'word_addin\vba\WordAiNativeTools.bas')
)

foreach ($modulePath in $modulePaths) {
    if (-not (Test-Path -LiteralPath $modulePath)) {
        throw "Missing VBA module: $modulePath"
    }
}

$resolvedOutputPath = [System.IO.Path]::GetFullPath($OutputPath)
if ((Test-Path -LiteralPath $resolvedOutputPath) -and -not $Force) {
    throw "Output file already exists. Use -Force to overwrite: $resolvedOutputPath"
}

$outputDir = Split-Path -Parent $resolvedOutputPath
New-Item -ItemType Directory -Force -Path $outputDir | Out-Null

try {
    $word = New-Object -ComObject Word.Application
} catch {
    throw 'Could not start Word through COM. Ensure Microsoft Word is installed and available.'
}

$word.Visible = $false
$document = $word.Documents.Add()

try {
    try {
        $vbProject = $document.VBProject
        if ($null -eq $vbProject) {
            throw 'vb_project_unavailable'
        }
        $vbComponents = $vbProject.VBComponents
        if ($null -eq $vbComponents) {
            throw 'vb_components_unavailable'
        }
    } catch {
        throw 'Word blocked access to the VBA project model. In Word, go to File -> Options -> Trust Center -> Trust Center Settings -> Macro Settings, enable "Trust access to the VBA project object model", close Word, then rerun this build script.'
    }

    foreach ($modulePath in $modulePaths) {
        $null = $vbComponents.Import($modulePath)
    }

    $wdFormatXMLTemplateMacroEnabled = 15
    $document.SaveAs([ref]$resolvedOutputPath, [ref]$wdFormatXMLTemplateMacroEnabled)
    $document.Saved = $true

    @{
        ok = $true
        output_path = $resolvedOutputPath
        imported_modules = $modulePaths
    } | ConvertTo-Json -Depth 6 -Compress
}
finally {
    $wdDoNotSaveChanges = 0
    if ($null -ne $document) {
        $document.Close([ref]$wdDoNotSaveChanges)
    }
    if ($null -ne $word) {
        $word.Quit()
    }
}
