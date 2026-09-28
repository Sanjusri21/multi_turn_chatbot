import React, { useState } from 'react';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { ChatPage } from './pages/ChatPage';
import { ToastContainer } from './components/UI/Toast';
import { RobotFace } from './components/Robot/RobotFace';
import { AnimatedChatBackground } from './components/Background/AnimatedChatBackground';

export function App() {
  const { isAuthenticated, isLoading } = useAuth();
  const [authView, setAuthView] = useState('login'); // 'login' or 'signup'

  if (isLoading) {
    return (
      <div className="app-loading-screen">
        <AnimatedChatBackground variant="auth" />
        <div style={{ width: 80, height: 80, marginBottom: 16, zIndex: 1 }}>
          <RobotFace state="THINKING" />
        </div>
        <div style={{ color: 'var(--accent-cyan)', fontWeight: 600, fontSize: '0.95rem', zIndex: 1 }}>
          Loading Zara AI Voice Assistant...
        </div>
      </div>
    );
  }

  return (
    <>
      {/* Premium Animated AI Conversation & Memory Universe Background */}
      <AnimatedChatBackground variant={!isAuthenticated ? 'auth' : 'full'} />

      {!isAuthenticated ? (
        authView === 'login' ? (
          <LoginPage onNavigateToSignup={() => setAuthView('signup')} />
        ) : (
          <SignupPage onNavigateToLogin={() => setAuthView('login')} />
        )
      ) : (
        <ChatPage />
      )}

      {/* Global Toast Notifications */}
      <ToastContainer />
    </>
  );
}

export default App;
