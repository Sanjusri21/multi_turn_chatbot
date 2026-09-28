import React, { useMemo } from 'react';
import { motion } from 'framer-motion';
import { 
  Brain, 
  MessageSquare, 
  Sparkles, 
  Cpu, 
  Database, 
  Bot, 
  Share2, 
  Zap, 
  Compass 
} from 'lucide-react';
import './background.css';

/**
 * AnimatedChatBackground - Futuristic AI-Memory Canvas
 * Communicates: AI + conversations + memory + knowledge.
 * Uses:
 * - deep navy, blue, indigo, violet, cyan
 * - glowing particles
 * - orbital/curved lines
 * - neural nodes
 * - floating chat icons
 * - subtle brain/memory icons
 * - soft gradient waves
 * - ambient glow
 * Non-intrusive: pointer-events: none, z-index: 0, fixed.
 */
export function AnimatedChatBackground({ variant = 'full' }) {
  const isAuth = variant === 'auth';

  // Floating particles representing memory bits / knowledge nodes
  const particles = useMemo(() => {
    const list = [];
    const count = isAuth ? 30 : 48;
    const colors = ['#00f2fe', '#4facfe', '#8b5cf6', '#a78bfa', '#38bdf8', '#c084fc'];
    for (let i = 0; i < count; i++) {
      const top = ((i * 47 + 19) % 94) + 3;
      const left = ((i * 71 + 31) % 94) + 3;
      const size = (i % 4 === 0 ? 3.5 : i % 3 === 0 ? 2.5 : i % 2 === 0 ? 2 : 1.5);
      const delay = (i * 0.35) % 5;
      const duration = 3.5 + ((i * 0.6) % 4);
      const color = colors[i % colors.length];
      list.push({ id: i, top, left, size, delay, duration, color });
    }
    return list;
  }, [isAuth]);

  // Subtle floating ambient knowledge and conversation icons
  const floatingIcons = useMemo(() => [
    { icon: Brain, top: '15%', left: '8%', delay: 0, color: '#a78bfa', size: 18, label: 'Memory' },
    { icon: MessageSquare, top: '22%', left: '88%', delay: 1.2, color: '#38bdf8', size: 18, label: 'Chat' },
    { icon: Sparkles, top: '78%', left: '12%', delay: 2.1, color: '#00f2fe', size: 16, label: 'Insights' },
    { icon: Cpu, top: '82%', left: '84%', delay: 0.8, color: '#818cf8', size: 18, label: 'Neural Engine' },
    { icon: Database, top: '48%', left: '4%', delay: 2.8, color: '#4facfe', size: 16, label: 'Persistent Store' },
    { icon: Share2, top: '38%', left: '92%', delay: 1.6, color: '#c084fc', size: 16, label: 'Context' },
  ], []);

  return (
    <div className="ai-memory-bg-canvas" aria-hidden="true">
      {/* 1. Ambient Gradient Waves & Deep Glows */}
      <div className="ai-ambient-glows">
        <div className="glow-wave glow-navy-deep" />
        <div className="glow-wave glow-indigo-violet" />
        <div className="glow-wave glow-cyan-blue" />
        <div className="glow-wave glow-ambient-center" />
      </div>

      {/* 2. Neural Nodes & Orbital Curved Trajectory Lines (SVG) */}
      <svg className="ai-neural-network-svg" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <linearGradient id="neuralGrad1" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor="#00f2fe" stopOpacity="0.4" />
            <stop offset="50%" stopColor="#8b5cf6" stopOpacity="0.25" />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity="0.05" />
          </linearGradient>

          <linearGradient id="neuralGrad2" x1="100%" y1="0%" x2="0%" y2="100%">
            <stop offset="0%" stopColor="#a78bfa" stopOpacity="0.35" />
            <stop offset="50%" stopColor="#00f2fe" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#1e1b4b" stopOpacity="0.05" />
          </linearGradient>

          <filter id="nodeGlow" x="-50%" y="-50%" width="200%" height="200%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* Curved Data Waves */}
        <path
          d="M -100 250 C 300 100, 600 450, 1100 220 S 1600 350, 2000 180"
          fill="none"
          stroke="url(#neuralGrad1)"
          strokeWidth="1.6"
          strokeDasharray="8 6"
          className="animated-neural-path path-fast"
        />
        <path
          d="M -50 600 C 400 750, 800 480, 1300 680 S 1800 500, 2100 620"
          fill="none"
          stroke="url(#neuralGrad2)"
          strokeWidth="1.4"
          strokeDasharray="6 8"
          className="animated-neural-path path-slow"
        />
        <path
          d="M 150 -50 C 350 400, 750 200, 1050 550 S 1450 300, 1650 900"
          fill="none"
          stroke="url(#neuralGrad1)"
          strokeWidth="1.2"
          strokeDasharray="4 6"
          className="animated-neural-path path-reverse"
        />

        {/* Orbital Ellipses */}
        <ellipse
          cx="30%"
          cy="40%"
          rx="320"
          ry="140"
          transform="rotate(-18 450 350)"
          fill="none"
          stroke="rgba(0, 242, 254, 0.12)"
          strokeWidth="1.2"
          strokeDasharray="5 5"
        />
        <ellipse
          cx="75%"
          cy="60%"
          rx="380"
          ry="160"
          transform="rotate(22 1100 550)"
          fill="none"
          stroke="rgba(167, 139, 250, 0.12)"
          strokeWidth="1.2"
          strokeDasharray="6 6"
        />

        {/* Synapse Connection Nodes */}
        <g filter="url(#nodeGlow)">
          <circle cx="22%" cy="32%" r="4" fill="#00f2fe" className="synapse-node node-pulse-1" />
          <circle cx="48%" cy="26%" r="3" fill="#a78bfa" className="synapse-node node-pulse-2" />
          <circle cx="68%" cy="44%" r="4.5" fill="#38bdf8" className="synapse-node node-pulse-3" />
          <circle cx="85%" cy="30%" r="3" fill="#c084fc" className="synapse-node node-pulse-1" />
          <circle cx="35%" cy="68%" r="4" fill="#818cf8" className="synapse-node node-pulse-2" />
          <circle cx="78%" cy="75%" r="3.5" fill="#00f2fe" className="synapse-node node-pulse-3" />
        </g>
      </svg>

      {/* 3. Glowing Memory Particles */}
      <div className="ai-particles-container">
        {particles.map((p) => (
          <div
            key={p.id}
            className="ai-memory-particle"
            style={{
              top: `${p.top}%`,
              left: `${p.left}%`,
              width: `${p.size}px`,
              height: `${p.size}px`,
              backgroundColor: p.color,
              boxShadow: `0 0 ${p.size * 3}px ${p.color}`,
              animationDelay: `${p.delay}s`,
              animationDuration: `${p.duration}s`,
            }}
          />
        ))}
      </div>

      {/* 4. Subtle Floating AI / Memory / Chat Badges */}
      <div className="ai-floating-icons-layer">
        {floatingIcons.map((item, idx) => {
          const Icon = item.icon;
          return (
            <div
              key={idx}
              className="ai-floating-icon-card"
              style={{
                top: item.top,
                left: item.left,
                animationDelay: `${item.delay}s`,
              }}
            >
              <Icon size={item.size} style={{ color: item.color }} />
              <span className="floating-icon-label">{item.label}</span>
            </div>
          );
        })}
      </div>
    </div>
  );
}
