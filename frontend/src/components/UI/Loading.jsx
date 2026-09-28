import React from 'react';
import { Loader2 } from 'lucide-react';

export function Loading({ text = "Loading...", size = 20 }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '10px', padding: '24px', color: 'var(--text-secondary)' }}>
      <Loader2 size={size} className="spin" style={{ animation: 'spin 1s linear infinite' }} />
      {text && <span style={{ fontSize: '0.88rem' }}>{text}</span>}
      <style>{`
        @keyframes spin {
          from { transform: rotate(0deg); }
          to { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
}
