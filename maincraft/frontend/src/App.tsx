import { useState, useEffect, useCallback, useRef } from 'react';
import Sidebar from './components/Sidebar';
import ChatView from './components/ChatView';
import WorldPanel from './components/WorldPanel';
import type { Chat, Message, Pack } from './types';
import * as api from './api';

export default function App() {
  const [chats, setChats] = useState<Chat[]>([]);
  const [activeChatId, setActiveChatId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [packs, setPacks] = useState<Pack[]>([]);
  const [activePack, setActivePack] = useState('gtnh');
  const [streaming, setStreaming] = useState(false);
  const [streamingContent, setStreamingContent] = useState('');
  const [toolStatus, setToolStatus] = useState('');
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [worldOpen, setWorldOpen] = useState(false);
  const [worldPages, setWorldPages] = useState<Record<string, string>>({});
  const abortRef = useRef(false);

  useEffect(() => {
    api.fetchPacks().then(setPacks);
    api.fetchChats().then(setChats);
  }, []);

  const loadChat = useCallback(async (id: string) => {
    const detail = await api.fetchChat(id);
    setMessages(detail.messages);
    setActivePack(detail.pack);
    setActiveChatId(id);
  }, []);

  const handleNewChat = async () => {
    const chat = await api.createChat(activePack);
    setChats(prev => [chat, ...prev]);
    setActiveChatId(chat.id);
    setMessages([]);
  };

  const handleSelectChat = (id: string) => {
    if (id !== activeChatId) loadChat(id);
  };

  const handleDeleteChat = async (id: string) => {
    await api.deleteChat(id);
    setChats(prev => prev.filter(c => c.id !== id));
    if (activeChatId === id) {
      setActiveChatId(null);
      setMessages([]);
    }
  };

  const handleRenameChat = async (id: string, title: string) => {
    await api.updateChat(id, { title });
    setChats(prev => prev.map(c => c.id === id ? { ...c, title } : c));
  };

  const handlePackChange = async (packId: string) => {
    setActivePack(packId);
    if (activeChatId) {
      await api.updateChat(activeChatId, { pack: packId });
      setChats(prev => prev.map(c => c.id === activeChatId ? { ...c, pack: packId } : c));
    }
  };

  const handleSend = async (text: string) => {
    let chatId = activeChatId;
    if (!chatId) {
      const chat = await api.createChat(activePack);
      setChats(prev => [chat, ...prev]);
      chatId = chat.id;
      setActiveChatId(chatId);
    }

    const userMsg: Message = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content: text,
      created_at: new Date().toISOString(),
    };
    setMessages(prev => [...prev, userMsg]);
    setStreaming(true);
    setStreamingContent('');
    setToolStatus('');
    abortRef.current = false;

    let full = '';
    try {
      for await (const event of api.streamMessage(chatId, text)) {
        if (abortRef.current) break;
        if (event.type === 'token') {
          full += event.content;
          setStreamingContent(full);
          setToolStatus('');
        } else if (event.type === 'tool') {
          setToolStatus(event.content);
        } else if (event.type === 'done') {
          full = event.content;
        } else if (event.type === 'error') {
          full = event.content;
        }
      }
    } catch (err) {
      full = `Error: ${err}`;
    }

    if (full) {
      const assistantMsg: Message = {
        id: `temp-a-${Date.now()}`,
        role: 'assistant',
        content: full,
        created_at: new Date().toISOString(),
      };
      setMessages(prev => [...prev, assistantMsg]);
    }

    setStreaming(false);
    setStreamingContent('');
    setToolStatus('');

    // Refresh chat list for updated title/timestamp
    api.fetchChats().then(setChats);
  };

  const handleStop = () => {
    abortRef.current = true;
    setStreaming(false);
    setToolStatus('');
  };

  const refreshWorld = useCallback(() => {
    api.fetchWorld().then(setWorldPages);
  }, []);

  useEffect(() => {
    if (worldOpen) refreshWorld();
  }, [worldOpen, refreshWorld]);

  return (
    <div className="flex h-full">
      <Sidebar
        chats={chats}
        activeId={activeChatId}
        onSelect={handleSelectChat}
        onNew={handleNewChat}
        onDelete={handleDeleteChat}
        onRename={handleRenameChat}
        collapsed={sidebarCollapsed}
        onToggle={() => setSidebarCollapsed(!sidebarCollapsed)}
      />
      <ChatView
        messages={messages}
        packs={packs}
        activePack={activePack}
        onPackChange={handlePackChange}
        onSend={handleSend}
        onStop={handleStop}
        streaming={streaming}
        streamingContent={streamingContent}
        toolStatus={toolStatus}
        onToggleWorld={() => setWorldOpen(!worldOpen)}
        worldOpen={worldOpen}
      />
      {worldOpen && (
        <WorldPanel
          pages={worldPages}
          onClose={() => setWorldOpen(false)}
          onRefresh={refreshWorld}
        />
      )}
    </div>
  );
}
