import React, { useState, useEffect, useCallback } from 'react';
import {
  ShieldCheck,
  Users,
  Clock,
  CheckCircle,
  XCircle,
  AlertTriangle,
  RotateCcw,
  MessageSquare,
  LogOut,
  RefreshCw,
  Search,
  Check,
  X,
  Ban,
  Calendar,
  Mail,
  UserCheck
} from 'lucide-react';
import { adminApi } from '../services/adminApi';
import { useAuth } from '../hooks/useAuth';
import { toast } from '../components/UI/Toast';

export function AdminDashboardPage({ onNavigateToChat }) {
  const { user, logout } = useAuth();
  const [users, setUsers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('pending'); // 'pending' | 'approved' | 'suspended' | 'rejected' | 'all'
  const [searchQuery, setSearchQuery] = useState('');
  const [actionLoading, setActionLoading] = useState(null);

  // Confirmation modal state
  const [confirmModal, setConfirmModal] = useState({
    isOpen: false,
    action: '', // 'reject' | 'suspend' | 'restore' | 'approve'
    targetUser: null,
  });

  const fetchUsers = useCallback(async () => {
    setLoading(true);
    try {
      const data = await adminApi.getUsers();
      setUsers(data || []);
    } catch (err) {
      toast.error(err.message || 'Failed to load user list.');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchUsers();
  }, [fetchUsers]);

  // Status counts
  const pendingUsers = users.filter((u) => u.account_status === 'PENDING');
  const approvedUsers = users.filter((u) => u.account_status === 'APPROVED');
  const suspendedUsers = users.filter((u) => u.account_status === 'SUSPENDED');
  const rejectedUsers = users.filter((u) => u.account_status === 'REJECTED');

  const filteredUsers = users.filter((u) => {
    const matchesSearch =
      u.name?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      u.email?.toLowerCase().includes(searchQuery.toLowerCase());

    if (!matchesSearch) return false;

    if (activeTab === 'pending') return u.account_status === 'PENDING';
    if (activeTab === 'approved') return u.account_status === 'APPROVED';
    if (activeTab === 'suspended') return u.account_status === 'SUSPENDED';
    if (activeTab === 'rejected') return u.account_status === 'REJECTED';
    return true; // 'all'
  });

  const handleActionClick = (action, targetUser) => {
    // For approve, execute immediately or confirm; for reject/suspend, confirm
    if (action === 'approve') {
      executeAction('approve', targetUser);
    } else {
      setConfirmModal({
        isOpen: true,
        action,
        targetUser,
      });
    }
  };

  const executeAction = async (action, targetUser) => {
    setActionLoading(targetUser.id);
    try {
      if (action === 'approve') {
        await adminApi.approveUser(targetUser.id);
        toast.success(`Approved ${targetUser.name} (${targetUser.email})`);
      } else if (action === 'reject') {
        await adminApi.rejectUser(targetUser.id);
        toast.success(`Rejected registration for ${targetUser.name}`);
      } else if (action === 'suspend') {
        await adminApi.suspendUser(targetUser.id);
        toast.warning(`Suspended access for ${targetUser.name}`);
      } else if (action === 'restore') {
        await adminApi.restoreUser(targetUser.id);
        toast.success(`Restored active access for ${targetUser.name}`);
      }
      setConfirmModal({ isOpen: false, action: '', targetUser: null });
      await fetchUsers();
    } catch (err) {
      toast.error(err.message || `Failed to ${action} user.`);
    } finally {
      setActionLoading(null);
    }
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    try {
      const d = new Date(dateStr);
      return d.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
      });
    } catch {
      return dateStr;
    }
  };

  return (
    <div className="admin-page">
      {/* Top Navbar */}
      <header className="admin-header">
        <div className="admin-header-brand">
          <div className="admin-logo-icon">
            <ShieldCheck size={22} />
          </div>
          <div>
            <h1 className="admin-title">Zara Admin Console</h1>
            <span className="admin-subtitle">Access & User Account Governance</span>
          </div>
        </div>

        <div className="admin-header-actions">
          <button
            type="button"
            className="admin-nav-btn btn-chat"
            onClick={onNavigateToChat}
            title="Open Zara AI Chat"
          >
            <MessageSquare size={16} />
            <span className="hide-on-mobile">Zara Chat</span>
          </button>

          <button
            type="button"
            className="admin-nav-btn btn-refresh"
            onClick={fetchUsers}
            disabled={loading}
            title="Refresh user data"
          >
            <RefreshCw size={16} className={loading ? 'spin' : ''} />
            <span className="hide-on-mobile">Refresh</span>
          </button>

          <button
            type="button"
            className="admin-nav-btn btn-logout"
            onClick={logout}
            title="Sign out of Admin Console"
          >
            <LogOut size={16} />
            <span className="hide-on-mobile">Logout</span>
          </button>
        </div>
      </header>

      {/* Main Container */}
      <main className="admin-container">
        {/* Metric Summary Cards */}
        <div className="admin-stats-grid">
          <div
            className={`admin-stat-card ${activeTab === 'pending' ? 'active-stat-card' : ''}`}
            onClick={() => setActiveTab('pending')}
          >
            <div className="stat-icon-wrapper pending-icon">
              <Clock size={22} />
            </div>
            <div className="stat-content">
              <span className="stat-number">{pendingUsers.length}</span>
              <span className="stat-label">Pending Review</span>
            </div>
            {pendingUsers.length > 0 && <span className="stat-pulse" />}
          </div>

          <div
            className={`admin-stat-card ${activeTab === 'approved' ? 'active-stat-card' : ''}`}
            onClick={() => setActiveTab('approved')}
          >
            <div className="stat-icon-wrapper approved-icon">
              <CheckCircle size={22} />
            </div>
            <div className="stat-content">
              <span className="stat-number">{approvedUsers.length}</span>
              <span className="stat-label">Approved Users</span>
            </div>
          </div>

          <div
            className={`admin-stat-card ${activeTab === 'suspended' ? 'active-stat-card' : ''}`}
            onClick={() => setActiveTab('suspended')}
          >
            <div className="stat-icon-wrapper suspended-icon">
              <Ban size={22} />
            </div>
            <div className="stat-content">
              <span className="stat-number">{suspendedUsers.length}</span>
              <span className="stat-label">Suspended</span>
            </div>
          </div>

          <div
            className={`admin-stat-card ${activeTab === 'rejected' ? 'active-stat-card' : ''}`}
            onClick={() => setActiveTab('rejected')}
          >
            <div className="stat-icon-wrapper rejected-icon">
              <XCircle size={22} />
            </div>
            <div className="stat-content">
              <span className="stat-number">{rejectedUsers.length}</span>
              <span className="stat-label">Rejected</span>
            </div>
          </div>
        </div>

        {/* Filter and Search Bar */}
        <div className="admin-controls-bar">
          <div className="admin-tabs">
            <button
              type="button"
              className={`admin-tab-btn ${activeTab === 'pending' ? 'active' : ''}`}
              onClick={() => setActiveTab('pending')}
            >
              Pending ({pendingUsers.length})
            </button>
            <button
              type="button"
              className={`admin-tab-btn ${activeTab === 'approved' ? 'active' : ''}`}
              onClick={() => setActiveTab('approved')}
            >
              Approved ({approvedUsers.length})
            </button>
            <button
              type="button"
              className={`admin-tab-btn ${activeTab === 'suspended' ? 'active' : ''}`}
              onClick={() => setActiveTab('suspended')}
            >
              Suspended ({suspendedUsers.length})
            </button>
            <button
              type="button"
              className={`admin-tab-btn ${activeTab === 'rejected' ? 'active' : ''}`}
              onClick={() => setActiveTab('rejected')}
            >
              Rejected ({rejectedUsers.length})
            </button>
            <button
              type="button"
              className={`admin-tab-btn ${activeTab === 'all' ? 'active' : ''}`}
              onClick={() => setActiveTab('all')}
            >
              All ({users.length})
            </button>
          </div>

          <div className="admin-search-wrapper">
            <Search size={16} className="search-icon" />
            <input
              type="text"
              placeholder="Search by name or email..."
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="admin-search-input"
            />
          </div>
        </div>

        {/* Users Table / Responsive Card View */}
        <div className="admin-table-container">
          {loading ? (
            <div className="admin-loading-state">
              <RefreshCw size={24} className="spin" />
              <span>Loading user data...</span>
            </div>
          ) : filteredUsers.length === 0 ? (
            <div className="admin-empty-state">
              <UserCheck size={40} className="empty-icon" />
              <h3>No users found</h3>
              <p>
                {activeTab === 'pending'
                  ? 'All signup requests have been reviewed!'
                  : 'No user records match this filter.'}
              </p>
            </div>
          ) : (
            <>
              {/* Desktop Table View */}
              <div className="admin-table-desktop">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>User</th>
                      <th>Email</th>
                      <th>Registered</th>
                      <th>Status</th>
                      <th>Role</th>
                      <th style={{ textAlign: 'right' }}>Actions</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((u) => (
                      <tr key={u.id}>
                        <td>
                          <div className="user-name-cell">
                            <div className="user-avatar-circle">
                              {u.name ? u.name.charAt(0).toUpperCase() : '?'}
                            </div>
                            <span className="user-fullname">{u.name}</span>
                          </div>
                        </td>
                        <td>
                          <span className="user-email-text">{u.email}</span>
                        </td>
                        <td>
                          <span className="user-date-text">{formatDate(u.created_at)}</span>
                        </td>
                        <td>
                          <span className={`status-tag status-${u.account_status.toLowerCase()}`}>
                            {u.account_status}
                          </span>
                        </td>
                        <td>
                          <span className={`role-tag role-${u.role.toLowerCase()}`}>
                            {u.role}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right' }}>
                          <div className="action-buttons-group">
                            {u.account_status === 'PENDING' && (
                              <>
                                <button
                                  type="button"
                                  className="btn-action btn-approve"
                                  onClick={() => handleActionClick('approve', u)}
                                  disabled={actionLoading === u.id}
                                  title="Approve user"
                                >
                                  <Check size={14} />
                                  <span>Approve</span>
                                </button>
                                <button
                                  type="button"
                                  className="btn-action btn-reject"
                                  onClick={() => handleActionClick('reject', u)}
                                  disabled={actionLoading === u.id || u.id === user?.id}
                                  title="Reject user"
                                >
                                  <X size={14} />
                                  <span>Reject</span>
                                </button>
                              </>
                            )}

                            {u.account_status === 'APPROVED' && u.role !== 'ADMIN' && (
                              <button
                                type="button"
                                className="btn-action btn-suspend"
                                onClick={() => handleActionClick('suspend', u)}
                                disabled={actionLoading === u.id || u.id === user?.id}
                                title="Suspend access"
                              >
                                <Ban size={14} />
                                <span>Suspend</span>
                              </button>
                            )}

                            {(u.account_status === 'SUSPENDED' || u.account_status === 'REJECTED') && (
                              <button
                                type="button"
                                className="btn-action btn-restore"
                                onClick={() => handleActionClick('restore', u)}
                                disabled={actionLoading === u.id}
                                title="Restore account"
                              >
                                <RotateCcw size={14} />
                                <span>Restore</span>
                              </button>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Mobile Card View */}
              <div className="admin-cards-mobile">
                {filteredUsers.map((u) => (
                  <div key={u.id} className="admin-user-card">
                    <div className="admin-user-card-header">
                      <div className="user-name-cell">
                        <div className="user-avatar-circle">
                          {u.name ? u.name.charAt(0).toUpperCase() : '?'}
                        </div>
                        <div>
                          <div className="user-fullname">{u.name}</div>
                          <div className="user-email-text">{u.email}</div>
                        </div>
                      </div>
                      <span className={`status-tag status-${u.account_status.toLowerCase()}`}>
                        {u.account_status}
                      </span>
                    </div>

                    <div className="admin-user-card-meta">
                      <div className="meta-item">
                        <Calendar size={13} />
                        <span>Registered: {formatDate(u.created_at)}</span>
                      </div>
                      <div className="meta-item">
                        <span className={`role-tag role-${u.role.toLowerCase()}`}>{u.role}</span>
                      </div>
                    </div>

                    <div className="admin-user-card-actions">
                      {u.account_status === 'PENDING' && (
                        <>
                          <button
                            type="button"
                            className="btn-action btn-approve full-width"
                            onClick={() => handleActionClick('approve', u)}
                            disabled={actionLoading === u.id}
                          >
                            <Check size={14} />
                            <span>Approve</span>
                          </button>
                          <button
                            type="button"
                            className="btn-action btn-reject full-width"
                            onClick={() => handleActionClick('reject', u)}
                            disabled={actionLoading === u.id || u.id === user?.id}
                          >
                            <X size={14} />
                            <span>Reject</span>
                          </button>
                        </>
                      )}

                      {u.account_status === 'APPROVED' && u.role !== 'ADMIN' && (
                        <button
                          type="button"
                          className="btn-action btn-suspend full-width"
                          onClick={() => handleActionClick('suspend', u)}
                          disabled={actionLoading === u.id || u.id === user?.id}
                        >
                          <Ban size={14} />
                          <span>Suspend</span>
                        </button>
                      )}

                      {(u.account_status === 'SUSPENDED' || u.account_status === 'REJECTED') && (
                        <button
                          type="button"
                          className="btn-action btn-restore full-width"
                          onClick={() => handleActionClick('restore', u)}
                          disabled={actionLoading === u.id}
                        >
                          <RotateCcw size={14} />
                          <span>Restore</span>
                        </button>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </main>

      {/* Confirmation Dialog Modal */}
      {confirmModal.isOpen && (
        <div className="admin-modal-backdrop" onClick={() => setConfirmModal({ isOpen: false, action: '', targetUser: null })}>
          <div className="admin-modal-card" onClick={(e) => e.stopPropagation()}>
            <div className="admin-modal-header">
              <div className="admin-modal-icon-warning">
                <AlertTriangle size={24} />
              </div>
              <div>
                <h3 className="admin-modal-title">
                  Confirm {confirmModal.action.toUpperCase()} Action
                </h3>
                <p className="admin-modal-subtitle">
                  Are you sure you want to {confirmModal.action} this account?
                </p>
              </div>
            </div>

            <div className="admin-modal-body">
              <div className="modal-user-preview">
                <strong>{confirmModal.targetUser?.name}</strong>
                <span>({confirmModal.targetUser?.email})</span>
              </div>
              <p className="modal-warning-text">
                {confirmModal.action === 'reject' &&
                  'The user will be denied access to Zara until reviewed or restored.'}
                {confirmModal.action === 'suspend' &&
                  'The user will be temporarily blocked from all chat, memory, and API features.'}
                {confirmModal.action === 'restore' &&
                  'The user will be granted full active access to Zara conversational features.'}
              </p>
            </div>

            <div className="admin-modal-actions">
              <button
                type="button"
                className="admin-modal-cancel-btn"
                onClick={() => setConfirmModal({ isOpen: false, action: '', targetUser: null })}
                disabled={actionLoading !== null}
              >
                Cancel
              </button>
              <button
                type="button"
                className={`admin-modal-confirm-btn confirm-${confirmModal.action}`}
                onClick={() => executeAction(confirmModal.action, confirmModal.targetUser)}
                disabled={actionLoading !== null}
              >
                {actionLoading ? 'Processing...' : `Yes, ${confirmModal.action.toUpperCase()}`}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default AdminDashboardPage;
