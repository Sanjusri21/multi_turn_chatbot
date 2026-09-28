import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sparkles,
  User,
  Copy,
  Check,
  RotateCcw,
  ThumbsUp,
  ThumbsDown,
  FileText,
  FileSpreadsheet,
  FileCode,
  Image as ImageIcon,
  File as GenericFileIcon,
  Volume2,
  Square,
  Play,
  Pause
} from 'lucide-react';
import { MarkdownRenderer } from './MarkdownRenderer';
import { chatApi } from '../../services/chatApi';
import { useChatContext } from '../../context/ChatContext';

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileIcon(att) {
  const ext = att.filename?.split('.').pop()?.toLowerCase();
  if (att.content_type?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
    return <ImageIcon size={18} className="doc-badge-icon img" />;
  }
  if (att.content_type === 'application/pdf' || ext === 'pdf') {
    return <FileText size={18} className="doc-badge-icon pdf" />;
  }
  if (att.content_type?.includes('csv') || ext === 'csv') {
    return <FileSpreadsheet size={18} className="doc-badge-icon csv" />;
  }
  if (['docx', 'doc'].includes(ext)) {
    return <FileText size={18} className="doc-badge-icon docx" />;
  }
  if (['json', 'md', 'txt'].includes(ext)) {
    return <FileCode size={18} className="doc-badge-icon code" />;
  }
  return <GenericFileIcon size={18} className="doc-badge-icon gen" />;
}

