import React, { useState, useEffect, useRef } from 'react';
import { ConversationItem } from './ConversationItem';
import { useChatContext } from '../../context/ChatContext';
import { chatApi } from '../../services/chatApi';

export function ConversationList({ searchQuery = '', onSelectConversation }) {
  const { conversations, currentConversationId } = useChatContext();
  const [searchResults, setSearchResults] = useState(null);
  const [isSearching, setIsSearching] = useState(false);
  const debounceTimerRef = useRef(null);

  // Debounced search querying database for title, keywords, and message contents (Requirement 2)
  useEffect(() => {
    const trimmed = searchQuery.trim();
    if (!trimmed) {
      setSearchResults(null);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    debounceTimerRef.current = setTimeout(async () => {
      try {
        const results = await chatApi.getConversations(trimmed);
        setSearchResults(results);
      } catch (err) {
        console.error('Conversation search error:', err);
        // Fallback to client-side filtering if search query fails
        const clientFiltered = conversations.filter((c) =>
          c.title.toLowerCase().includes(trimmed.toLowerCase())
        );
        setSearchResults(clientFiltered);
      } finally {
        setIsSearching(false);
      }
    }, 280);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [searchQuery, conversations]);

  const itemsToDisplay = searchResults !== null ? searchResults : conversations;

  // Group conversations by date: Today, Yesterday, Previous 7 days, Older (Requirement 15)
  const now = new Date();
  const todayStart = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime();
  const yesterdayStart = todayStart - 86400000;
  const sevenDaysAgoStart = todayStart - 7 * 86400000;

  const groups = {
    today: [],
    yesterday: [],
    previous7Days: [],
    older: [],
  };

  itemsToDisplay.forEach((conv) => {
    const updatedTime = new Date(conv.updated_at).getTime();
    if (updatedTime >= todayStart) {
      groups.today.push(conv);
    } else if (updatedTime >= yesterdayStart) {
      groups.yesterday.push(conv);
    } else if (updatedTime >= sevenDaysAgoStart) {
      groups.previous7Days.push(conv);
    } else {
      groups.older.push(conv);
    }
  });

  if (itemsToDisplay.length === 0) {
    return (
      <div className="conversations-empty-state">
        {isSearching
          ? 'Searching...'
          : searchQuery
          ? 'No matching conversations'
          : 'No conversations yet'}
      </div>
    );
  }

  const renderGroup = (title, items) => {
    if (items.length === 0) return null;
    return (
      <div className="conversation-group">
        <div className="sidebar-section-title">{title}</div>
        {items.map((conv) => (
          <ConversationItem
            key={conv.id}
            conversation={conv}
            isActive={conv.id === currentConversationId}
            onSelect={onSelectConversation}
          />
        ))}
      </div>
    );
  };

  return (
    <div className="conversations-container">
      {renderGroup('Today', groups.today)}
      {renderGroup('Yesterday', groups.yesterday)}
      {renderGroup('Previous 7 days', groups.previous7Days)}
      {renderGroup('Older', groups.older)}
    </div>
  );
}
