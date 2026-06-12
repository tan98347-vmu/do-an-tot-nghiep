// ignore_for_file: avoid_web_libraries_in_flutter, deprecated_member_use

import 'dart:html' as html;
import 'dart:ui_web' as ui;

import 'package:flutter/widgets.dart';

import '../../core/iframe_blocker.dart';

final _registeredHelpVideos = <String>{};
final _helpVideoElements = <String, html.VideoElement>{};
final _helpVideoSources = <String, String>{};

class HelpVideoPlayer extends StatelessWidget {
  final String viewKey;
  final String assetPath;
  final String unavailableMessage;

  const HelpVideoPlayer({
    super.key,
    required this.viewKey,
    required this.assetPath,
    required this.unavailableMessage,
  });

  @override
  Widget build(BuildContext context) {
    final source = 'assets/$assetPath';
    if (_registeredHelpVideos.add(viewKey)) {
      ui.platformViewRegistry.registerViewFactory(viewKey, (int _) {
        final video = html.VideoElement()
          ..src = source
          ..controls = true
          ..preload = 'metadata'
          ..setAttribute('playsinline', 'true')
          ..setAttribute('controlsList', 'nodownload')
          ..style.width = '100%'
          ..style.height = '100%'
          ..style.display = 'block'
          ..style.backgroundColor = '#111827';
        video.style.setProperty('object-fit', 'contain');
        video.append(
          html.ParagraphElement()..text = unavailableMessage,
        );
        _helpVideoElements[viewKey] = video;
        _helpVideoSources[viewKey] = source;
        return video;
      });
    }

    final existing = _helpVideoElements[viewKey];
    if (existing != null && _helpVideoSources[viewKey] != source) {
      existing
        ..pause()
        ..src = source
        ..load();
      _helpVideoSources[viewKey] = source;
    }

    return IframeBlocker(
      placeholderHeight: 320,
      child: HtmlElementView(viewType: viewKey),
    );
  }
}
