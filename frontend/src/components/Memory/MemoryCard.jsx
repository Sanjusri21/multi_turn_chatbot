import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Edit2, Trash2 } from 'lucide-react';
import { Button } from '../UI/Button';

export function MemoryCard({ memory, onEdit, onDelete }) {
  const getCategoryClass = (cat) => {
    const valid = ['identity', 'education', 'skill', 'interest', 'preference', 'goal'];
    return valid.includes(cat?.toLowerCase()) ? cat.toLowerCase() : 'other';
  };

  return (
    <motion.div
      className="memory-card"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.95 }}
      transition={{ duration: 0.2 }}
    >
      <div>
        <div className="memory-card-header">
          <span className={`category-tag ${getCategoryClass(memory.category)}`}>
            {memory.category}
          </span>
        </div>

        <div className="memory-card-key">{memory.key.replace(/_/g, ' ')}</div>
        <div className="memory-card-value">{memory.value}</div>
      </div>

      <div className="memory-card-footer">
        <Button
          size="sm"
          variant="ghost"
          icon={Edit2}
          onClick={() => onEdit(memory)}
        >
          Edit
        </Button>
        <Button
          size="sm"
          variant="danger"
          icon={Trash2}
          onClick={() => onDelete(memory.id)}
        >
          Delete
        </Button>
      </div>
    </motion.div>
  );
}
