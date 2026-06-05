Attribute VB_Name = "WordAiNativeTools"
Option Explicit

Private Const MAX_EXCERPT_WORDS As Long = 5

Public Function InspectDocument() As String
    Dim bodyText As String
    bodyText = ActiveDocument.Content.Text
    InspectDocument = "{" & _
        JsonPair("scope", "whole_document") & "," & _
        JsonPair("content_text_excerpt", Left$(bodyText, 1000)) & "," & _
        JsonNumberPair("content_text_length", Len(bodyText)) & "," & _
        JsonNumberPair("paragraph_count", ActiveDocument.Paragraphs.Count) & "," & _
        JsonNumberPair("word_count", CountMeaningfulWordsInRange(ActiveDocument.Content)) & "," & _
        JsonBoolPair("track_revisions_state", ActiveDocument.TrackRevisions) & _
        "}"
End Function

Public Function InspectSelection() As String
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    InspectSelection = "{" & _
        JsonPair("scope", "selection") & "," & _
        JsonBoolPair("is_collapsed", targetRange.Start = targetRange.End) & "," & _
        JsonPair("text_excerpt", Left$(targetRange.Text, 500)) & "," & _
        JsonNumberPair("text_length", Len(targetRange.Text)) & "," & _
        JsonNumberPair("word_count", CountMeaningfulWordsInRange(targetRange)) & "," & _
        JsonNumberPair("paragraph_count", targetRange.Paragraphs.Count) & _
        "}"
End Function

Public Function InspectTextMatches(ByVal targetText As String, ByVal replacementText As String, ByVal occurrence As String) As String
    Dim searchRange As Range
    Set searchRange = ActiveDocument.Content
    InspectTextMatches = "{" & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & "," & _
        JsonPair("occurrence", occurrence) & "," & _
        JsonNumberPair("target_count", CountMatchesInRange(searchRange, targetText)) & "," & _
        JsonNumberPair("replacement_count", CountMatchesInRange(searchRange, replacementText)) & _
        "}"
End Function

Public Function InspectFormatState(ByVal scopeName As String) As String
    Dim targetRange As Range
    Set targetRange = ResolveScopeRange(scopeName)
    InspectFormatState = SerializeRangeFormat(targetRange, scopeName)
End Function

Public Function ReplaceTextMatches( _
    ByVal targetText As String, _
    ByVal replacementText As String, _
    ByVal occurrence As String, _
    Optional ByVal matchCaseText As String = "", _
    Optional ByVal matchWholeWordText As String = "" _
) As String
    Dim docRange As Range
    Dim beforeCount As Long
    Dim afterTargetCount As Long
    Dim afterReplacementCount As Long
    Dim replacedCount As Long
    Dim beforeText As String
    Dim afterText As String
    Dim matchCase As Boolean
    Dim matchWholeWord As Boolean

    Set docRange = ActiveDocument.Content
    matchCase = ParseBooleanTextWithDefault(matchCaseText, False)
    matchWholeWord = ParseBooleanTextWithDefault(matchWholeWordText, False)
    beforeText = docRange.Text
    beforeCount = CountExactOccurrencesInText(beforeText, targetText, matchCase)
    replacedCount = ExecuteReplace(docRange, targetText, replacementText, occurrence, matchCaseText, matchWholeWordText)
    afterText = ActiveDocument.Content.Text
    afterTargetCount = CountExactOccurrencesInText(afterText, targetText, matchCase)
    afterReplacementCount = CountExactOccurrencesInText(afterText, replacementText, matchCase)

    ReplaceTextMatches = "{" & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & "," & _
        JsonPair("occurrence", occurrence) & "," & _
        JsonBoolPair("match_case", matchCase) & "," & _
        JsonBoolPair("match_whole_word", matchWholeWord) & "," & _
        JsonNumberPair("before_match_count", beforeCount) & "," & _
        JsonNumberPair("replaced_count", replacedCount) & "," & _
        JsonNumberPair("target_count_after", afterTargetCount) & "," & _
        JsonNumberPair("replacement_count_after", afterReplacementCount) & _
        "}"
End Function

Public Function ReplaceSelectionText(ByVal replacementText As String) As String
    Dim targetRange As Range
    Dim originalText As String
    Set targetRange = CurrentSelectionRange()
    originalText = targetRange.Text
    targetRange.Text = replacementText
    ReplaceSelectionText = "{" & _
        JsonPair("scope", "selection") & "," & _
        JsonPair("original_text_excerpt", Left$(originalText, 500)) & "," & _
        JsonPair("replacement_text", replacementText) & "," & _
        JsonNumberPair("original_length", Len(originalText)) & "," & _
        JsonNumberPair("replacement_length", Len(replacementText)) & _
        "}"
End Function

