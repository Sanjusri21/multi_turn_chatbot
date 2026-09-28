import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sliders, Palette, Bookmark, User, X, Cpu } from 'lucide-react';
import { GeneralSettings } from './GeneralSettings';
import { AppearanceSettings } from './AppearanceSettings';
import { MemorySettings } from './MemorySettings';
import { AccountSettings } from './AccountSettings';
import { MemoryDebugger } from './MemoryDebugger';
import { useChatContext } from '../../context/ChatContext';

export function SettingsModal({ isOpen, onClose, onOpenMemoryPanel }) {
  const [activeTab, setActiveTab] = useState('general');
  const { userSettings, updateUserSettings, showToast } = useChatContext();

  if (!isOpen) return null;

  const tabs = [
    { id: 'general', label: 'General', icon: Sliders },
    { id: 'appearance', label: 'Appearance', icon: Palette },
    { id: 'memory', label: 'Memory', icon: Bookmark },
    { id: 'debugger', label: 'Memory Debugger', icon: Cpu },
    { id: 'account', label: 'Account', icon: User },
  ];

  return (
    <div className="modal-overlay" onClick={onClose}>
      <motion.div
        className="settings-modal-dialog"
        onClick={(e) => e.stopPropagation()}
        initial={{ opacity: 0, scale: 0.95, y: 15 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 15 }}
        transition={{ duration: 0.2 }}
      >
        {/* Left Sidebar */}
        <div className="settings-sidebar">
          <div className="settings-sidebar-header">
            <h3>Settings</h3>
          </div>
          <div className="settings-nav">
            {tabs.map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  className={`settings-nav-item ${isActive ? 'active' : ''}`}
                  onClick={() => setActiveTab(tab.id)}
                >
                  <Icon size={18} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* Right Content Pane */}
        <div className="settings-content-pane">
          <button className="settings-close-btn" onClick={onClose}>
            <X size={18} />
          </button>

          <div className="settings-scroll-body">
            {activeTab === 'general' && (
              <GeneralSettings
                settings={userSettings}
                onUpdate={updateUserSettings}
              />
            )}
            {activeTab === 'appearance' && (
              <AppearanceSettings
                settings={userSettings}
                onUpdate={updateUserSettings}
              />
            )}
            {activeTab === 'memory' && (
              <MemorySettings
                settings={userSettings}
                onUpdate={updateUserSettings}
                onOpenMemoryPanel={() => {
                  onClose();
                  if (onOpenMemoryPanel) onOpenMemoryPanel();
                }}
              />
            )}
            {activeTab === 'debugger' && (
              <MemoryDebugger />
            )}
            {activeTab === 'account' && (
              <AccountSettings onShowToast={showToast} />
            )}
          </div>
        </div>
      </motion.div>
    </div>
  );
}
