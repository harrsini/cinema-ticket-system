import { useState, useRef, useEffect } from 'react'
import { Send, Film, RotateCcw } from 'lucide-react'

import { sendMessage } from './api'

import MessageBubble    from './components/MessageBubble'
import TypingIndicator  from './components/TypingIndicator'
import TheatreSelector  from './components/TheatreSelector'
import ShowSelector     from './components/ShowSelector'
import SeatSelector     from './components/SeatSelector'
import EmailInput       from './components/EmailInput'
import BookingConfirmed from './components/BookingConfirmed'

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Creates a bot text message object */
const botMsg  = (content)        => ({ role: 'assistant', content, type: 'text' })
/** Creates a user text message object */
const userMsg = (content)        => ({ role: 'user',      content, type: 'text' })
/** Creates a rich bot message that carries an interactive widget */
const richMsg = (content, type, data, raw) => ({
  role: 'assistant', content, type, data, raw
})

const WELCOME = botMsg(
  "👋 Hi! I'm **CineBot**. I can help you discover movies, answer movie questions, and book cinema tickets.\n\nWhat would you like to watch today?"
)

// ---------------------------------------------------------------------------
// App
// ---------------------------------------------------------------------------

export default function App() {
  const [messages,  setMessages]  = useState([WELCOME])
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)

  // Tracks what interactive widget (if any) is waiting for the user
  // Values: null | 'theatre_selection' | 'show_selection' |
  //         'seat_selection' | 'awaiting_email'
  const [pendingWidget, setPendingWidget] = useState(null)

  const bottomRef  = useRef(null)
  const inputRef   = useRef(null)

  // Auto-scroll on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // ---------------------------------------------------------------------------
  // Core: send a raw string to the backend and process the response
  // ---------------------------------------------------------------------------
  const dispatch = async (text, displayText = text) => {
    if (!text.trim()) return

    // Add user bubble (displayText may differ from text sent, e.g. theatre name)
    setMessages((prev) => [...prev, userMsg(displayText)])
    setInput('')
    setLoading(true)
    setPendingWidget(null)

    try {
      const result = await sendMessage(text)

      switch (result.type) {
        case 'theatre_selection':
          setMessages((prev) => [
            ...prev,
            richMsg(result.message, 'theatre_selection', result.data, result),
          ])
          setPendingWidget('theatre_selection')
          break

        case 'show_selection':
          setMessages((prev) => [
            ...prev,
            richMsg(result.message, 'show_selection', result.data, result),
          ])
          setPendingWidget('show_selection')
          break

        case 'seat_selection':
          setMessages((prev) => [
            ...prev,
            richMsg(result.message, 'seat_selection', result.data, result),
          ])
          setPendingWidget('seat_selection')
          break

        case 'awaiting_email':
          setMessages((prev) => [
            ...prev,
            richMsg(result.message, 'awaiting_email', null, result),
          ])
          setPendingWidget('awaiting_email')
          break

        case 'booking_confirmed':
          setMessages((prev) => [
            ...prev,
            richMsg(result.message, 'booking_confirmed', null, result),
          ])
          setPendingWidget(null)
          break

        default:
          // Plain text response
          setMessages((prev) => [...prev, botMsg(result.message)])
          setPendingWidget(null)
      }
    } catch (err) {
      console.error(err)
      setMessages((prev) => [
        ...prev,
        botMsg('⚠️ Something went wrong. Please try again.'),
      ])
      setPendingWidget(null)
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  // ---------------------------------------------------------------------------
  // Widget callbacks — each one sends the selected value back to the backend
  // ---------------------------------------------------------------------------

  const handleTheatreSelect = (theatre) => dispatch(theatre)
  const handleShowSelect    = (time)    => dispatch(time)

  const handleSeatConfirm = (seats) => {
    const seatStr = seats.join(', ')
    dispatch(seatStr, `Seats: ${seatStr}`)
  }

  const handleEmailSubmit = (email) => dispatch(email)

  // ---------------------------------------------------------------------------
  // Text input submit (used when no widget is active or for override typing)
  // ---------------------------------------------------------------------------
  const handleSubmit = (e) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    dispatch(input)
  }

  // ---------------------------------------------------------------------------
  // Reset conversation
  // ---------------------------------------------------------------------------
  const handleReset = () => {
    setMessages([WELCOME])
    setInput('')
    setPendingWidget(null)
    setLoading(false)
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------
  return (
    <div className="flex flex-col h-screen bg-cinema-bg">

      {/* ---- Header ---- */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-cinema-border bg-cinema-card/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-cinema-accent flex items-center justify-center shadow-lg shadow-cinema-accent/30">
            <Film size={18} className="text-white" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-none">CineBot</h1>
            <p className="text-xs text-cinema-muted mt-0.5">AI Cinema Booking</p>
          </div>
        </div>

        <button
          onClick={handleReset}
          title="Start over"
          className="flex items-center gap-2 text-xs text-cinema-muted hover:text-cinema-text
                     border border-cinema-border hover:border-cinema-accent/50
                     px-3 py-1.5 rounded-lg transition-all duration-200"
        >
          <RotateCcw size={13} />
          New session
        </button>
      </header>

      {/* ---- Messages ---- */}
      <main className="flex-1 overflow-y-auto px-4 py-6 space-y-4 max-w-3xl w-full mx-auto">
        {messages.map((msg, idx) => (
          <div key={idx}>
            <MessageBubble role={msg.role} content={msg.content} />

            {/* Render interactive widget only on the last relevant message */}
            {msg.type === 'theatre_selection' && idx === messages.length - 1 && (
              <div className="ml-11">
                <TheatreSelector theatres={msg.data} onSelect={handleTheatreSelect} />
              </div>
            )}

            {msg.type === 'show_selection' && idx === messages.length - 1 && (
              <div className="ml-11">
                <ShowSelector shows={msg.data} onSelect={handleShowSelect} />
              </div>
            )}

            {msg.type === 'seat_selection' && idx === messages.length - 1 && (
              <div className="ml-11">
                <SeatSelector seats={msg.data} onConfirm={handleSeatConfirm} />
              </div>
            )}

            {msg.type === 'awaiting_email' && idx === messages.length - 1 && (
              <div className="ml-11">
                <EmailInput onSubmit={handleEmailSubmit} />
              </div>
            )}

            {msg.type === 'booking_confirmed' && (
              <div className="ml-11">
                <BookingConfirmed result={msg.raw} />
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div>
            <TypingIndicator />
          </div>
        )}

        <div ref={bottomRef} />
      </main>

      {/* ---- Input bar ---- */}
      <footer className="border-t border-cinema-border bg-cinema-card/50 backdrop-blur-sm px-4 py-4">
        <form
          onSubmit={handleSubmit}
          className="max-w-3xl mx-auto flex items-center gap-3"
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            placeholder={
              pendingWidget === 'theatre_selection' ? 'Or type a theatre name…' :
              pendingWidget === 'show_selection'    ? 'Or type a show time…' :
              pendingWidget === 'awaiting_email'    ? 'Use the email field above…' :
              'Ask me about movies or book tickets…'
            }
            className="flex-1 bg-cinema-card border border-cinema-border rounded-xl
                       px-4 py-3 text-sm text-cinema-text placeholder:text-cinema-muted
                       focus:outline-none focus:border-cinema-accent/60
                       disabled:opacity-50 transition-colors"
          />
          <button
            type="submit"
            disabled={!input.trim() || loading}
            className="w-11 h-11 rounded-xl bg-cinema-accent
                       disabled:opacity-30 disabled:cursor-not-allowed
                       flex items-center justify-center
                       hover:bg-red-700 active:scale-95 transition-all"
          >
            <Send size={16} className="text-white" />
          </button>
        </form>

        <p className="text-center text-xs text-cinema-muted mt-2">
          CineBot may make mistakes. Confirm booking details before finalising.
        </p>
      </footer>

    </div>
  )
}