Public Function VerifyTextReplacement( _
    ByVal targetText As String, _
    ByVal replacementText As String, _
    Optional ByVal expectedReplacedCountText As String = "", _
    Optional ByVal matchCaseText As String = "", _
    Optional ByVal matchWholeWordText As String = "" _
) As String
    Dim targetCount As Long
    Dim replacementCount As Long
    Dim verified As Boolean
    Dim contentText As String
    Dim deletedTargetRevisionCount As Long
    Dim insertedReplacementRevisionCount As Long
    Dim revisionAwareVerification As Boolean
    Dim expectedReplacedCount As Long
    Dim matchCase As Boolean
    Dim matchWholeWord As Boolean
    Dim replacementSatisfied As Boolean
    Dim targetSatisfied As Boolean
    contentText = ActiveDocument.Content.Text
    matchCase = ParseBooleanTextWithDefault(matchCaseText, False)
    matchWholeWord = ParseBooleanTextWithDefault(matchWholeWordText, False)
    expectedReplacedCount = ParseLongWithDefault(expectedReplacedCountText, 0)
    targetCount = CountMatchesInRange(ActiveDocument.Content, targetText, matchCase, matchWholeWord)
    replacementCount = CountMatchesInRange(ActiveDocument.Content, replacementText, matchCase, matchWholeWord)
    revisionAwareVerification = (ActiveDocument.TrackRevisions Or ActiveDocument.Revisions.Count > 0)
    If revisionAwareVerification Then
        deletedTargetRevisionCount = CountRevisionTextMatches(targetText, wdRevisionDelete, matchCase)
        insertedReplacementRevisionCount = CountRevisionTextMatches(replacementText, wdRevisionInsert, matchCase)
        replacementSatisfied = ((replacementCount > 0) Or (insertedReplacementRevisionCount > 0))
        targetSatisfied = ((targetCount = 0) Or (deletedTargetRevisionCount > 0))
        If expectedReplacedCount > 0 Then
            replacementSatisfied = ((replacementCount >= expectedReplacedCount) Or (insertedReplacementRevisionCount >= expectedReplacedCount))
            targetSatisfied = ((targetCount = 0) Or (deletedTargetRevisionCount >= expectedReplacedCount))
        End If
        verified = replacementSatisfied And targetSatisfied
    Else
        If expectedReplacedCount > 0 Then
            verified = (targetCount = 0 And replacementCount >= expectedReplacedCount)
        Else
            verified = (targetCount = 0 And replacementCount > 0)
        End If
    End If
    VerifyTextReplacement = "{" & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & "," & _
        JsonNumberPair("expected_replaced_count", expectedReplacedCount) & "," & _
        JsonNumberPair("target_count", targetCount) & "," & _
        JsonNumberPair("replacement_count", replacementCount) & "," & _
        JsonBoolPair("track_revisions_state", ActiveDocument.TrackRevisions) & "," & _
        JsonNumberPair("deleted_target_revision_count", deletedTargetRevisionCount) & "," & _
        JsonNumberPair("inserted_replacement_revision_count", insertedReplacementRevisionCount) & "," & _
        JsonBoolPair("matches_expected_replacement", verified) & "," & _
        JsonBoolPair("verified", verified) & _
        "}"
End Function

Public Function NormalizeCaseWholeDocument(ByVal caseName As String) As String
    Dim docRange As Range
    Dim beforeText As String
    Set docRange = ActiveDocument.Content
    beforeText = docRange.Text

    ApplyCaseTransform docRange, caseName

    NormalizeCaseWholeDocument = "{" & _
        JsonPair("scope", "whole_document") & "," & _
        JsonPair("case", LCase$(Trim$(caseName))) & "," & _
        JsonNumberPair("original_length", Len(beforeText)) & "," & _
        JsonNumberPair("transformed_length", Len(docRange.Text)) & _
        "}"
End Function

Public Function NormalizeCaseSelection(ByVal caseName As String) As String
    Dim targetRange As Range
    Dim beforeText As String
    Set targetRange = CurrentSelectionRange()
    beforeText = targetRange.Text

    ApplyCaseTransform targetRange, caseName

    NormalizeCaseSelection = "{" & _
        JsonPair("scope", "selection") & "," & _
        JsonPair("case", LCase$(Trim$(caseName))) & "," & _
        JsonNumberPair("original_length", Len(beforeText)) & "," & _
        JsonNumberPair("transformed_length", Len(targetRange.Text)) & _
        "}"
End Function

Public Function ApplyFormatWholeDocument( _
    ByVal boldText As String, _
    ByVal italicText As String, _
    ByVal fontColor As String, _
    ByVal fontName As String, _
    ByVal fontSizeText As String _
) As String
    Dim docRange As Range
    Set docRange = ActiveDocument.Content
    ApplyFormatToRange docRange, boldText, italicText, fontColor, fontName, fontSizeText
    ApplyFormatWholeDocument = SerializeRangeFormat(docRange, "whole_document")
End Function

Public Function ApplyFormatSelection( _
    ByVal boldText As String, _
    ByVal italicText As String, _
    ByVal fontColor As String, _
    ByVal fontName As String, _
    ByVal fontSizeText As String _
) As String
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    ApplyFormatToRange targetRange, boldText, italicText, fontColor, fontName, fontSizeText
    ApplyFormatSelection = SerializeRangeFormat(targetRange, "selection")
End Function

Public Function ClearFormatSelection() As String
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    targetRange.Font.Reset
    ClearFormatSelection = SerializeRangeFormat(targetRange, "selection")
End Function

Public Function SetParagraphAlignment(ByVal alignmentName As String) As String
    Dim paragraphItem As Paragraph
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    For Each paragraphItem In targetRange.Paragraphs
        paragraphItem.Alignment = ParseAlignmentName(alignmentName)
    Next paragraphItem
    SetParagraphAlignment = SerializeRangeFormat(targetRange, "selection")
End Function

Public Function SetLineSpacing(ByVal lineSpacingText As String) As String
    Dim paragraphItem As Paragraph
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    For Each paragraphItem In targetRange.Paragraphs
        paragraphItem.LineSpacingRule = ParseLineSpacingRule(lineSpacingText)
    Next paragraphItem
    SetLineSpacing = SerializeRangeFormat(targetRange, "selection")
End Function

Public Function SetParagraphSpacing(ByVal spacingBeforeText As String, ByVal spacingAfterText As String) As String
    Dim paragraphItem As Paragraph
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    For Each paragraphItem In targetRange.Paragraphs
        If HasMeaningfulValue(spacingBeforeText) Then
            paragraphItem.SpaceBefore = CDbl(spacingBeforeText)
        End If
        If HasMeaningfulValue(spacingAfterText) Then
            paragraphItem.SpaceAfter = CDbl(spacingAfterText)
        End If
    Next paragraphItem
    SetParagraphSpacing = SerializeRangeFormat(targetRange, "selection")
