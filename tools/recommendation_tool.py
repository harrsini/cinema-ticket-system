"""
tools/recommendation_tool.py
-----------------------------
AI-powered movie recommendation engine for CineBot.

Architecture
------------
                         User message
                              │
                    ┌─────────▼──────────┐
                    │  LLM Intent Parser  │  (Groq / Qwen)
                    │  _parse_rec_intent  │  → structured query dict
                    └─────────┬──────────┘
                              │
               ┌──────────────▼───────────────┐
               │    TMDB Data Fetcher          │
               │  _fetch_recommendations()     │
               │                               │
               │  Strategies (in priority):    │
               │  1. by_person  (actor/dir)    │
               │  2. similar_to (seed movie)   │
               │  3. by_genre                  │
               │  4. trending                  │
               │  5. top_rated                 │
               └──────────────┬───────────────┘
                              │  raw TMDB results (list of dicts)
                    ┌─────────▼──────────┐
                    │  LLM Presenter      │  (Groq / Qwen)
                    │  _present_results   │  → natural language reply
                    └─────────┬──────────┘
                              │
                         Response dict

Design principles
-----------------
* The LLM NEVER invents movie data.  It only:
    (a) parses the user's intent into a structured query
    (b) formats real TMDB data into a natural reply
* All movie facts (title, rating, overview, genres) come from TMDB.
* Extensibility hook: get_recommendations() accepts an optional
  `user_history` list of booking dicts so personalisation can be
  layered on top later without changing the function signature.
"""

import logging
import os
from typing import Optional

import requests
from dotenv import load_dotenv

from chatbot.llm import get_response

load_dotenv()

logger = logging.getLogger(__name__)

TMDB_API_KEY = os.getenv("TMDB_API_KEY")
TMDB_BASE    = "https://api.themoviedb.org/3"

# Maximum number of movies to surface per recommendation
MAX_RESULTS = 8


# ---------------------------------------------------------------------------
# TMDB helpers
# ---------------------------------------------------------------------------

def _tmdb_get(endpoint: str, params: dict) -> dict:
    """Thin wrapper around requests.get for TMDB — returns {} on failure."""
    params["api_key"] = TMDB_API_KEY
    try:
        resp = requests.get(f"{TMDB_BASE}{endpoint}", params=params, timeout=10)
        resp.raise_for_status()
        return resp.json()
    except requests.RequestException as exc:
        logger.error("TMDB request failed (%s): %s", endpoint, exc)
        return {}


def _genre_name_to_id(genre_name: str) -> Optional[int]:
    """Resolve a genre name to its TMDB genre ID (case-insensitive)."""
    data = _tmdb_get("/genre/movie/list", {"language": "en-US"})
    for g in data.get("genres", []):
        if g["name"].lower() == genre_name.lower():
            return g["id"]
    # Partial match fallback
    for g in data.get("genres", []):
        if genre_name.lower() in g["name"].lower():
            return g["id"]
    return None


def _search_person_id(name: str) -> Optional[int]:
    """Return the TMDB person ID for an actor or director."""
    data = _tmdb_get("/search/person", {"query": name})
    results = data.get("results", [])
    return results[0]["id"] if results else None


def _search_movie_id(title: str) -> Optional[int]:
    """Return the TMDB movie ID for a given title."""
    data = _tmdb_get("/search/movie", {"query": title})
    results = data.get("results", [])
    return results[0]["id"] if results else None


def _format_movie(movie: dict) -> dict:
    """Extract the fields we care about from a raw TMDB movie record."""
    return {
        "title":        movie.get("title", "Unknown"),
        "overview":     movie.get("overview", ""),
        "rating":       round(movie.get("vote_average", 0), 1),
        "release_date": movie.get("release_date", "")[:4] or "N/A",
        "popularity":   round(movie.get("popularity", 0), 1),
    }


# ---------------------------------------------------------------------------
# TMDB recommendation strategies
# ---------------------------------------------------------------------------

def _fetch_by_genre(genre_name: str) -> list[dict]:
    genre_id = _genre_name_to_id(genre_name)
    if not genre_id:
        logger.warning("Unknown genre: %s", genre_name)
        return []
    data = _tmdb_get(
        "/discover/movie",
        {"with_genres": genre_id, "sort_by": "vote_average.desc",
         "vote_count.gte": 200, "language": "en-US"},
    )
    return [_format_movie(m) for m in data.get("results", [])[:MAX_RESULTS]]


def _fetch_similar_to(movie_title: str) -> list[dict]:
    movie_id = _search_movie_id(movie_title)
    if not movie_id:
        return []
    data = _tmdb_get(f"/movie/{movie_id}/similar", {"language": "en-US"})
    return [_format_movie(m) for m in data.get("results", [])[:MAX_RESULTS]]


