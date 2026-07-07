import { Bot } from 'lucide-react'

export default function TypingIndicator() {
  return (
    <div className="flex gap-3 items-center animate-fade-in">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-cinema-accent flex items-center justify-center">
        <Bot size={16} className="text-white" />
      </div>
      <div className="bg-cinema-card border border-cinema-border rounded-2xl rounded-tl-sm px-4 py-3 flex gap-1.5 items-center">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="w-2 h-2 rounded-full bg-cinema-muted"
            style={{ animation: `pulseDot 1.4s infinite ease-in-out ${i * 0.16}s` }}
          />
        ))}
      </div>
    </div>
  )
}
