import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Cpu, 
  CheckCircle2, 
  Layers, 
  FileText, 
  Bookmark, 
  Clock, 
  Key, 
  Eye, 
  X, 
  RefreshCw,
  Sparkles
} from 'lucide-react';
import { chatApi } from '../../services/chatApi';
import { useChatContext } from '../../context/ChatContext';

export function MemoryDebugger() {
  const { currentConversationId } = useChatContext();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [isContextModalOpen, setIsContextModalOpen] = useState(false);

  const fetchDebugData = async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await chatApi.getDebugContext(currentConversationId);
      setData(result);
    } catch (err) {
      console.error('Failed to load debug context:', err);
      setError(err.message || 'Failed to fetch debug context.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDebugData();
  }, [currentConversationId]);

  if (loading) {
    return (
      <div className="settings-section" style={{ textAlign: 'center', padding: '40px 0' }}>
        <RefreshCw size={24} className="spin-icon" style={{ color: 'var(--accent-cyan)' }} />
        <p style={{ marginTop: '12px', color: 'var(--text-secondary)' }}>Loading LLM Context Inspection Data...</p>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="settings-section">
        <h3 className="settings-section-title">Memory Debugger</h3>
        <p style={{ color: 'var(--accent-red, #ef4444)' }}>{error || 'No debug data available.'}</p>
        <button
          className="btn-secondary"
          onClick={fetchDebugData}
          style={{ marginTop: '12px', padding: '6px 14px' }}
        >
          Retry
        </button>
      </div>
    );
  }

  return (
    <div className="settings-section memory-debugger-root">
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px' }}>
        <div>
          <h3 className="settings-section-title" style={{ margin: 0 }}>Memory Debugger</h3>
          <p className="settings-section-desc" style={{ margin: '4px 0 0' }}>
            Real-time inspection of tokens, memory blocks, and prompts sent to the LLM.
          </p>
        </div>
        <button
          className="btn-icon"
          onClick={fetchDebugData}
          title="Refresh Debug Data"
          style={{
            background: 'rgba(255, 255, 255, 0.05)',
            border: '1px solid var(--border-color)',
            borderRadius: '6px',
            padding: '6px 10px',
            color: 'var(--text-secondary)',
            cursor: 'pointer',
            display: 'flex',
            alignItems: 'center',
            gap: '6px',
            fontSize: '0.8rem'
          }}
        >
          <RefreshCw size={13} />
          <span>Refresh</span>
        </button>
      </div>

      {/* 1. LLM Provider & Model & Usage */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Cpu size={16} color="var(--accent-cyan, #00f2fe)" />
            <span style={{ fontWeight: 600, fontSize: '0.9rem' }}>LLM Provider:</span>
          </div>
          <span style={badgeStyle}>{data.llm_provider}</span>
        </div>

        <div style={cardRowStyle}>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Model</span>
          <span style={{ fontFamily: 'monospace', fontSize: '0.85rem', color: '#38bdf8' }}>{data.model_name}</span>
        </div>

        <div style={cardRowStyle}>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.85rem' }}>Context Usage</span>
          <span style={{ fontWeight: 600, fontSize: '0.85rem' }}>
            {data.context_usage.current_messages} / {data.context_usage.max_messages} messages
          </span>
        </div>
      </div>

      {/* 2. System Prompt Status */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <CheckCircle2 size={16} color="var(--accent-green, #10b981)" />
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>SYSTEM PROMPT</span>
          </div>
          <span style={{ color: 'var(--accent-green, #10b981)', fontSize: '0.82rem', fontWeight: 600 }}>✓ Loaded</span>
        </div>
      </div>

      {/* 3. User Response Style Preference */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} color="var(--accent-purple, #a855f7)" />
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>RESPONSE STYLE</span>
          </div>
          <span style={{ textTransform: 'capitalize', color: 'var(--accent-purple, #a855f7)', fontWeight: 600, fontSize: '0.82rem' }}>
            {data.user_preferences?.response_style || 'Balanced'}
          </span>
        </div>
        <p style={{ margin: '6px 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
          {data.user_preferences?.instructions}
        </p>
      </div>

      {/* 4. Long-Term Memory */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Bookmark size={16} color="var(--accent-cyan, #00f2fe)" />
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>LONG-TERM MEMORY</span>
          </div>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            {data.memories.length} fact(s) injected
          </span>
        </div>

        {data.memories.length > 0 ? (
          <div style={{ marginTop: '8px', display: 'flex', flexDirection: 'column', gap: '5px' }}>
            {data.memories.map((m, idx) => (
              <div key={idx} style={{ fontSize: '0.82rem', display: 'flex', alignItems: 'center', gap: '6px' }}>
                <span style={{ color: 'var(--accent-green, #10b981)' }}>✓</span>
                <strong style={{ color: 'var(--text-primary)', textTransform: 'capitalize' }}>{m.key}:</strong>
                <span style={{ color: 'var(--text-secondary)' }}>{m.value}</span>
                <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginLeft: 'auto' }}>[{m.category}]</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ margin: '6px 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            No persistent memories stored yet.
          </p>
        )}
      </div>

      {/* 5. Conversation Summary */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <FileText size={16} color="#eab308" />
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>CONVERSATION SUMMARY</span>
          </div>
          <span style={{ color: data.conversation_summary ? 'var(--accent-green, #10b981)' : 'var(--text-secondary)', fontSize: '0.82rem', fontWeight: 600 }}>
            {data.conversation_summary ? '✓ Available' : 'None yet'}
          </span>
        </div>
        {data.conversation_summary && (
          <p style={{ margin: '6px 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
            "{data.conversation_summary}"
          </p>
        )}
      </div>

      {/* 6. Important Keywords */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Key size={16} color="#ec4899" />
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>IMPORTANT KEYWORDS</span>
          </div>
          <span style={{ color: 'var(--text-secondary)', fontSize: '0.82rem' }}>
            {data.keywords?.length || 0} tracked
          </span>
        </div>
        {data.keywords && data.keywords.length > 0 ? (
          <div style={{ marginTop: '8px', display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
            {data.keywords.map((kw, idx) => (
              <span
                key={idx}
                style={{
                  background: 'rgba(236, 72, 153, 0.1)',
                  border: '1px solid rgba(236, 72, 153, 0.25)',
                  color: '#f472b6',
                  fontSize: '0.76rem',
                  padding: '2px 8px',
                  borderRadius: '12px'
                }}
              >
                {kw}
              </span>
            ))}
          </div>
        ) : (
          <p style={{ margin: '6px 0 0', fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
            Keywords extracted as topics emerge.
          </p>
        )}
      </div>

      {/* 7. Recent Messages */}
      <div className="debug-card" style={cardStyle}>
        <div style={cardRowStyle}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Clock size={16} color="#60a5fa" />
            <span style={{ fontWeight: 600, fontSize: '0.88rem' }}>RECENT MESSAGES</span>
          </div>
          <span style={{ color: 'var(--accent-green, #10b981)', fontSize: '0.82rem', fontWeight: 600 }}>
            ✓ {data.recent_messages?.length || 0} messages included
          </span>
        </div>
      </div>

      {/* 8. Final Context Inspection Action */}
      <div style={{ marginTop: '16px', textAlign: 'center' }}>
        <button
          className="btn-primary"
          onClick={() => setIsContextModalOpen(true)}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 20px',
            background: 'var(--gradient-primary, linear-gradient(135deg, #00f2fe 0%, #4facfe 100%))',
            color: '#050b14',
            fontWeight: 700,
            border: 'none',
            borderRadius: 'var(--radius-md, 8px)',
            cursor: 'pointer'
          }}
        >
          <Eye size={16} />
          <span>View Final Context</span>
        </button>
      </div>

      {/* Final Context Modal Viewer */}
      <AnimatePresence>
        {isContextModalOpen && (
          <div
            className="modal-overlay"
            style={{ zIndex: 9999, background: 'rgba(0, 0, 0, 0.8)' }}
            onClick={() => setIsContextModalOpen(false)}
          >
            <motion.div
              style={{
                background: '#0d131f',
                border: '1px solid var(--border-color)',
                borderRadius: '12px',
                width: '90%',
                maxWidth: '750px',
                maxHeight: '85vh',
                display: 'flex',
                flexDirection: 'column',
                overflow: 'hidden',
                boxShadow: '0 20px 50px rgba(0, 0, 0, 0.6)'
              }}
              onClick={(e) => e.stopPropagation()}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.95 }}
            >
              <div
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '14px 20px',
                  borderBottom: '1px solid var(--border-color)',
                  background: 'rgba(255, 255, 255, 0.02)'
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <Eye size={16} color="var(--accent-cyan, #00f2fe)" />
                  <span style={{ fontWeight: 700, fontSize: '0.95rem' }}>Final Context Sent to LLM</span>
                </div>
                <button
                  onClick={() => setIsContextModalOpen(false)}
                  style={{ background: 'transparent', border: 'none', color: 'var(--text-secondary)', cursor: 'pointer' }}
                >
                  <X size={18} />
                </button>
              </div>

              <div style={{ padding: '16px 20px', overflowY: 'auto', flex: 1 }}>
                <pre
                  style={{
                    background: '#070a10',
                    border: '1px solid rgba(255, 255, 255, 0.08)',
                    borderRadius: '8px',
                    padding: '14px',
                    color: '#e2e8f0',
                    fontSize: '0.82rem',
                    lineHeight: 1.55,
                    fontFamily: 'monospace',
                    whiteSpace: 'pre-wrap',
                    wordBreak: 'break-word'
                  }}
                >
                  {data.final_context}
                </pre>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

const cardStyle = {
  background: 'rgba(255, 255, 255, 0.03)',
  border: '1px solid var(--border-color, rgba(255, 255, 255, 0.08))',
  borderRadius: '8px',
  padding: '12px 16px',
  marginBottom: '10px'
};

const cardRowStyle = {
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'space-between',
  gap: '12px'
};

const badgeStyle = {
  background: 'rgba(0, 242, 254, 0.1)',
  color: 'var(--accent-cyan, #00f2fe)',
  padding: '2px 8px',
  borderRadius: '4px',
  fontSize: '0.8rem',
  fontWeight: 600
};
