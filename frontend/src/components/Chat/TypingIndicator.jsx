import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Globe, BookOpen, Search, Compass } from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';

export function TypingIndicator() {
  const { searchingStatus } = useChatContext();

  const getStatusConfig = () => {
    if (!searchingStatus || !searchingStatus.stage) {
      return {
        icon: <Sparkles size={15} className="typing-status-icon sparkles" />,
        label: 'Generating...',
        badgeClass: 'status-generating'
      };
    }

    switch (searchingStatus.stage) {
      case 'searching':
        return {
          icon: <Search size={15} className="typing-status-icon spin-slow" />,
          label: searchingStatus.message || '🔎 Searching the web...',
          badgeClass: 'status-searching'
        };
      case 'reading_sources':
        return {
          icon: <BookOpen size={15} className="typing-status-icon pulse-subtle" />,
          label: searchingStatus.message || '📚 Reading current sources...',
          badgeClass: 'status-reading'
        };
      case 'generating':
        return {
          icon: <Sparkles size={15} className="typing-status-icon sparkles" />,
          label: searchingStatus.message || '✦ Generating answer...',
          badgeClass: 'status-generating'
        };
      case 'thinking':
        return {
          icon: <Compass size={15} className="typing-status-icon spin-slow" />,
          label: searchingStatus.message || '✦ Thinking...',
          badgeClass: 'status-thinking'
        };
      case 'fallback':
        return {
          icon: <Sparkles size={15} className="typing-status-icon sparkles" />,
          label: searchingStatus.message || 'Gemini unavailable — using backup AI...',
          badgeClass: 'status-fallback'
        };
      default:
        return {
          icon: <Sparkles size={15} className="typing-status-icon sparkles" />,
          label: searchingStatus.message || 'Generating...',
          badgeClass: 'status-generating'
        };
    }
  };

  const statusConfig = getStatusConfig();

  return (
    <motion.div
      className="message-row assistant typing-row"
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: 10 }}
      transition={{ duration: 0.2 }}
    >
      <div className="message-avatar">
        <Sparkles size={16} />
      </div>
      <div className={`typing-indicator-container ${statusConfig.badgeClass}`}>
        <AnimatePresence mode="wait">
          <motion.div
            key={statusConfig.label}
            className="typing-status-badge"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
            transition={{ duration: 0.18 }}
            style={{ display: 'inline-flex', alignItems: 'center', gap: '6px' }}
          >
            {statusConfig.icon}
            <span className="typing-label">{statusConfig.label}</span>
          </motion.div>
        </AnimatePresence>

        <div className="typing-dots-wrapper">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
        </div>
      </div>
    </motion.div>
  );
}
