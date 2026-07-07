import re
from database.mongodb import seats


def _natural_seat_key(seat: dict) -> tuple:
    """
    Sort key for alphanumeric seat numbers so they read naturally:
      A1, A2, A3 … A10, B1, B2 … Z10
    rather than the default lexicographic order (A1, A10, A2 …).
    """
    number = seat["seat_number"]
    # Split into letter prefix and numeric suffix, e.g. "A10" → ("A", 10)
    match = re.match(r"([A-Za-z]+)(\d+)", number)
    if match:
        return (match.group(1).upper(), int(match.group(2)))
    # Fallback for non-standard formats
    return (number, 0)


def get_available_seats(show_id):

    available = list(
        seats.find(
            {
                "show_id": show_id,
                "status": "Available"
            },
            {
                "_id": 0,
                "seat_number": 1,
                "status": 1
            }
        )
    )

    booked = list(
        seats.find(
            {
                "show_id": show_id,
                "status": "Booked"
            },
            {
                "_id": 0,
                "seat_number": 1,
                "status": 1
            }
        )
    )

    all_seats = available + booked

    # Sort seats in natural ascending order: A1, A2 … A10, B1, B2 …
    all_seats.sort(key=_natural_seat_key)

    return all_seats

from database.mongodb import seats


def book_seats(show_id, seat_numbers):

    result = seats.update_many(
        {
            "show_id": show_id,
            "seat_number": {
                "$in": seat_numbers
            },
            "status": "Available"
        },
        {
            "$set": {
                "status": "Booked"
            }
        }
    )

    return result.modified_count

from database.mongodb import bookings


def create_booking(booking):

    result = bookings.insert_one(booking)

    return result.inserted_id


def update_booking_s3(booking_id, s3_object_key: str, s3_url: str | None = None):
    """
    Persist the S3 object key (and optional pre-signed URL) back into the
    booking document so the record is self-contained for future lookups.

    Parameters
    ----------
    booking_id   : bson.ObjectId returned by create_booking().
    s3_object_key: The S3 key, e.g. "tickets/<booking_id>.pdf".
    s3_url       : Pre-signed download URL (optional — URLs expire, so storing
                   the key is more durable; a fresh URL can always be generated).
    """
    update_fields = {"s3_object_key": s3_object_key}
    if s3_url:
        update_fields["s3_url"] = s3_url

    bookings.update_one(
        {"_id": booking_id},
        {"$set": update_fields},
    )