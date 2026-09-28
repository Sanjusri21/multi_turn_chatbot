import React, { useState, useEffect } from 'react';
import { motion, AnimatePresence, useMotionValue } from 'framer-motion';
import { RobotFace } from './RobotFace';
import { floatingVariants } from './robotAnimations';
import { useChatContext } from '../../context/ChatContext';

export function RotoBot() {
  const { rotoBotState, rotoBotBubble, triggerRotoBotReaction } = useChatContext();
  const [isDragging, setIsDragging] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  // Position state separated strictly from expression state
  const [position, setPosition] = useState({ x: 0, y: 0 });
  const x = useMotionValue(0);
  const y = useMotionValue(0);

  // Dynamic drag constraints so RotoBot cannot disappear outside the viewport
  const [dragConstraints, setDragConstraints] = useState({
    top: -10,
    left: -700,
    right: 15,
    bottom: 500,
  });

  useEffect(() => {
    const updateConstraints = () => {
      const w = window.innerWidth;
      const h = window.innerHeight;
      setDragConstraints({
        top: -10,
        left: -(w - 320),
        right: 15,
        bottom: h - 220,
      });
    };
    updateConstraints();
    window.addEventListener('resize', updateConstraints);
    return () => window.removeEventListener('resize', updateConstraints);
  }, []);

  const handleDragStart = () => {
    setIsDragging(true);
  };

  const handleDragEnd = () => {
    setIsDragging(false);
    // Explicitly record final coordinates into position state
    const currentX = x.get();
    const currentY = y.get();
    setPosition({ x: currentX, y: currentY });
  };

  const handleClick = () => {
    // Only trigger speech easter egg if user clicked without dragging
    if (isDragging) return;

    const funReactions = [
      { state: 'SUCCESS', msg: 'Zara systems 100% nominal! 🚀' },
      { state: 'HAPPY', msg: 'Beep boop! Always here for you! ✨' },
      { state: 'LISTENING', msg: 'Ready when you are! 🎧' },
      { state: 'CONFUSED', msg: "Did you click my helmet? I'm Zara! 🤖" },
    ];
    const picked = funReactions[Math.floor(Math.random() * funReactions.length)];
    triggerRotoBotReaction(picked.state, picked.msg, 3500);
  };

  return (
    <div className="rotobot-container">
      {/* 1. DRAGGABLE WRAPPER:
             Owns X/Y position and dragging gestures only.
             Changing expression does NOT affect or reset this layer. */}
      <motion.div
        className={`rotobot-draggable-wrapper ${isDragging ? 'is-dragging' : ''}`}
        drag
        dragMomentum={false}
        dragElastic={0.08}
        dragConstraints={dragConstraints}
        style={{ x, y }}
        whileHover={{ scale: isDragging ? 1.08 : 1.03 }}
        whileDrag={{ scale: 1.08 }}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
        onClick={handleClick}
        onHoverStart={() => setIsHovered(true)}
        onHoverEnd={() => setIsHovered(false)}
        title="I'm Zara! Drag me anywhere on screen or click me."
      >
        {/* 2. ROBOT ANIMATION CONTAINER:
               Owns floating bobbing and expression animations (HAPPY, THINKING, etc.).
               Runs inside the coordinate space of the draggable wrapper. */}
        <motion.div
          className="rotobot-animation-container"
          variants={floatingVariants}
          animate={rotoBotState}
        >
          {/* Floating Speech Bubble */}
          <AnimatePresence>
            {rotoBotBubble && (
              <motion.div
                className="rotobot-bubble"
                initial={{ opacity: 0, y: 10, scale: 0.8 }}
                animate={{ opacity: 1, y: 0, scale: 1 }}
                exit={{ opacity: 0, y: 6, scale: 0.8 }}
                transition={{ duration: 0.25 }}
              >
                {rotoBotBubble}
              </motion.div>
            )}
          </AnimatePresence>

          {/* 3. ROBOT FACE SVG & EXPRESSIONS */}
          <RobotFace state={rotoBotState} />

          {/* Status Badge */}
          <span className={`rotobot-status-badge ${rotoBotState.toLowerCase()}`}>
            {rotoBotState}
          </span>
        </motion.div>
      </motion.div>
    </div>
  );
}