def _fetch_by_person(person_name: str) -> list[dict]:
    """Return movies featuring or directed by the named person."""
    person_id = _search_person_id(person_name)
    if not person_id:
        return []
    data = _tmdb_get(
        f"/person/{person_id}/movie_credits",
        {"language": "en-US"},
    )
    # Combine cast and crew credits, de-duplicate
    combined = {
        m["id"]: m
        for m in data.get("cast", []) + data.get("crew", [])
        if m.get("vote_average", 0) >= 5 and m.get("vote_count", 0) >= 50
    }
    # Sort by vote_average descending
    ranked = sorted(combined.values(), key=lambda m: m.get("vote_average", 0), reverse=True)
    return [_format_movie(m) for m in ranked[:MAX_RESULTS]]


def _fetch_trending() -> list[dict]:
    data = _tmdb_get("/trending/movie/week", {"language": "en-US"})
    return [_format_movie(m) for m in data.get("results", [])[:MAX_RESULTS]]


def _fetch_top_rated(genre_name: str | None = None) -> list[dict]:
    params: dict = {
        "sort_by": "vote_average.desc",
        "vote_count.gte": 500,
        "language": "en-US",
    }
    if genre_name:
        genre_id = _genre_name_to_id(genre_name)
        if genre_id:
            params["with_genres"] = genre_id
    data = _tmdb_get("/discover/movie", params)
    return [_format_movie(m) for m in data.get("results", [])[:MAX_RESULTS]]


# ---------------------------------------------------------------------------
# LLM intent parsing
# ---------------------------------------------------------------------------

_INTENT_PROMPT = """
You are the intent-parsing brain of CineBot's recommendation engine.

Analyze the user's message and return ONLY a JSON object with these fields:

  strategy  : one of "by_genre" | "by_person" | "similar_to" | "trending" | "top_rated"
  genre     : genre name if mentioned (Action, Comedy, Horror, Romance, Sci-Fi, Thriller, Drama, etc.)
  person    : actor or director name if mentioned
  movie     : seed movie title for "similar_to"
  mood      : a single genre keyword inferred from vague mood words
               (e.g. "bored" → "Comedy", "excited" → "Action", "romantic" → "Romance")

Rules:
1. Return ONLY the JSON object — no markdown, no explanation.
2. Omit fields that are not applicable.
3. If the user mentions a person (actor / director), use strategy "by_person".
4. If the user says "like <movie>" or "similar to <movie>", use "similar_to".
5. If the user mentions a genre explicitly, use "by_genre".
6. If the user mentions "top-rated" or "best", use "top_rated".
7. If the request is vague or mood-based, infer a genre and use "by_genre".
8. Fallback: use "trending".

Examples:

User: Recommend action movies
{"strategy":"by_genre","genre":"Action"}

User: Suggest movies like Interstellar
{"strategy":"similar_to","movie":"Interstellar"}

User: Recommend Rajinikanth movies
{"strategy":"by_person","person":"Rajinikanth"}

User: What are the top-rated sci-fi movies?
{"strategy":"top_rated","genre":"Sci-Fi"}

User: I'm bored. Suggest something exciting.
{"strategy":"by_genre","genre":"Action","mood":"Action"}

User: Something fun
{"strategy":"by_genre","genre":"Comedy","mood":"Comedy"}

User: Trending movies
{"strategy":"trending"}
"""


def _parse_rec_intent(user_input: str) -> dict:
    """Use the LLM to parse the recommendation intent from free-form user text."""
    messages = [
        {"role": "system", "content": _INTENT_PROMPT},
        {"role": "user",   "content": user_input},
    ]
    result = get_response(messages)
    logger.debug("Recommendation intent: %s", result)
    return result


# ---------------------------------------------------------------------------
# LLM response presenter
# ---------------------------------------------------------------------------

_PRESENTER_PROMPT = """
You are CineBot's friendly movie presenter.

You have been given a list of real movies from TMDB.
Your job is to present them naturally and engagingly in response to the user's request.

Rules:
1. Do NOT invent any movie details. Only use the data provided.
2. Present each movie as a short bullet with: title, year, rating, and one-line overview.
3. Use a warm, conversational tone.
4. Keep your total response under 400 words.
5. Do not include any JSON in your reply.
6. End with a short friendly sign-off encouraging the user to book.
"""


