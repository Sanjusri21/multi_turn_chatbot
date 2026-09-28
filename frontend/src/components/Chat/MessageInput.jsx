import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  Send,
  Paperclip,
  X,
  Image as ImageIcon,
  FileText,
  FileSpreadsheet,
  FileCode,
  File as GenericFileIcon,
  Loader2,
  AlertCircle,
  Square
} from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';
import { fileApi } from '../../services/fileApi';
import { useVoiceInput } from '../../hooks/useVoiceInput';
import { VoiceInput, VoiceIndicator } from '../Voice/VoiceInput';

const ALLOWED_EXTENSIONS = ['png', 'jpg', 'jpeg', 'webp', 'pdf', 'txt', 'csv', 'docx', 'json', 'md'];
const MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024; // 10 MB

function formatFileSize(bytes) {
  if (!bytes || bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function getFileBadgeIcon(contentType, filename) {
  const ext = filename?.split('.').pop()?.toLowerCase();
  if (contentType?.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp'].includes(ext)) {
    return <ImageIcon size={15} className="file-type-icon img" />;
  }
  if (contentType === 'application/pdf' || ext === 'pdf') {
    return <FileText size={15} className="file-type-icon pdf" />;
  }
  if (contentType?.includes('csv') || ext === 'csv') {
    return <FileSpreadsheet size={15} className="file-type-icon csv" />;
  }
  if (['docx', 'doc'].includes(ext)) {
    return <FileText size={15} className="file-type-icon docx" />;
  }
  if (['json', 'md', 'txt'].includes(ext)) {
    return <FileCode size={15} className="file-type-icon code" />;
  }
  return <GenericFileIcon size={15} className="file-type-icon gen" />;
}

export function MessageInput({ onSendMessage, disabled }) {
  const [text, setText] = useState('');
  const [attachments, setAttachments] = useState([]);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadError, setUploadError] = useState(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const textareaRef = useRef(null);
  const fileInputRef = useRef(null);
  const dragCounterRef = useRef(0);

  const {
    triggerRotoBotReaction,
    rotoBotState,
    userSettings,
    showToast,
    isSending,
    stopGenerating,
    selectedLanguage,
  } = useChatContext();

  // Voice Recognition Hook connected with selectedLanguage
  const {
    status: voiceStatus,
    isListening,
    isSupported,
    errorMessage: voiceError,
    toggleListening,
    stopListening
  } = useVoiceInput({
    language: selectedLanguage,
    onTranscript: (fullText) => {
      setText(fullText);
      if (rotoBotState === 'IDLE' || rotoBotState === 'SLEEPING') {
        triggerRotoBotReaction('LISTENING', "Zara is listening! 🎙️", 3000);
      }
    },
    onError: (err) => {
      showToast(err, 'error');
    }
  });

  const handleVoiceToggle = (e) => {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (!isSupported) {
      showToast('Voice input is not supported in this browser. Try Google Chrome or Microsoft Edge.', 'error');
      return;
    }
    toggleListening(text);
  };

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = `${Math.min(textareaRef.current.scrollHeight, 140)}px`;
    }
  }, [text]);

  const handleChange = (e) => {
    setText(e.target.value);
    if (e.target.value.trim().length > 0 && (rotoBotState === 'IDLE' || rotoBotState === 'SLEEPING')) {
      triggerRotoBotReaction('LISTENING', "I'm listening! 👂", 4000);
    }
  };

  const handleKeyDown = (e) => {
    const enterBehavior = userSettings?.enter_behavior || 'send';
    if (enterBehavior === 'send') {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    } else {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        handleSubmit();
      }
    }
  };

  // Upload a single file to backend
  const uploadSingleFile = async (file) => {
    // 1. Validate file size
    if (file.size > MAX_FILE_SIZE_BYTES) {
      throw new Error(`"${file.name}" exceeds the 10 MB maximum file size limit.`);
    }

    // 2. Validate file extension
    const ext = file.name.split('.').pop()?.toLowerCase();
    if (!ext || !ALLOWED_EXTENSIONS.includes(ext)) {
      throw new Error(
        `"${file.name}" has an unsupported format. Supported: PNG, JPG, JPEG, WEBP, PDF, TXT, CSV, DOCX, JSON, MD.`
      );
    }

    // 3. Perform upload
    const uploadedData = await fileApi.uploadFile(file);

    // Create local object URL for instant image preview if image
    let previewUrl = uploadedData.file_url;
    if (file.type.startsWith('image/')) {
      try {
        previewUrl = URL.createObjectURL(file);
      } catch (e) {
        // fallback
      }
    }

    return {
      id: uploadedData.id,
      filename: uploadedData.filename,
      content_type: uploadedData.content_type,
      file_size: uploadedData.file_size,
      file_url: previewUrl,
      is_image: file.type.startsWith('image/') || ['png', 'jpg', 'jpeg', 'webp'].includes(ext),
    };
  };

  // Process incoming files from file picker, drag-and-drop, or paste
  const handleFilesSelected = async (fileList) => {
    if (!fileList || fileList.length === 0) return;
    setUploadError(null);
    setIsUploading(true);

    const filesArray = Array.from(fileList);
    const newAttachments = [];

    try {
      for (const file of filesArray) {
        const item = await uploadSingleFile(file);
        newAttachments.push(item);
      }
      setAttachments((prev) => [...prev, ...newAttachments]);
      showToast(`Uploaded ${newAttachments.length} file(s)`, 'success');
    } catch (err) {
      console.error('File upload error:', err);
      const msg = err.message || 'Failed to upload file. Please try again.';
      setUploadError(msg);
      showToast(msg, 'error');
    } finally {
      setIsUploading(false);
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
    }
  };

  const handleRemoveAttachment = (idToRemove) => {
    setAttachments((prev) => prev.filter((a) => a.id !== idToRemove));
  };

  // Drag and Drop handlers
  const handleDragEnter = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current += 1;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  };

  const handleDragLeave = (e) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current -= 1;
    if (dragCounterRef.current <= 0) {
      setIsDragOver(false);
      dragCounterRef.current = 0;
    }
  };

  const handleDragOver = (e) => {
    e.preventDefault();
    e.stopPropagation();
  };

  const handleDrop = (e) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
    dragCounterRef.current = 0;

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      handleFilesSelected(e.dataTransfer.files);
    }
  };

  // Clipboard Paste (Ctrl+V) for images
  const handlePaste = useCallback((e) => {
    const items = e.clipboardData?.items;
    if (!items) return;

    for (let i = 0; i < items.length; i++) {
      if (items[i].type.indexOf('image') !== -1) {
        const file = items[i].getAsFile();
        if (file) {
          const timestamp = new Date().toISOString().replace(/[:.]/g, '-');
          const ext = file.type.split('/')[1] || 'png';
          const namedFile = new File([file], `pasted-image-${timestamp}.${ext}`, { type: file.type });
          handleFilesSelected([namedFile]);
        }
      }
    }
  }, []);

  useEffect(() => {
    window.addEventListener('paste', handlePaste);
    return () => {
      window.removeEventListener('paste', handlePaste);
    };
  }, [handlePaste]);

  const handleSubmit = () => {
    if ((!text.trim() && attachments.length === 0) || disabled || isUploading || isSending) return;

    if (isListening) {
      stopListening();
    }

    onSendMessage(text, attachments);
    setText('');
    setAttachments([]);
    setUploadError(null);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const isSendDisabled = (!text.trim() && attachments.length === 0) || disabled || isUploading || isSending;

  return (
    <div
      className={`chat-input-area ${isDragOver ? 'drag-active' : ''}`}
      onDragEnter={handleDragEnter}
      onDragLeave={handleDragLeave}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
    >
      {/* Drag & Drop Visual Overlay */}
      {isDragOver && (
        <div className="chat-dropzone-overlay">
          <div className="dropzone-content">
            <Paperclip size={32} className="dropzone-icon" />
            <p className="dropzone-title">Drop files here</p>
            <span className="dropzone-sub">Upload documents or images to discuss</span>
          </div>
        </div>
      )}

      {/* Hidden file input */}
      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".png,.jpg,.jpeg,.webp,.pdf,.txt,.csv,.docx,.json,.md"
        style={{ display: 'none' }}
        onChange={(e) => handleFilesSelected(e.target.files)}
      />

      <div className="chat-input-card">
        {/* Attachment Previews Area (above input text) */}
        {attachments.length > 0 && (
          <div className="chat-attachment-preview-bar">
            {attachments.map((att) => (
              <div key={att.id} className="attachment-chip-card">
                {att.is_image ? (
                  <div className="attachment-img-preview">
                    <img src={att.file_url} alt={att.filename} />
                  </div>
                ) : (
                  <div className="attachment-file-icon">
                    {getFileBadgeIcon(att.content_type, att.filename)}
                  </div>
                )}
                <div className="attachment-info-col">
                  <span className="attachment-filename" title={att.filename}>
                    {att.filename}
                  </span>
                  <span className="attachment-meta">
                    {att.filename.split('.').pop()?.toUpperCase()} • {formatFileSize(att.file_size)}
                  </span>
                </div>
                <button
                  type="button"
                  className="attachment-remove-btn"
                  onClick={() => handleRemoveAttachment(att.id)}
                  title="Remove attachment"
                  aria-label={`Remove ${att.filename}`}
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Uploading Spinner Indicator */}
        {isUploading && (
          <div className="chat-uploading-indicator">
            <Loader2 size={15} className="spinner-icon" />
            <span>Processing and analyzing attachment...</span>
          </div>
        )}

        {/* Upload or Voice Error Banner */}
        {(uploadError || voiceError) && (
          <div className="chat-input-error-banner">
            <AlertCircle size={14} />
            <span>{uploadError || voiceError}</span>
            <button
              type="button"
              className="error-dismiss-btn"
              onClick={() => {
                setUploadError(null);
              }}
            >
              <X size={12} />
            </button>
          </div>
        )}

        {/* Main Dock: [ + / Attach ] [ Textarea ] [ Mic ] [ Send ] */}
        <div className="chat-input-dock">
          {/* 1. Attachment Button */}
          <button
            type="button"
            className="input-action-btn attach-btn"
            onClick={() => fileInputRef.current?.click()}
            disabled={disabled || isUploading}
            title="Attach documents or images (Max 10 MB)"
            aria-label="Attach file"
          >
            <Paperclip size={18} />
          </button>

          {/* 2. Text Input Area */}
          <div className="input-textarea-container">
            <textarea
              ref={textareaRef}
              className="chat-textarea"
              rows={1}
              placeholder={
                isListening
                  ? "Listening to your voice..."
                  : "Ask anything, summarize a document, or analyze an image..."
              }
              value={text}
              onChange={handleChange}
              onKeyDown={handleKeyDown}
              disabled={disabled}
            />

            {/* Inline voice waveform when recording */}
            <VoiceIndicator isListening={isListening} />
          </div>

          {/* 3. Microphone Button */}
          <VoiceInput
            status={voiceStatus}
            isListening={isListening}
            isSupported={isSupported}
            onToggle={handleVoiceToggle}
            disabled={disabled || isUploading}
          />

          {/* 4. Send or Stop Button */}
          {isSending ? (
            <button
              type="button"
              className="chat-send-btn stop-generating-btn"
              onClick={stopGenerating}
              title="Stop generating"
              aria-label="Stop generating"
            >
              <Square size={13} fill="currentColor" />
            </button>
          ) : (
            <button
              type="button"
              className="chat-send-btn"
              onClick={handleSubmit}
              disabled={isSendDisabled}
              title="Send message (Enter)"
              aria-label="Send message"
            >
              <Send size={16} />
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
