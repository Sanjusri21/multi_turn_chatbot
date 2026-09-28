import React from 'react';
import { motion } from 'framer-motion';
import { RobotFace } from '../Robot/RobotFace';
import { floatingVariants } from '../Robot/robotAnimations';
import { Sparkles, Clock, Compass } from 'lucide-react';

export function AuthLayout({ children, robotState = 'HAPPY', robotSpeech = "Welcome! I'm RotoBot 🤖" }) {
  const promptPills = [
    { text: 'Tell me about yourself', icon: Sparkles },
    { text: 'What do you like?', icon: Compass },
    { text: 'Continue our previous chat', icon: Clock },
  ];

  return (
    <div className="auth-page">
      <div className="auth-container">
        {/* Left Side: Centered Animated RotoBot Welcome Showcase */}
        <div className="auth-hero">
          <div className="auth-hero-centered-content">
            <motion.div
              className="auth-robot-card"
              variants={floatingVariants}
              animate={robotState}
              whileHover={{ scale: 1.05 }}
            >
              {/* Robot Speech Bubble */}
              {robotSpeech && (
                <div className="auth-robot-bubble">
                  {robotSpeech}
                </div>
              )}

              {/* Large Robot Face - Horizontally Centered */}
              <div className="auth-robot-wrapper">
                <RobotFace state={robotState} />
              </div>
            </motion.div>

            <h1 className="auth-hero-title">
              Welcome to <span className="text-gradient">MemoryBot</span>
            </h1>

            <p className="auth-hero-subtitle">
              An intelligent AI companion with persistent memory.
              Your conversations remember what matters, across
              every session.
            </p>

            <div className="auth-prompt-pills">
              {promptPills.map((p, idx) => {
                const Icon = p.icon;
                return (
                  <div key={idx} className="auth-prompt-pill">
                    <Icon size={14} className="pill-icon" />
                    <span>{p.text}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>

        {/* Right Side: Existing Auth Card */}
        <div className="auth-card-wrapper">
          <motion.div
            className="auth-card"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, ease: 'easeOut' }}
          >
            {children}
          </motion.div>
        </div>
      </div>
    </div>
  );
}
