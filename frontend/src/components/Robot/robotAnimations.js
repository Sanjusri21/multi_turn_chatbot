// Framer Motion animation variants for RotoBot

export const floatingVariants = {
  IDLE: {
    y: [0, -8, 0],
    rotate: [0, 1, -1, 0],
    transition: {
      duration: 3.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  HAPPY: {
    y: [0, -14, 0, -8, 0],
    scale: [1, 1.05, 1],
    rotate: [0, -3, 3, 0],
    transition: {
      duration: 0.8,
      repeat: 2,
      ease: 'easeInOut',
    },
  },
  THINKING: {
    y: [0, -4, 0],
    rotate: [-2, 2, -2],
    transition: {
      duration: 2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  LISTENING: {
    y: [0, -6, 0],
    scale: [1, 1.03, 1],
    transition: {
      duration: 1.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  TYPING: {
    y: [0, 2, 0],
    rotate: [0, -1, 1, 0],
    transition: {
      duration: 1.2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  SUCCESS: {
    y: [0, -18, 0],
    scale: [1, 1.1, 1],
    rotate: [0, 6, -6, 0],
    transition: {
      duration: 0.7,
      repeat: 2,
      ease: 'easeOut',
    },
  },
  CONFUSED: {
    rotate: [-12, -8, -12],
    y: [0, -4, 0],
    transition: {
      duration: 2.2,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  SLEEPING: {
    y: [0, -3, 0],
    rotate: [2, 4, 2],
    transition: {
      duration: 4.5,
      repeat: Infinity,
      ease: 'easeInOut',
    },
  },
  ERROR: {
    x: [-3, 3, -3, 3, 0],
    y: [0, -2, 0],
    transition: {
      duration: 0.4,
      repeat: 2,
    },
  },
};

export const eyeColors = {
  IDLE: '#00f2fe',
  HAPPY: '#34d399',
  THINKING: '#fbbf24',
  LISTENING: '#c084fc',
  TYPING: '#38bdf8',
  SUCCESS: '#10b981',
  CONFUSED: '#f97316',
  SLEEPING: '#94a3b8',
  ERROR: '#f43f5e',
};
