import React, { useState } from 'react';
import { Sidebar } from '../components/Sidebar/Sidebar';
import { ChatHeader } from '../components/Chat/ChatHeader';
import { ChatWindow } from '../components/Chat/ChatWindow';
import { MemoryPanel } from '../components/Memory/MemoryPanel';
import { SettingsModal } from '../components/Settings/SettingsModal';
import { RotoBot } from '../components/Robot/RotoBot';
import { useChatContext } from '../context/ChatContext';

export function ChatPage({ onNavigateToAdmin }) {
  const { userSettings } = useChatContext();
  const [isMemoryOpen, setIsMemoryOpen] = useState(false);
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isMobileSidebarOpen, setIsMobileSidebarOpen] = useState(false);
  const [activeNav, setActiveNav] = useState('chat');

  const handleOpenMemory = () => {
    setActiveNav('memory');
    setIsMemoryOpen(true);
  };

  const handleCloseMemory = () => {
    setIsMemoryOpen(false);
    setActiveNav('chat');
  };

  const handleOpenSettings = () => {
    setActiveNav('settings');
    setIsSettingsOpen(true);
  };

  const handleCloseSettings = () => {
    setIsSettingsOpen(false);
    setActiveNav('chat');
  };

  return (
    <div className="chat-layout-root">
      {/* 1. TOP HEADER - Spans full width across the top of the entire screen */}
      <ChatHeader
        onOpenMemory={handleOpenMemory}
        onOpenSettings={handleOpenSettings}
        onToggleMobileSidebar={() => setIsMobileSidebarOpen((prev) => !prev)}
        onNavigateToAdmin={onNavigateToAdmin}
      />

      {/* 2. MAIN WORKSPACE - Left: Responsive Sidebar / Mobile Drawer | Right: Chat Area */}
      <div className="chat-body-workspace">
        <Sidebar
          activeNav={activeNav}
          setActiveNav={setActiveNav}
          onOpenMemory={handleOpenMemory}
          onOpenSettings={handleOpenSettings}
          isOpenMobile={isMobileSidebarOpen}
          onCloseMobile={() => setIsMobileSidebarOpen(false)}
          onNavigateToAdmin={onNavigateToAdmin}
        />

        <main className="chat-content-container">
          <ChatWindow />
          {userSettings?.show_floating_robot !== false && <RotoBot />}
        </main>
      </div>

      {/* Slide-out Memory Panel */}
      <MemoryPanel
        isOpen={isMemoryOpen}
        onClose={handleCloseMemory}
      />

      {/* Settings Modal */}
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={handleCloseSettings}
        onOpenMemoryPanel={() => {
          setIsSettingsOpen(false);
          handleOpenMemory();
        }}
      />
    </div>
  );
}

export default ChatPage;
