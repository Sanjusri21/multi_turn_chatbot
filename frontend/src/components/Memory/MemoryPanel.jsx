import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Plus, Trash2, X, Brain, Edit2, ShieldAlert } from 'lucide-react';
import { MemoryManager } from './MemoryManager';
import { Button } from '../UI/Button';
import { Modal } from '../UI/Modal';
import { Toggle } from '../UI/Toggle';
import { useMemory } from '../../hooks/useMemory';
import { useChatContext } from '../../context/ChatContext';

export function MemoryPanel({ isOpen, onClose }) {
  const { memories, addMemory, updateMemory, deleteMemory, clearAll, refreshMemories } = useMemory();
  const { userSettings, updateUserSettings } = useChatContext();

  const [isManagerOpen, setIsManagerOpen] = useState(false);
  const [editingMemory, setEditingMemory] = useState(null);
  const [isConfirmClearOpen, setIsConfirmClearOpen] = useState(false);

  // Auto-refresh memories from backend whenever the panel is opened
  React.useEffect(() => {
    if (isOpen) {
      refreshMemories();
    }
  }, [isOpen, refreshMemories]);

  if (!isOpen) return null;

  // Requirement 9: Organize memories into standardized categories
  const categories = [
    {
      title: '👤 Personal',
      filter: (m) => ['personal', 'identity'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    },
    {
      title: '🎓 Education',
      filter: (m) => ['education'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    },
    {
      title: '💻 Technologies',
      filter: (m) => ['technology', 'technologies', 'skill', 'skills'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    },
    {
      title: '🚀 Projects',
      filter: (m) => ['project', 'projects'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    },
    {
      title: '🎯 Goals',
      filter: (m) => ['goal', 'goals'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    },
    {
      title: '⭐ Preferences',
      filter: (m) => ['preference', 'preferences', 'interest', 'interests'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    },
    {
      title: '📋 Other',
      filter: (m) => !['personal', 'identity', 'education', 'technology', 'technologies', 'skill', 'skills', 'project', 'projects', 'goal', 'goals', 'preference', 'preferences', 'interest', 'interests'].includes(m.category?.toLowerCase() || m.memory_type?.toLowerCase()),
    }
  ];

  const handleEdit = (memory) => {
    setEditingMemory(memory);
    setIsManagerOpen(true);
  };

  const handleSave = (data) => {
    if (editingMemory) {
      updateMemory(editingMemory.id, data);
    } else {
      addMemory(data);
    }
    setEditingMemory(null);
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <motion.div
        className="memory-slideout-panel"
        onClick={(e) => e.stopPropagation()}
        initial={{ x: '100%', opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        exit={{ x: '100%', opacity: 0 }}
        transition={{ type: 'spring', damping: 25, stiffness: 280 }}
      >
        {/* Header */}
        <div className="memory-panel-header">
          <div className="memory-panel-title-group">
            <div className="memory-brain-icon">
              <Brain size={20} color="var(--accent-cyan, #00f2fe)" />
            </div>
            <div>
              <h3>Persistent Memories</h3>
              <p className="memory-panel-subtext">
                Zara retains useful personal facts across all conversations.
              </p>
            </div>
          </div>

          <button className="memory-close-btn" onClick={onClose} title="Close panel">
            <X size={20} />
          </button>
        </div>

        {/* Settings Toggles inside Memory Panel */}
        <div className="memory-panel-controls">
          <div className="memory-control-toggle">
            <Toggle
              label="Enable memory"
              checked={userSettings?.memory_enabled !== false}
              onChange={(val) => updateUserSettings({ memory_enabled: val })}
            />
          </div>

          <div className="memory-control-toggle">
            <Toggle
              label="Automatically save useful info"
              checked={userSettings?.auto_save_memory !== false}
              onChange={(val) => updateUserSettings({ auto_save_memory: val })}
              disabled={userSettings?.memory_enabled === false}
            />
          </div>
        </div>

        {/* Action Bar */}
        <div className="memory-panel-actions">
          <Button
            size="sm"
            variant="primary"
            icon={Plus}
            onClick={() => {
              setEditingMemory(null);
              setIsManagerOpen(true);
            }}
          >
            Add Memory
          </Button>

          {memories.length > 0 && (
            <Button
              size="sm"
              variant="danger"
              icon={Trash2}
              onClick={() => setIsConfirmClearOpen(true)}
            >
              Forget All
            </Button>
          )}
        </div>

        {/* Categorized Memory Lists */}
        <div className="memory-panel-scroll-area">
          {memories.length === 0 ? (
            <div className="memory-empty-state">
              <Brain size={44} style={{ opacity: 0.35, marginBottom: 12 }} />
              <h4>No memories recorded yet</h4>
              <p>
                As you chat with Zara, she will extract your name, education, technologies, and projects. You can also add memories manually above!
              </p>
            </div>
          ) : (
            categories.map(({ title, filter }) => {
              const items = memories.filter(filter);
              if (items.length === 0) return null;
              return (
                <div key={title} className="memory-category-block">
                  <div className="memory-category-heading">{title}</div>
                  <div className="memory-items-list">
                    {items.map((mem) => (
                      <div key={mem.id || mem.key} className="memory-list-item">
                        <div className="memory-item-content">
                          <span className="memory-item-key">{(mem.key || 'fact').replace(/_/g, ' ')}</span>
                          <span className="memory-item-val">{mem.value || mem.memory_text}</span>
                        </div>
                        <div className="memory-item-actions">
                          <button
                            className="memory-action-btn"
                            onClick={() => handleEdit(mem)}
                            title="Edit memory"
                          >
                            <Edit2 size={13} />
                          </button>
                          <button
                            className="memory-action-btn delete"
                            onClick={() => deleteMemory(mem.id)}
                            title="Forget memory"
                          >
                            <Trash2 size={13} />
                          </button>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* Create/Edit Modal */}
        <MemoryManager
          isOpen={isManagerOpen}
          onClose={() => {
            setIsManagerOpen(false);
            setEditingMemory(null);
          }}
          initialData={editingMemory}
          onSave={handleSave}
        />

        {/* Clear All Confirmation Modal */}
        <Modal
          isOpen={isConfirmClearOpen}
          onClose={() => setIsConfirmClearOpen(false)}
          title="Forget All Memories?"
          footer={
            <>
              <Button variant="secondary" onClick={() => setIsConfirmClearOpen(false)}>
                Cancel
              </Button>
              <Button
                variant="danger"
                onClick={() => {
                  clearAll();
                  setIsConfirmClearOpen(false);
                }}
              >
                Forget All Memories
              </Button>
            </>
          }
        >
          <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
            <ShieldAlert size={24} color="var(--accent-rose, #f43f5e)" style={{ flexShrink: 0 }} />
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
              Are you sure you want to forget all personal memories? MemoryBot will clear everything it learned about you across all past sessions.
            </p>
          </div>
        </Modal>
      </motion.div>
    </div>
  );
}