End Function

Public Function ToggleTrackChanges(ByVal enabledText As String) As String
    ActiveDocument.TrackRevisions = ParseBooleanText(enabledText)
    ToggleTrackChanges = "{" & _
        JsonBoolPair("track_revisions_state", ActiveDocument.TrackRevisions) & _
        "}"
End Function

Public Function ReplaceInHeaders(ByVal targetText As String, ByVal replacementText As String) As String
    WordAiMacroBridge.ReplaceInHeaders targetText, replacementText
    ReplaceInHeaders = "{" & _
        JsonBoolPair("ok", True) & "," & _
        JsonPair("scope", "headers") & "," & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & _
        "}"
End Function

Public Function ReplaceInFooters(ByVal targetText As String, ByVal replacementText As String) As String
    WordAiMacroBridge.ReplaceInFooters targetText, replacementText
    ReplaceInFooters = "{" & _
        JsonBoolPair("ok", True) & "," & _
        JsonPair("scope", "footers") & "," & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & _
        "}"
End Function

Public Function ReplaceInTables(ByVal targetText As String, ByVal replacementText As String) As String
    WordAiMacroBridge.ReplaceInTables targetText, replacementText
    ReplaceInTables = "{" & _
        JsonBoolPair("ok", True) & "," & _
        JsonPair("scope", "tables") & "," & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & _
        "}"
End Function

Public Function InsertCommentSelection(ByVal commentText As String) As String
    Dim targetRange As Range
    Set targetRange = CurrentSelectionRange()
    ActiveDocument.Comments.Add Range:=targetRange, Text:=commentText
    InsertCommentSelection = "{" & _
        JsonBoolPair("ok", True) & "," & _
        JsonPair("comment_text", commentText) & _
        "}"
End Function

Public Function VerifyDocumentCase(ByVal expectedCase As String) As String
    VerifyDocumentCase = VerifyRangeCase(ActiveDocument.Content, "whole_document", expectedCase)
End Function

Public Function VerifyDocumentFormatCoverage( _
    ByVal boldText As String, _
    ByVal italicText As String, _
    ByVal fontColor As String _
) As String
    VerifyDocumentFormatCoverage = VerifyRangeFormatCoverage(ActiveDocument.Content, "whole_document", boldText, italicText, fontColor, "", "", "", "", "", "")
End Function

Public Function VerifySelectionText(ByVal expectedText As String) As String
    Dim actualText As String
    Dim verified As Boolean
    actualText = CurrentSelectionRange().Text
    verified = (actualText = expectedText)
    VerifySelectionText = "{" & _
        JsonPair("expected_text", expectedText) & "," & _
        JsonPair("actual_text", actualText) & "," & _
        JsonBoolPair("verified", verified) & _
        "}"
End Function

Public Function VerifySelectionCase(ByVal expectedCase As String) As String
    VerifySelectionCase = VerifyRangeCase(CurrentSelectionRange(), "selection", expectedCase)
End Function

Public Function VerifySelectionFormat( _
    ByVal boldText As String, _
    ByVal italicText As String, _
    ByVal fontColor As String, _
    ByVal alignmentName As String, _
    ByVal fontName As String, _
    ByVal fontSizeText As String, _
    ByVal lineSpacingText As String, _
    ByVal spacingBeforeText As String, _
    ByVal spacingAfterText As String _
) As String
    VerifySelectionFormat = VerifyRangeFormatCoverage(CurrentSelectionRange(), "selection", boldText, italicText, fontColor, alignmentName, fontName, fontSizeText, lineSpacingText, spacingBeforeText, spacingAfterText)
End Function

Public Function VerifyTrackChangesState(ByVal expectedEnabledText As String) As String
    Dim expectedEnabled As Boolean
    Dim verified As Boolean
    expectedEnabled = ParseBooleanText(expectedEnabledText)
    verified = (ActiveDocument.TrackRevisions = expectedEnabled)
    VerifyTrackChangesState = "{" & _
        JsonBoolPair("expected_enabled", expectedEnabled) & "," & _
        JsonBoolPair("actual_enabled", ActiveDocument.TrackRevisions) & "," & _
        JsonBoolPair("verified", verified) & _
        "}"
End Function

Public Function VerifyHeaderReplacement(ByVal targetText As String, ByVal replacementText As String) As String
    VerifyHeaderReplacement = VerifyScopedReplacement("headers", targetText, replacementText)
End Function

Public Function VerifyFooterReplacement(ByVal targetText As String, ByVal replacementText As String) As String
    VerifyFooterReplacement = VerifyScopedReplacement("footers", targetText, replacementText)
End Function

Public Function VerifyTableReplacement(ByVal targetText As String, ByVal replacementText As String) As String
    VerifyTableReplacement = VerifyScopedReplacement("tables", targetText, replacementText)
End Function

Public Function VerifyCommentSelection(ByVal commentText As String) As String
    Dim targetRange As Range
    Dim commentCount As Long
    Dim verified As Boolean
    Dim latestComment As String

    Set targetRange = CurrentSelectionRange()
    commentCount = targetRange.Comments.Count
    If commentCount > 0 Then
        latestComment = targetRange.Comments(1).Range.Text
    End If
    verified = (commentCount > 0)
    If Len(Trim$(commentText)) > 0 Then
        verified = verified And (InStr(1, latestComment, commentText, vbTextCompare) > 0)
    End If

    VerifyCommentSelection = "{" & _
        JsonNumberPair("comment_count", commentCount) & "," & _
        JsonPair("latest_comment_excerpt", Left$(latestComment, 500)) & "," & _
        JsonBoolPair("verified", verified) & _
        "}"
