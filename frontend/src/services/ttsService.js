/**
 * Zara Multilingual Voice Synthesis (TTS) Service
 * Supports English, Tamil (தமிழ்), and Hindi (हिन्दी).
 * Dynamically resolves installed device voices with graceful fallbacks.
 */

class TTSService {
  constructor() {
    this.synth = typeof window !== 'undefined' ? window.speechSynthesis : null;
    this.voices = [];
    this.currentUtterance = null;
    this.activeMessageId = null;
    this._listeners = new Set();

    if (this.synth) {
      this.loadVoices();
      if (this.synth.onvoiceschanged !== undefined) {
        this.synth.onvoiceschanged = () => this.loadVoices();
      }
    }
  }

  loadVoices() {
    if (!this.synth) return [];
    this.voices = this.synth.getVoices() || [];
    return this.voices;
  }

  getVoices() {
    if (!this.voices.length) {
      this.loadVoices();
    }
    return this.voices;
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

  findBestVoice(language = 'en') {
    const voices = this.getVoices();
    if (!voices || voices.length === 0) return null;

    const lang = (language || 'en').toLowerCase();

    if (lang === 'ta') {
      // 1. Exact Tamil voice
      const taVoice = voices.find(
        (v) =>
          v.lang.toLowerCase().replace('_', '-').startsWith('ta') ||
          v.name.toLowerCase().includes('tamil') ||
          v.name.includes('தமிழ்')
      );
      if (taVoice) return taVoice;
    } else if (lang === 'hi') {
      // 1. Exact Hindi voice
      const hiVoice = voices.find(
        (v) =>
          v.lang.toLowerCase().replace('_', '-').startsWith('hi') ||
          v.name.toLowerCase().includes('hindi') ||
          v.name.includes('हिन्दी') ||
          v.name.toLowerCase().includes('kalpana') ||
          v.name.toLowerCase().includes('hemant')
      );
      if (hiVoice) return hiVoice;
    } else {
      // English: Prefer Zara/Zira or natural female English voices
      const preferredZara = voices.find(
        (v) =>
          (v.name.toLowerCase().includes('zara') ||
            v.name.toLowerCase().includes('zira') ||
            v.name.toLowerCase().includes('samantha') ||
            v.name.toLowerCase().includes('natural')) &&
          v.lang.toLowerCase().startsWith('en')
      );
      if (preferredZara) return preferredZara;

      const enVoice = voices.find((v) => v.lang.toLowerCase().startsWith('en'));
      if (enVoice) return enVoice;
    }

    // Fallback: any voice matching language prefix or default voice
    const fallback = voices.find((v) => v.lang.toLowerCase().startsWith(lang)) || voices[0];
    return fallback || null;
  }

  speak(text, language = 'en', options = {}) {
    if (!this.synth) {
      if (options.onError) {
        options.onError(new Error('SpeechSynthesis is not supported in this browser.'));
      }
      return false;
    }

    // Cancel any active speech before starting new speech
    this.stop();

    const clean = this.cleanTextForSpeech(text);
    if (!clean) return false;

    try {
      const utterance = new SpeechSynthesisUtterance(clean);
      const voice = this.findBestVoice(language);

      if (voice) {
        utterance.voice = voice;
        utterance.lang = voice.lang;
      } else {
        const langMap = { en: 'en-US', ta: 'ta-IN', hi: 'hi-IN' };
        utterance.lang = langMap[language] || 'en-US';
      }

      // Slightly tuned rate and pitch for a natural assistant voice
      utterance.rate = 1.0;
      utterance.pitch = 1.05;

      this.activeMessageId = options.messageId || null;
      this.currentUtterance = utterance;

      utterance.onstart = () => {
        this._notify({ state: 'speaking', messageId: this.activeMessageId, language });
        if (options.onStart) options.onStart();
      };

      utterance.onend = () => {
        this.activeMessageId = null;
        this.currentUtterance = null;
        this._notify({ state: 'idle', messageId: null, language });
        if (options.onEnd) options.onEnd();
      };

      utterance.onerror = (e) => {
        // 'interrupted' or 'canceled' are normal when stop() is called
        if (e.error !== 'interrupted' && e.error !== 'canceled') {
          console.warn('TTS playback notice:', e.error);
        }
        this.activeMessageId = null;
        this.currentUtterance = null;
        this._notify({ state: 'idle', messageId: null, language });
        if (options.onError) options.onError(e);
      };

      this.synth.speak(utterance);
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
export default ttsService;
