import React from 'react';
import { motion } from 'framer-motion';
import { Sparkles, Code2, BrainCircuit, MessageSquare, Compass, Cpu } from 'lucide-react';
import { useAuth } from '../../hooks/useAuth';

export function WelcomeScreen({ onSelectPrompt }) {
  const { user } = useAuth();
  const userName = user?.name || 'Sanju';

  const promptCards = [
    {
      icon: Sparkles,
      title: "Meet Zara",
      desc: "Learn how Zara's persistent multilingual memory and voice work across sessions",
      prompt: "Tell me about yourself and how your persistent multilingual memory works.",
    },
    {
      icon: Compass,
      title: "What is Python?",
      desc: "Learn programming fundamentals, libraries, and real-world uses",
      prompt: "What is Python? Explain its key features and why it is so popular.",
    },
    {
      icon: BrainCircuit,
      title: "Multilingual Voice Chat",
      desc: "Talk in English, தமிழ் (Tamil), or हिन्दी (Hindi) with Zara",
      prompt: "Hello Zara! You support English, Tamil, and Hindi. What can you do?",
    },
    {
      icon: Code2,
      title: "Learn Python & FastAPI",
      desc: "Build modern, high-performance backends and AI assistants",
      prompt: "I am learning Python and FastAPI to build AI applications. Can you guide me?",
    },
  ];

  return (
    <div className="welcome-screen-container">
      {/* Centered Sleek AI Hero */}
      <motion.div
        className="welcome-hero-card"
        initial={{ opacity: 0, scale: 0.92 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.35 }}
      >
        <div className="welcome-ai-badge">
          <Sparkles size={36} />
        </div>

        <h1 className="welcome-hero-title">
          Hello, <span className="text-gradient">{userName}</span>! 👋
        </h1>
        <p className="welcome-hero-subtitle">
          I'm Zara — your multilingual AI voice assistant who remembers our conversations across sessions. Let's chat!
        </p>

        {/* Suggestion Cards Grid */}
        <div className="welcome-cards-grid">
          {promptCards.map((item, index) => {
            const Icon = item.icon;
            return (
              <motion.div
                key={index}
                className="welcome-card"
                whileHover={{ y: -4, borderColor: 'var(--accent-cyan)' }}
                whileTap={{ scale: 0.98 }}
                onClick={() => onSelectPrompt(item.prompt)}
              >
                <div className="welcome-card-icon">
                  <Icon size={18} />
                </div>
                <div className="welcome-card-content">
                  <div className="welcome-card-title">{item.title}</div>
                  <div className="welcome-card-desc">{item.desc}</div>
                </div>
              </motion.div>
            );
          })}
        </div>
      </motion.div>
    </div>
  );
}
