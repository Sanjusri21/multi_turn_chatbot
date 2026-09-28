import React, { useState } from 'react';
import { MessageSquare, Edit2, Trash2, Check, X } from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';

export function ConversationItem({ conversation, isActive }) {
  const { setCurrentConversationId, renameConversation, deleteConversation } = useChatContext();
  const [isEditing, setIsEditing] = useState(false);
  const [newTitle, setNewTitle] = useState(conversation.title);

  const handleSelect = () => {
    setCurrentConversationId(conversation.id);
  };

  const handleSaveRename = (e) => {
    e.stopPropagation();
    if (newTitle.trim() && newTitle !== conversation.title) {
      renameConversation(conversation.id, newTitle.trim());
    }
    setIsEditing(false);
  };

  const handleCancelRename = (e) => {
    e.stopPropagation();
    setNewTitle(conversation.title);
    setIsEditing(false);
  };

  const handleDelete = (e) => {
    e.stopPropagation();
    if (window.confirm(`Delete conversation "${conversation.title}"?`)) {
      deleteConversation(conversation.id);
    }
  };

  return (
    <div
      className={`conversation-item ${isActive ? 'active' : ''}`}
      onClick={handleSelect}
    >
      <div className="conv-title-wrapper">
        <MessageSquare size={16} style={{ flexShrink: 0, opacity: isActive ? 1 : 0.6 }} />

        {isEditing ? (
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onClick={(e) => e.stopPropagation()}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleSaveRename(e);
              if (e.key === 'Escape') handleCancelRename(e);
            }}
            autoFocus
            style={{
              background: 'rgba(0, 0, 0, 0.4)',
              border: '1px solid var(--accent-cyan)',
              borderRadius: '4px',
              color: '#fff',
              fontSize: '0.85rem',
              padding: '2px 6px',
              width: '100%',
              outline: 'none',
            }}
          />
        ) : (
          <span className="conv-title" title={conversation.title}>
            {conversation.title}
          </span>
        )}
      </div>

      <div className="conv-actions">
        {isEditing ? (
          <>
            <button className="conv-action-btn" onClick={handleSaveRename} title="Save">
              <Check size={14} color="var(--accent-green)" />
            </button>
            <button className="conv-action-btn" onClick={handleCancelRename} title="Cancel">
              <X size={14} color="var(--accent-rose)" />
            </button>
          </>
        ) : (
          <>
            <button
              className="conv-action-btn"
              onClick={(e) => {
                e.stopPropagation();
                setIsEditing(true);
              }}
              title="Rename"
            >
              <Edit2 size={13} />
            </button>
            <button
              className="conv-action-btn delete"
              onClick={handleDelete}
              title="Delete"
            >
              <Trash2 size={13} />
            </button>
          </>
        )}
      </div>
    </div>
  );
}
