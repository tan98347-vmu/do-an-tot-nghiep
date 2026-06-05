// Tệp này dùng để: hỗ trợ bootstrap hoặc bridge web trong flutter_frontend/web/voice_assistant_bridge.js.
// Cách hoạt động: được gọi từ lớp phía trên, xử lý dữ liệu theo vai trò hiện có và trả kết quả về cho luồng gọi.
// Vai trò trong hệ thống: Đây là tài nguyên web đầu vào của Flutter.
// Tác dụng khi hệ thống vận hành: giúp bản build web hoạt động đúng trong trình duyệt.

(function () {
  const STATUS_EVENT = 'ai-assistant-voice-status';
  const RESULT_EVENT = 'ai-assistant-voice-result';
  const READY_EVENT = 'ai-assistant-voice-ready';
  const ERROR_EVENT = 'ai-assistant-voice-error';
  const DEBUG_EVENT = 'ai-assistant-voice-debug';
  const SPEECH_END_EVENT = 'ai-assistant-voice-speech-end';
  const MAX_LISTEN_MS = 20000;
  const SILENCE_TIMEOUT_MS = 3000;

  // Mục đích: Hàm `emitRaw` triển khai phần việc `emit Raw` trong flutter_frontend/web/voice_assistant_bridge.js.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là hàm thuộc tài nguyên web đầu vào của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  function emitRaw(name, detail) {
    window.dispatchEvent(new CustomEvent(name, { detail }));
  }

  // Mục đích: Hàm `debug` triển khai phần việc `debug` trong flutter_frontend/web/voice_assistant_bridge.js.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là hàm thuộc tài nguyên web đầu vào của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  function debug(message, extra) {
    if (extra !== undefined) {
      console.log('[voice_bridge]', message, extra);
    } else {
      console.log('[voice_bridge]', message);
    }
    emitRaw(DEBUG_EVENT, {
      message,
      extra: extra === undefined ? null : extra,
      at: new Date().toISOString(),
    });
  }

  // Mục đích: Hàm `emit` triển khai phần việc `emit` trong flutter_frontend/web/voice_assistant_bridge.js.
  // Cách hoạt động: Thành phần này nhận dữ liệu đầu vào từ lớp gọi phía trên, áp dụng logic hiện có rồi trả lại kết quả hoặc giao diện phù hợp.
  // Vai trò trong hệ thống: Đây là hàm thuộc tài nguyên web đầu vào của Flutter.
  // Tác dụng khi hệ thống vận hành: Thành phần này giúp luồng `flutter_frontend` chạy đúng trách nhiệm tại đúng thời điểm.

  function emit(name, detail) {
    debug(`emit ${name}`, detail);
    emitRaw(name, detail);
  }

  const RecognitionCtor = window.SpeechRecognition || window.webkitSpeechRecognition || null;

  const bridge = {
    recognition: null,
    speaking: false,
    listening: false,
    currentTranscript: '',
    listenStartedAt: 0,
    stopReason: 'idle',
    maxTimer: null,
    silenceTimer: null,

    isSupported() {
      const supported = !!RecognitionCtor && !!window.speechSynthesis;
      debug('isSupported', {
        supported,
        hasRecognitionCtor: !!RecognitionCtor,
        hasSpeechSynthesis: !!window.speechSynthesis,
        voicesCount:
          window.speechSynthesis && window.speechSynthesis.getVoices
            ? window.speechSynthesis.getVoices().length
            : 0,
        isSecureContext: window.isSecureContext,
        location: window.location.href,
      });
      return supported;
    },

    clearMaxTimer() {
      if (this.maxTimer) {
        clearTimeout(this.maxTimer);
        this.maxTimer = null;
      }
    },

    clearSilenceTimer() {
      if (this.silenceTimer) {
        clearTimeout(this.silenceTimer);
        this.silenceTimer = null;
      }
    },

    armSilenceTimer(reason) {
      this.clearSilenceTimer();
      if (!this.listening) {
        return;
      }
      debug('silence_timer armed', {
        timeoutMs: SILENCE_TIMEOUT_MS,
        reason,
        transcriptLength: String(this.currentTranscript || '').trim().length,
      });
      this.silenceTimer = setTimeout(() => {
        debug('silence_timer fired', {
          timeoutMs: SILENCE_TIMEOUT_MS,
          transcriptLength: String(this.currentTranscript || '').trim().length,
        });
        this.stopReason = 'silence_timeout';
        try {
          this.recognition.stop();
        } catch (error) {
          debug('recognition.stop failed on silence timer', {
            message: error && error.message ? error.message : String(error),
          });
        }
      }, SILENCE_TIMEOUT_MS);
    },

    getPreferredVoice() {
      if (!window.speechSynthesis || !window.speechSynthesis.getVoices) {
        return null;
      }
      const voices = window.speechSynthesis.getVoices() || [];
      const preferred =
        voices.find((voice) => /^vi(-|_)?/i.test(String(voice.lang || ''))) ||
        voices.find((voice) => /vietnam/i.test(String(voice.name || ''))) ||
        voices[0] ||
        null;
      debug('preferred_voice resolved', {
        voicesCount: voices.length,
        selectedName: preferred ? preferred.name : null,
        selectedLang: preferred ? preferred.lang : null,
      });
      return preferred;
    },

    resetRecognitionState() {
      this.clearMaxTimer();
      this.clearSilenceTimer();
      this.currentTranscript = '';
      this.listenStartedAt = 0;
      this.stopReason = 'idle';
      this.listening = false;
    },

    ensureRecognition() {
      if (!RecognitionCtor) {
        return null;
      }
      if (this.recognition) {
        return this.recognition;
      }

      const recognition = new RecognitionCtor();
      debug('ensureRecognition create', {
        ctor: RecognitionCtor && RecognitionCtor.name,
        isSecureContext: window.isSecureContext,
        language: 'vi-VN',
      });
      recognition.lang = 'vi-VN';
      recognition.interimResults = true;
      recognition.continuous = true;
      recognition.maxAlternatives = 1;

      recognition.onstart = () => {
        this.listening = true;
        this.listenStartedAt = Date.now();
        emit(STATUS_EVENT, { status: 'listening' });
      };

      recognition.onend = () => {
        const transcript = String(this.currentTranscript || '').trim();
        const elapsedMs = this.listenStartedAt ? Date.now() - this.listenStartedAt : 0;
        const reason = this.stopReason || 'ended';
        debug('recognition.onend', {
          transcriptLength: transcript.length,
          reason,
          elapsedMs,
        });
        this.listening = false;
        this.clearMaxTimer();
        this.clearSilenceTimer();

        if (!transcript) {
          emit(STATUS_EVENT, { status: 'idle' });
          emit(ERROR_EVENT, {
            message: 'Không ghi nhận được nội dung giọng nói.',
            reason,
            elapsedMs,
          });
          this.currentTranscript = '';
          this.stopReason = 'idle';
          return;
        }

        emit(STATUS_EVENT, {
          status: 'processing',
          transcript,
          reason,
          elapsedMs,
        });
        emit(READY_EVENT, {
          transcript,
          reason,
          elapsedMs,
        });
        this.currentTranscript = '';
        this.stopReason = 'idle';
      };

      recognition.onerror = (event) => {
        debug('recognition.onerror', {
          error: event && event.error ? String(event.error) : '',
          message: event && event.message ? String(event.message) : '',
          type: event && event.type ? String(event.type) : '',
        });
        this.clearMaxTimer();
        this.clearSilenceTimer();
        this.listening = false;
        emit(ERROR_EVENT, {
          message: event && event.error ? String(event.error) : 'speech-recognition-error',
        });
        emit(STATUS_EVENT, { status: 'idle' });
      };

      recognition.onresult = (event) => {
        let transcript = '';
        let isFinal = false;
        for (let i = 0; i < event.results.length; i += 1) {
          const result = event.results[i];
          if (!result || !result[0]) {
            continue;
          }
          transcript += result[0].transcript || '';
          if (result.isFinal) {
            isFinal = true;
          }
        }
        transcript = String(transcript || '').trim();
        this.currentTranscript = transcript;
        if (transcript) {
          this.armSilenceTimer(isFinal ? 'final_result' : 'interim_result');
        }
        emit(RESULT_EVENT, {
          transcript,
          final: isFinal,
          elapsedMs: this.listenStartedAt ? Date.now() - this.listenStartedAt : 0,
        });
      };

      this.recognition = recognition;
      return recognition;
    },

    startListening() {
      const recognition = this.ensureRecognition();
      if (!recognition) {
        debug('startListening unsupported');
        emit(STATUS_EVENT, { status: 'unsupported' });
        emit(ERROR_EVENT, {
          message: 'Trình duyệt hiện tại không hỗ trợ SpeechRecognition hoặc speechSynthesis.',
        });
        return false;
      }
      try {
        debug('startListening begin', {
          isSecureContext: window.isSecureContext,
          location: window.location.href,
          maxListenMs: MAX_LISTEN_MS,
          silenceTimeoutMs: SILENCE_TIMEOUT_MS,
        });
        this.clearMaxTimer();
        this.clearSilenceTimer();
        window.speechSynthesis.cancel();
        this.speaking = false;
        this.currentTranscript = '';
        this.stopReason = 'listening';
        recognition.start();
        this.maxTimer = setTimeout(() => {
          debug('max_listen_timeout reached', { maxListenMs: MAX_LISTEN_MS });
          this.stopReason = 'max_duration';
          try {
            recognition.stop();
          } catch (error) {
            debug('recognition.stop failed on max timer', {
              message: error && error.message ? error.message : String(error),
            });
          }
        }, MAX_LISTEN_MS);
        return true;
      } catch (error) {
        debug('startListening exception', {
          message: error && error.message ? error.message : String(error),
          isSecureContext: window.isSecureContext,
          location: window.location.href,
        });
        emit(ERROR_EVENT, {
          message: error && error.message ? error.message : String(error),
        });
        return false;
      }
    },

    stopListening() {
      if (this.recognition) {
        try {
          this.stopReason = 'manual_stop';
          this.clearSilenceTimer();
          this.recognition.stop();
        } catch (_) {}
      } else {
        emit(STATUS_EVENT, { status: 'idle' });
      }
    },

    speak(text) {
      const content = String(text || '').trim();
      debug('speak begin', { length: content.length, preview: content.slice(0, 240) });
      if (!content || !window.speechSynthesis) {
        emit(SPEECH_END_EVENT, { text: content });
        emit(STATUS_EVENT, { status: 'idle' });
        return false;
      }

      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(content);
        utterance.lang = 'vi-VN';
        utterance.rate = 1;
        utterance.pitch = 1;
        utterance.volume = 1;
        const preferredVoice = this.getPreferredVoice();
        if (preferredVoice) {
          utterance.voice = preferredVoice;
          utterance.lang = preferredVoice.lang || utterance.lang;
        }
        utterance.onstart = () => {
          this.speaking = true;
          emit(STATUS_EVENT, {
            status: 'speaking',
            voiceName: utterance.voice ? utterance.voice.name : null,
            voiceLang: utterance.voice ? utterance.voice.lang : utterance.lang,
          });
        };
        utterance.onend = () => {
          this.speaking = false;
          emit(SPEECH_END_EVENT, { text: content });
          emit(STATUS_EVENT, { status: 'idle' });
        };
        utterance.onerror = (event) => {
          debug('speechSynthesis.onerror', {
            error: event && event.error ? String(event.error) : '',
          });
          this.speaking = false;
          emit(ERROR_EVENT, {
            message: event && event.error ? String(event.error) : 'speech-synthesis-error',
          });
          emit(SPEECH_END_EVENT, { text: content });
          emit(STATUS_EVENT, { status: 'idle' });
        };
        window.speechSynthesis.speak(utterance);
        try {
          window.speechSynthesis.resume();
        } catch (_) {}
        return true;
      } catch (error) {
        debug('speak exception', {
          message: error && error.message ? error.message : String(error),
        });
        this.speaking = false;
        emit(ERROR_EVENT, {
          message: error && error.message ? error.message : String(error),
        });
        emit(SPEECH_END_EVENT, { text: content });
        emit(STATUS_EVENT, { status: 'idle' });
        return false;
      }
    },

    stopSpeaking() {
      try {
        window.speechSynthesis.cancel();
      } catch (_) {}
      this.speaking = false;
      emit(STATUS_EVENT, { status: 'idle' });
      emit(SPEECH_END_EVENT, { text: '' });
    },
  };

  window.aiAssistantVoice = bridge;
  if (window.speechSynthesis && 'onvoiceschanged' in window.speechSynthesis) {
    window.speechSynthesis.onvoiceschanged = () => {
      debug('speechSynthesis.voiceschanged', {
        voicesCount: window.speechSynthesis.getVoices().length,
      });
    };
  }
})();
