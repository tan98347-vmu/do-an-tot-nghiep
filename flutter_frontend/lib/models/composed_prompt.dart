class ComposedPromptSection {
  final String label;
  final String content;

  const ComposedPromptSection({
    required this.label,
    required this.content,
  });

  factory ComposedPromptSection.fromJson(Map<String, dynamic> json) {
    return ComposedPromptSection(
      label: '${json['label'] ?? ''}',
      content: '${json['content'] ?? ''}',
    );
  }
}

class ComposedPrompt {
  final String composedText;
  final int tokenEstimate;
  final List<ComposedPromptSection> sections;

  const ComposedPrompt({
    required this.composedText,
    required this.tokenEstimate,
    required this.sections,
  });

  const ComposedPrompt.empty()
      : composedText = '',
        tokenEstimate = 0,
        sections = const [];

  factory ComposedPrompt.fromJson(Map<String, dynamic> json) {
    return ComposedPrompt(
      composedText: '${json['composed_text'] ?? ''}',
      tokenEstimate: (json['token_estimate'] as num?)?.toInt() ?? 0,
      sections: ((json['sections'] as List?) ?? const [])
          .whereType<Map>()
          .map((item) => ComposedPromptSection.fromJson(
                Map<String, dynamic>.from(item),
              ))
          .toList(),
    );
  }

  bool get isEmpty => composedText.trim().isEmpty && sections.isEmpty;
}