End Function

Public Function ExportDocument() As String
    Dim bodyText As String
    ActiveDocument.Save
    bodyText = ActiveDocument.Content.Text
    ExportDocument = "{" & _
        JsonBoolPair("ok", True) & "," & _
        JsonPair("active_document_name", ActiveDocument.Name) & "," & _
        JsonPair("active_document_path", ActiveDocument.FullName) & "," & _
        JsonPair("content_text", bodyText) & "," & _
        JsonNumberPair("content_text_length", Len(bodyText)) & _
        "}"
End Function

Private Function VerifyRangeCase(ByVal targetRange As Range, ByVal scopeName As String, ByVal expectedCase As String) As String
    Dim totalWords As Long
    Dim matchingWords As Long
    Dim nonMatchingExcerpt As String
    Dim currentWord As Range
    Dim wordText As String
    Dim verified As Boolean
    Dim normalizedExpectedCase As String
    Dim isUppercaseVerified As Boolean
    Dim isLowercaseVerified As Boolean

    normalizedExpectedCase = LCase$(Trim$(expectedCase))

    For Each currentWord In targetRange.Words
        wordText = CleanWordText(currentWord.Text)
        If Len(wordText) > 0 Then
            totalWords = totalWords + 1
            Select Case normalizedExpectedCase
                Case "uppercase"
                    If wordText = UCase$(wordText) Then
                        matchingWords = matchingWords + 1
                    Else
                        CollectExcerpt nonMatchingExcerpt, wordText
                    End If
                Case "lowercase"
                    If wordText = LCase$(wordText) Then
                        matchingWords = matchingWords + 1
                    Else
                        CollectExcerpt nonMatchingExcerpt, wordText
                    End If
                Case Else
                    CollectExcerpt nonMatchingExcerpt, wordText
            End Select
        End If
    Next currentWord

    If normalizedExpectedCase = "uppercase" Or normalizedExpectedCase = "lowercase" Then
        verified = (totalWords > 0 And matchingWords = totalWords)
    Else
        verified = False
    End If
    isUppercaseVerified = (normalizedExpectedCase = "uppercase" And verified)
    isLowercaseVerified = (normalizedExpectedCase = "lowercase" And verified)
    VerifyRangeCase = "{" & _
        JsonPair("scope", scopeName) & "," & _
        JsonPair("expected", expectedCase) & "," & _
        JsonBoolPair("is_all_uppercase", isUppercaseVerified) & "," & _
        JsonBoolPair("is_all_lowercase", isLowercaseVerified) & "," & _
        JsonBoolPair("matches_expected_case", verified) & "," & _
        JsonNumberPair("case_ratio", ComputeRatio(matchingWords, totalWords)) & "," & _
        JsonPair("non_matching_excerpt", nonMatchingExcerpt) & "," & _
        JsonBoolPair("verified", verified) & "," & _
        JsonNumberPair("total_word_count", totalWords) & _
        "}"
End Function

Private Function VerifyRangeFormatCoverage( _
    ByVal targetRange As Range, _
    ByVal scopeName As String, _
    ByVal boldText As String, _
    ByVal italicText As String, _
    ByVal fontColor As String, _
    ByVal alignmentName As String, _
    ByVal fontName As String, _
    ByVal fontSizeText As String, _
    ByVal lineSpacingText As String, _
    ByVal spacingBeforeText As String, _
    ByVal spacingAfterText As String _
) As String
    Dim totalWords As Long
    Dim matchingWords As Long
    Dim failingExcerpt As String
    Dim currentWord As Range
    Dim wordText As String
    Dim expectBold As Variant
    Dim expectItalic As Variant
    Dim expectColor As String
    Dim expectedAlignment As String
    Dim expectedFontName As String
    Dim expectedFontSize As String
    Dim expectedLineSpacing As String
    Dim expectedSpacingBefore As String
    Dim expectedSpacingAfter As String
    Dim matchesExpected As Boolean
    Dim alignmentMatches As Boolean
    Dim lineSpacingMatches As Boolean
    Dim spacingMatches As Boolean
    Dim verified As Boolean

    expectBold = NullableBooleanText(boldText)
    expectItalic = NullableBooleanText(italicText)
    expectColor = NormalizeColorName(fontColor)
    expectedAlignment = LCase$(Trim$(alignmentName))
    expectedFontName = LCase$(Trim$(fontName))
    expectedFontSize = Trim$(fontSizeText)
    expectedLineSpacing = LCase$(Trim$(lineSpacingText))
    expectedSpacingBefore = Trim$(spacingBeforeText)
    expectedSpacingAfter = Trim$(spacingAfterText)

    For Each currentWord In targetRange.Words
        wordText = CleanWordText(currentWord.Text)
        If Len(wordText) > 0 Then
            totalWords = totalWords + 1
            matchesExpected = True
            If Not IsNull(expectBold) Then
                matchesExpected = matchesExpected And (CBool(currentWord.Font.Bold <> 0) = CBool(expectBold))
            End If
            If Not IsNull(expectItalic) Then
                matchesExpected = matchesExpected And (CBool(currentWord.Font.Italic <> 0) = CBool(expectItalic))
            End If
            If Len(expectColor) > 0 Then
                matchesExpected = matchesExpected And (LCase$(NormalizeColorName(currentWord.Font.Color)) = LCase$(expectColor))
            End If
            If Len(expectedFontName) > 0 Then
                matchesExpected = matchesExpected And (LCase$(Trim$(currentWord.Font.Name)) = expectedFontName)
            End If
            If Len(expectedFontSize) > 0 Then
                matchesExpected = matchesExpected And (CLng(currentWord.Font.Size) = CLng(CDbl(expectedFontSize)))
            End If
            If matchesExpected Then
                matchingWords = matchingWords + 1
            Else
                CollectExcerpt failingExcerpt, wordText
            End If
        End If
    Next currentWord

    alignmentMatches = RangeParagraphsMatch(targetRange, expectedAlignment)
    lineSpacingMatches = RangeParagraphLineSpacingMatches(targetRange, expectedLineSpacing)
    spacingMatches = RangeParagraphSpacingMatches(targetRange, expectedSpacingBefore, expectedSpacingAfter)
    verified = (totalWords > 0 And matchingWords = totalWords And alignmentMatches And lineSpacingMatches And spacingMatches)

    VerifyRangeFormatCoverage = "{" & _
        JsonPair("scope", scopeName) & "," & _
        JsonBoolPair("all_runs_bold", IsNull(expectBold) Or (totalWords > 0 And matchingWords = totalWords)) & "," & _
        JsonNumberPair("bold_run_ratio", ComputeRatio(matchingWords, totalWords)) & "," & _
        JsonPair("non_bold_ranges", failingExcerpt) & "," & _
        JsonBoolPair("paragraph_alignment_matches", alignmentMatches) & "," & _
        JsonBoolPair("line_spacing_matches", lineSpacingMatches) & "," & _
        JsonBoolPair("paragraph_spacing_matches", spacingMatches) & "," & _
        JsonBoolPair("matches_expected_format", verified) & "," & _
        JsonBoolPair("verified", verified) & "," & _
        JsonNumberPair("total_word_count", totalWords) & _
        "}"
