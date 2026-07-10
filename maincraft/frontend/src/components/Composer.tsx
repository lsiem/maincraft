import { useRef, useEffect } from 'react';
import { Send, Square } from 'lucide-react';

interface Props {
  onSend: (text: string) => void;
  onStop: () => void;
  disabled: boolean;
  streaming: boolean;
}

export default function Composer({ onSend, onStop, disabled, streaming }: Props) {
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    if (!disabled && textareaRef.current) {
      textareaRef.current.focus();
    }
  }, [disabled]);

  const handleSubmit = () => {
    const text = textareaRef.current?.value.trim();
    if (!text || disabled) return;
    onSend(text);
    if (textareaRef.current) textareaRef.current.value = '';
    autoResize();
  };

  const autoResize = () => {
    const el = textareaRef.current;
    if (el) {
      el.style.height = 'auto';
      el.style.height = Math.min(el.scrollHeight, 200) + 'px';
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="border-t border-border bg-surface px-4 py-3">
      <div className="max-w-3xl mx-auto flex items-end gap-2 bg-surface-raised rounded-2xl border border-border px-4 py-2">
        <textarea
          ref={textareaRef}
          placeholder="Ask about quests, recipes, progression…"
          rows={1}
          disabled={disabled}
          onInput={autoResize}
          onKeyDown={handleKeyDown}
          className="flex-1 bg-transparent resize-none outline-none text-sm py-1.5 max-h-[200px] placeholder:text-text-muted"
        />
        {streaming ? (
          <button onClick={onStop} className="p-2 rounded-lg bg-red-600/20 text-red-400 hover:bg-red-600/30 transition-colors" title="Stop">
            <Square size={18} />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={disabled}
            className="p-2 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-40"
            title="Send"
          >
            <Send size={18} />
          </button>
        )}
      </div>
      <p className="text-center text-[11px] text-text-muted mt-2">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  );
}
