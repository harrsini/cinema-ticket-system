from chatbot.planner import plan

from tools.booking_tool import (
    start_booking,
    select_theatre,
    select_show,
    confirm_booking,
    finalize_booking,
)

from tools.movie_tool import get_complete_movie_details
from tools.recommendation_tool import get_recommendations


def cinema_tool(user_input):

    decision = plan(user_input)

    print("\nPlanner Output:", decision)

    intent = decision.get("intent")

    # ==================================================
    # BOOKING FLOW
    # ==================================================

    if intent == "book_seats":

        movie = decision.get("movie")

        if not movie:
            return {
                "success": False,
                "type": "text",
                "message": "🎬 Which movie would you like to book?"
            }

        return start_booking(movie)

    elif intent == "select_theatre":

        theatre = decision.get("theatre")

        if not theatre:
            return {
                "success": False,
                "type": "text",
                "message": "Please select a theatre."
            }

        return select_theatre(theatre)

    elif intent == "select_show":

        show_time = decision.get("time")

        if not show_time:
            return {
                "success": False,
                "type": "text",
                "message": "Please select a show timing."
            }

        return select_show(show_time)
    
    elif intent == "confirm_booking":

        seats = decision.get("seats")

        if not seats:

            return {
                "success": False,
                "type":    "text",
                "message": "Please choose your seats.",
            }

        return confirm_booking(seats)

    # ==================================================
    # EMAIL COLLECTION → FINALIZE BOOKING
    # ==================================================

    elif intent == "provide_email":

        email = decision.get("email")

        if not email:
            return {
                "success": False,
                "type":    "text",
                "message": "I couldn't read that email address. Please try again.",
            }

        from chatbot.memory import get_memory
        memory = get_memory()

        # If there are pending seats, this email finalizes the booking
        if memory.get("pending_seats"):
            return finalize_booking(email)

        # Otherwise just acknowledge (edge case)
        return {
            "success": True,
            "type":    "text",
            "message": f"Got it — I've noted your email as **{email}**.",
        }

    # ==================================================
    # MOVIE DETAILS
    # ==================================================

    elif intent == "movie_details":

        movie = decision.get("movie")

        details = get_complete_movie_details(movie)

        if details is None:
            return {
                "success": False,
                "type": "text",
                "message": "Sorry, I couldn't find that movie."
            }

        return {
            "success": True,
            "type": "text",
            "message":
                f"🎬 **{details['title']}**\n\n"
                f"📝 {details['overview']}\n\n"
                f"🎭 Genre: {', '.join(details['genres'])}\n"
                f"🎬 Director: {details['director']}\n"
                f"⏱ Runtime: {details['runtime']} mins\n"
                f"⭐ Rating: {details['rating']}/10"
        }

    # ==================================================
    # MOVIE CAST
    # ==================================================

    elif intent == "movie_cast":

        movie = decision.get("movie")

        details = get_complete_movie_details(movie)

        if details is None:
            return {
                "success": False,
                "type": "text",
                "message": "Sorry, I couldn't find that movie."
            }

        cast = "\n".join(details["cast"])

        return {
            "success": True,
            "type": "text",
            "message":
                f"🎭 **Main Cast of {details['title']}**\n\n{cast}"
        }

    # ==================================================
    # MOVIE REVIEW
    # ==================================================

    elif intent == "movie_review":

        movie = decision.get("movie")

        details = get_complete_movie_details(movie)

        if details is None:
            return {
                "success": False,
                "type": "text",
                "message": "Sorry, I couldn't find that movie."
            }

        return {
            "success": True,
            "type": "text",
            "message":
                f"⭐ **{details['title']}**\n\n"
                f"TMDb Rating: **{details['rating']}/10**\n\n"
                f"{details['overview']}"
        }

    # ==================================================
    # MOVIE RECOMMENDATIONS
    # ==================================================

    elif intent == "recommend_movies":

        return get_recommendations(user_input)

    # ==================================================
    # GENERAL CHAT
    # ==================================================

    elif intent == "general_chat":

        return {
            "success": True,
            "type": "text",
            "message": "😊 Hi! I can help you with movie details and cinema ticket bookings."
        }

    # ==================================================
    # UNKNOWN INTENT
    # ==================================================

    # ==================================================
    # UNKNOWN INTENT — give a helpful nudge instead of a dead end
    # ==================================================

    print(f"[cinema_tool] Unhandled intent: {intent!r} | decision: {decision}")

    return {
        "success": False,
        "type": "text",
        "message": (
            "🤔 I didn't quite catch that. Here's what I can help with:\n\n"
            "- 🎬 **Book tickets** — \"Book tickets for Coolie\"\n"
            "- 🎭 **Movie details** — \"Tell me about Interstellar\"\n"
            "- 🌟 **Recommendations** — \"Suggest action movies\"\n"
            "- 👥 **Cast info** — \"Who acted in Vikram?\""
        )
    }