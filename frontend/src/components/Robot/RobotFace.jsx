import React from 'react';
import { motion } from 'framer-motion';
import { RobotExpressions } from './RobotExpressions';
import { eyeColors } from './robotAnimations';

export function RobotFace({ state = 'IDLE' }) {
  const currentEyeColor = eyeColors[state] || eyeColors.IDLE;

  return (
    <svg
      viewBox="0 0 100 100"
      className="rotobot-svg"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
    >
      <defs>
        {/* Helmet Gradient */}
        <linearGradient id="helmetGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#2a3b5c" />
          <stop offset="60%" stopColor="#18233a" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>

        {/* Visor Gradient */}
        <linearGradient id="visorGrad" x1="0%" y1="0%" x2="0%" y2="100%">
          <stop offset="0%" stopColor="#080e1a" />
          <stop offset="100%" stopColor="#04070e" />
        </linearGradient>

        {/* Torso Gradient */}
        <linearGradient id="bodyGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#1e293b" />
          <stop offset="100%" stopColor="#0f172a" />
        </linearGradient>

        {/* Cosmic Saturn Halo Ring Gradient */}
        <linearGradient id="saturnRingGrad" x1="0%" y1="0%" x2="100%" y2="100%">
          <stop offset="0%" stopColor="#fef08a" />
          <stop offset="45%" stopColor="#f59e0b" />
          <stop offset="100%" stopColor="#38bdf8" />
        </linearGradient>
      </defs>

      {/* --- PLANETARY SATURN HALO RING --- */}
      <g transform="translate(50, 15) rotate(-24)">
        <ellipse
          cx="0"
          cy="0"
          rx="22"
          ry="6.5"
          fill="none"
          stroke="url(#saturnRingGrad)"
          strokeWidth="2.6"
          opacity="0.9"
          filter="drop-shadow(0 0 6px rgba(245, 158, 11, 0.65))"
        />
      </g>

      {/* --- ANTENNA --- */}
      <line
        x1="50"
        y1="22"
        x2="50"
        y2="10"
        stroke="#475569"
        strokeWidth="3.5"
        strokeLinecap="round"
      />
      {/* Glowing Antenna Orb */}
      <motion.circle
        cx="50"
        cy="9"
        r="4.5"
        fill={currentEyeColor}
        filter={`drop-shadow(0 0 8px ${currentEyeColor})`}
        animate={{
          scale: state === 'LISTENING' || state === 'THINKING' ? [1, 1.4, 1] : [1, 1.15, 1],
          opacity: [0.8, 1, 0.8],
        }}
        transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* --- SIDE EAR DISCS --- */}
      <circle cx="21" cy="46" r="5" fill="#334155" stroke="#475569" strokeWidth="1.5" />
      <circle cx="79" cy="46" r="5" fill="#334155" stroke="#475569" strokeWidth="1.5" />
      <circle cx="21" cy="46" r="2.5" fill={currentEyeColor} opacity="0.6" />
      <circle cx="79" cy="46" r="2.5" fill={currentEyeColor} opacity="0.6" />

      {/* --- ROBOT HEAD HELMET --- */}
      <rect
        x="23"
        y="22"
        width="54"
        height="48"
        rx="22"
        fill="url(#helmetGrad)"
        stroke="rgba(255, 255, 255, 0.18)"
        strokeWidth="1.5"
      />

      {/* --- GLASS VISOR --- */}
      <rect
        x="27"
        y="30"
        width="46"
        height="32"
        rx="14"
        fill="url(#visorGrad)"
        stroke="rgba(255, 255, 255, 0.08)"
        strokeWidth="1.2"
      />

      {/* Visor subtle glossy reflection curve */}
      <path
        d="M 32 34 Q 50 31 68 34"
        stroke="rgba(255, 255, 255, 0.15)"
        strokeWidth="1.5"
        strokeLinecap="round"
      />

      {/* --- EYES / EXPRESSIONS --- */}
      <RobotExpressions state={state} />

      {/* --- ROBOT TORSO --- */}
      <rect
        x="36"
        y="72"
        width="28"
        height="22"
        rx="8"
        fill="url(#bodyGrad)"
        stroke="rgba(255, 255, 255, 0.12)"
        strokeWidth="1.5"
      />

      {/* Chest Heart/Reactor Core */}
      <motion.circle
        cx="50"
        cy="83"
        r="4"
        fill={currentEyeColor}
        filter={`drop-shadow(0 0 6px ${currentEyeColor})`}
        animate={{
          scale: [1, 1.25, 1],
          opacity: [0.7, 1, 0.7],
        }}
        transition={{ duration: 2, repeat: Infinity, ease: 'easeInOut' }}
      />

      {/* --- ARMS --- */}
      {/* Left arm */}
      <path
        d={state === 'HAPPY' ? "M 35 76 Q 25 74 26 68" : "M 35 76 Q 28 82 32 88"}
        stroke="#334155"
        strokeWidth="4"
        strokeLinecap="round"
        fill="none"
      />
      {/* Right arm */}
      <path
        d={state === 'HAPPY' ? "M 65 76 Q 75 74 74 68" : "M 65 76 Q 72 82 68 88"}
        stroke="#334155"
        strokeWidth="4"
        strokeLinecap="round"
        fill="none"
      />
    </svg>
  );
}
