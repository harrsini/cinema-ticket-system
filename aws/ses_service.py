"""
aws/ses_service.py
------------------
Sends booking-confirmation emails via Amazon SES.

The email contains:
  - Booking ID, movie, theatre, date, time, seats
  - A pre-signed S3 link to download the PDF ticket

Design contract
---------------
* The caller (booking_tool.py) catches all exceptions; this module
  logs them and returns a structured result dict instead of raising.
* A failed email NEVER cancels a booking.
* All credentials and the sender address come from environment variables.
"""

import logging
import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Internal helpers — credentials read at call-time, not at import
# ---------------------------------------------------------------------------

def _get_ses_client():
    """Return a configured boto3 SES client, reading credentials fresh from env."""
    sender = os.getenv("SES_SENDER_EMAIL")
    if not sender:
        raise RuntimeError(
            "SES_SENDER_EMAIL is not set. "
            "Add a verified sender address to your .env file."
        )
    client = boto3.client(
        "ses",
        region_name=os.getenv("AWS_REGION", "us-east-1"),
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    )
    return client, sender


def _build_email_body(booking: dict, booking_id: str, ticket_url: str | None) -> tuple[str, str]:
    """
    Build plain-text and HTML versions of the confirmation email.

    Returns
    -------
    (plain_text, html_text)
    """
    movie   = booking.get("movie_name", "N/A")
    theatre = booking.get("theatre_name", "N/A")
    date    = booking.get("date", "N/A")
    time    = booking.get("time", "N/A")
    seats   = ", ".join(booking.get("seats", []))

    download_section_plain = (
        f"Download your ticket: {ticket_url}"
        if ticket_url
        else "Your ticket will be available shortly."
    )

    download_section_html = (
        f'<p><a href="{ticket_url}" '
        f'style="background:#e50914;color:#fff;padding:10px 20px;'
        f'border-radius:4px;text-decoration:none;font-weight:bold;">'
        f'📄 Download Your Ticket</a></p>'
        if ticket_url
        else "<p>Your ticket will be available shortly.</p>"
    )

    plain = f"""
🎬 CineBot — Booking Confirmation

Hi there,

Your booking is confirmed! Here are the details:

  Booking ID : {booking_id}
  Movie      : {movie}
  Theatre    : {theatre}
  Date       : {date}
  Time       : {time}
  Seats      : {seats}

{download_section_plain}

🍿 Enjoy your movie!
— The CineBot Team
""".strip()

    html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <style>
    body      {{ font-family: Arial, sans-serif; background: #f4f4f4; margin: 0; padding: 20px; }}
    .card     {{ background: #ffffff; max-width: 560px; margin: auto; border-radius: 8px;
                 box-shadow: 0 2px 8px rgba(0,0,0,0.12); overflow: hidden; }}
    .header   {{ background: #141414; color: #e50914; text-align: center; padding: 24px; font-size: 22px; }}
    .body     {{ padding: 28px 32px; color: #333; }}
    .label    {{ font-weight: bold; color: #555; width: 110px; display: inline-block; }}
    .row      {{ margin: 8px 0; font-size: 15px; }}
    .footer   {{ background: #f4f4f4; text-align: center; padding: 16px; font-size: 12px; color: #888; }}
  </style>
</head>
<body>
  <div class="card">
    <div class="header">🎬 CineBot — Booking Confirmed!</div>
    <div class="body">
      <p>Hi there, your booking is confirmed. Here are the details:</p>

      <div class="row"><span class="label">Booking ID</span> {booking_id}</div>
      <div class="row"><span class="label">Movie</span> {movie}</div>
      <div class="row"><span class="label">Theatre</span> {theatre}</div>
      <div class="row"><span class="label">Date</span> {date}</div>
      <div class="row"><span class="label">Time</span> {time}</div>
      <div class="row"><span class="label">Seats</span> {seats}</div>

      <br />
      {download_section_html}
    </div>
    <div class="footer">🍿 Enjoy your movie! — The CineBot Team</div>
  </div>
</body>
</html>
""".strip()

    return plain, html


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def send_booking_confirmation(
    recipient_email: str,
    booking: dict,
    booking_id: str,
    ticket_url: str | None = None,
) -> dict:
    """
    Send a booking confirmation email via Amazon SES.

    Parameters
    ----------
    recipient_email : Customer's email address.
    booking         : Booking dict (movie_name, theatre_name, date, time, seats).
    booking_id      : MongoDB ObjectId as string.
    ticket_url      : Pre-signed S3 URL for ticket download (optional).

    Returns
    -------
    dict with keys:
        success    bool
        message_id str | None  — SES message ID on success
        message    str         — human-readable status
    """
    try:
        client, sender = _get_ses_client()

        plain, html = _build_email_body(booking, booking_id, ticket_url)

        movie = booking.get("movie_name", "Your Movie")
        subject = f"🎬 Booking Confirmed — {movie} | CineBot"

        response = client.send_email(
            Source=sender,
            Destination={"ToAddresses": [recipient_email]},
            Message={
                "Subject": {"Data": subject, "Charset": "UTF-8"},
                "Body": {
                    "Text": {"Data": plain, "Charset": "UTF-8"},
                    "Html": {"Data": html,  "Charset": "UTF-8"},
                },
            },
        )

        message_id = response["MessageId"]
        logger.info(
            "Confirmation email sent to %s (MessageId: %s)", recipient_email, message_id
        )
        print(f"[CineBot SES] Email sent to {recipient_email} — MessageId: {message_id}")

        return {
            "success":    True,
            "message_id": message_id,
            "message":    f"Confirmation email sent to {recipient_email}.",
        }

    except (BotoCoreError, ClientError) as exc:
        logger.error(
            "SES email failed for booking %s to %s: %s",
            booking_id, recipient_email, exc,
        )
        print(f"[CineBot SES] Send failed to {recipient_email}: {exc}")

        # Surface the AWS error code so callers can handle specific cases
        # (e.g. MessageRejected = unverified recipient in sandbox mode)
        error_code = None
        if hasattr(exc, "response"):
            error_code = exc.response.get("Error", {}).get("Code")

        return {
            "success":    False,
            "message_id": None,
            "error_code": error_code,
            "message":    f"Email delivery failed: {exc}",
        }
    except RuntimeError as exc:
        logger.error("SES configuration error: %s", exc)
        print(f"[CineBot SES] Config error: {exc}")
        return {
            "success":    False,
            "message_id": None,
            "error_code": None,
            "message":    str(exc),
        }