End Function

Private Function VerifyScopedReplacement(ByVal scopeName As String, ByVal targetText As String, ByVal replacementText As String) As String
    Dim targetCount As Long
    Dim replacementCount As Long
    Dim verified As Boolean

    Select Case LCase$(Trim$(scopeName))
        Case "headers"
            targetCount = CountMatchesInHeaders(targetText)
            replacementCount = CountMatchesInHeaders(replacementText)
        Case "footers"
            targetCount = CountMatchesInFooters(targetText)
            replacementCount = CountMatchesInFooters(replacementText)
        Case "tables"
            targetCount = CountMatchesInTables(targetText)
            replacementCount = CountMatchesInTables(replacementText)
    End Select

    verified = (targetCount = 0 And replacementCount > 0)
    VerifyScopedReplacement = "{" & _
        JsonPair("scope", scopeName) & "," & _
        JsonPair("target_text", targetText) & "," & _
        JsonPair("replacement_text", replacementText) & "," & _
        JsonNumberPair("target_count", targetCount) & "," & _
        JsonNumberPair("replacement_count", replacementCount) & "," & _
        JsonBoolPair("verified", verified) & _
        "}"
End Function

Private Function SerializeRangeFormat(ByVal targetRange As Range, ByVal scopeName As String) As String
    Dim firstParagraph As Paragraph
    Set firstParagraph = targetRange.Paragraphs(1)
    SerializeRangeFormat = "{" & _
        JsonPair("scope", scopeName) & "," & _
        JsonBoolPair("bold", CBool(targetRange.Font.Bold <> 0)) & "," & _
        JsonBoolPair("italic", CBool(targetRange.Font.Italic <> 0)) & "," & _
        JsonPair("font_name", targetRange.Font.Name) & "," & _
        JsonNumberPair("font_size", CLng(targetRange.Font.Size)) & "," & _
        JsonPair("font_color", NormalizeColorName(targetRange.Font.Color)) & "," & _
        JsonPair("alignment", NormalizeAlignmentName(firstParagraph.Alignment)) & "," & _
        JsonPair("line_spacing", NormalizeLineSpacingName(firstParagraph.LineSpacingRule)) & "," & _
        JsonNumberPair("line_spacing_rule", firstParagraph.LineSpacingRule) & "," & _
        JsonNumberPair("space_before", firstParagraph.SpaceBefore) & "," & _
        JsonNumberPair("space_after", firstParagraph.SpaceAfter) & _
        "}"
End Function

Private Sub ApplyFormatToRange( _
    ByVal targetRange As Range, _
    ByVal boldText As String, _
    ByVal italicText As String, _
    ByVal fontColor As String, _
    ByVal fontName As String, _
    ByVal fontSizeText As String _
)
    If HasMeaningfulValue(boldText) Then
        targetRange.Font.Bold = ParseBooleanText(boldText)
    End If
    If HasMeaningfulValue(italicText) Then
        targetRange.Font.Italic = ParseBooleanText(italicText)
    End If
    If HasMeaningfulValue(fontName) Then
        targetRange.Font.Name = fontName
    End If
    If HasMeaningfulValue(fontSizeText) Then
        targetRange.Font.Size = CDbl(fontSizeText)
    End If
    If HasMeaningfulValue(fontColor) Then
        targetRange.Font.Color = ParseColorValue(fontColor)
    End If
End Sub

Private Sub ApplyCaseTransform(ByVal targetRange As Range, ByVal caseName As String)
    Select Case LCase$(Trim$(caseName))
        Case "uppercase"
            targetRange.Case = wdUpperCase
        Case "lowercase"
            targetRange.Case = wdLowerCase
        Case Else
            Err.Raise vbObjectError + 1000, "WordAiNativeTools", "Unsupported case transform."
    End Select
End Sub

Private Function ResolveScopeRange(ByVal scopeName As String) As Range
    If LCase$(Trim$(scopeName)) = "whole_document" Then
        Set ResolveScopeRange = ActiveDocument.Content
    Else
        Set ResolveScopeRange = CurrentSelectionRange()
    End If