export function MessageBubble({ message, onRegenerate, isLastAssistant, isRegenerating = false }) {
  const isUser = message.role === 'user';
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null); // 'like', 'dislike', null
  const [showMemoriesBadge, setShowMemoriesBadge] = useState(
    Boolean(message.extracted_memories && message.extracted_memories.length > 0)
  );

  const {
    showToast,
    speakMessage,
    stopSpeaking,
    pauseSpeaking,
    resumeSpeaking,
    ttsPlayingMessageId,
    selectedLanguage
  } = useChatContext();
  const isPlayingSpeech = ttsPlayingMessageId === message.id;
  const [isPaused, setIsPaused] = useState(false);
  const token = localStorage.getItem('token');

  // Auto-dismiss memory saved badge after 5 seconds (Requirement 7)
  useEffect(() => {
    if (showMemoriesBadge) {
      const timer = setTimeout(() => {
        setShowMemoriesBadge(false);
      }, 5000);
      return () => clearTimeout(timer);
    }
  }, [showMemoriesBadge]);

  const handleCopy = async () => {
    if (!message.content) return;
    try {
      await navigator.clipboard.writeText(message.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Clipboard copy failed:', err);
    }
  };

  const handleFeedback = async (type) => {
    if (!message.id || message.id.startsWith('temp-') || message.id.startsWith('err-')) return;
    const nextFeedback = feedback === type ? null : type;
    setFeedback(nextFeedback);

    try {
      await chatApi.submitFeedback({
        message_id: message.id,
        feedback: nextFeedback,
      });
      if (nextFeedback) {
        showToast('Thanks for your feedback.', 'info');
      }
    } catch (err) {
      console.error('Failed to submit feedback:', err);
    }
  };

  const formatTime = (ts) => {
    if (!ts) return '';
    try {
      const d = new Date(ts);
      return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch {
      return '';
    }
  };

  const getFileViewUrl = (att) => {
    if (att.file_url) {
      if (att.file_url.startsWith('blob:') || att.file_url.startsWith('data:')) {
        return att.file_url;
      }
      return `${att.file_url}${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    }
    if (att.id) {
      return `/api/files/${att.id}/view${token ? `?token=${encodeURIComponent(token)}` : ''}`;
    }
    return '#';
  };

  const isImageAttachment = (att) => {
    const ext = att.filename?.split('.').pop()?.toLowerCase();
    return att.content_type?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp'].includes(ext);
  };

  return (
    <motion.div
      className={`message-row ${isUser ? 'user' : 'assistant'}`}
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.22, ease: 'easeOut' }}
    >
      {/* Avatar */}
      <div className="message-avatar" title={isUser ? 'You' : 'Zara'}>
        {isUser ? <User size={16} /> : <Sparkles size={16} />}
      </div>

      <div className="message-content-wrapper">
        <div className="message-bubble">
          {/* Display Attachments Above Text Content */}
          {message.attachments && message.attachments.length > 0 && (
            <div className="message-attachments-display-group">
              {message.attachments.map((att, idx) => {
                const isImg = isImageAttachment(att);
                const fileUrl = getFileViewUrl(att);

                if (isImg) {
                  return (
                    <div key={att.id || idx} className="msg-attachment-card image-card">
                      <a
                        href={fileUrl}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="msg-attachment-thumb-link"
                      >
                        <img
                          src={fileUrl}
                          alt={att.filename}
                          className="msg-attachment-thumbnail"
                          loading="lazy"
                        />
                      </a>
                      <div className="msg-attachment-card-info">
                        <span className="msg-attachment-name" title={att.filename}>
                          {att.filename}
                        </span>
                        <span className="msg-attachment-size">
                          {formatFileSize(att.file_size)}
                        </span>
                      </div>
                    </div>
                  );
                }

                return (
                  <div key={att.id || idx} className="msg-attachment-card doc-card">
                    <div className="msg-doc-icon-box">
                      {getFileIcon(att)}
                    </div>
                    <div className="msg-attachment-card-info">
                      <span className="msg-attachment-name" title={att.filename}>
                        {att.filename}
                      </span>
                      <span className="msg-attachment-meta">
                        {att.filename?.split('.').pop()?.toUpperCase() || 'DOCUMENT'} • {formatFileSize(att.file_size)}
                      </span>
                    </div>
                  </div>
                );
              })}
            </div>
          )}

          {/* Text Message Content */}
          {isUser ? (
            <div className="user-message-text">{message.content}</div>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}

          {/* Subtle Memory Used Indicator */}
          {!isUser && message.memory_used && (
            <div
              className="memory-cross-conv-indicator"
              style={{
                marginTop: '8px',
                fontSize: '0.74rem',
                color: 'var(--accent-cyan, #06b6d4)',
                background: 'rgba(6, 182, 212, 0.08)',
                border: '1px solid rgba(6, 182, 212, 0.25)',
                borderRadius: '8px',
                padding: '4px 10px',
                display: 'inline-flex',
                alignItems: 'center',
                gap: '6px',
                fontWeight: 500,
              }}
            >
              <span style={{ fontSize: '0.85rem' }}>🧠</span>
              <span>From memory</span>
            </div>
          )}

          {/* Subtle auto-dismissing Memory Saved Indicator */}
          <AnimatePresence>
            {showMemoriesBadge && message.extracted_memories && message.extracted_memories.length > 0 && (
              <motion.div
                className="extracted-memories-badge-group"
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: 'auto' }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
              >
                {message.extracted_memories.map((mem, idx) => (
                  <div key={idx} className="memory-tag-chip" title="Persistent Long-Term Memory Stored">
                    <Sparkles size={11} className="sparkle-icon" />
                    <span>
                      ✨ Memory saved: <strong>{mem.key}</strong> ({mem.value})
                    </span>
                  </div>
                ))}
              </motion.div>
            )}
          </AnimatePresence>
        </div>

        {/* Footer Bar: Timestamp & Action Controls (Requirements 3, 4, 14) */}
        <div className="message-footer-bar">
          <span className="message-timestamp">{formatTime(message.timestamp)}</span>

          {!isUser && (
            <div className="message-action-buttons">
              {/* Zara Voice Output Controls: [ 🔊 Speak ] or [ ⏸ Pause / ▶ Resume / ⏹ Stop ] */}
              {!isPlayingSpeech ? (
                <button
                  className="msg-action-btn"
                  onClick={() => {
                    setIsPaused(false);
                    speakMessage(message.id, message.content, selectedLanguage);
                  }}
                  title="Zara speak response"
                  type="button"
                >
                  <Volume2 size={13} />
                  <span className="action-btn-label">Speak</span>
                </button>
              ) : (
                <div style={{ display: 'inline-flex', gap: '4px', alignItems: 'center' }}>
                  {isPaused ? (
                    <button
                      className="msg-action-btn active-voice"
                      onClick={() => {
                        resumeSpeaking();
                        setIsPaused(false);
                      }}
                      title="Resume voice playback"
                      type="button"
                      style={{ color: 'var(--accent-cyan, #06b6d4)', borderColor: 'rgba(6, 182, 212, 0.4)' }}
                    >
                      <Play size={12} fill="currentColor" />
                      <span className="action-btn-label">Resume</span>
                    </button>
                  ) : (
                    <button
                      className="msg-action-btn active-voice"
                      onClick={() => {
                        pauseSpeaking();
                        setIsPaused(true);
                      }}
                      title="Pause voice playback"
                      type="button"
                      style={{ color: 'var(--accent-cyan, #06b6d4)', borderColor: 'rgba(6, 182, 212, 0.4)' }}
                    >
                      <Pause size={12} fill="currentColor" />
                      <span className="action-btn-label">Pause</span>
                    </button>
                  )}

                  <button
                    className="msg-action-btn"
                    onClick={() => {
                      stopSpeaking();
                      setIsPaused(false);
                    }}
                    title="Stop voice playback"
                    type="button"
                  >
                    <Square size={12} fill="currentColor" />
                    <span className="action-btn-label">Stop</span>
                  </button>
                </div>
              )}

              {/* Copy Response Button */}
              <button
                className="msg-action-btn"
                onClick={handleCopy}
                title="Copy response"
                type="button"
              >
                {copied ? <Check size={13} color="var(--accent-green, #10b981)" /> : <Copy size={13} />}
                {copied && <span className="action-btn-label">Copied</span>}
              </button>

              {/* Regenerate Button (Shown on assistant messages) */}
              {onRegenerate && (
                <button
                  className="msg-action-btn"
                  onClick={() => onRegenerate(message.id)}
                  title="Regenerate response"
                  type="button"
                  disabled={isRegenerating}
                >
                  <RotateCcw size={13} className={isRegenerating ? 'spin-icon' : ''} />
                  {isRegenerating && <span className="action-btn-label">Regenerating...</span>}
                </button>
              )}

              {/* Thumbs Up Feedback */}
              <button
                className={`msg-action-btn ${feedback === 'like' ? 'active-like' : ''}`}
                onClick={() => handleFeedback('like')}
                title="Helpful response"
                type="button"
              >
                <ThumbsUp size={13} />
              </button>

              {/* Thumbs Down Feedback */}
              <button
                className={`msg-action-btn ${feedback === 'dislike' ? 'active-dislike' : ''}`}
                onClick={() => handleFeedback('dislike')}
                title="Unhelpful response"
                type="button"
              >
                <ThumbsDown size={13} />
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  );
}
