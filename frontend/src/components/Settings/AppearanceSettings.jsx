import React from 'react';
import { Toggle } from '../UI/Toggle';
import { Sun, Moon, Monitor } from 'lucide-react';

export function AppearanceSettings({ settings, onUpdate }) {
  const currentTheme = settings.theme || 'dark';

  const themeOptions = [
    { value: 'dark', label: 'Dark', icon: Moon },
    { value: 'light', label: 'Light', icon: Sun },
    { value: 'system', label: 'System', icon: Monitor },
  ];

  return (
    <div className="settings-section">
      <h3 className="settings-section-title">Appearance & Theme</h3>
      <p className="settings-section-desc">Customize the visual theme, accent colors, and interface animations.</p>

      {/* Theme Selection */}
      <div className="settings-field-group">
        <label className="form-label">Theme</label>
        <div className="theme-toggle-grid">
          {themeOptions.map((opt) => {
            const Icon = opt.icon;
            const isSelected = currentTheme === opt.value;
            return (
              <button
                key={opt.value}
                type="button"
                className={`theme-card-btn ${isSelected ? 'active' : ''}`}
                onClick={() => onUpdate({ theme: opt.value })}
              >
                <Icon size={20} />
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Animations Toggle */}
      <div className="settings-field-group" style={{ marginTop: 24 }}>
        <div className="settings-toggle-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Interface Animations</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Enable smooth micro-animations and floating physics.
            </div>
          </div>
          <Toggle
            checked={settings.animations_enabled !== false}
            onChange={(val) => onUpdate({ animations_enabled: val })}
          />
        </div>
      </div>

      {/* Floating Robot Mascot Toggle */}
      <div className="settings-field-group" style={{ marginTop: 20 }}>
        <div className="settings-toggle-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Floating Robot Mascot</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Display the interactive animated floating robot in your chat workspace.
            </div>
          </div>
          <Toggle
            checked={settings.show_floating_robot !== false}
            onChange={(val) => onUpdate({ show_floating_robot: val })}
          />
        </div>
      </div>
    </div>
  );
}