End Function

Private Function CurrentSelectionRange() As Range
    Set CurrentSelectionRange = Selection.Range.Duplicate
End Function

Private Function RangeParagraphsMatch(ByVal targetRange As Range, ByVal expectedAlignment As String) As Boolean
    Dim paragraphItem As Paragraph
    If Len(expectedAlignment) = 0 Then
        RangeParagraphsMatch = True
        Exit Function
    End If
    RangeParagraphsMatch = True
    For Each paragraphItem In targetRange.Paragraphs
        If NormalizeAlignmentName(paragraphItem.Alignment) <> expectedAlignment Then
            RangeParagraphsMatch = False
            Exit Function
        End If
    Next paragraphItem
End Function

Private Function RangeParagraphLineSpacingMatches(ByVal targetRange As Range, ByVal expectedLineSpacing As String) As Boolean
    Dim paragraphItem As Paragraph
    If Len(expectedLineSpacing) = 0 Then
        RangeParagraphLineSpacingMatches = True
        Exit Function
    End If
    RangeParagraphLineSpacingMatches = True
    For Each paragraphItem In targetRange.Paragraphs
        If NormalizeLineSpacingName(paragraphItem.LineSpacingRule) <> expectedLineSpacing Then
            RangeParagraphLineSpacingMatches = False
            Exit Function
        End If
    Next paragraphItem
End Function

Private Function RangeParagraphSpacingMatches(ByVal targetRange As Range, ByVal expectedSpacingBefore As String, ByVal expectedSpacingAfter As String) As Boolean
    Dim paragraphItem As Paragraph
    Dim actualBefore As String
    Dim actualAfter As String
    RangeParagraphSpacingMatches = True
    If Len(expectedSpacingBefore) = 0 And Len(expectedSpacingAfter) = 0 Then
        Exit Function
    End If
    For Each paragraphItem In targetRange.Paragraphs
        actualBefore = CStr(CLng(paragraphItem.SpaceBefore))
        actualAfter = CStr(CLng(paragraphItem.SpaceAfter))
        If Len(expectedSpacingBefore) > 0 And actualBefore <> CStr(CLng(CDbl(expectedSpacingBefore))) Then
            RangeParagraphSpacingMatches = False
            Exit Function
        End If
        If Len(expectedSpacingAfter) > 0 And actualAfter <> CStr(CLng(CDbl(expectedSpacingAfter))) Then
            RangeParagraphSpacingMatches = False
            Exit Function
        End If
    Next paragraphItem
End Function

Private Function CountMeaningfulWordsInRange(ByVal targetRange As Range) As Long
    Dim currentWord As Range
    For Each currentWord In targetRange.Words
        If Len(CleanWordText(currentWord.Text)) > 0 Then
            CountMeaningfulWordsInRange = CountMeaningfulWordsInRange + 1
        End If
    Next currentWord
End Function

Private Function CountMatchesInHeaders(ByVal targetText As String) As Long
    Dim sectionItem As Section
    For Each sectionItem In ActiveDocument.Sections
        CountMatchesInHeaders = CountMatchesInHeaders + CountMatchesInRange(sectionItem.Headers(wdHeaderFooterPrimary).Range, targetText)
    Next sectionItem
End Function

Private Function CountMatchesInFooters(ByVal targetText As String) As Long
    Dim sectionItem As Section
    For Each sectionItem In ActiveDocument.Sections
        CountMatchesInFooters = CountMatchesInFooters + CountMatchesInRange(sectionItem.Footers(wdHeaderFooterPrimary).Range, targetText)
    Next sectionItem
End Function

Private Function CountMatchesInTables(ByVal targetText As String) As Long
    Dim tableItem As Table
    Dim cellItem As Cell
    Dim cellRange As Range
    For Each tableItem In ActiveDocument.Tables
        For Each cellItem In tableItem.Range.Cells
            Set cellRange = cellItem.Range.Duplicate
            cellRange.End = cellRange.End - 1
            CountMatchesInTables = CountMatchesInTables + CountMatchesInRange(cellRange, targetText)
        Next cellItem
    Next tableItem
End Function

Private Function CountMatchesInRange( _
    ByVal searchRange As Range, _
    ByVal targetText As String, _
    Optional ByVal matchCase As Boolean = False, _
    Optional ByVal matchWholeWord As Boolean = False _
) As Long
    Dim probe As Range
    If Len(targetText) = 0 Then
        Exit Function
    End If
    Set probe = searchRange.Duplicate
    probe.Find.ClearFormatting
    probe.Find.Replacement.ClearFormatting
    With probe.Find
        .Text = targetText
        .Replacement.Text = ""
        .Forward = True
        .Wrap = wdFindStop
        .Format = False
        .MatchCase = matchCase
        .MatchWholeWord = matchWholeWord
    End With
    Do While probe.Find.Execute
        CountMatchesInRange = CountMatchesInRange + 1
        probe.Collapse wdCollapseEnd
    Loop
End Function

Private Function CountExactOccurrencesInText(ByVal sourceText As String, ByVal targetText As String, Optional ByVal matchCase As Boolean = True) As Long
    Dim searchStart As Long
    Dim matchPosition As Long
    Dim compareMode As VbCompareMethod
    If Len(targetText) = 0 Then
        Exit Function
    End If
    compareMode = IIf(matchCase, vbBinaryCompare, vbTextCompare)
    searchStart = 1
    Do
        matchPosition = InStr(searchStart, sourceText, targetText, compareMode)
        If matchPosition <= 0 Then
            Exit Do
        End If
        CountExactOccurrencesInText = CountExactOccurrencesInText + 1
        searchStart = matchPosition + Len(targetText)
    Loop
End Function

