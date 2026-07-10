import { useState } from 'react';
import { Plus, MessageSquare, Trash2, Pencil, Check, X } from 'lucide-react';
import type { Chat } from '../types';
import { PACK_COLORS, PACK_LABELS } from '../types';

interface Props {
  chats: Chat[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  collapsed: boolean;
  onToggle: () => void;
}

function groupByDate(chats: Chat[]): { label: string; chats: Chat[] }[] {
  const now = new Date();
  const today = now.toDateString();
  const yesterday = new Date(now.getTime() - 86400000).toDateString();

  const groups: Record<string, Chat[]> = {};
  for (const chat of chats) {
    const d = new Date(chat.updated_at).toDateString();
    let label = d;
    if (d === today) label = 'Today';
    else if (d === yesterday) label = 'Yesterday';
    else label = new Date(chat.updated_at).toLocaleDateString();
    (groups[label] ??= []).push(chat);
  }
  return Object.entries(groups).map(([label, chats]) => ({ label, chats }));
}

export default function Sidebar({ chats, activeId, onSelect, onNew, onDelete, onRename, collapsed, onToggle }: Props) {
  const [renaming, setRenaming] = useState<string | null>(null);
  const [renameValue, setRenameValue] = useState('');

  if (collapsed) {
    return (
      <div className="w-14 flex flex-col items-center py-4 gap-3 border-r border-border bg-surface-raised shrink-0">
        <button onClick={onToggle} className="p-2 rounded-lg hover:bg-surface-overlay transition-colors" title="Open sidebar">
          <MessageSquare size={20} />
        </button>
        <button onClick={onNew} className="p-2 rounded-lg hover:bg-surface-overlay transition-colors" title="New chat">
          <Plus size={20} />
        </button>
      </div>
    );
  }

  const groups = groupByDate(chats);

  return (
    <div className="w-64 flex flex-col border-r border-border bg-surface-raised shrink-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="font-semibold text-sm">Modpack Guide</span>
        <button onClick={onNew} className="p-1.5 rounded-lg hover:bg-surface-overlay transition-colors" title="New chat">
          <Plus size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto py-2">
        {groups.map(({ label, chats: groupChats }) => (
          <div key={label}>
            <div className="px-4 py-1 text-xs text-text-muted font-medium">{label}</div>
            {groupChats.map(chat => (
              <div
                key={chat.id}
                className={`group flex items-center gap-2 mx-2 px-3 py-2 rounded-lg cursor-pointer transition-colors ${
                  activeId === chat.id ? 'bg-surface-overlay' : 'hover:bg-surface-overlay/50'
                }`}
                onClick={() => onSelect(chat.id)}
              >
                {renaming === chat.id ? (
                  <form className="flex-1 flex gap-1" onSubmit={e => { e.preventDefault(); onRename(chat.id, renameValue); setRenaming(null); }}>
                    <input
                      autoFocus
                      value={renameValue}
                      onChange={e => setRenameValue(e.target.value)}
                      className="flex-1 bg-surface text-sm px-2 py-0.5 rounded border border-border outline-none"
                      onClick={e => e.stopPropagation()}
                    />
                    <button type="submit" onClick={e => e.stopPropagation()}><Check size={14} /></button>
                    <button type="button" onClick={e => { e.stopPropagation(); setRenaming(null); }}><X size={14} /></button>
                  </form>
                ) : (
                  <>
                    <span className="flex-1 text-sm truncate">{chat.title}</span>
                    <span className={`text-[10px] px-1.5 py-0.5 rounded text-white ${PACK_COLORS[chat.pack] ?? 'bg-gray-600'}`}>
                      {PACK_LABELS[chat.pack] ?? chat.pack}
                    </span>
                    <div className="hidden group-hover:flex gap-1">
                      <button
                        onClick={e => { e.stopPropagation(); setRenaming(chat.id); setRenameValue(chat.title); }}
                        className="p-0.5 hover:text-accent"
                      ><Pencil size={13} /></button>
                      <button
                        onClick={e => { e.stopPropagation(); onDelete(chat.id); }}
                        className="p-0.5 hover:text-red-400"
                      ><Trash2 size={13} /></button>
                    </div>
                  </>
                )}
              </div>
            ))}
          </div>
        ))}
        {chats.length === 0 && (
          <div className="px-4 py-8 text-center text-text-muted text-sm">No chats yet</div>
        )}
      </div>
    </div>
  );
}
