import { useState } from 'react'
import { Mail, Send } from 'lucide-react'

export default function EmailInput({ onSubmit }) {
  const [email, setEmail] = useState('')

  const isValid = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)

  const handleSubmit = (e) => {
    e.preventDefault()
    if (!isValid) return
    onSubmit(email)
  }

  return (
    <form onSubmit={handleSubmit} className="mt-2 animate-slide-up">
      <div className="card flex gap-3 items-center">
        <Mail size={16} className="text-cinema-muted flex-shrink-0" />
        <input
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          autoFocus
          className="flex-1 bg-transparent text-sm text-cinema-text placeholder:text-cinema-muted
                     outline-none border-none focus:ring-0"
        />
        <button
          type="submit"
          disabled={!isValid}
          className="flex-shrink-0 w-8 h-8 rounded-lg bg-cinema-accent
                     disabled:opacity-30 disabled:cursor-not-allowed
                     flex items-center justify-center transition-opacity"
        >
          <Send size={14} className="text-white" />
        </button>
      </div>
    </form>
  )
}