Private Function CountRevisionTextMatches( _
    ByVal targetText As String, _
    ByVal expectedRevisionType As WdRevisionType, _
    Optional ByVal matchCase As Boolean = True _
) As Long
    Dim revisionItem As Revision
    Dim revisionText As String
    If Len(targetText) = 0 Then
        Exit Function
    End If
    For Each revisionItem In ActiveDocument.Revisions
        If revisionItem.Type = expectedRevisionType Then
            revisionText = revisionItem.Range.Text
            CountRevisionTextMatches = CountRevisionTextMatches + CountExactOccurrencesInText(revisionText, targetText, matchCase)
        End If
    Next revisionItem
End Function

Private Function ExecuteReplace( _
    ByVal searchRange As Range, _
    ByVal targetText As String, _
    ByVal replacementText As String, _
    ByVal occurrence As String, _
    Optional ByVal matchCaseText As String = "", _
    Optional ByVal matchWholeWordText As String = "" _
) As Long
    Dim probe As Range
    Dim matchCase As Boolean
    Dim matchWholeWord As Boolean
    If Len(targetText) = 0 Then
        Exit Function
    End If
    matchCase = ParseBooleanTextWithDefault(matchCaseText, False)
    matchWholeWord = ParseBooleanTextWithDefault(matchWholeWordText, False)
    Set probe = searchRange.Duplicate
    probe.Find.ClearFormatting
    probe.Find.Replacement.ClearFormatting
    With probe.Find
        .Text = targetText
        .Forward = True
        .Wrap = wdFindStop
        .Format = False
        .MatchCase = matchCase
        .MatchWholeWord = matchWholeWord
    End With
    If LCase$(Trim$(occurrence)) = "first" Then
        If probe.Find.Execute Then
            ReplaceFoundRangeExact probe, replacementText
            ExecuteReplace = 1
        End If
        Exit Function
    End If
    Do While probe.Find.Execute
        ReplaceFoundRangeExact probe, replacementText
        ExecuteReplace = ExecuteReplace + 1
        probe.Collapse wdCollapseEnd
        probe.End = ActiveDocument.Content.End
    Loop
End Function

Private Sub ReplaceFoundRangeExact(ByVal targetRange As Range, ByVal replacementText As String)
    Dim fontBold As Long
    Dim fontItalic As Long
    Dim fontUnderline As Long
    Dim fontColor As Long
    Dim highlightColor As Long
    Dim fontName As String
    Dim fontSize As Single
    Dim paragraphAlignment As Long
    Dim lineSpacingRule As Long
    Dim spaceBefore As Single
    Dim spaceAfter As Single
    Dim styleName As String

    If targetRange Is Nothing Then
        Exit Sub
    End If

    On Error Resume Next
    fontBold = targetRange.Font.Bold
    fontItalic = targetRange.Font.Italic
    fontUnderline = targetRange.Font.Underline
    fontColor = targetRange.Font.Color
    highlightColor = targetRange.HighlightColorIndex
    fontName = targetRange.Font.Name
    fontSize = targetRange.Font.Size
    styleName = CStr(targetRange.Style)
    If targetRange.Paragraphs.Count > 0 Then
        paragraphAlignment = targetRange.Paragraphs(1).Alignment
        lineSpacingRule = targetRange.Paragraphs(1).LineSpacingRule
        spaceBefore = targetRange.Paragraphs(1).SpaceBefore
        spaceAfter = targetRange.Paragraphs(1).SpaceAfter
    End If
    On Error GoTo 0

    targetRange.Text = replacementText

    If Len(replacementText) = 0 Then
        Exit Sub
    End If

    On Error Resume Next
    If Len(styleName) > 0 Then
        targetRange.Style = styleName
    End If
    targetRange.Font.Bold = fontBold
    targetRange.Font.Italic = fontItalic
    targetRange.Font.Underline = fontUnderline
    targetRange.Font.Color = fontColor
    targetRange.HighlightColorIndex = highlightColor
    If Len(fontName) > 0 Then
        targetRange.Font.Name = fontName
    End If
    If fontSize > 0 Then
        targetRange.Font.Size = fontSize
    End If
    If targetRange.Paragraphs.Count > 0 Then
        targetRange.Paragraphs(1).Alignment = paragraphAlignment
        targetRange.Paragraphs(1).LineSpacingRule = lineSpacingRule
        targetRange.Paragraphs(1).SpaceBefore = spaceBefore
        targetRange.Paragraphs(1).SpaceAfter = spaceAfter
    End If
    On Error GoTo 0
End Sub

Private Function CleanWordText(ByVal value As String) As String
    Dim normalized As String
    normalized = Replace$(value, vbCr, "")
    normalized = Replace$(normalized, vbTab, "")
    normalized = Replace$(normalized, Chr$(7), "")
    normalized = Trim$(normalized)
    CleanWordText = normalized
End Function

Private Sub CollectExcerpt(ByRef buffer As String, ByVal value As String)
    If Len(value) = 0 Then
        Exit Sub
    End If
    If Len(buffer) = 0 Then
        buffer = value
        Exit Sub
    End If
    If UBound(Split(buffer, " | ")) + 1 >= MAX_EXCERPT_WORDS Then
        Exit Sub
    End If
    buffer = buffer & " | " & value
End Sub

Private Function ComputeRatio(ByVal matchingCount As Long, ByVal totalCount As Long) As Double
    If totalCount <= 0 Then
        ComputeRatio = 0
        Exit Function
    End If
    ComputeRatio = Round(CDbl(matchingCount) / CDbl(totalCount), 4)
End Function

Private Function HasMeaningfulValue(ByVal value As String) As Boolean
    HasMeaningfulValue = (Len(Trim$(value)) > 0)
