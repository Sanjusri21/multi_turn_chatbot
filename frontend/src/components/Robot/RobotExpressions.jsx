import React from 'react';
import { motion } from 'framer-motion';
import { eyeColors } from './robotAnimations';

export function RobotExpressions({ state = 'IDLE' }) {
  const color = eyeColors[state] || eyeColors.IDLE;

  switch (state) {
    case 'HAPPY':
      // Curved happy crescents ^ ^
      return (
        <g>
          {/* Left happy eye */}
          <path
            d="M 33 46 Q 39 37 45 46"
            stroke={color}
            strokeWidth="4.5"
            strokeLinecap="round"
            fill="none"
            filter="drop-shadow(0 0 6px rgba(52, 211, 153, 0.8))"
          />
          {/* Right happy eye */}
          <path
            d="M 55 46 Q 61 37 67 46"
            stroke={color}
            strokeWidth="4.5"
            strokeLinecap="round"
            fill="none"
            filter="drop-shadow(0 0 6px rgba(52, 211, 153, 0.8))"
          />
          {/* Joyful smile */}
          <path
            d="M 45 54 Q 50 58 55 54"
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
        </g>
      );

    case 'THINKING':
      // Scanning horizontal pill bars moving left/right
      return (
        <g>
          <motion.rect
            x="32"
            y="42"
            width="14"
            height="6"
            rx="3"
            fill={color}
            filter="drop-shadow(0 0 6px rgba(251, 191, 36, 0.8))"
            animate={{ x: [30, 36, 30] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.rect
            x="54"
            y="42"
            width="14"
            height="6"
            rx="3"
            fill={color}
            filter="drop-shadow(0 0 6px rgba(251, 191, 36, 0.8))"
            animate={{ x: [52, 58, 52] }}
            transition={{ duration: 1.2, repeat: Infinity, ease: 'easeInOut' }}
          />
        </g>
      );

    case 'LISTENING':
      // Dilated wide eyes with animated pulse
      return (
        <g>
          <motion.circle
            cx="39"
            cy="44"
            r="7"
            fill={color}
            filter="drop-shadow(0 0 8px rgba(192, 132, 252, 0.8))"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
          />
          <motion.circle
            cx="61"
            cy="44"
            r="7"
            fill={color}
            filter="drop-shadow(0 0 8px rgba(192, 132, 252, 0.8))"
            animate={{ scale: [1, 1.2, 1] }}
            transition={{ duration: 1, repeat: Infinity, ease: 'easeInOut' }}
          />
        </g>
      );

    case 'TYPING':
      // Eyes looking downwards
      return (
        <g>
          <ellipse
            cx="39"
            cy="48"
            rx="6.5"
            ry="4.5"
            fill={color}
            filter="drop-shadow(0 0 6px rgba(56, 189, 248, 0.8))"
          />
          <ellipse
            cx="61"
            cy="48"
            rx="6.5"
            ry="4.5"
            fill={color}
            filter="drop-shadow(0 0 6px rgba(56, 189, 248, 0.8))"
          />
        </g>
      );

    case 'SUCCESS':
      // Star sparkles / happy stars
      return (
        <g>
          <circle cx="39" cy="43" r="6" fill={color} filter="drop-shadow(0 0 8px #10b981)" />
          <circle cx="61" cy="43" r="6" fill={color} filter="drop-shadow(0 0 8px #10b981)" />
          <path
            d="M 43 53 Q 50 60 57 53"
            stroke={color}
            strokeWidth="3.5"
            strokeLinecap="round"
            fill="none"
          />
        </g>
      );

    case 'CONFUSED':
      // Asymmetric curious eyes (one larger, one arched)
      return (
        <g>
          <circle cx="38" cy="42" r="7" fill={color} filter="drop-shadow(0 0 6px #f97316)" />
          <circle cx="62" cy="46" r="4.5" fill={color} filter="drop-shadow(0 0 6px #f97316)" />
          <path
            d="M 46 54 Q 50 51 54 55"
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
            fill="none"
          />
        </g>
      );

    case 'SLEEPING':
      // Closed slit eyes - - with small Zs
      return (
        <g>
          <line
            x1="33"
            y1="45"
            x2="45"
            y2="45"
            stroke={color}
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          <line
            x1="55"
            y1="45"
            x2="67"
            y2="45"
            stroke={color}
            strokeWidth="3.5"
            strokeLinecap="round"
          />
          {/* Animated floating Z */}
          <motion.text
            x="70"
            y="30"
            fill="#94a3b8"
            fontSize="10"
            fontWeight="bold"
            animate={{ y: [30, 20, 30], opacity: [0.3, 1, 0.3] }}
            transition={{ duration: 2, repeat: Infinity }}
          >
            z
          </motion.text>
          <motion.text
            x="76"
            y="20"
            fill="#94a3b8"
            fontSize="8"
            fontWeight="bold"
            animate={{ y: [20, 10, 20], opacity: [0.2, 0.9, 0.2] }}
            transition={{ duration: 2.2, delay: 0.5, repeat: Infinity }}
          >
            z
          </motion.text>
        </g>
      );

    case 'ERROR':
      // Angry/worried downward angled red slits > <
      return (
        <g>
          <line
            x1="34"
            y1="42"
            x2="44"
            y2="46"
            stroke={color}
            strokeWidth="4"
            strokeLinecap="round"
            filter="drop-shadow(0 0 8px #f43f5e)"
          />
          <line
            x1="66"
            y1="42"
            x2="56"
            y2="46"
            stroke={color}
            strokeWidth="4"
            strokeLinecap="round"
            filter="drop-shadow(0 0 8px #f43f5e)"
          />
          <line
            x1="45"
            y1="54"
            x2="55"
            y2="54"
            stroke={color}
            strokeWidth="3"
            strokeLinecap="round"
          />
        </g>
      );

    case 'IDLE':
    default:
      // Calm, friendly round glowing cyan LED eyes
      return (
        <g>
          <circle
            cx="39"
            cy="44"
            r="6"
            fill={color}
            filter="drop-shadow(0 0 8px rgba(0, 242, 254, 0.9))"
          />
          <circle
            cx="61"
            cy="44"
            r="6"
            fill={color}
            filter="drop-shadow(0 0 8px rgba(0, 242, 254, 0.9))"
          />
          {/* Subtle tiny shine reflection */}
          <circle cx="37" cy="42" r="1.8" fill="#ffffff" opacity="0.8" />
          <circle cx="59" cy="42" r="1.8" fill="#ffffff" opacity="0.8" />
        </g>
      );
  }
}
