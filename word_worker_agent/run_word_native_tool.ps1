param(
    [Parameter(Mandatory = $true)][string]$MacroName,
    [Parameter(Mandatory = $true)][string]$ArgumentsJson,
    [Parameter(Mandatory = $false)][string]$SaveAfter = 'false',
    [Parameter(Mandatory = $false)][string]$AddinPath = ''
)

$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [System.Text.UTF8Encoding]::new($false)

$repoRoot = Split-Path -Parent $PSScriptRoot
$defaultAddinPath = Join-Path $repoRoot '.codex-runtime\native-word-addin\WordAiNativeWorker.dotm'
if (-not $AddinPath) {
    $AddinPath = $defaultAddinPath
}
$resolvedAddinPath = [System.IO.Path]::GetFullPath($AddinPath)

function Get-WordApplication {
    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    } catch {
        throw 'active_word_application_not_found'
    }
}

function Get-OptionalString {
    param(
        $Source,
        [string]$PropertyName,
        [string]$DefaultValue = ''
    )

    if ($null -eq $Source) {
        return $DefaultValue
    }

    $property = $Source.PSObject.Properties[$PropertyName]
    if ($null -eq $property -or $null -eq $property.Value) {
        return $DefaultValue
    }

    return [string]$property.Value
}

function Ensure-NativeAddInLoaded {
    param(
        [Parameter(Mandatory = $true)]
        $WordApplication,

        [Parameter(Mandatory = $true)]
        [string]$FullAddinPath
    )

    if (-not (Test-Path -LiteralPath $FullAddinPath)) {
        throw "native_word_addin_missing:$FullAddinPath"
    }

    $addinDirectory = Split-Path -Parent $FullAddinPath
    $addinName = Split-Path -Leaf $FullAddinPath

    foreach ($existingAddin in $WordApplication.AddIns) {
        if ([string]::Equals($existingAddin.Path, $addinDirectory, [System.StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals($existingAddin.Name, $addinName, [System.StringComparison]::OrdinalIgnoreCase)) {
            $existingAddin.Installed = $true
            return $existingAddin
        }
    }

    $addin = $WordApplication.AddIns.Add($FullAddinPath, $true)
    $addin.Installed = $true
    return $addin
}

function Reload-NativeAddIn {
    param(
        [Parameter(Mandatory = $true)]
        $WordApplication,

        [Parameter(Mandatory = $true)]
        [string]$FullAddinPath
    )

    $addinDirectory = Split-Path -Parent $FullAddinPath
    $addinName = Split-Path -Leaf $FullAddinPath

    foreach ($existingAddin in $WordApplication.AddIns) {
        if ([string]::Equals($existingAddin.Path, $addinDirectory, [System.StringComparison]::OrdinalIgnoreCase) -and
            [string]::Equals($existingAddin.Name, $addinName, [System.StringComparison]::OrdinalIgnoreCase)) {
            $existingAddin.Installed = $false
            $existingAddin.Installed = $true
            return $existingAddin
        }
    }

    return Ensure-NativeAddInLoaded -WordApplication $WordApplication -FullAddinPath $FullAddinPath
}

function Build-MacroCandidates {
    param(
        [Parameter(Mandatory = $true)]
        [string]$RequestedMacroName,

        [Parameter(Mandatory = $true)]
        [string]$FullAddinPath
    )

    $candidates = New-Object System.Collections.Generic.List[string]
    $addinLeafName = Split-Path -Leaf $FullAddinPath
    $procedureName = $RequestedMacroName
    if ($RequestedMacroName.Contains('.')) {
        $procedureName = $RequestedMacroName.Split('.')[-1]
    }

    foreach ($candidate in @(
        $RequestedMacroName,
        "'$addinLeafName'!$RequestedMacroName",
        "'$addinLeafName'!$procedureName",
        $procedureName
    )) {
        if ([string]::IsNullOrWhiteSpace($candidate)) {
            continue
        }
        if (-not $candidates.Contains($candidate)) {
            $null = $candidates.Add($candidate)
        }
    }

    return $candidates
}

function Invoke-WordMacro {
    param(
        [Parameter(Mandatory = $true)]
        $WordApplication,

        [Parameter(Mandatory = $true)]
        [string]$RequestedMacroName,

        [Parameter(Mandatory = $true)]
        [string]$FullAddinPath,

        [Parameter(Mandatory = $false)]
        [object[]]$Arguments = @()
    )

    $attemptErrors = New-Object System.Collections.Generic.List[string]

    foreach ($passLabel in @('initial', 'reloaded')) {
        if ($passLabel -eq 'reloaded') {
            Reload-NativeAddIn -WordApplication $WordApplication -FullAddinPath $FullAddinPath | Out-Null
        }

        foreach ($candidate in (Build-MacroCandidates -RequestedMacroName $RequestedMacroName -FullAddinPath $FullAddinPath)) {
            try {
                return [pscustomobject]@{
                    macro_name = $candidate
                    result = Invoke-WordRunWithArguments -WordApplication $WordApplication -MacroCandidate $candidate -Arguments $Arguments
                }
            } catch {
                $attemptErrors.Add("${passLabel}:${candidate}: $($_.Exception.Message)")
            }
        }
    }

    $attemptSummary = [string]::Join(' | ', $attemptErrors.ToArray())
    throw "native_word_macro_not_found:$RequestedMacroName | attempts=$attemptSummary"
}

function Invoke-WordRunWithArguments {
    param(
        [Parameter(Mandatory = $true)]
        $WordApplication,

        [Parameter(Mandatory = $true)]
        [string]$MacroCandidate,

        [Parameter(Mandatory = $false)]
        [object[]]$Arguments = @()
    )

    switch ($Arguments.Count) {
        0 { return $WordApplication.Run($MacroCandidate) }
        1 { return $WordApplication.Run($MacroCandidate, $Arguments[0]) }
        2 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1]) }
        3 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2]) }
        4 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2], $Arguments[3]) }
        5 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2], $Arguments[3], $Arguments[4]) }
        6 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2], $Arguments[3], $Arguments[4], $Arguments[5]) }
        7 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2], $Arguments[3], $Arguments[4], $Arguments[5], $Arguments[6]) }
        8 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2], $Arguments[3], $Arguments[4], $Arguments[5], $Arguments[6], $Arguments[7]) }
        9 { return $WordApplication.Run($MacroCandidate, $Arguments[0], $Arguments[1], $Arguments[2], $Arguments[3], $Arguments[4], $Arguments[5], $Arguments[6], $Arguments[7], $Arguments[8]) }
        default { throw "native_word_macro_argument_count_unsupported:$($Arguments.Count)" }
    }
}

