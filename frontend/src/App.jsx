import React, { useState, useEffect, useCallback } from 'react';
import { useAuth } from './hooks/useAuth';
import { LoginPage } from './pages/LoginPage';
import { SignupPage } from './pages/SignupPage';
import { PendingApprovalPage } from './pages/PendingApprovalPage';
import { AdminDashboardPage } from './pages/AdminDashboardPage';
import { ChatPage } from './pages/ChatPage';
import { ToastContainer, toast } from './components/UI/Toast';
import { RobotFace } from './components/Robot/RobotFace';
import { AnimatedChatBackground } from './components/Background/AnimatedChatBackground';
import { ShieldAlert, ArrowLeft } from 'lucide-react';

export function App() {
  const { isAuthenticated, isApproved, isPending, isAdmin, user, isLoading, logout } = useAuth();
  const [currentPath, setCurrentPath] = useState(() => window.location.pathname || '/');

  // Handle URL navigation and browser back/forward buttons
  const navigate = useCallback((path) => {
    if (window.location.pathname !== path) {
      window.history.pushState({}, '', path);
    }
    setCurrentPath(path);
  }, []);

  useEffect(() => {
    const handlePopState = () => {
      setCurrentPath(window.location.pathname || '/');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  // Route protection and redirection effects
  useEffect(() => {
    if (isLoading) return;

    if (!isAuthenticated) {
      // Unauthenticated users can only access /login, /signup, or /pending
      if (currentPath !== '/login' && currentPath !== '/signup' && currentPath !== '/pending') {
        navigate('/login');
      }
    } else {
      // User is authenticated
      if (isPending) {
        if (currentPath !== '/pending') {
          navigate('/pending');
        }
      } else if (isApproved) {
        // Normal user trying to access /admin -> redirect to /chat
        if (currentPath === '/admin' && !isAdmin) {
          toast.error('Access denied. Administrator privileges required.');
          navigate('/chat');
        } else if (currentPath === '/login' || currentPath === '/signup' || currentPath === '/pending' || currentPath === '/') {
          navigate(isAdmin ? '/admin' : '/chat');
        }
      }
    }
  }, [isAuthenticated, isApproved, isPending, isAdmin, currentPath, isLoading, navigate]);

  // Loading Screen
  if (isLoading) {
    return (
      <div className="app-loading-screen">
        <AnimatedChatBackground variant="auth" />
        <div style={{ width: 80, height: 80, marginBottom: 16, zIndex: 1 }}>
          <RobotFace state="THINKING" />
        </div>
        <div style={{ color: 'var(--accent-cyan, #06b6d4)', fontWeight: 600, fontSize: '0.95rem', zIndex: 1 }}>
          Loading Zara AI Voice Assistant...
        </div>
      </div>
    );
  }

  // Handle Suspended or Rejected Account states
  if (isAuthenticated && (user?.account_status === 'SUSPENDED' || user?.account_status === 'REJECTED')) {
    const isRejected = user?.account_status === 'REJECTED';
    return (
      <div className="auth-page">
        <AnimatedChatBackground variant="auth" />
        <div className="auth-container" style={{ maxWidth: 500, margin: '0 auto', padding: '24px' }}>
          <div className="auth-form-card" style={{ textAlign: 'center', padding: '36px 28px' }}>
            <div style={{ marginBottom: 18, display: 'flex', justifyContent: 'center' }}>
              <div style={{
                width: 64,
                height: 64,
                borderRadius: 18,
                background: isRejected ? 'rgba(148, 163, 184, 0.15)' : 'rgba(239, 68, 68, 0.15)',
                color: isRejected ? '#94a3b8' : '#f87171',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <ShieldAlert size={32} />
              </div>
            </div>

            <h2 className="auth-title" style={{ marginBottom: 8 }}>
              {isRejected ? 'Account Request Rejected' : 'Account Suspended'}
            </h2>
            <p className="auth-subtitle" style={{ color: '#cbd5e1', marginBottom: 20 }}>
              {isRejected
                ? 'Your account request was rejected. Please contact the administrator.'
                : 'Your account has been suspended. Please contact the administrator.'}
            </p>

            <button
              type="button"
              className="pending-back-btn"
              onClick={() => {
                logout();
                navigate('/login');
              }}
              style={{ width: '100%', justifyContent: 'center' }}
            >
              <ArrowLeft size={16} />
              <span>Back to Login</span>
            </button>
          </div>
        </div>
        <ToastContainer />
      </div>
    );
  }

  return (
    <>
      {/* Dynamic Animated Space Background */}
      <AnimatedChatBackground variant={!isAuthenticated || isPending ? 'auth' : 'full'} />

      {/* 1. Unauthenticated Views */}
      {!isAuthenticated && (
        <>
          {currentPath === '/signup' ? (
            <SignupPage onNavigateToLogin={() => navigate('/login')} />
          ) : currentPath === '/pending' ? (
            <PendingApprovalPage onBackToLogin={() => navigate('/login')} />
          ) : (
            <LoginPage onNavigateToSignup={() => navigate('/signup')} />
          )}
        </>
      )}

      {/* 2. Authenticated but Pending Approval View */}
      {isAuthenticated && isPending && (
        <PendingApprovalPage
          onBackToLogin={() => {
            logout();
            navigate('/login');
          }}
        />
      )}

      {/* 3. Authenticated & Approved Views */}
      {isAuthenticated && isApproved && (
        <>
          {currentPath === '/admin' && isAdmin ? (
            <AdminDashboardPage onNavigateToChat={() => navigate('/chat')} />
          ) : (
            <ChatPage onNavigateToAdmin={() => navigate('/admin')} />
          )}
        </>
      )}

      {/* Global Toast Notifications */}
      <ToastContainer />
    </>
  );
}

export default App;
