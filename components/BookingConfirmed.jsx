import { CheckCircle, Download, ExternalLink, Mail, Ticket } from 'lucide-react'

export default function BookingConfirmed({ result }) {
  const { booking, booking_id, ticket_path, ticket_url, email, email_status } = result

  // Derive filename from ticket_path (backend returns full local path)
  const filename = ticket_path
    ? ticket_path.replace(/\\/g, '/').split('/').pop()
    : null

  const emailNote = {
    sent:        { color: 'text-green-400',  text: `Confirmation sent to ${email}` },
    unverified:  { color: 'text-yellow-400', text: `Email not verified in SES sandbox — download ticket below` },
    failed:      { color: 'text-red-400',    text: `Email delivery failed — download ticket below` },
  }[email_status] ?? { color: 'text-cinema-muted', text: '' }

  return (
    <div className="mt-2 animate-slide-up card border-green-500/30 bg-green-500/5">

      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <CheckCircle size={20} className="text-green-400" />
        <span className="font-semibold text-green-400">Booking Confirmed!</span>
      </div>

      {/* Booking details */}
      <div className="space-y-2 text-sm mb-4">
        <div className="flex justify-between">
          <span className="text-cinema-muted">Booking ID</span>
          <span className="font-mono text-xs text-cinema-accent">{booking_id}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-cinema-muted">Movie</span>
          <span className="font-medium">{booking.movie_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-cinema-muted">Theatre</span>
          <span>{booking.theatre_name}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-cinema-muted">Date & Time</span>
          <span>{booking.date} · {booking.time}</span>
        </div>
        <div className="flex justify-between">
          <span className="text-cinema-muted">Seats</span>
          <span className="font-mono">{booking.seats.join(', ')}</span>
        </div>
      </div>

      <div className="border-t border-cinema-border pt-3 space-y-2">

        {/* Email status */}
        {email_status && (
          <div className={`flex items-center gap-2 text-xs ${emailNote.color}`}>
            <Mail size={13} />
            {emailNote.text}
          </div>
        )}

        {/* Download buttons */}
        <div className="flex gap-2 flex-wrap">
          {filename && (
            <a
              href={`/api/ticket/${filename}`}
              download={filename}
              className="btn-primary flex items-center gap-2 text-sm"
            >
              <Download size={14} />
              Download Ticket
            </a>
          )}

          {ticket_url && (
            <a
              href={ticket_url}
              target="_blank"
              rel="noreferrer"
              className="btn-ghost flex items-center gap-2 text-sm"
            >
              <ExternalLink size={14} />
              Open from Cloud
            </a>
          )}
        </div>

      </div>
    </div>
  )
}