End Function

Private Function ParseBooleanText(ByVal value As String) As Boolean
    ParseBooleanText = (LCase$(Trim$(value)) = "true")
End Function

Private Function ParseBooleanTextWithDefault(ByVal value As String, ByVal defaultValue As Boolean) As Boolean
    If Len(Trim$(value)) = 0 Then
        ParseBooleanTextWithDefault = defaultValue
    Else
        ParseBooleanTextWithDefault = ParseBooleanText(value)
    End If
End Function

Private Function ParseLongWithDefault(ByVal value As String, ByVal defaultValue As Long) As Long
    If Len(Trim$(value)) = 0 Then
        ParseLongWithDefault = defaultValue
        Exit Function
    End If
    If IsNumeric(value) Then
        ParseLongWithDefault = CLng(value)
        Exit Function
    End If
    ParseLongWithDefault = defaultValue
End Function

Private Function NullableBooleanText(ByVal value As String) As Variant
    If Len(Trim$(value)) = 0 Then
        NullableBooleanText = Null
    Else
        NullableBooleanText = ParseBooleanText(value)
    End If
End Function

Private Function ParseColorValue(ByVal value As String) As Long
    Select Case LCase$(Trim$(value))
        Case "", "black"
            ParseColorValue = wdColorBlack
        Case "red"
            ParseColorValue = wdColorRed
        Case "blue"
            ParseColorValue = wdColorBlue
        Case "green"
            ParseColorValue = wdColorGreen
        Case Else
            ParseColorValue = wdColorBlack
    End Select
End Function

Private Function NormalizeColorName(ByVal value As Variant) As String
    If IsNumeric(value) Then
        Select Case CLng(value)
            Case wdColorBlack
                NormalizeColorName = "black"
                Exit Function
            Case wdColorRed
                NormalizeColorName = "red"
                Exit Function
            Case wdColorBlue
                NormalizeColorName = "blue"
                Exit Function
            Case wdColorGreen
                NormalizeColorName = "green"
                Exit Function
        End Select
    End If
    NormalizeColorName = LCase$(Trim$(CStr(value)))
End Function

Private Function ParseAlignmentName(ByVal value As String) As WdParagraphAlignment
    Select Case LCase$(Trim$(value))
        Case "center"
            ParseAlignmentName = wdAlignParagraphCenter
        Case "right"
            ParseAlignmentName = wdAlignParagraphRight
        Case "justify"
            ParseAlignmentName = wdAlignParagraphJustify
        Case Else
            ParseAlignmentName = wdAlignParagraphLeft
    End Select
End Function

Private Function NormalizeAlignmentName(ByVal alignmentValue As WdParagraphAlignment) As String
    Select Case alignmentValue
        Case wdAlignParagraphCenter
            NormalizeAlignmentName = "center"
        Case wdAlignParagraphRight
            NormalizeAlignmentName = "right"
        Case wdAlignParagraphJustify
            NormalizeAlignmentName = "justify"
        Case Else
            NormalizeAlignmentName = "left"
    End Select
End Function

Private Function NormalizeLineSpacingName(ByVal spacingValue As WdLineSpacing) As String
    Select Case spacingValue
        Case wdLineSpace1pt5
            NormalizeLineSpacingName = "1.5"
        Case wdLineSpaceDouble
            NormalizeLineSpacingName = "2.0"
        Case Else
            NormalizeLineSpacingName = "single"
    End Select
End Function

Private Function ParseLineSpacingRule(ByVal value As String) As WdLineSpacing
    Select Case LCase$(Trim$(value))
        Case "1.5", "1_5", "one_point_five"
            ParseLineSpacingRule = wdLineSpace1pt5
        Case "2", "2.0", "double"
            ParseLineSpacingRule = wdLineSpaceDouble
        Case Else
            ParseLineSpacingRule = wdLineSpaceSingle
    End Select
End Function

Private Function JsonPair(ByVal keyName As String, ByVal value As String) As String
    JsonPair = JsonQuote(keyName) & ":" & JsonQuote(value)
End Function

Private Function JsonBoolPair(ByVal keyName As String, ByVal value As Boolean) As String
    JsonBoolPair = JsonQuote(keyName) & ":" & JsonBool(value)
End Function

Private Function JsonNumberPair(ByVal keyName As String, ByVal value As Variant) As String
    JsonNumberPair = JsonQuote(keyName) & ":" & Replace$(CStr(value), ",", ".")
End Function

Private Function JsonQuote(ByVal value As String) As String
    JsonQuote = """" & JsonEscape(value) & """"
End Function

Private Function JsonBool(ByVal value As Boolean) As String
    If value Then
        JsonBool = "true"
    Else
        JsonBool = "false"
    End If
End Function

Private Function JsonEscape(ByVal value As String) As String
    Dim escaped As String
    Dim currentChar As String
    Dim codePoint As Long
    Dim index As Long

    For index = 1 To Len(value)
        currentChar = Mid$(value, index, 1)
        codePoint = AscW(currentChar)
        If codePoint < 0 Then
            codePoint = codePoint + 65536
        End If

        Select Case codePoint
            Case 34
                escaped = escaped & Chr$(92) & Chr$(34)
            Case 92
                escaped = escaped & "\\"
            Case 8
                escaped = escaped & "\b"
            Case 9
                escaped = escaped & "\t"
            Case 10
                escaped = escaped & "\n"
            Case 12
                escaped = escaped & "\f"
            Case 13
                escaped = escaped & "\r"
            Case 0 To 31
                escaped = escaped & "\u" & Right$("0000" & Hex$(codePoint), 4)
            Case Else
                escaped = escaped & currentChar
        End Select
    Next index

    JsonEscape = escaped
End Function
