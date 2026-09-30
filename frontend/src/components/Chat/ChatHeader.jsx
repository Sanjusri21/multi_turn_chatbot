import React, { useState, useRef, useEffect } from 'react';
import { Bot, Bookmark, Settings, Sun, Moon, User, LogOut, Sparkles, Globe, Volume2, VolumeX, ChevronDown, Menu, ShieldCheck } from 'lucide-react';
import { useChatContext } from '../../context/ChatContext';
import { useAuth } from '../../hooks/useAuth';

export function ChatHeader({ onOpenMemory, onOpenSettings, onToggleMobileSidebar, onNavigateToAdmin }) {
  const {
    memories,
    userSettings,
    updateUserSettings,
    currentConversationId,
    conversations,
    selectedLanguage,
    setSelectedLanguage,
    autoVoiceEnabled,
    setAutoVoiceEnabled,
  } = useChatContext();
  const { user, logout } = useAuth();
  const [isProfileOpen, setIsProfileOpen] = useState(false);
  const [isLangOpen, setIsLangOpen] = useState(false);
  const profileRef = useRef(null);
  const langRef = useRef(null);

  const currentTheme = userSettings?.theme || 'dark';

  const activeConversation = conversations.find((c) => c.id === currentConversationId);
  const convTitle = activeConversation ? activeConversation.title : 'New Chat Session';

  const toggleTheme = () => {
    const nextTheme = currentTheme === 'dark' ? 'light' : 'dark';
    updateUserSettings({ theme: nextTheme });
  };

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (profileRef.current && !profileRef.current.contains(e.target)) {
        setIsProfileOpen(false);
      }
      if (langRef.current && !langRef.current.contains(e.target)) {
        setIsLangOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const languageOptions = [
    { code: 'en', label: 'English', native: 'English' },
    { code: 'ta', label: 'Tamil', native: 'தமிழ்' },
    { code: 'hi', label: 'Hindi', native: 'हिन्दी' },
  ];

  const currentLangObj = languageOptions.find((l) => l.code === selectedLanguage) || languageOptions[0];

  return (
    <header className="chat-top-header">
      {/* Left: Mobile Hamburger & Zara Branding */}
      <div className="header-left-col">
        {/* Mobile Hamburger Drawer Toggle (☰) */}
        <button
          className="mobile-hamburger-btn show-on-mobile-only"
          onClick={onToggleMobileSidebar}
          title="Open Menu Drawer"
          aria-label="Open Menu Drawer"
        >
          <Menu size={20} />
        </button>

        <div className="header-brand-box">
          <div className="header-robot-glow-icon">
            <Sparkles size={18} color="#050b14" />
          </div>
          <div style={{ display: 'flex', flexDirection: 'column' }}>
            <span className="header-brand-title" style={{ lineHeight: 1.1 }}>Zara</span>
            <span style={{ fontSize: '0.68rem', color: 'var(--accent-cyan, #06b6d4)', fontWeight: 600, letterSpacing: '0.5px' }} className="hide-on-mobile">
              AI Assistant
            </span>
          </div>
        </div>

        <div className="header-status-pill hide-on-mobile" title="Zara AI Voice Assistant Active">
          <span className="header-status-dot" />
          <span className="header-model-tag" style={{ fontSize: '0.75rem', color: 'var(--text-secondary, #94a3b8)', marginLeft: '4px' }}>
            Zara 2.0
          </span>
        </div>
      </div>

      {/* Center: Current Conversation Context */}
      <div className="header-center-col">
        <div className="header-conv-breadcrumb" title={convTitle}>
          <Sparkles size={13} className="breadcrumb-icon" />
          <span className="breadcrumb-text">{convTitle}</span>
        </div>
      </div>

      {/* Right: Language Selector, Auto Voice & Quick Controls */}
      <div className="header-right-col" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        {/* Language Selector Dropdown */}
        <div className="header-lang-selector-wrapper" ref={langRef} style={{ position: 'relative' }}>
          <button
            className="header-action-btn"
            style={{
              padding: '6px 10px',
              borderRadius: '8px',
              gap: '6px',
              fontSize: '0.82rem',
              fontWeight: 500,
              width: 'auto',
              display: 'flex',
              alignItems: 'center',
              background: 'var(--bg-card, rgba(255, 255, 255, 0.05))',
              border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.1))',
            }}
            onClick={() => setIsLangOpen(!isLangOpen)}
            title="Switch Language (English | தமிழ் | हिन्दी)"
          >
            <Globe size={15} color="var(--accent-cyan, #06b6d4)" />
            <span>{currentLangObj.native}</span>
            <ChevronDown size={13} style={{ opacity: 0.7 }} />
          </button>

          {isLangOpen && (
            <div
              style={{
                position: 'absolute',
                top: 'calc(100% + 6px)',
                right: 0,
                background: 'var(--bg-surface, #0f172a)',
                border: '1px solid var(--border-subtle, rgba(255, 255, 255, 0.15))',
                borderRadius: '10px',
                padding: '4px',
                boxShadow: '0 10px 25px -5px rgba(0, 0, 0, 0.5)',
                minWidth: '150px',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '6px 10px', fontSize: '0.72rem', color: 'var(--text-muted, #64748b)', fontWeight: 600 }}>
                SELECT LANGUAGE
              </div>
              {languageOptions.map((opt) => (
                <button
                  key={opt.code}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    width: '100%',
                    padding: '8px 12px',
                    fontSize: '0.85rem',
                    color: selectedLanguage === opt.code ? 'var(--accent-cyan, #06b6d4)' : 'var(--text-primary, #f8fafc)',
                    background: selectedLanguage === opt.code ? 'rgba(6, 182, 212, 0.12)' : 'transparent',
                    border: 'none',
                    borderRadius: '6px',
                    cursor: 'pointer',
                    textAlign: 'left',
                    transition: 'background 0.15s ease',
                  }}
                  onClick={() => {
                    setSelectedLanguage(opt.code);
                    setIsLangOpen(false);
                  }}
                >
                  <span style={{ fontWeight: selectedLanguage === opt.code ? 600 : 400 }}>
                    {opt.native}
                  </span>
                  <span style={{ fontSize: '0.75rem', opacity: 0.7 }}>
                    ({opt.label})
                  </span>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Auto Voice Toggle */}
        <button
          className={`header-action-btn ${autoVoiceEnabled ? 'active' : ''}`}
          style={{
            padding: '6px 10px',
            borderRadius: '8px',
            gap: '6px',
            fontSize: '0.78rem',
            fontWeight: 500,
            width: 'auto',
            display: 'flex',
            alignItems: 'center',
            color: autoVoiceEnabled ? 'var(--accent-cyan, #06b6d4)' : 'var(--text-muted, #64748b)',
            background: autoVoiceEnabled ? 'rgba(6, 182, 212, 0.12)' : 'var(--bg-card, rgba(255, 255, 255, 0.05))',
            border: autoVoiceEnabled ? '1px solid rgba(6, 182, 212, 0.4)' : '1px solid var(--border-subtle, rgba(255, 255, 255, 0.1))',
          }}
          onClick={() => setAutoVoiceEnabled(!autoVoiceEnabled)}
          title={`Auto Voice is currently ${autoVoiceEnabled ? 'ON (Zara speaks automatically)' : 'OFF (Press speaker on message to speak)'}`}
        >
          {autoVoiceEnabled ? <Volume2 size={16} /> : <VolumeX size={16} />}
          <span>Voice: {autoVoiceEnabled ? 'ON' : 'OFF'}</span>
        </button>

        {/* Memory Trigger */}
        <button
          className="header-action-btn"
          onClick={onOpenMemory}
          title="Open Persistent Memory Drawer"
        >
          <Bookmark size={17} />
          {memories.length > 0 && <span className="header-mem-badge">{memories.length}</span>}
        </button>

        {/* Theme Toggle */}
        <button
          className="header-action-btn"
          onClick={toggleTheme}
          title={`Switch to ${currentTheme === 'dark' ? 'light' : 'dark'} mode`}
        >
          {currentTheme === 'dark' ? <Sun size={17} /> : <Moon size={17} />}
        </button>

        {/* Admin Console Quick Button (for ADMIN users) */}
        {user?.role === 'ADMIN' && (
          <button
            className="header-action-btn admin-quick-btn"
            onClick={onNavigateToAdmin}
            title="Open Admin Console"
            style={{
              background: 'rgba(139, 92, 246, 0.16)',
              border: '1px solid rgba(139, 92, 246, 0.4)',
              color: '#c084fc',
              padding: '6px 10px',
              borderRadius: '8px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '0.8rem',
              fontWeight: 600,
            }}
          >
            <ShieldCheck size={16} />
            <span className="hide-on-mobile">Admin</span>
          </button>
        )}

        {/* Settings Button */}
        <button
          className="header-action-btn"
          onClick={onOpenSettings}
          title="Settings"
        >
          <Settings size={17} />
        </button>

        {/* User Profile Dropdown */}
        <div className="header-user-menu-wrapper" ref={profileRef}>
          <button
            className="header-user-pill-btn"
            onClick={() => setIsProfileOpen(!isProfileOpen)}
            title="User Profile"
          >
            <div className="header-user-avatar">
              <User size={15} />
            </div>
            <span className="header-user-name">{user?.name || 'Sanju'}</span>
          </button>

          {isProfileOpen && (
            <div className="profile-dropdown-card">
              <div className="profile-dropdown-header">
                <div className="profile-dropdown-name">{user?.name || 'Sanju'}</div>
                <div className="profile-dropdown-email">{user?.email || ''}</div>
              </div>

              <div className="profile-dropdown-items">
                {user?.role === 'ADMIN' && (
                  <button
                    className="profile-dropdown-item"
                    onClick={() => {
                      setIsProfileOpen(false);
                      if (onNavigateToAdmin) onNavigateToAdmin();
                    }}
                  >
                    <ShieldCheck size={15} color="#c084fc" />
                    <span style={{ color: '#c084fc' }}>Admin Console</span>
                  </button>
                )}

                <button
                  className="profile-dropdown-item"
                  onClick={() => {
                    setIsProfileOpen(false);
                    onOpenMemory();
                  }}
                >
                  <Bookmark size={15} />
                  <span>Memories ({memories.length})</span>
                </button>

                <button
                  className="profile-dropdown-item"
                  onClick={() => {
                    setIsProfileOpen(false);
                    onOpenSettings();
                  }}
                >
                  <Settings size={15} />
                  <span>Settings</span>
                </button>

                <button
                  className="profile-dropdown-item"
                  onClick={() => {
                    toggleTheme();
                    setIsProfileOpen(false);
                  }}
                >
                  {currentTheme === 'dark' ? <Sun size={15} /> : <Moon size={15} />}
                  <span>{currentTheme === 'dark' ? 'Light Theme' : 'Dark Theme'}</span>
                </button>

                <div className="dropdown-divider" />

                <button
                  className="profile-dropdown-item danger"
                  onClick={() => {
                    setIsProfileOpen(false);
                    logout();
                  }}
                >
                  <LogOut size={15} />
                  <span>Log out</span>
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </header>
  );
}
