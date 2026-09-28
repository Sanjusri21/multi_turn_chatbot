import { useState, useCallback } from 'react';
import { useChatContext } from '../context/ChatContext';
import { memoryApi } from '../services/memoryApi';

export function useMemory() {
  const { memories, loadMemories, showToast, triggerRotoBotReaction } = useChatContext();
  const [loading, setLoading] = useState(false);

  const addMemory = async ({ key, value, category }) => {
    setLoading(true);
    try {
      await memoryApi.createMemory({ key, value, category });
      await loadMemories();
      showToast('Memory added successfully', 'success');
      triggerRotoBotReaction('SUCCESS', 'Memory committed to long-term storage! 🧠');
    } catch (err) {
      showToast(err.message || 'Failed to add memory', 'error');
    } finally {
      setLoading(false);
    }
  };

  const updateMemory = async (id, data) => {
    setLoading(true);
    try {
      await memoryApi.updateMemory(id, data);
      await loadMemories();
      showToast('Memory updated', 'success');
      triggerRotoBotReaction('HAPPY', 'Memory updated! ✨');
    } catch (err) {
      showToast(err.message || 'Failed to update memory', 'error');
    } finally {
      setLoading(false);
    }
  };

  const deleteMemory = async (id) => {
    setLoading(true);
    try {
      await memoryApi.deleteMemory(id);
      await loadMemories();
      showToast('Memory deleted', 'info');
      triggerRotoBotReaction('CONFUSED', 'Memory erased 🧹');
    } catch (err) {
      showToast(err.message || 'Failed to delete memory', 'error');
    } finally {
      setLoading(false);
    }
  };

  const clearAll = async () => {
    setLoading(true);
    try {
      await memoryApi.clearAllMemories();
      await loadMemories();
      showToast('All memories cleared', 'info');
      triggerRotoBotReaction('CONFUSED', 'Clean slate! All memories forgotten.');
    } catch (err) {
      showToast(err.message || 'Failed to clear memories', 'error');
    } finally {
      setLoading(false);
    }
  };

  return {
    memories,
    loading,
    addMemory,
    updateMemory,
    deleteMemory,
    clearAll,
    refreshMemories: loadMemories,
  };
}
