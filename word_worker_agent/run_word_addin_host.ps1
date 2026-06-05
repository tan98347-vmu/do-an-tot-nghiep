param(
    [Parameter(Mandatory = $true)]
    [ValidateSet('open', 'close')]
    [string]$Action,

    [Parameter(Mandatory = $true)]
    [string]$DocumentPath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Get-WordApplication {
    try {
        return [Runtime.InteropServices.Marshal]::GetActiveObject('Word.Application')
    }
    catch {
        return New-Object -ComObject Word.Application
    }
}

function Get-DocumentByPath {
    param(
        [Parameter(Mandatory = $true)]
        $WordApplication,

        [Parameter(Mandatory = $true)]
        [string]$FullPath
    )

    foreach ($candidate in $WordApplication.Documents) {
        if ([string]::Equals($candidate.FullName, $FullPath, [System.StringComparison]::OrdinalIgnoreCase)) {
            return $candidate
        }
    }
    return $null
}

$fullPath = [System.IO.Path]::GetFullPath($DocumentPath)
$word = Get-WordApplication
$word.Visible = $true

if ($Action -eq 'open') {
    $document = Get-DocumentByPath -WordApplication $word -FullPath $fullPath
    $openedExisting = $true
    if ($null -eq $document) {
        $openedExisting = $false
        $document = $word.Documents.Open($fullPath, $false, $false)
    }
    $document.Activate()
    $word.Activate()
    $result = @{
        action = 'open'
        document_path = $fullPath
        document_name = $document.Name
        opened_existing = $openedExisting
        visible = [bool]$word.Visible
        document_count = [int]$word.Documents.Count
    }
    $result | ConvertTo-Json -Depth 6 -Compress
    exit 0
}

$document = Get-DocumentByPath -WordApplication $word -FullPath $fullPath
if ($null -eq $document) {
    @{
        action = 'close'
        document_path = $fullPath
        closed = $false
        already_closed = $true
        document_count = [int]$word.Documents.Count
    } | ConvertTo-Json -Depth 6 -Compress
    exit 0
}

$wdDoNotSaveChanges = 0
$document.Close([ref]$wdDoNotSaveChanges)
@{
    action = 'close'
    document_path = $fullPath
    closed = $true
    already_closed = $false
    document_count = [int]$word.Documents.Count
} | ConvertTo-Json -Depth 6 -Compress
