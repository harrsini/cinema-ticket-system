import re
from datetime import date, timedelta

from database.mongodb import shows


# ---------------------------------------------------------------------------
# Date remapping
# ---------------------------------------------------------------------------
# Shows in the DB have hardcoded dates from when the data was seeded.
# We remap them so they always appear relative to today, keeping the same
# day-offset pattern (day 0 = today, day 1 = tomorrow, etc.).

def _remap_date(stored_date_str: str, anchor_date: date, today: date) -> str:
    """
    Shift a stored date by the same number of days that have passed
    since the anchor date, so shows always appear relative to today.

    Example:
      anchor  = 2026-06-27  (earliest date in DB)
      stored  = 2026-06-27  → offset 0 → today
      stored  = 2026-06-28  → offset 1 → tomorrow
    """
    try:
        stored = date.fromisoformat(stored_date_str)
        offset = (stored - anchor_date).days
        remapped = today + timedelta(days=offset)
        return remapped.strftime("%Y-%m-%d")
    except (ValueError, TypeError):
        return stored_date_str   # leave unchanged if format is unexpected


def get_theatres(movie_name):
    """
    Returns all theatres showing the given movie.
    """

    return shows.distinct(
        "theatre_name",
        {
            "movie_name": {
                "$regex": f"^{re.escape(movie_name)}$",
                "$options": "i"
            }
        }
    )


def resolve_theatre_name(user_input, available_theatres):
    """
    Resolves a user-typed theatre name to the canonical name stored in MongoDB.

    Matching is done in priority order:
      1. Exact match (case-insensitive)
      2. User input is a substring of the theatre name (case-insensitive)
      3. Any word in the user input matches any word in the theatre name

    Returns a dict with one of three shapes:
      {"status": "matched",   "theatre": "<canonical name>"}
      {"status": "ambiguous", "matches": ["...", "..."]}
      {"status": "not_found", "available": ["...", "..."]}
    """
    query = user_input.strip().lower()
    query_words = set(query.split())

    # --- pass 1: exact match ---
    for theatre in available_theatres:
        if theatre.strip().lower() == query:
            return {"status": "matched", "theatre": theatre}

    # --- pass 2: query is a substring of the theatre name ---
    substring_matches = [
        t for t in available_theatres
        if query in t.lower()
    ]
    if len(substring_matches) == 1:
        return {"status": "matched", "theatre": substring_matches[0]}
    if len(substring_matches) > 1:
        return {"status": "ambiguous", "matches": substring_matches}

    # --- pass 3: word-level overlap (e.g. "kg" → "KG Cinemas") ---
    word_matches = [
        t for t in available_theatres
        if query_words & set(t.lower().split())   # non-empty intersection
    ]
    if len(word_matches) == 1:
        return {"status": "matched", "theatre": word_matches[0]}
    if len(word_matches) > 1:
        return {"status": "ambiguous", "matches": word_matches}

    return {"status": "not_found", "available": available_theatres}


def get_show_timings(movie_name, theatre_name):
    """
    Returns all available shows for a movie in a theatre.
    Dates are remapped relative to today so they never appear in the past.
    """

    raw_shows = list(
        shows.find(
            {
                "movie_name": {
                    "$regex": f"^{re.escape(movie_name)}$",
                    "$options": "i"
                },
                "theatre_name": {
                    "$regex": f"^{re.escape(theatre_name)}$",
                    "$options": "i"
                }
            },
            {
                "_id": 1,
                "date": 1,
                "time": 1,
                "ticket_price": 1
            }
        )
    )

    if not raw_shows:
        return raw_shows

    # Find the earliest stored date to use as anchor
    stored_dates = [
        date.fromisoformat(s["date"])
        for s in raw_shows
        if s.get("date")
    ]
    if not stored_dates:
        return raw_shows

    anchor = min(stored_dates)
    today  = date.today()

    # Remap each show's date
    for show in raw_shows:
        if show.get("date"):
            show["date"] = _remap_date(show["date"], anchor, today)

    return raw_shows