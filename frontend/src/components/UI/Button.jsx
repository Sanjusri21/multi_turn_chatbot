import React from 'react';

export function Button({
  children,
  variant = 'primary', // 'primary', 'secondary', 'danger', 'ghost'
  size = 'md', // 'sm', 'md', 'lg'
  disabled = false,
  onClick,
  className = '',
  icon: Icon,
  type = 'button',
}) {
  const baseStyle = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '8px',
    borderRadius: '8px',
    fontWeight: '600',
    cursor: disabled ? 'not-allowed' : 'pointer',
    transition: 'all 0.2s ease',
    border: 'none',
    opacity: disabled ? 0.5 : 1,
    outline: 'none',
    fontFamily: 'inherit',
  };

  const sizes = {
    sm: { padding: '6px 12px', fontSize: '0.8rem' },
    md: { padding: '8px 16px', fontSize: '0.88rem' },
    lg: { padding: '12px 22px', fontSize: '1rem' },
  };

  const variants = {
    primary: {
      background: 'linear-gradient(135deg, #00f2fe 0%, #4facfe 100%)',
      color: '#050b14',
      boxShadow: '0 2px 10px rgba(0, 242, 254, 0.25)',
    },
    secondary: {
      background: 'rgba(255, 255, 255, 0.08)',
      color: '#f0f4fc',
      border: '1px solid rgba(255, 255, 255, 0.12)',
    },
    danger: {
      background: 'rgba(244, 63, 94, 0.15)',
      color: '#f43f5e',
      border: '1px solid rgba(244, 63, 94, 0.3)',
    },
    ghost: {
      background: 'transparent',
      color: '#94a3b8',
    },
  };

  return (
    <button
      type={type}
      disabled={disabled}
      onClick={onClick}
      style={{
        ...baseStyle,
        ...sizes[size],
        ...variants[variant],
      }}
      className={className}
    >
      {Icon && <Icon size={size === 'sm' ? 14 : size === 'lg' ? 18 : 16} />}
      {children}
    </button>
  );
}
