import 'dart:html' as html;
import 'dart:typed_data';

void downloadBlob(List<int> bytes, String filename, String mime) {
  final blob = html.Blob([Uint8List.fromList(bytes)], mime);
  final url = html.Url.createObjectUrlFromBlob(blob);
  final anchor = html.AnchorElement(href: url)
    ..setAttribute('download', filename)
    ..style.display = 'none';
  html.document.body?.children.add(anchor);
  anchor.click();
  anchor.remove();
  html.Url.revokeObjectUrl(url);
}
