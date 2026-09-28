/**
 * Zara Multilingual Voice Synthesis (TTS) Service
 * Supports English, Tamil (தமிழ்), and Hindi (हिन्दी).
 * Dynamically resolves installed device voices with strict language boundary enforcement.
 */

// Language mapping matching project codes and language names
const rawLanguageMap = {
  english: "en-IN",
  tamil: "ta-IN",
  hindi: "hi-IN",
  en: "en-IN",
  ta: "ta-IN",
  hi: "hi-IN",
};

export const languageMap = new Proxy(rawLanguageMap, {
  get(target, prop) {
    if (typeof prop === 'string') {
      const key = prop.toLowerCase().trim();
      if (key in target) return target[key];
      if (key.startsWith('ta')) return 'ta-IN';
      if (key.startsWith('hi')) return 'hi-IN';
      if (key.startsWith('en')) return 'en-IN';
    }
    return target[prop] || 'en-IN';
  }
});

class TTSService {
  constructor() {
    this.synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    this.voices = [];
    this.currentUtterance = null;
    this.activeMessageId = null;
    this._listeners = new Set();
    this.warningHandler = null;

    if (this.synth) {
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => {
          this.loadVoices();
        };
      }
    }
  }

  loadVoices() {
    if (!this.synth) return [];
    const list = this.synth.getVoices() || [];
    if (list && list.length > 0) {
      this.voices = list;
    }
    return this.voices;
  }

  getVoices() {
    if (!this.voices || this.voices.length === 0) {
      this.loadVoices();
    }
    return this.voices;
  }

  setWarningHandler(handler) {
    this.warningHandler = handler;
  }

  notifyWarning(message) {
    if (this.warningHandler) {
      try {
        this.warningHandler(message);
      } catch (err) {
        console.warn('TTS warning handler error:', err);
      }
    }
    if (typeof window !== 'undefined') {
      try {
        window.dispatchEvent(
          new CustomEvent('tts:voice-unavailable', { detail: { message } })
        );
      } catch (e) {
        // ignore
      }
    }
  }

  cleanTextForSpeech(rawText) {
    if (!rawText) return '';
    return rawText
      // Remove code blocks
      .replace(/```[\s\S]*?```/g, 'Code block omitted.')
      // Remove inline code
      .replace(/`([^`]+)`/g, '$1')
      // Remove markdown bold/italic
      .replace(/[*_~#]/g, '')
      // Remove markdown links [text](url) -> text
      .replace(/\[([^\]]+)\]\([^)]+\)/g, '$1')
      // Standardize whitespace
      .replace(/\s+/g, ' ')
      .trim();
  }

  speak(text, language = 'en', options = {}) {
    if (!this.synth) {
      if (options.onError) {
        options.onError(new Error('SpeechSynthesis is not supported in this browser.'));
      }
      return false;
    }

    const clean = this.cleanTextForSpeech(text);
    if (!clean) return false;

    const selectedLanguage = language || 'en';

    try {
      // 1. Create utterance
      const utterance = new SpeechSynthesisUtterance(clean);

      // 2. Set utterance language
      utterance.lang = languageMap[selectedLanguage];

      // 3. Retrieve available voices (handling asynchronous loading)
      let voices = this.getVoices();
      if (!voices || voices.length === 0) {
        voices = this.synth.getVoices() || [];
        this.voices = voices;
      }

      const languageCode = languageMap[selectedLanguage].toLowerCase();
      const prefix = languageCode.split("-")[0];

      // 4. Select an installed browser voice strictly matching selected language
      let voice = null;
      if (prefix === 'ta') {
        // Find exact ta-IN / ta-* or voice named Tamil
        voice = voices.find(
          (v) => v.lang && v.lang.toLowerCase().replace('_', '-') === languageCode
        ) || voices.find(
          (v) => {
            const l = v.lang ? v.lang.toLowerCase().replace('_', '-') : '';
            return (
              l.startsWith('ta') ||
              (v.name && (v.name.toLowerCase().includes('tamil') || v.name.includes('தமிழ்')))
            );
          }
        ) || null;
      } else if (prefix === 'hi') {
        // Find exact hi-IN / hi-* or voice named Hindi
        voice = voices.find(
          (v) => v.lang && v.lang.toLowerCase().replace('_', '-') === languageCode
        ) || voices.find(
          (v) => {
            const l = v.lang ? v.lang.toLowerCase().replace('_', '-') : '';
            return (
              l.startsWith('hi') ||
              (v.name && (
                v.name.toLowerCase().includes('hindi') ||
                v.name.includes('हिन्दी') ||
                v.name.toLowerCase().includes('kalpana') ||
                v.name.toLowerCase().includes('hemant')
              ))
            );
          }
        ) || null;
      } else {
        // English: First try en-IN, then natural/Zara, then any en-*
        voice = voices.find(
          (v) => v.lang && v.lang.toLowerCase().replace('_', '-') === languageCode
        ) || voices.find(
          (v) => (
            v.name &&
            (v.name.toLowerCase().includes('zara') ||
              v.name.toLowerCase().includes('zira') ||
              v.name.toLowerCase().includes('samantha') ||
              v.name.toLowerCase().includes('natural')) &&
            v.lang &&
            v.lang.toLowerCase().startsWith('en')
          )
        ) || voices.find(
          (v) => (v.lang && v.lang.toLowerCase().startsWith('en')) ||
                 (v.name && v.name.toLowerCase().includes('english'))
        ) || null;
      }

      // DO NOT silently use an English voice for Tamil or Hindi
      if (voice) {
        utterance.voice = voice;
      } else {
        if (prefix === 'ta') {
          const warnMsg = "Tamil voice is not available in this browser. Please install/use a Tamil TTS voice or use Chrome/Edge with Tamil voice support.";
          this.notifyWarning(warnMsg);
          if (options.onVoiceUnavailable) {
            options.onVoiceUnavailable(warnMsg);
          }
        } else if (prefix === 'hi') {
          const warnMsg = "Hindi voice is not available in this browser.";
          this.notifyWarning(warnMsg);
          if (options.onVoiceUnavailable) {
            options.onVoiceUnavailable(warnMsg);
          }
        }
      }

      // Console debugging required for verification
      console.log("Selected language:", selectedLanguage);
      console.log("TTS language:", utterance.lang);
      console.log("Available voices:", voices);
      console.log("Selected voice:", voice);

      // Tuned rate and pitch for natural playback
      utterance.rate = 1.0;
      utterance.pitch = 1.05;

      this.activeMessageId = options.messageId || null;
      this.currentUtterance = utterance;

      utterance.onstart = () => {
        this._notify({ state: 'speaking', messageId: this.activeMessageId, language: selectedLanguage });
        if (options.onStart) options.onStart();
      };

      utterance.onend = () => {
        this.activeMessageId = null;
        this.currentUtterance = null;
        this._notify({ state: 'idle', messageId: null, language: selectedLanguage });
        if (options.onEnd) options.onEnd();
      };

      utterance.onerror = (e) => {
        if (e.error !== 'interrupted' && e.error !== 'canceled') {
          console.warn('TTS playback notice:', e.error);
        }
        this.activeMessageId = null;
        this.currentUtterance = null;
        this._notify({ state: 'idle', messageId: null, language: selectedLanguage });
        if (options.onError) options.onError(e);
      };

      // Prevent duplicate speech
      window.speechSynthesis.cancel();
      window.speechSynthesis.speak(utterance);
      return true;
    } catch (err) {
      console.warn('SpeechSynthesis error:', err);
      if (options.onError) options.onError(err);
      return false;
    }
  }

  stop() {
    if (this.synth) {
      try {
        this.synth.cancel();
      } catch (err) {
        // ignore
      }
    }
    this.activeMessageId = null;
    this.currentUtterance = null;
    this._notify({ state: 'idle', messageId: null });
  }

  pause() {
    if (this.synth && this.synth.speaking) {
      try {
        this.synth.pause();
        this._notify({ state: 'paused', messageId: this.activeMessageId });
      } catch (err) {
        // ignore
      }
    }
  }

  resume() {
    if (this.synth && this.synth.paused) {
      try {
        this.synth.resume();
        this._notify({ state: 'speaking', messageId: this.activeMessageId });
      } catch (err) {
        // ignore
      }
    }
  }

  isSpeaking() {
    return Boolean(this.synth && this.synth.speaking);
  }

  isPaused() {
    return Boolean(this.synth && this.synth.paused);
  }

  getActiveMessageId() {
    return this.activeMessageId;
  }

  subscribe(listener) {
    this._listeners.add(listener);
    return () => this._listeners.delete(listener);
  }

  _notify(data) {
    this._listeners.forEach((fn) => {
      try {
        fn(data);
      } catch (e) {
        console.error(e);
      }
    });
  }
}

export const ttsService = new TTSService();

// Setup global listener for async voice loading
if (typeof window !== 'undefined' && window.speechSynthesis) {
  window.speechSynthesis.onvoiceschanged = () => {
    ttsService.loadVoices();
  };
}

// Modular standalone function exports
export function speakText(text, language = 'en', options = {}) {
  return ttsService.speak(text, language, options);
}

export function stopSpeaking() {
  return ttsService.stop();
}

ttsService.speakText = speakText;
ttsService.stopSpeaking = stopSpeaking;

export default ttsService;
