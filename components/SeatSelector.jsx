import { useState } from 'react'
import { CheckCircle } from 'lucide-react'

export default function SeatSelector({ seats, onConfirm }) {
  const [selected, setSelected] = useState([])

  const toggle = (seat) => {
    if (seat.status !== 'Available') return
    setSelected((prev) =>
      prev.includes(seat.seat_number)
        ? prev.filter((s) => s !== seat.seat_number)
        : [...prev, seat.seat_number]
    )
  }

  const handleConfirm = () => {
    if (selected.length === 0) return
    onConfirm(selected)
  }

  if (!seats || seats.length === 0) {
    return (
      <div className="card mt-2 text-cinema-muted text-sm">
        No seats available.
      </div>
    )
  }

  // Group seats by row letter
  const rows = seats.reduce((acc, seat) => {
    const row = seat.seat_number[0]
    if (!acc[row]) acc[row] = []
    acc[row].push(seat)
    return acc
  }, {})

  return (
    <div className="mt-2 animate-slide-up">
      <p className="text-xs text-cinema-muted mb-3 uppercase tracking-wider">
        Select your seats
      </p>

      {/* Screen indicator */}
      <div className="mb-4 text-center">
        <div className="inline-block w-40 h-1.5 rounded-full bg-gradient-to-r from-transparent via-cinema-accent to-transparent" />
        <p className="text-xs text-cinema-muted mt-1">Screen</p>
      </div>

      {/* Seat grid */}
      <div className="card space-y-2">
        {Object.entries(rows).map(([row, rowSeats]) => (
          <div key={row} className="flex items-center gap-2">
            <span className="text-xs text-cinema-muted w-4 font-mono">{row}</span>
            <div className="flex flex-wrap gap-1.5">
              {rowSeats.map((seat) => {
                const isAvailable = seat.status === 'Available'
                const isSelected  = selected.includes(seat.seat_number)

                let seatStyle = ''
                if (isSelected) {
                  seatStyle = 'bg-cinema-accent text-white shadow-lg shadow-cinema-accent/30 scale-105'
                } else if (!isAvailable) {
                  seatStyle = 'bg-red-900/60 text-red-400 border border-red-800/50 cursor-not-allowed opacity-70'
                } else {
                  seatStyle = 'bg-cinema-border hover:bg-cinema-accent/20 hover:text-cinema-accent text-cinema-muted cursor-pointer'
                }

                return (
                  <button
                    key={seat.seat_number}
                    onClick={() => toggle(seat)}
                    disabled={!isAvailable}
                    title={isAvailable ? seat.seat_number : `${seat.seat_number} — Booked`}
                    className={`w-8 h-8 rounded-md text-xs font-mono font-medium
                                transition-all duration-150 active:scale-90 ${seatStyle}`}
                  >
                    {seat.seat_number.slice(1)}
                  </button>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Legend */}
      <div className="flex gap-4 mt-3 text-xs text-cinema-muted">
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-cinema-border inline-block" />
          Available
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-cinema-accent inline-block" />
          Selected
        </span>
        <span className="flex items-center gap-1.5">
          <span className="w-3 h-3 rounded-sm bg-red-900/60 border border-red-800/50 inline-block" />
          Booked
        </span>
      </div>

      {/* Confirm button */}
      {selected.length > 0 && (
        <button
          onClick={handleConfirm}
          className="btn-primary mt-4 w-full flex items-center justify-center gap-2"
        >
          <CheckCircle size={16} />
          Confirm {selected.length} seat{selected.length > 1 ? 's' : ''} — {selected.join(', ')}
        </button>
      )}
    </div>
  )
}
