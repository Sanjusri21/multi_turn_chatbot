import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { CheckCircle2, AlertCircle, Info, AlertTriangle } from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';

/**
 * Global toast dispatcher for showing notifications anywhere in the app.
 */
export const toast = {
  success: (message) => {
    window.dispatchEvent(new CustomEvent('zara:toast', { detail: { message, type: 'success' } }));
  },
  error: (message) => {
    window.dispatchEvent(new CustomEvent('zara:toast', { detail: { message, type: 'error' } }));
  },
  info: (message) => {
    window.dispatchEvent(new CustomEvent('zara:toast', { detail: { message, type: 'info' } }));
  },
  warning: (message) => {
    window.dispatchEvent(new CustomEvent('zara:toast', { detail: { message, type: 'warning' } }));
  }
};

export function ToastContainer() {
  let contextToasts = [];
  try {
    const chatCtx = useChatContext();
    if (chatCtx?.toasts) {
      contextToasts = chatCtx.toasts;
    }
  } catch {
    // Safe fallback if rendered outside ChatProvider
  }

  const [eventToasts, setEventToasts] = useState([]);

  useEffect(() => {
    const handleToast = (e) => {
      const { message, type } = e.detail || {};
      if (!message) return;
      const id = Date.now() + Math.random();
      setEventToasts((prev) => [...prev, { id, message, type: type || 'info' }]);
      setTimeout(() => {
        setEventToasts((prev) => prev.filter((t) => t.id !== id));
      }, 4500);
    };

    window.addEventListener('zara:toast', handleToast);
    return () => window.removeEventListener('zara:toast', handleToast);
  }, []);

  const allToasts = [...contextToasts, ...eventToasts];

  const getIcon = (type) => {
    switch (type) {
      case 'success':
        return <CheckCircle2 size={16} color="var(--accent-green, #10b981)" />;
      case 'error':
        return <AlertCircle size={16} color="var(--accent-rose, #f43f5e)" />;
      case 'warning':
        return <AlertTriangle size={16} color="#f59e0b" />;
      default:
        return <Info size={16} color="var(--accent-cyan, #06b6d4)" />;
    }
  };

  return (
    <div className="toast-container">
      <AnimatePresence>
        {allToasts.map((item) => (
          <motion.div
            key={item.id}
            className={`toast ${item.type}`}
            initial={{ opacity: 0, x: 40, scale: 0.9 }}
            animate={{ opacity: 1, x: 0, scale: 1 }}
            exit={{ opacity: 0, x: 20, scale: 0.9 }}
            transition={{ duration: 0.2 }}
          >
            {getIcon(item.type)}
            <span>{item.message}</span>
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  );
}

