import React from 'react';
import { Dropdown } from '../UI/Dropdown';

export function GeneralSettings({ settings, onUpdate }) {
  const languages = [
    { label: 'English', value: 'en' },
    { label: 'Español (Spanish)', value: 'es' },
    { label: 'Français (French)', value: 'fr' },
    { label: 'Deutsch (German)', value: 'de' },
    { label: 'हिन्दी (Hindi)', value: 'hi' },
  ];

  const responseStyles = [
    {
      value: 'concise',
      label: 'Concise',
      desc: 'Answer directly and avoid unnecessary explanation.'
    },
    {
      value: 'balanced',
      label: 'Balanced (Default)',
      desc: 'Provide clear, well-structured, informative, and engaging responses.'
    },
    {
      value: 'detailed',
      label: 'Detailed',
      desc: 'Provide deeper explanation, examples, edge cases, and relevant technical details.'
    },
    {
      value: 'beginner-friendly',
      label: 'Beginner-friendly',
      desc: 'Explain concepts using simple language, examples, and step-by-step explanations.'
    },
  ];

  const enterBehaviors = [
    { label: 'Send message (Press Shift+Enter for new line)', value: 'send' },
    { label: 'Insert new line (Click Send to submit)', value: 'newline' },
  ];

  const currentStyle = settings.response_style || 'balanced';

  return (
    <div className="settings-section">
      <h3 className="settings-section-title">General Preferences</h3>
      <p className="settings-section-desc">Customize default language, conversational tone, and response style.</p>

      {/* Requirement 11: Response Style Radio Selection */}
      <div className="settings-field-group" style={{ marginBottom: '22px' }}>
        <label className="settings-field-label" style={{ display: 'block', marginBottom: '10px', fontWeight: 600 }}>
          Response Style
        </label>
        <div className="response-style-options" style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {responseStyles.map((item) => {
            const isSelected = currentStyle === item.value || (item.value === 'beginner-friendly' && currentStyle === 'beginner_friendly');
            return (
              <label
                key={item.value}
                style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: '12px',
                  padding: '10px 14px',
                  borderRadius: 'var(--radius-md, 8px)',
                  background: isSelected ? 'rgba(0, 242, 254, 0.08)' : 'rgba(255, 255, 255, 0.03)',
                  border: isSelected ? '1px solid var(--accent-cyan, #00f2fe)' : '1px solid rgba(255, 255, 255, 0.08)',
                  cursor: 'pointer',
                  transition: 'all 0.15s ease'
                }}
              >
                <input
                  type="radio"
                  name="responseStyle"
                  value={item.value}
                  checked={isSelected}
                  onChange={() => onUpdate({ response_style: item.value })}
                  style={{ marginTop: '3px' }}
                />
                <div>
                  <div style={{ fontWeight: 600, fontSize: '0.92rem', color: isSelected ? 'var(--accent-cyan, #00f2fe)' : 'var(--text-primary)' }}>
                    {item.label}
                  </div>
                  <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary, #94a3b8)', marginTop: '2px' }}>
                    {item.desc}
                  </div>
                </div>
              </label>
            );
          })}
        </div>
      </div>

      <div className="settings-field-group">
        <Dropdown
          label="Language"
          value={settings.language || 'en'}
          options={languages}
          onChange={(val) => onUpdate({ language: val })}
        />
      </div>

      <div className="settings-field-group">
        <Dropdown
          label="Enter Key Behavior"
          value={settings.enter_behavior || 'send'}
          options={enterBehaviors}
          onChange={(val) => onUpdate({ enter_behavior: val })}
        />
      </div>
    </div>
  );
}
