import React from 'react';
import { MemoryPanel } from '../components/Memory/MemoryPanel';

export function MemoryPage() {
  return (
    <div style={{ flex: 1, overflowY: 'auto' }}>
      <MemoryPanel />
    </div>
  );
}
