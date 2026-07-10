import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneDark } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, User, Bot } from 'lucide-react';

interface Props {
  role: 'user' | 'assistant';
  content: string;
  streaming?: boolean;
}

export default function MessageBubble({ role, content, streaming }: Props) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(content);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const isUser = role === 'user';

  return (
    <div className={`flex gap-3 px-4 py-4 ${isUser ? '' : 'bg-surface-raised/30'}`}>
      <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
        isUser ? 'bg-accent/20 text-accent' : 'bg-surface-overlay text-text-muted'
      }`}>
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs text-text-muted mb-1 font-medium">
          {isUser ? 'You' : 'Guide'}
        </div>
        {isUser ? (
          <p className="text-sm whitespace-pre-wrap">{content}</p>
        ) : (
          <div className="prose text-sm max-w-none">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                code({ className, children, ...props }) {
                  const match = /language-(\w+)/.exec(className || '');
                  const codeStr = String(children).replace(/\n$/, '');
                  if (match) {
                    return (
                      <SyntaxHighlighter style={oneDark} language={match[1]} PreTag="div">
                        {codeStr}
                      </SyntaxHighlighter>
                    );
                  }
                  return <code className={className} {...props}>{children}</code>;
                },
              }}
            >
              {content}
            </ReactMarkdown>
            {streaming && <span className="inline-block w-2 h-4 bg-accent animate-pulse ml-0.5" />}
          </div>
        )}
        {!isUser && content && !streaming && (
          <button onClick={handleCopy} className="mt-2 text-text-muted hover:text-text transition-colors" title="Copy">
            {copied ? <Check size={14} /> : <Copy size={14} />}
          </button>
        )}
      </div>
    </div>
  );
}
