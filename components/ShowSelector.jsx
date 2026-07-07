import { Calendar, Clock, IndianRupee } from 'lucide-react'

export default function ShowSelector({ shows, onSelect }) {
  if (!shows || shows.length === 0) {
    return (
      <div className="card mt-2 text-cinema-muted text-sm">
        No shows available.
      </div>
    )
  }

  return (
    <div className="mt-2 animate-slide-up">
      <p className="text-xs text-cinema-muted mb-2 uppercase tracking-wider">Select a show</p>
      <div className="grid gap-2">
        {shows.map((show, idx) => (
          <button
            key={show._id ?? idx}
            onClick={() => onSelect(show.time)}
            className="flex items-center gap-4 w-full text-left px-4 py-3 rounded-xl
                       bg-cinema-card border border-cinema-border
                       hover:border-cinema-accent hover:bg-cinema-accent/10
                       transition-all duration-200 group"
          >
            <div className="flex items-center gap-1.5 text-cinema-muted group-hover:text-cinema-text transition-colors">
              <Calendar size={14} />
              <span className="text-sm">{show.date}</span>
            </div>

            <div className="flex items-center gap-1.5 text-cinema-accent font-semibold">
              <Clock size={14} />
              <span className="text-sm">{show.time}</span>
            </div>

            <div className="flex items-center gap-1 text-cinema-muted group-hover:text-cinema-text transition-colors ml-auto">
              <IndianRupee size={13} />
              <span className="text-sm">{show.ticket_price}</span>
            </div>
          </button>
        ))}
      </div>
    </div>
  )
}
