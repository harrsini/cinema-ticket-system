"""
tools/booking_tool.py
---------------------
Implements the five-step cinema booking flow:

  Step 1  start_booking(movie)          → theatre selection
  Step 2  select_theatre(theatre_name)  → show selection
  Step 3  select_show(time)             → seat selection
  Step 4  confirm_booking(seat_numbers) → ask for email
  Step 5  finalize_booking(email)       → booking confirmed
                                           + PDF ticket
                                           + S3 upload
                                           + SES email

S3 and SES are fire-and-forget — failures are logged but never
cancel the booking.
"""

import logging

from chatbot.memory import update_memory, get_memory, reset_memory

from database.theatre_queries import (
    get_theatres,
    get_show_timings,
    resolve_theatre_name,
)
from database.booking_queries import (
    get_available_seats,
    book_seats,
    create_booking,
    update_booking_s3,
)

from ticket.generate_ticket import generate_ticket

from aws.s3_service  import upload_ticket_and_get_url
from aws.ses_service import send_booking_confirmation

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Step 1 — Start Booking
# ---------------------------------------------------------------------------

def start_booking(movie: str) -> dict:

    update_memory({"movie": movie})

    theatres = get_theatres(movie)

    print(f"[start_booking] movie='{movie}' → theatres={theatres}")

    return {
        "success": True,
        "type":    "theatre_selection",
        "message": f"🎬 Great choice! '{movie}' is playing at these theatres:",
        "data":    theatres,
    }


# ---------------------------------------------------------------------------
# Step 2 — Select Theatre
# ---------------------------------------------------------------------------

def select_theatre(theatre_name: str) -> dict:

    memory = get_memory()
    movie  = memory["movie"]

    theatres   = get_theatres(movie)
    resolution = resolve_theatre_name(theatre_name, theatres)

    if resolution["status"] == "ambiguous":
        options = "\n".join(f"  • {t}" for t in resolution["matches"])
        return {
            "success": False,
            "type":    "text",
            "message": (
                f"🤔 Multiple theatres match '{theatre_name}'. "
                f"Please be more specific:\n{options}"
            ),
        }

    if resolution["status"] == "not_found":
        options = "\n".join(f"  • {t}" for t in resolution["available"])
        return {
            "success": False,
            "type":    "text",
            "message": (
                f"❌ No theatre found matching '{theatre_name}'. "
                f"Available theatres:\n{options}"
            ),
        }

    matched_theatre = resolution["theatre"]
    update_memory({"theatre": matched_theatre})

    shows = get_show_timings(movie, matched_theatre)

    return {
        "success": True,
        "type":    "show_selection",
        "message": f"🎥 Available shows at {matched_theatre}:",
        "data":    shows,
    }


# ---------------------------------------------------------------------------
# Step 3 — Select Show
# ---------------------------------------------------------------------------

def select_show(time: str) -> dict:

    memory  = get_memory()
    movie   = memory["movie"]
    theatre = memory["theatre"]

    shows = get_show_timings(movie, theatre)

    selected_show = next((s for s in shows if s["time"] == time), None)

    if selected_show is None:
        return {
            "success": False,
            "type":    "text",
            "message": "❌ Show not found.",
        }

    update_memory({
        "show_id": selected_show["_id"],
        "date":    selected_show["date"],
        "time":    selected_show["time"],
    })

    available_seats = get_available_seats(selected_show["_id"])

    return {
        "success": True,
        "type":    "seat_selection",
        "message": "💺 These seats are currently available:",
        "data":    available_seats,
    }


# ---------------------------------------------------------------------------
# Step 4 — Seat selection confirmed → ask for email
# ---------------------------------------------------------------------------