$word = Get-WordApplication
$document = $word.ActiveDocument
if ($null -eq $document) {
    throw 'active_word_document_not_found'
}

Ensure-NativeAddInLoaded -WordApplication $word -FullAddinPath $resolvedAddinPath | Out-Null

$arguments = $ArgumentsJson | ConvertFrom-Json
$result = $null
$executedMacroName = $MacroName

switch ($MacroName) {
    'WordAiNativeTools.InspectDocument' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.InspectSelection' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.InspectTextMatches' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            (Get-OptionalString -Source $arguments -PropertyName 'replacement_text'),
            (Get-OptionalString -Source $arguments -PropertyName 'occurrence' -DefaultValue 'all')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.InspectFormatState' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'scope' -DefaultValue 'selection')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ReplaceTextMatches' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text,
            (Get-OptionalString -Source $arguments -PropertyName 'occurrence' -DefaultValue 'all'),
            (Get-OptionalString -Source $arguments -PropertyName 'match_case'),
            (Get-OptionalString -Source $arguments -PropertyName 'match_whole_word')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ReplaceSelectionText' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyTextReplacement' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text,
            (Get-OptionalString -Source $arguments -PropertyName 'expected_replaced_count'),
            (Get-OptionalString -Source $arguments -PropertyName 'match_case'),
            (Get-OptionalString -Source $arguments -PropertyName 'match_whole_word')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.NormalizeCaseWholeDocument' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.case
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.NormalizeCaseSelection' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.case
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ApplyFormatWholeDocument' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'bold'),
            (Get-OptionalString -Source $arguments -PropertyName 'italic'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_color'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_name'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_size')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ApplyFormatSelection' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'bold'),
            (Get-OptionalString -Source $arguments -PropertyName 'italic'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_color'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_name'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_size')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ClearFormatSelection' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.SetParagraphAlignment' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.alignment
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.SetLineSpacing' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.line_spacing
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.SetParagraphSpacing' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'spacing_before'),
            (Get-OptionalString -Source $arguments -PropertyName 'spacing_after')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ToggleTrackChanges' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'enabled' -DefaultValue 'false')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ReplaceInHeaders' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ReplaceInFooters' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ReplaceInTables' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.InsertCommentSelection' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.comment_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyDocumentCase' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.expected
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyDocumentFormatCoverage' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'bold'),
            (Get-OptionalString -Source $arguments -PropertyName 'italic'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_color')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifySelectionText' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.expected_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifySelectionCase' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.expected
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifySelectionFormat' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'bold'),
            (Get-OptionalString -Source $arguments -PropertyName 'italic'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_color'),
            (Get-OptionalString -Source $arguments -PropertyName 'alignment'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_name'),
            (Get-OptionalString -Source $arguments -PropertyName 'font_size'),
            (Get-OptionalString -Source $arguments -PropertyName 'line_spacing'),
            (Get-OptionalString -Source $arguments -PropertyName 'spacing_before'),
            (Get-OptionalString -Source $arguments -PropertyName 'spacing_after')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyTrackChangesState' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'expected_enabled' -DefaultValue 'false')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyHeaderReplacement' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyFooterReplacement' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyTableReplacement' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            [string]$arguments.target_text,
            [string]$arguments.replacement_text
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.VerifyCommentSelection' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath -Arguments @(
            (Get-OptionalString -Source $arguments -PropertyName 'comment_text')
        )
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    'WordAiNativeTools.ExportDocument' {
        $macroInvocation = Invoke-WordMacro -WordApplication $word -RequestedMacroName $MacroName -FullAddinPath $resolvedAddinPath
        $executedMacroName = $macroInvocation.macro_name
        $result = $macroInvocation.result
    }
    default {
        throw "unsupported_macro_name:$MacroName"
    }
}

if ($SaveAfter -eq 'true') {
    $document.Save()
}

if ($null -eq $result) {
    @{
        ok = $true
        macro_name = $executedMacroName
        active_document_name = [string]$document.Name
        active_document_path = [string]$document.FullName
        addin_path = $resolvedAddinPath
    } | ConvertTo-Json -Depth 6 -Compress
    exit 0
}

if ($result -is [string]) {
    [string]$result
    exit 0
}

@{
    ok = $true
    macro_name = $executedMacroName
    active_document_name = [string]$document.Name
    active_document_path = [string]$document.FullName
    addin_path = $resolvedAddinPath
    result = $result
} | ConvertTo-Json -Depth 6 -Compress
