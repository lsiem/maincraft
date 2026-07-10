import { useEffect, useRef } from 'react';
import MessageBubble from './MessageBubble';
import Composer from './Composer';
import PackSelector from './PackSelector';
import { Globe, PanelRightOpen } from 'lucide-react';
import type { Message, Pack } from '../types';
import { STARTER_PROMPTS } from '../types';

interface Props {
  messages: Message[];
  packs: Pack[];
  activePack: string;
  onPackChange: (packId: string) => void;
  onSend: (text: string) => void;
  onStop: () => void;
  streaming: boolean;
  streamingContent: string;
  toolStatus: string;
  onToggleWorld: () => void;
  worldOpen: boolean;
}

export default function ChatView({
  messages, packs, activePack, onPackChange, onSend, onStop,
  streaming, streamingContent, toolStatus, onToggleWorld, worldOpen,
}: Props) {
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, toolStatus]);

  const prompts = STARTER_PROMPTS[activePack] ?? STARTER_PROMPTS.gtnh;
  const isEmpty = messages.length === 0 && !streaming;

  return (
    <div className="flex-1 flex flex-col min-w-0">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-border bg-surface shrink-0">
        <PackSelector packs={packs} activePack={activePack} onChange={onPackChange} />
        <button
          onClick={onToggleWorld}
          className={`p-2 rounded-lg transition-colors ${worldOpen ? 'bg-accent/20 text-accent' : 'hover:bg-surface-overlay text-text-muted'}`}
          title="World state"
        >
          {worldOpen ? <PanelRightOpen size={18} /> : <Globe size={18} />}
        </button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {isEmpty ? (
          <div className="flex flex-col items-center justify-center h-full px-4">
            <h2 className="text-2xl font-semibold mb-2">Modpack Guide</h2>
            <p className="text-text-muted text-sm mb-8">Ask anything about quests, recipes, or progression</p>
            <div className="grid gap-2 w-full max-w-lg">
              {prompts.map(p => (
                <button
                  key={p}
                  onClick={() => onSend(p)}
                  className="text-left px-4 py-3 rounded-xl border border-border hover:bg-surface-overlay transition-colors text-sm"
                >
                  {p}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto">
            {messages.map(m => (
              <MessageBubble key={m.id} role={m.role} content={m.content} />
            ))}
            {streaming && streamingContent && (
              <MessageBubble role="assistant" content={streamingContent} streaming />
            )}
            {toolStatus && (
              <div className="px-4 py-2 text-xs text-text-muted italic animate-pulse">
                {toolStatus}
              </div>
            )}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Composer */}
      <Composer onSend={onSend} onStop={onStop} disabled={streaming} streaming={streaming} />
    </div>
  );
}
