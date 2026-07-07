import ReactMarkdown from 'react-markdown'
import { Bot, User } from 'lucide-react'

export default function MessageBubble({ role, content }) {
  const isBot = role === 'assistant'

  return (
    <div className={`flex gap-3 animate-slide-up ${isBot ? 'justify-start' : 'justify-end'}`}>

      {/* Bot avatar */}
      {isBot && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cinema-accent flex items-center justify-center">
          <Bot size={16} className="text-white" />
        </div>
      )}

      {/* Bubble */}
      <div
        className={`max-w-[75%] px-4 py-3 rounded-2xl text-sm leading-relaxed ${
          isBot
            ? 'bg-cinema-card border border-cinema-border rounded-tl-sm text-cinema-text'
            : 'bg-cinema-accent rounded-tr-sm text-white'
        }`}
      >
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="mb-1 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
            code: ({ children }) => (
              <code className="bg-black/30 px-1 py-0.5 rounded text-xs font-mono">{children}</code>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>

      {/* User avatar */}
      {!isBot && (
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cinema-border flex items-center justify-center">
          <User size={16} className="text-cinema-text" />
        </div>
      )}
    </div>
  )
}