def confirm_booking(seat_numbers: list[str]) -> dict:
    """
    Hold the chosen seats in memory and ask the customer for their email
    so we can send the confirmation via SES.
    """
    # Persist seats as pending — actual booking happens in finalize_booking
    update_memory({"pending_seats": seat_numbers})

    return {
        "success": True,
        "type":    "awaiting_email",
        "message": (
            "✅ Great seats! Please share your **email address** and we'll "
            "send your booking confirmation and ticket there. 📧\n\n"
            "_(Just type your email to continue)_"
        ),
    }


# ---------------------------------------------------------------------------
# Step 5 — Email received → finalize booking
# ---------------------------------------------------------------------------

def finalize_booking(email: str) -> dict:
    """
    Called once the customer provides their email address.
    Marks seats, creates the booking, generates PDF, uploads to S3, sends email.
    """
    memory       = get_memory()
    seat_numbers = memory.get("pending_seats")

    if not seat_numbers:
        return {
            "success": False,
            "type":    "text",
            "message": "❌ No seats selected. Please start the booking again.",
        }

    # --- 5a. Mark seats as booked -------------------------------------------
    updated = book_seats(memory["show_id"], seat_numbers)

    if updated != len(seat_numbers):
        return {
            "success": False,
            "type":    "text",
            "message": "❌ One or more selected seats are already booked.",
        }

    # --- 5b. Persist booking to MongoDB -------------------------------------
    booking = {
        "movie_name":   memory["movie"],
        "theatre_name": memory["theatre"],
        "date":         memory["date"],
        "time":         memory["time"],
        "seats":        seat_numbers,
        "seat_count":   len(seat_numbers),
        "email":        email,
    }

    booking_id     = create_booking(booking)
    booking_id_str = str(booking_id)

    # --- 5c. Generate PDF ticket --------------------------------------------
    ticket_path, pdf_bytes = generate_ticket(booking, booking_id_str)

    # --- 5d. Upload ticket to S3 (non-fatal) --------------------------------
    ticket_url    = None
    s3_object_key = None
    aws_notes: list[str] = []

    s3_result = upload_ticket_and_get_url(pdf_bytes, booking_id_str)

    if s3_result["success"]:
        s3_object_key = s3_result["object_key"]
        ticket_url    = s3_result["url"]
        update_booking_s3(booking_id, s3_object_key, ticket_url)
        logger.info("Ticket uploaded to S3: %s", s3_object_key)
    else:
        logger.warning("S3 upload failed: %s", s3_result["message"])
        print(f"[CineBot] S3 upload failed: {s3_result['message']}")
        aws_notes.append("⚠️ Cloud upload failed — use the local download below.")

    # --- 5e. Send confirmation email via SES (non-fatal) --------------------
    ses_result = send_booking_confirmation(
        recipient_email=email,
        booking=booking,
        booking_id=booking_id_str,
        ticket_url=ticket_url,
    )

    # email_status: "sent" | "unverified" | "failed"
    if ses_result["success"]:
        email_status = "sent"
        logger.info("Confirmation email sent to %s", email)
    elif ses_result.get("error_code") == "MessageRejected":
        # Sandbox restriction — recipient not verified in SES
        email_status = "unverified"
        logger.warning("SES sandbox: recipient %s is not verified", email)
    else:
        email_status = "failed"
        logger.warning("SES email failed: %s", ses_result["message"])
        print(f"[CineBot] SES failed: {ses_result['message']}")

    # --- 5f. Clear session memory and return --------------------------------
    reset_memory()

    confirmation_message = (
        f"🎉 Booking Confirmed!\n\n"
        f"Booking ID: `{booking_id_str}`"
    )

    if aws_notes:
        confirmation_message += "\n\n" + "\n".join(aws_notes)

    return {
        "success":      True,
        "type":         "booking_confirmed",
        "message":      confirmation_message,
        "booking":      booking,
        "booking_id":   booking_id_str,
        "ticket_path":  ticket_path,
        "ticket_url":   ticket_url,
        "email":        email,
        "email_status": email_status,   # "sent" | "unverified" | "failed"
    }