def _present_results(user_input: str, movies: list[dict]) -> str:
    """Use the LLM to format TMDB data into a natural reply."""
    if not movies:
        return (
            "🎬 I couldn't find matching movies right now. "
            "Try a different genre or tell me a movie you enjoy!"
        )

    movie_list = "\n".join(
        f"- {m['title']} ({m['release_date']}) | ⭐ {m['rating']} | {m['overview'][:120]}…"
        for m in movies
    )

    messages = [
        {"role": "system", "content": _PRESENTER_PROMPT},
        {
            "role": "user",
            "content": (
                f"User request: {user_input}\n\n"
                f"Movies from TMDB:\n{movie_list}"
            ),
        },
    ]

    try:
        # _present_results expects a plain string back from the LLM, not JSON.
        # We call the Groq client directly to get the raw string.
        from groq import Groq
        client  = Groq(api_key=os.getenv("GROQ_API_KEY"))
        import re
        resp    = client.chat.completions.create(
            model="qwen/qwen3-32b",
            messages=messages,
            temperature=0.7,
        )
        content = resp.choices[0].message.content
        # Strip any <think> blocks the model may emit
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()
        return content
    except Exception as exc:           # noqa: BLE001
        logger.error("LLM presenter failed: %s", exc)
        # Graceful fallback: plain-text list
        lines = [f"🎬 Here are some movies you might enjoy:\n"]
        for m in movies:
            lines.append(
                f"• **{m['title']}** ({m['release_date']}) — "
                f"⭐ {m['rating']}\n  {m['overview'][:100]}…"
            )
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Personalisation hook (future)
# ---------------------------------------------------------------------------

def _enrich_with_history(query: dict, user_history: list[dict]) -> dict:
    """
    Enrich a parsed recommendation query with signals from the user's
    booking history.

    This function is intentionally minimal today — it is the designed
    extension point for personalised recommendations.

    Future workflow
    ---------------
    User Booking History
         ↓
    Extract preferred genres  (from TMDB metadata of booked movies)
         ↓
    Blend with current query  (boost matching genres, filter out
                               already-seen movies)
         ↓
    Return enriched query dict

    Parameters
    ----------
    query        : Parsed intent dict from _parse_rec_intent().
    user_history : List of booking documents from MongoDB
                   (each has at minimum: movie_name).

    Returns
    -------
    Enriched query dict (today: returned unchanged as a passthrough).
    """
    if not user_history:
        return query

    # --- placeholder: extract movie names from history --------------------
    # booked_titles = [b.get("movie_name") for b in user_history if b.get("movie_name")]
    # TODO: fetch TMDB genre data for each booked title, tally preferred
    #       genres, and inject them as a bias into `query`.
    # ----------------------------------------------------------------------

    logger.debug(
        "Personalisation hook called with %d history items (not yet active).",
        len(user_history),
    )
    return query   # passthrough until personalisation is implemented


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def get_recommendations(
    user_input: str,
    user_history: list[dict] | None = None,
) -> dict:
    """
    Return AI-powered movie recommendations for the given user message.

    Parameters
    ----------
    user_input   : Raw user message, e.g. "Recommend action movies".
    user_history : Optional list of past booking dicts from MongoDB.
                   Used by the personalisation hook (future feature).

    Returns
    -------
    dict with keys:
        success  bool
        type     "text"
        message  str   — formatted recommendation text
    """
    try:
        # 1. Parse intent
        query = _parse_rec_intent(user_input)

        # 2. Personalisation hook (passthrough today, extensible later)
        if user_history:
            query = _enrich_with_history(query, user_history)

        strategy = query.get("strategy", "trending")
        logger.info("Recommendation strategy: %s | query: %s", strategy, query)

        # 3. Fetch real data from TMDB
        movies: list[dict] = []

        if strategy == "by_person" and query.get("person"):
            movies = _fetch_by_person(query["person"])

        elif strategy == "similar_to" and query.get("movie"):
            movies = _fetch_similar_to(query["movie"])

        elif strategy == "by_genre" and query.get("genre"):
            movies = _fetch_by_genre(query.get("mood") or query["genre"])

        elif strategy == "top_rated":
            movies = _fetch_top_rated(query.get("genre"))

        else:
            # "trending" or any fallback
            movies = _fetch_trending()

        # 4. LLM formats the real data into a natural reply
        reply = _present_results(user_input, movies)

        return {
            "success": True,
            "type":    "text",
            "message": reply,
        }

    except Exception as exc:           # noqa: BLE001
        logger.error("Recommendation engine error: %s", exc)
        return {
            "success": False,
            "type":    "text",
            "message": (
                "🎬 Sorry, I couldn't fetch recommendations right now. "
                "Please try again in a moment!"
            ),
        }
