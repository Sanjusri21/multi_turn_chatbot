import React from 'react';
import { Mic, Loader2, AlertCircle } from 'lucide-react';
import '../../styles/voice.css';

export function VoiceInput({ isListening, status = 'idle', onToggle, disabled = false, isSupported = true }) {
  const handleClick = (e) => {
    e.preventDefault();
    e.stopPropagation();
    if (onToggle) {
      onToggle(e);
    }
  };

  const getTitle = () => {
    if (!isSupported) {
      return 'Voice input is not supported in this browser. Try Google Chrome or Microsoft Edge.';
    }
    if (status === 'error') {
      return 'Microphone error. Click to retry.';
    }
    if (status === 'processing') {
      return 'Processing speech...';
    }
    if (status === 'listening' || isListening) {
      return 'Listening... (Click to stop)';
    }
    return 'Voice input (Speech to text)';
  };

  const effectiveStatus = status !== 'idle' ? status : (isListening ? 'listening' : 'idle');

  return (
    <button
      type="button"
      className={`voice-btn ${effectiveStatus === 'listening' ? 'recording' : ''} ${effectiveStatus === 'error' ? 'error' : ''}`}
      onClick={handleClick}
      disabled={disabled}
      title={getTitle()}
      aria-label={getTitle()}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        justifyContent: 'center',
      }}
    >
      {effectiveStatus === 'listening' ? (
        <span
          className="voice-recording-dot"
          style={{
            display: 'inline-block',
            width: 12,
            height: 12,
            borderRadius: '50%',
            backgroundColor: '#ef4444',
            boxShadow: '0 0 10px rgba(239, 68, 68, 0.9)',
          }}
          title="Listening..."
        />
      ) : effectiveStatus === 'processing' ? (
        <Loader2 size={18} className="spinner-icon" style={{ color: 'var(--accent-cyan, #06b6d4)' }} />
      ) : effectiveStatus === 'error' ? (
        <AlertCircle size={18} style={{ color: '#ef4444' }} />
      ) : (
        <Mic size={18} style={{ opacity: isSupported ? 1 : 0.4 }} />
      )}
    </button>
  );
}

export function VoiceIndicator({ isListening }) {
  if (!isListening) return null;

  return (
    <div className="voice-recording-indicator">
      <span className="voice-waveform">
        <span className="voice-waveform-bar" />
        <span className="voice-waveform-bar" />
        <span className="voice-waveform-bar" />
        <span className="voice-waveform-bar" />
        <span className="voice-waveform-bar" />
      </span>
      <span>Listening...</span>
    </div>
  );
}
