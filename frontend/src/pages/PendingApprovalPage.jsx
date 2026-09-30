import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Lock, ArrowLeft, RefreshCw, CheckCircle2, Clock } from 'lucide-react';
import { useAuth } from '../hooks/useAuth';
import { authApi } from '../services/authApi';
import { RobotFace } from '../components/Robot/RobotFace';
import { floatingVariants } from '../components/Robot/robotAnimations';

export function PendingApprovalPage({ onBackToLogin }) {
  const { user, logout, setUser } = useAuth();
  const [checking, setChecking] = useState(false);
  const [statusMessage, setStatusMessage] = useState('');

  const handleCheckStatus = async () => {
    setChecking(true);
    setStatusMessage('');
    try {
      const profile = await authApi.getMe();
      setUser(profile);
      localStorage.setItem('user', JSON.stringify(profile));
      if (profile.account_status === 'APPROVED' || profile.role === 'ADMIN') {
        setStatusMessage('Your account is approved! Redirecting...');
      } else if (profile.account_status === 'REJECTED') {
        setStatusMessage('Your account request was rejected. Please contact the administrator.');
      } else {
        setStatusMessage('Your account is still pending administrator review. Please check back later.');
      }
    } catch (err) {
      setStatusMessage('Unable to refresh status. Please try logging in again.');
    } finally {
      setChecking(false);
    }
  };

  const handleBackToLogin = () => {
    logout();
    if (onBackToLogin) onBackToLogin();
  };

  return (
    <div className="auth-page">
      <div className="auth-container pending-container">
        {/* Left Side: Animated Patient RotoBot */}
        <div className="auth-hero">
          <div className="auth-hero-centered-content">
            <motion.div
              className="auth-robot-card"
              variants={floatingVariants}
              animate="THINKING"
            >
              <div className="auth-robot-bubble">
                Hang tight! An administrator is reviewing your account ⏳
              </div>
              <div className="auth-robot-wrapper">
                <RobotFace state="THINKING" />
              </div>
            </motion.div>
            <div className="pending-hero-tip">
              <Clock size={16} />
              <span>Security first: Zara protects multi-turn memories and real-time agents with verified access.</span>
            </div>
          </div>
        </div>

        {/* Right Side: Pending Approval Notice Card */}
        <div className="auth-form-card pending-card">
          <div className="pending-badge-icon-wrapper">
            <div className="pending-badge-icon">
              <Lock size={36} className="lock-icon-glow" />
            </div>
          </div>

          <div className="auth-header text-center">
            <h2 className="auth-title">Account Pending</h2>
            <p className="auth-subtitle">Your account has been created successfully.</p>
          </div>

          <div className="pending-body-text">
            <p>
              An administrator needs to approve your account before you can access Zara.
            </p>
            <p className="pending-note">
              We will let you know when your account is approved.
            </p>
          </div>

          {user && (
            <div className="pending-user-summary">
              <div className="pending-user-row">
                <span className="pending-label">Registered Name:</span>
                <span className="pending-val">{user.name}</span>
              </div>
              <div className="pending-user-row">
                <span className="pending-label">Email:</span>
                <span className="pending-val">{user.email}</span>
              </div>
              <div className="pending-user-row">
                <span className="pending-label">Status:</span>
                <span className="status-pill status-pill-pending">
                  <Clock size={12} />
                  <span>PENDING APPROVAL</span>
                </span>
              </div>
            </div>
          )}

          {statusMessage && (
            <div className={`pending-status-alert ${statusMessage.includes('approved') ? 'alert-success' : 'alert-info'}`}>
              {statusMessage}
            </div>
          )}

          <div className="pending-actions">
            <button
              type="button"
              className="pending-check-btn"
              onClick={handleCheckStatus}
              disabled={checking}
            >
              <RefreshCw size={16} className={checking ? 'spin' : ''} />
              <span>{checking ? 'Checking Status...' : 'Check Approval Status'}</span>
            </button>

            <button
              type="button"
              className="pending-back-btn"
              onClick={handleBackToLogin}
            >
              <ArrowLeft size={16} />
              <span>Back to Login</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default PendingApprovalPage;
