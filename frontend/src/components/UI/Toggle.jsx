import React from 'react';

export function Toggle({ checked, onChange, disabled = false, label }) {
  return (
    <label style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', cursor: disabled ? 'not-allowed' : 'pointer', width: '100%' }}>
      {label && <span style={{ fontSize: '0.9rem', color: 'var(--text-primary)', fontWeight: 500 }}>{label}</span>}
      <div
        onClick={() => !disabled && onChange(!checked)}
        style={{
          width: 44,
          height: 24,
          borderRadius: 9999,
          backgroundColor: checked ? 'var(--accent-cyan)' : 'rgba(255, 255, 255, 0.15)',
          position: 'relative',
          transition: 'background-color 0.2s ease',
          opacity: disabled ? 0.5 : 1,
          flexShrink: 0,
        }}
      >
        <div
          style={{
            width: 18,
            height: 18,
            borderRadius: '50%',
            backgroundColor: checked ? '#050b14' : '#ffffff',
            position: 'absolute',
            top: 3,
            left: checked ? 23 : 3,
            transition: 'left 0.2s ease, background-color 0.2s ease',
            boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
          }}
        />
      </div>
    </label>
  );
}
