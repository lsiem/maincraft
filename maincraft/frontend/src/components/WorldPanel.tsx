import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { X, Send, RefreshCw } from 'lucide-react';
import { describeWorld } from '../api';

interface Props {
  pages: Record<string, string>;
  onClose: () => void;
  onRefresh: () => void;
}

const PAGE_LABELS: Record<string, string> = {
  progression: 'Progression',
  base_infrastructure: 'Infrastructure',
  bottlenecks: 'Bottlenecks',
  index: 'Index',
};

export default function WorldPanel({ pages, onClose, onRefresh }: Props) {
  const [describe, setDescribe] = useState('');
  const [describing, setDescribing] = useState(false);
  const [activeTab, setActiveTab] = useState('progression');

  const handleDescribe = async () => {
    if (!describe.trim() || describing) return;
    setDescribing(true);
    try {
      await describeWorld(describe.trim());
      setDescribe('');
      onRefresh();
    } finally {
      setDescribing(false);
    }
  };

  const tabs = ['progression', 'base_infrastructure', 'bottlenecks'];

  return (
    <div className="w-80 flex flex-col border-l border-border bg-surface-raised shrink-0">
      <div className="flex items-center justify-between px-4 py-3 border-b border-border">
        <span className="font-semibold text-sm">World State</span>
        <div className="flex gap-1">
          <button onClick={onRefresh} className="p-1.5 rounded-lg hover:bg-surface-overlay transition-colors" title="Refresh">
            <RefreshCw size={16} />
          </button>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-surface-overlay transition-colors" title="Close">
            <X size={16} />
          </button>
        </div>
      </div>

      <div className="flex border-b border-border">
        {tabs.map(tab => (
          <button
            key={tab}
            onClick={() => setActiveTab(tab)}
            className={`flex-1 px-2 py-2 text-xs font-medium transition-colors ${
              activeTab === tab ? 'text-accent border-b-2 border-accent' : 'text-text-muted hover:text-text'
            }`}
          >
            {PAGE_LABELS[tab]}
          </button>
        ))}
      </div>

      <div className="flex-1 overflow-y-auto p-4">
        <div className="prose text-sm max-w-none">
          <ReactMarkdown remarkPlugins={[remarkGfm]}>
            {pages[activeTab] ?? '_No data yet_'}
          </ReactMarkdown>
        </div>
      </div>

      <div className="border-t border-border p-3">
        <p className="text-xs text-text-muted mb-2">Describe your world</p>
        <div className="flex gap-2">
          <input
            value={describe}
            onChange={e => setDescribe(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && handleDescribe()}
            placeholder="I just built a steam boiler…"
            disabled={describing}
            className="flex-1 bg-surface text-sm px-3 py-2 rounded-lg border border-border outline-none placeholder:text-text-muted"
          />
          <button
            onClick={handleDescribe}
            disabled={describing || !describe.trim()}
            className="p-2 rounded-lg bg-accent text-white hover:bg-accent-hover transition-colors disabled:opacity-40"
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
