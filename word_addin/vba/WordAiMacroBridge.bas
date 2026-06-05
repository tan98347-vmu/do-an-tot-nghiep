Attribute VB_Name = "WordAiMacroBridge"
Option Explicit

Public Sub ReplaceInHeaders(ByVal targetText As String, ByVal replacementText As String)
    Dim sectionItem As Section
    Dim headerRange As Range
    For Each sectionItem In ActiveDocument.Sections
        Set headerRange = sectionItem.Headers(wdHeaderFooterPrimary).Range
        headerRange.Find.ClearFormatting
        headerRange.Find.Replacement.ClearFormatting
        With headerRange.Find
            .Text = targetText
            .Replacement.Text = replacementText
            .Forward = True
            .Wrap = wdFindContinue
            .Format = False
            .MatchCase = False
            .MatchWholeWord = False
            .Execute Replace:=wdReplaceAll
        End With
    Next sectionItem
End Sub

Public Sub ReplaceInFooters(ByVal targetText As String, ByVal replacementText As String)
    Dim sectionItem As Section
    Dim footerRange As Range
    For Each sectionItem In ActiveDocument.Sections
        Set footerRange = sectionItem.Footers(wdHeaderFooterPrimary).Range
        footerRange.Find.ClearFormatting
        footerRange.Find.Replacement.ClearFormatting
        With footerRange.Find
            .Text = targetText
            .Replacement.Text = replacementText
            .Forward = True
            .Wrap = wdFindContinue
            .Format = False
            .MatchCase = False
            .MatchWholeWord = False
            .Execute Replace:=wdReplaceAll
        End With
    Next sectionItem
End Sub

Public Sub SetTrackRevisions(ByVal enabledText As String)
    ActiveDocument.TrackRevisions = (LCase$(Trim$(enabledText)) = "true")
End Sub

Public Sub ReplaceInTables(ByVal targetText As String, ByVal replacementText As String)
    Dim tableItem As Table
    Dim cellItem As Cell
    Dim cellRange As Range
    For Each tableItem In ActiveDocument.Tables
        For Each cellItem In tableItem.Range.Cells
            Set cellRange = cellItem.Range
            cellRange.End = cellRange.End - 1
            cellRange.Find.ClearFormatting
            cellRange.Find.Replacement.ClearFormatting
            With cellRange.Find
                .Text = targetText
                .Replacement.Text = replacementText
                .Forward = True
                .Wrap = wdFindStop
                .Format = False
                .MatchCase = False
                .MatchWholeWord = False
                .Execute Replace:=wdReplaceAll
            End With
        Next cellItem
    Next tableItem
End Sub
