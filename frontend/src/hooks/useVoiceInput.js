import { useState, useRef, useEffect, useCallback } from 'react';

export function useVoiceInput({ onTranscript, onError, language = 'en' } = {}) {
  const [status, setStatus] = useState('idle'); // 'idle' | 'listening' | 'processing' | 'error'
  const [isListening, setIsListening] = useState(false);
  const [isSupported, setIsSupported] = useState(true);
  const [errorMessage, setErrorMessage] = useState(null);

  const recognitionRef = useRef(null);
  const finalTranscriptRef = useRef('');
  const isListeningRef = useRef(false);
  const baseTextRef = useRef('');
  const transcriptCallbackRef = useRef(onTranscript);
  const errorCallbackRef = useRef(onError);
  const languageRef = useRef(language);

  useEffect(() => {
    transcriptCallbackRef.current = onTranscript;
  }, [onTranscript]);

  useEffect(() => {
    errorCallbackRef.current = onError;
  }, [onError]);

  useEffect(() => {
    languageRef.current = language;
    if (recognitionRef.current) {
      const langMap = {
        en: 'en-US',
        ta: 'ta-IN',
        hi: 'hi-IN',
      };
      recognitionRef.current.lang = langMap[language] || 'en-US';
    }
  }, [language]);

  // Check browser support on mount
  useEffect(() => {
    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      setIsSupported(false);
    }
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        try {
          recognitionRef.current.onstart = null;
          recognitionRef.current.onresult = null;
          recognitionRef.current.onerror = null;
          recognitionRef.current.onend = null;
          recognitionRef.current.abort();
        } catch {
          // ignore
        }
      }
    };
  }, []);

  // Initialize SpeechRecognition once and reuse across renders
  const getRecognition = useCallback(() => {
    if (recognitionRef.current) {
      const langMap = {
        en: 'en-US',
        ta: 'ta-IN',
        hi: 'hi-IN',
      };
      recognitionRef.current.lang = langMap[languageRef.current] || 'en-US';
      return recognitionRef.current;
    }

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) return null;

    const recognition = new SpeechRecognition();
    recognition.continuous = true;
    recognition.interimResults = true;
    const langMap = {
      en: 'en-US',
      ta: 'ta-IN',
      hi: 'hi-IN',
    };
    recognition.lang = langMap[languageRef.current] || 'en-US';

    recognition.onstart = () => {
      isListeningRef.current = true;
      setIsListening(true);
      setStatus('listening');
      setErrorMessage(null);
    };

    recognition.onresult = (event) => {
      setStatus('processing');
      let interimTranscript = '';

      for (let i = event.resultIndex; i < event.results.length; i++) {
        const transcript = event.results[i][0].transcript;

        if (event.results[i].isFinal) {
          finalTranscriptRef.current += transcript + ' ';
        } else {
          interimTranscript += transcript;
        }
      }

      const combinedSpeech = (finalTranscriptRef.current + interimTranscript).trim();
      const existingText = baseTextRef.current.trim();
      const fullText = [existingText, combinedSpeech]
        .filter(Boolean)
        .join(' ')
        .trim();

      if (transcriptCallbackRef.current) {
        transcriptCallbackRef.current(fullText);
      }
      setStatus('listening');
    };

    recognition.onerror = (event) => {
      let errorText = 'Speech recognition error occurred.';
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        errorText = 'Microphone permission denied.';
      } else if (event.error === 'no-speech') {
        // Natural timeout during silence - stop gracefully without error toast
        isListeningRef.current = false;
        setIsListening(false);
        setStatus('idle');
        return;
      } else if (event.error === 'audio-capture') {
        errorText = 'No microphone was found or microphone is busy.';
      } else if (event.error === 'network') {
        errorText = 'Network connection error during voice recognition.';
      }

      setErrorMessage(errorText);
      setStatus('error');
      errorCallbackRef.current?.(errorText);
      isListeningRef.current = false;
      setIsListening(false);
    };

    recognition.onend = () => {
      isListeningRef.current = false;
      setIsListening(false);
      setStatus('idle');
    };

    recognitionRef.current = recognition;
    return recognition;
  }, []);

  const stopListening = useCallback(() => {
    if (recognitionRef.current) {
      try {
        recognitionRef.current.stop();
      } catch {
        // ignore
      }
    }
    isListeningRef.current = false;
    setIsListening(false);
    setStatus('idle');
  }, []);

  const startListening = useCallback(async (currentText = '') => {
    setErrorMessage(null);
    setStatus('processing');
    finalTranscriptRef.current = '';
    baseTextRef.current = (currentText || '').trim();

    const SpeechRecognition =
      window.SpeechRecognition ||
      window.webkitSpeechRecognition;

    if (!SpeechRecognition) {
      const msg = 'Voice input is not supported in this browser. Try Google Chrome or Microsoft Edge.';
      setErrorMessage(msg);
      setStatus('error');
      errorCallbackRef.current?.(msg);
      return;
    }

    // Permission check & prompt
    if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        stream.getTracks().forEach((track) => track.stop());
      } catch (mediaErr) {
        const deniedMsg = 'Microphone permission denied.';
        setErrorMessage(deniedMsg);
        setStatus('error');
        errorCallbackRef.current?.(deniedMsg);
        isListeningRef.current = false;
        setIsListening(false);
        return;
      }
    }

    try {
      const recognition = getRecognition();
      if (!recognition) return;

      if (isListeningRef.current) {
        recognition.stop();
      }

      recognition.start();
    } catch (err) {
      if (err.name !== 'InvalidStateError') {
        const msg = 'Microphone permission denied.';
        setErrorMessage(msg);
        setStatus('error');
        errorCallbackRef.current?.(msg);
        isListeningRef.current = false;
        setIsListening(false);
      }
    }
  }, [getRecognition]);

  const toggleListening = useCallback((currentText = '') => {
    if (isListeningRef.current) {
      stopListening();
    } else {
      startListening(currentText);
    }
  }, [startListening, stopListening]);

  return {
    status,
    isListening,
    isSupported,
    errorMessage,
    startListening,
    stopListening,
    toggleListening,
  };
}
