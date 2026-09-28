import React, { useState } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Button } from '../UI/Button';
import { Modal } from '../UI/Modal';
import { Lock, LogOut, Trash2, User, Mail, AlertTriangle } from 'lucide-react';
import { authApi } from '../../services/authApi';

export function AccountSettings({ onShowToast }) {
  const { user, logout } = useAuth();
  const [isPasswordModalOpen, setIsPasswordModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);

  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [isChanging, setIsChanging] = useState(false);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    setPasswordError('');

    if (newPassword.length < 8) {
      setPasswordError('New password must be at least 8 characters.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setPasswordError('Passwords do not match.');
      return;
    }

    setIsChanging(true);
    try {
      await authApi.changePassword({
        current_password: currentPassword,
        new_password: newPassword,
      });
      if (onShowToast) onShowToast('Password updated successfully!', 'success');
      setIsPasswordModalOpen(false);
      setCurrentPassword('');
      setNewPassword('');
      setConfirmPassword('');
    } catch (err) {
      setPasswordError(err.message || 'Failed to update password.');
    } finally {
      setIsChanging(false);
    }
  };

  const handleDeleteAccount = async () => {
    try {
      await authApi.deleteAccount();
      logout();
    } catch (err) {
      if (onShowToast) onShowToast(err.message || 'Failed to delete account', 'error');
    }
  };

  return (
    <div className="settings-section">
      <h3 className="settings-section-title">Account Details</h3>
      <p className="settings-section-desc">Manage your profile credentials and account actions.</p>

      {/* User Information */}
      <div className="account-info-card">
        <div className="account-avatar-large">
          <User size={24} />
        </div>
        <div>
          <div style={{ fontWeight: 700, fontSize: '1.05rem', color: 'var(--text-primary)' }}>
            {user?.name || 'User'}
          </div>
          <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', display: 'flex', alignItems: 'center', gap: 6 }}>
            <Mail size={13} />
            <span>{user?.email || 'user@example.com'}</span>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="account-actions-list">
        <div className="account-action-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Password</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Change your login password.
            </div>
          </div>
          <Button
            size="sm"
            variant="secondary"
            icon={Lock}
            onClick={() => setIsPasswordModalOpen(true)}
          >
            Change Password
          </Button>
        </div>

        <div className="account-action-row">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--text-primary)' }}>Sign Out</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Log out of your current session on this device.
            </div>
          </div>
          <Button
            size="sm"
            variant="secondary"
            icon={LogOut}
            onClick={logout}
          >
            Log Out
          </Button>
        </div>

        <div className="account-action-row danger">
          <div>
            <div style={{ fontWeight: 600, fontSize: '0.9rem', color: 'var(--accent-rose)' }}>Delete Account</div>
            <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>
              Permanently wipe your account, conversations, and all stored memories.
            </div>
          </div>
          <Button
            size="sm"
            variant="danger"
            icon={Trash2}
            onClick={() => setIsDeleteModalOpen(true)}
          >
            Delete Account
          </Button>
        </div>
      </div>

      {/* Change Password Modal */}
      <Modal
        isOpen={isPasswordModalOpen}
        onClose={() => setIsPasswordModalOpen(false)}
        title="Change Password"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsPasswordModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={handleChangePassword} disabled={isChanging}>
              {isChanging ? 'Updating...' : 'Save Password'}
            </Button>
          </>
        }
      >
        <form onSubmit={handleChangePassword}>
          {passwordError && <div className="auth-error-alert" style={{ marginBottom: 12 }}>{passwordError}</div>}
          <div className="form-group">
            <label className="form-label">Current Password</label>
            <input
              type="password"
              className="form-input"
              value={currentPassword}
              onChange={(e) => setCurrentPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">New Password</label>
            <input
              type="password"
              className="form-input"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              required
            />
          </div>
          <div className="form-group">
            <label className="form-label">Confirm New Password</label>
            <input
              type="password"
              className="form-input"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              required
            />
          </div>
        </form>
      </Modal>

      {/* Delete Account Confirmation Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Delete Your Account?"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button variant="danger" onClick={handleDeleteAccount}>
              Permanently Delete
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', gap: 12, alignItems: 'flex-start' }}>
          <AlertTriangle size={24} color="var(--accent-rose)" style={{ flexShrink: 0, marginTop: 2 }} />
          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            This action is <strong>irreversible</strong>. All your conversations, message history,
            and personal persistent memories will be deleted from the database immediately.
          </p>
        </div>
      </Modal>
    </div>
  );
}
