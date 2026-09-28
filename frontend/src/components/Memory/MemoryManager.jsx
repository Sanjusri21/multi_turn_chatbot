import React, { useState, useEffect } from 'react';
import { Modal } from '../UI/Modal';
import { Button } from '../UI/Button';

export function MemoryManager({ isOpen, onClose, initialData, onSave }) {
  const [key, setKey] = useState('');
  const [value, setValue] = useState('');
  const [category, setCategory] = useState('personal');

  const categories = [
    { value: 'personal', label: '👤 Personal' },
    { value: 'education', label: '🎓 Education' },
    { value: 'technology', label: '💻 Technologies' },
    { value: 'project', label: '🚀 Projects' },
    { value: 'goal', label: '🎯 Goals' },
    { value: 'preference', label: '⭐ Preferences' },
    { value: 'other', label: '📋 Other' },
  ];

  useEffect(() => {
    if (initialData) {
      setKey(initialData.key || '');
      setValue(initialData.value || '');
      const rawCat = initialData.category?.toLowerCase() || 'personal';
      const normalizedCat = rawCat === 'identity' ? 'personal' : rawCat === 'skill' ? 'technology' : rawCat === 'interest' ? 'preference' : rawCat;
      setCategory(normalizedCat);
    } else {
      setKey('');
      setValue('');
      setCategory('personal');
    }
  }, [initialData, isOpen]);

  const handleSubmit = (e) => {
    e.preventDefault();
    if (!key.trim() || !value.trim()) return;
    onSave({ key: key.trim(), value: value.trim(), category });
    onClose();
  };

  const inputStyle = {
    width: '100%',
    padding: '10px 14px',
    borderRadius: '8px',
    border: '1px solid var(--border-color)',
    background: 'var(--bg-primary)',
    color: '#fff',
    fontSize: '0.9rem',
    marginBottom: '14px',
    outline: 'none',
    boxSizing: 'border-box',
    fontFamily: 'inherit',
  };

  const labelStyle = {
    display: 'block',
    fontSize: '0.8rem',
    fontWeight: '600',
    color: 'var(--text-secondary)',
    marginBottom: '6px',
    textTransform: 'uppercase',
  };

  return (
    <Modal
      isOpen={isOpen}
      onClose={onClose}
      title={initialData ? 'Edit Persistent Memory' : 'Create New Memory'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            Cancel
          </Button>
          <Button variant="primary" onClick={handleSubmit} disabled={!key.trim() || !value.trim()}>
            Save Memory
          </Button>
        </>
      }
    >
      <form onSubmit={handleSubmit}>
        <div>
          <label style={labelStyle}>Memory Key</label>
          <input
            type="text"
            placeholder="e.g. name, favorite_framework, major"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            style={inputStyle}
            disabled={!!initialData} // Key should remain stable on edit
          />
        </div>

        <div>
          <label style={labelStyle}>Category</label>
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            style={inputStyle}
          >
            {categories.map((cat) => (
              <option key={cat.value} value={cat.value}>
                {cat.label}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label style={labelStyle}>Memory Value</label>
          <textarea
            rows={3}
            placeholder="e.g. Sanju, React, AI & Data Science"
            value={value}
            onChange={(e) => setValue(e.target.value)}
            style={{ ...inputStyle, resize: 'vertical' }}
          />
        </div>
      </form>
    </Modal>
  );
}
