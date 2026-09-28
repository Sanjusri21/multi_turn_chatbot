import React from 'react';
import { AuthLayout } from '../components/Auth/AuthLayout';
import { LoginForm } from '../components/Auth/LoginForm';

export function LoginPage({ onNavigateToSignup }) {
  return (
    <AuthLayout
      robotState="HAPPY"
      robotSpeech="Welcome back! Let's chat 👋"
    >
      <LoginForm onSwitchToSignup={onNavigateToSignup} />
    </AuthLayout>
  );
}
