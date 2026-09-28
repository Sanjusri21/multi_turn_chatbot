import React, { useState } from 'react';
import { AuthLayout } from '../components/Auth/AuthLayout';
import { SignupForm } from '../components/Auth/SignupForm';

export function SignupPage({ onNavigateToLogin }) {
  const [robotState, setRobotState] = useState('HAPPY');
  const [robotSpeech, setRobotSpeech] = useState("Join MemoryBot! I'll remember everything important 🤖✨");

  const handleRobotReaction = (state, speech) => {
    setRobotState(state);
    if (speech) setRobotSpeech(speech);
  };

  return (
    <AuthLayout robotState={robotState} robotSpeech={robotSpeech}>
      <SignupForm
        onSwitchToLogin={onNavigateToLogin}
        onRobotStateChange={handleRobotReaction}
      />
    </AuthLayout>
  );
}
