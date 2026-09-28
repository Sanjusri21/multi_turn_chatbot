import React, { useState } from 'react';
import { Eye, EyeOff, Mail, Lock, User, Check, X, ArrowRight, Loader2 } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function SignupForm({ onSwitchToLogin, onRobotStateChange }) {
  const { signup } = useAuth();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  // Criteria validation
  const hasMinLen = password.length >= 8;
  const hasNumber = /\d/.test(password);
  const hasSpecial = /[@$!%*?&#^()_+=\-[\]{}|;:,.<>]/.test(password);
  const isMatch = password.length > 0 && password === confirmPassword;
  const isFormValid = name.trim().length >= 2 && email.includes('@') && hasMinLen && hasNumber && hasSpecial && isMatch;

  const handlePasswordChange = (val) => {
    setPassword(val);
    if (val.length >= 8 && onRobotStateChange) {
      onRobotStateChange('HAPPY', "Great password strength! 🎉");
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');

    if (!isFormValid) {
      if (!isMatch) {
        setError('Passwords do not match.');
      } else {
        setError('Please satisfy all password criteria.');
      }
      return;
    }

    setIsSubmitting(true);
    try {
      await signup(name.trim(), email.trim(), password);
    } catch (err) {
      setError(err.message || 'Registration failed. Email might already exist.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div>
      <div className="auth-header">
        <h2 className="auth-title">Create Account</h2>
        <p className="auth-subtitle">Join MemoryBot and unlock persistent AI memory</p>
      </div>

      {error && <div className="auth-error-alert">{error}</div>}

      <form onSubmit={handleSubmit} className="auth-form">
        <div className="form-group">
          <label className="form-label">Full Name</label>
          <div className="input-wrapper">
            <User size={18} className="input-icon" />
            <input
              type="text"
              className="form-input"
              placeholder="e.g. Sanju"
              value={name}
              onChange={(e) => setName(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Email Address</label>
          <div className="input-wrapper">
            <Mail size={18} className="input-icon" />
            <input
              type="email"
              className="form-input"
              placeholder="name@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              disabled={isSubmitting}
              required
            />
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Password</label>
          <div className="input-wrapper">
            <Lock size={18} className="input-icon" />
            <input
              type={showPassword ? 'text' : 'password'}
              className="form-input"
              placeholder="Create a strong password"
              value={password}
              onChange={(e) => handlePasswordChange(e.target.value)}
              disabled={isSubmitting}
              required
            />
            <button
              type="button"
              className="password-toggle-btn"
              onClick={() => setShowPassword(!showPassword)}
              tabIndex={-1}
            >
              {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
        </div>

        {/* Password Strength Checklist */}
        <div className="password-criteria-box">
          <div className={`criteria-item ${hasMinLen ? 'valid' : ''}`}>
            {hasMinLen ? <Check size={14} /> : <X size={14} />}
            <span>At least 8 characters</span>
          </div>
          <div className={`criteria-item ${hasNumber ? 'valid' : ''}`}>
            {hasNumber ? <Check size={14} /> : <X size={14} />}
            <span>One number (0-9)</span>
          </div>
          <div className={`criteria-item ${hasSpecial ? 'valid' : ''}`}>
            {hasSpecial ? <Check size={14} /> : <X size={14} />}
            <span>One special character (@$!%*...)</span>
          </div>
        </div>

        <div className="form-group">
          <label className="form-label">Confirm Password</label>
          <div className="input-wrapper">
            <Lock size={18} className="input-icon" />
            <input
              type={showPassword ? 'text' : 'password'}
              className="form-input"
              placeholder="Confirm your password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              disabled={isSubmitting}
              required
            />
            {confirmPassword && (
              <span style={{ position: 'absolute', right: 12, top: 12 }}>
                {isMatch ? <Check size={16} color="var(--accent-green)" /> : <X size={16} color="var(--accent-rose)" />}
              </span>
            )}
          </div>
        </div>

        <button
          type="submit"
          className="auth-submit-btn"
          disabled={!isFormValid || isSubmitting}
        >
          {isSubmitting ? (
            <>
              <Loader2 size={18} className="spin" />
              <span>Creating Account...</span>
            </>
          ) : (
            <>
              <span>Create Account</span>
              <ArrowRight size={18} />
            </>
          )}
        </button>
      </form>

      <div className="auth-footer">
        Already have an account?{' '}
        <button type="button" className="text-link font-semibold" onClick={onSwitchToLogin}>
          Sign in
        </button>
      </div>
    </div>
  );
}
