"""
ticket/generate_ticket.py
--------------------------
Generates a PDF ticket using ReportLab.

Returns both:
  - The local file path  (for backward-compat / local download fallback)
  - The raw PDF bytes    (for S3 upload without a second disk read)
"""

import io
import os

from reportlab.lib.pagesizes import A6
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer


def generate_ticket(booking: dict, booking_id: str) -> tuple[str, bytes]:
    """
    Build a PDF ticket for the given booking.

    Parameters
    ----------
    booking    : Booking dict with keys movie_name, theatre_name,
                 date, time, seats.
    booking_id : MongoDB ObjectId as a string — used as the filename.

    Returns
    -------
    (file_path, pdf_bytes)
        file_path : str   — path to the saved PDF, e.g. "tickets/<id>.pdf"
        pdf_bytes : bytes — raw PDF content ready for S3 upload
    """
    # Save inside ticket/tickets/ relative to this file's directory
    # so the path is consistent regardless of where uvicorn is launched from.
    tickets_dir = os.path.join(os.path.dirname(__file__), "tickets")
    os.makedirs(tickets_dir, exist_ok=True)

    file_path = os.path.join(tickets_dir, f"{booking_id}.pdf")

    # Build the PDF into an in-memory buffer first so we can both
    # write it to disk AND hand the bytes to S3 without a second read.
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A6,
        leftMargin=12 * mm,
        rightMargin=12 * mm,
        topMargin=14 * mm,
        bottomMargin=14 * mm,
    )

    styles = getSampleStyleSheet()
    story  = []

    story.append(Paragraph("<b>🎬 CineBot Movie Ticket</b>", styles["Title"]))
    story.append(Spacer(1, 12))

    story.append(Paragraph(f"<b>Booking ID:</b> {booking_id}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Movie:</b> {booking['movie_name']}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Theatre:</b> {booking['theatre_name']}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Date:</b> {booking['date']}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(Paragraph(f"<b>Time:</b> {booking['time']}", styles["Normal"]))
    story.append(Spacer(1, 4))
    story.append(
        Paragraph(
            f"<b>Seats:</b> {', '.join(booking['seats'])}",
            styles["Normal"],
        )
    )

    story.append(Spacer(1, 20))
    story.append(Paragraph("<b>🍿 Enjoy your movie!</b>", styles["Heading2"]))

    doc.build(story)

    # Grab raw bytes from the buffer
    pdf_bytes = buffer.getvalue()

    # Also persist to disk (local fallback / debugging)
    with open(file_path, "wb") as f:
        f.write(pdf_bytes)

    return file_path, pdf_bytes
