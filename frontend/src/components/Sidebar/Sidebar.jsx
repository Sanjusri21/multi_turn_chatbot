import React, { useState } from 'react';
import { 
  Bot, 
  Plus, 
  MessageSquare, 
  Brain, 
  Settings, 
  LogOut, 
  ChevronDown, 
  ChevronRight, 
  Search,
  PanelLeftClose,
  PanelLeft,
  ShieldCheck,
  X
} from 'lucide-react';
import { ConversationList } from './ConversationList';
import { useChatContext } from '../../context/ChatContext';
import { useAuth } from '../../hooks/useAuth';

export function Sidebar({ 
  activeNav = 'chat', 
  setActiveNav, 
  onOpenMemory, 
  onOpenSettings,
  isOpenMobile = false,
  onCloseMobile,
  onNavigateToAdmin
}) {
  const { createNewChat } = useChatContext();
  const { user, logout } = useAuth();
  const [searchQuery, setSearchQuery] = useState('');
  const [isCollapsed, setIsCollapsed] = useState(false);
  const [isConvExpanded, setIsConvExpanded] = useState(true);

  const handleNavClick = (navKey, action) => {
    if (setActiveNav) setActiveNav(navKey);
    if (action) action();
    if (onCloseMobile) onCloseMobile();
  };

  const handleNewChat = () => {
    if (setActiveNav) setActiveNav('chat');
    createNewChat();
    if (onCloseMobile) onCloseMobile();
  };

  return (
    <>
      {/* Mobile Drawer Overlay Backdrop */}
      {isOpenMobile && (
        <div 
          className="sidebar-mobile-backdrop" 
          onClick={onCloseMobile} 
          aria-hidden="true" 
        />
      )}

      <aside className={`chat-sidebar ${isCollapsed ? 'collapsed' : ''} ${isOpenMobile ? 'mobile-open' : ''}`}>
        {/* 1. TOP BRAND HEADER */}
        <div className="sidebar-brand-section">
          <div className="sidebar-brand-wrapper">
            <div className="brand-robot-glow-icon">
              <Bot size={20} color="#050b14" />
            </div>
            {!isCollapsed && (
              <div className="brand-text-block">
                <span className="brand-title">Zara</span>
                <span className="brand-subtitle">Multilingual AI Voice</span>
              </div>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
            {/* Desktop collapse button */}
            <button
              className="sidebar-collapse-toggle-btn hide-on-mobile"
              onClick={() => setIsCollapsed(!isCollapsed)}
              title={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            >
              {isCollapsed ? <PanelLeft size={16} /> : <PanelLeftClose size={16} />}
            </button>

            {/* Mobile close drawer button */}
            <button
              className="sidebar-close-mobile-btn show-on-mobile-only"
              onClick={onCloseMobile}
              title="Close sidebar"
            >
              <X size={18} />
            </button>
          </div>
        </div>

        {/* 2. LARGE NEW CHAT BUTTON */}
        <div className="sidebar-new-chat-container">
          <button 
            className="large-new-chat-btn" 
            onClick={handleNewChat} 
            title="Start a new conversation"
          >
            <Plus size={18} strokeWidth={2.6} />
            {!isCollapsed && <span>New Chat</span>}
          </button>
        </div>

        {/* 3. NAVIGATION (Chat, Memory, Admin, Settings, Logout) */}
        <nav className="sidebar-nav-menu" aria-label="Main Navigation">
          <button
            className={`sidebar-nav-item ${activeNav === 'chat' ? 'active' : ''}`}
            onClick={() => handleNavClick('chat')}
            title="Chat"
          >
            <MessageSquare size={17} className="nav-icon" />
            {!isCollapsed && <span className="nav-label">Chat</span>}
          </button>

          <button
            className={`sidebar-nav-item ${activeNav === 'memory' ? 'active' : ''}`}
            onClick={() => handleNavClick('memory', onOpenMemory)}
            title="Memory"
          >
            <Brain size={17} className="nav-icon" />
            {!isCollapsed && <span className="nav-label">Memory</span>}
          </button>

          {user?.role === 'ADMIN' && (
            <button
              className="sidebar-nav-item sidebar-admin-btn"
              onClick={() => {
                if (onCloseMobile) onCloseMobile();
                if (onNavigateToAdmin) onNavigateToAdmin();
              }}
              title="Admin Dashboard"
            >
              <ShieldCheck size={17} className="nav-icon" color="#c084fc" />
              {!isCollapsed && <span className="nav-label" style={{ color: '#c084fc' }}>Admin Console</span>}
            </button>
          )}

          <button
            className={`sidebar-nav-item ${activeNav === 'settings' ? 'active' : ''}`}
            onClick={() => handleNavClick('settings', onOpenSettings)}
            title="Settings"
          >
            <Settings size={17} className="nav-icon" />
            {!isCollapsed && <span className="nav-label">Settings</span>}
          </button>

          <button
            className="sidebar-nav-item logout-nav-item"
            onClick={() => logout()}
            title="Logout"
          >
            <LogOut size={17} className="nav-icon" />
            {!isCollapsed && <span className="nav-label">Logout</span>}
          </button>
        </nav>

        {/* 4. CONVERSATION LIST SECTION */}
        {!isCollapsed && (
          <div className="sidebar-conversations-section">
            <div 
              className="sidebar-conv-header"
              onClick={() => setIsConvExpanded(!isConvExpanded)}
              title={isConvExpanded ? 'Collapse conversations' : 'Expand conversations'}
            >
              <span className="conv-header-title">Conversations</span>
              <button className="conv-chevron-btn" tabIndex={-1}>
                {isConvExpanded ? <ChevronDown size={15} /> : <ChevronRight size={15} />}
              </button>
            </div>

            {isConvExpanded && (
              <>
                <div className="sidebar-conv-search-box">
                  <Search size={14} className="search-icon" />
                  <input
                    type="text"
                    className="conv-search-input"
                    placeholder="Search conversations..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                  />
                </div>

                <div className="sidebar-conv-scroll-area">
                  <ConversationList 
                    searchQuery={searchQuery} 
                    onSelectConversation={() => {
                      if (onCloseMobile) onCloseMobile();
                    }}
                  />
                </div>
              </>
            )}
          </div>
        )}
      </aside>
    </>
  );
}

export default Sidebar;
