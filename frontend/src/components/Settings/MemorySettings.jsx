import React from 'react';
import { Toggle } from '../UI/Toggle';
import { Button } from '../UI/Button';
import { Bookmark, ExternalLink } from 'lucide-react';

export function MemorySettings({ settings, onUpdate, onOpenMemoryPanel }) {
  return (
    <div className="settings-section">
      <h3 className="settings-section-title">Memory & Personalization</h3>
      <p className="settings-section-desc">
        Control how MemoryBot extracts, stores, and references your personal facts across conversations.
      </p>

      {/* Enable Memory Toggle */}
      <div className="settings-field-group">
        <div className="settings-toggle-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Enable Memory</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Allow MemoryBot to access stored personal facts in new conversations.
            </div>
          </div>
          <Toggle
            checked={settings.memory_enabled !== false}
            onChange={(val) => onUpdate({ memory_enabled: val })}
          />
        </div>
      </div>

      {/* Auto Save Memory Toggle */}
      <div className="settings-field-group" style={{ marginTop: 20 }}>
        <div className="settings-toggle-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>
              Automatically Save Useful Information
            </div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Let Zara automatically detect and save facts like your name, skills, and goals.
            </div>
          </div>
          <Toggle
            checked={settings.auto_save_memory !== false}
            onChange={(val) => onUpdate({ auto_save_memory: val })}
            disabled={settings.memory_enabled === false}
          />
        </div>
      </div>

      {/* Manage Memories Action */}
      <div style={{ marginTop: 28, paddingTop: 18, borderTop: '1px solid var(--border-color)' }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Manage Stored Memories</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              View, edit, or delete the individual facts currently stored about you.
            </div>
          </div>
          <Button
            variant="secondary"
            size="sm"
            icon={ExternalLink}
            onClick={onOpenMemoryPanel}
          >
            Manage Memories
          </Button>
        </div>
      </div>
    </div>
  );
}
