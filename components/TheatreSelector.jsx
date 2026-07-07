import { MapPin } from 'lucide-react'

export default function TheatreSelector({ theatres, onSelect }) {
  if (!theatres || theatres.length === 0) {
    return (
      <div className="card mt-2 text-cinema-muted text-sm">
        No theatres found for this movie.
      </div>
    )
  }

  return (
    <div className="mt-2 animate-slide-up">
      <p className="text-xs text-cinema-muted mb-2 uppercase tracking-wider">Select a theatre</p>
      <div className="grid gap-2">
        {theatres.map((theatre) => (
          <button
            key={theatre}
            onClick={() => onSelect(theatre)}
            className="flex items-center gap-3 w-full text-left px-4 py-3 rounded-xl
                       bg-cinema-card border border-cinema-border
                       hover:border-cinema-accent hover:bg-cinema-accent/10
                       transition-all duration-200 group"
          >
            <MapPin
              size={16}
              className="text-cinema-muted group-hover:text-cinema-accent transition-colors flex-shrink-0"
            />
            <span className="text-sm font-medium text-cinema-text group-hover:text-cinema-accent transition-colors">
              {theatre}
            </span>
          </button>
        ))}
      </div>
    </div>
  )
}
