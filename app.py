import streamlit as st
from tools.cinema_tool import cinema_tool

# --------------------------------------------------
# Page Configuration
# --------------------------------------------------

st.set_page_config(
    page_title="🎬 CineBot",
    page_icon="🎬",
    layout="wide"
)

# --------------------------------------------------
# Title
# --------------------------------------------------

st.title("🎬 CineBot")
st.caption("Your AI-Powered Cinema Ticket Booking Assistant")

# --------------------------------------------------
# Chat History
# --------------------------------------------------

if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": (
                "👋 Hi! I'm CineBot. I can help you discover movies, "
                "get recommendations, and book cinema tickets. "
                "What would you like to watch today?"
            )
        }
    ]

# Display Previous Messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --------------------------------------------------
# Chat Input
# --------------------------------------------------

if prompt := st.chat_input("Ask me about movies or book tickets..."):

    # ----------------------------
    # User Message
    # ----------------------------

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    # ----------------------------
    # Get Response
    # ----------------------------

    result = cinema_tool(prompt)

    assistant_message = result["message"]

    # ----------------------------
    # Assistant Message
    # ----------------------------

    with st.chat_message("assistant"):

        st.markdown(assistant_message)

        # ----------------------------
        # Theatre Selection
        # ----------------------------

        if result["type"] == "theatre_selection":

            st.markdown("### 🎭 Available Theatres")

            if not result.get("data"):
                st.warning("No theatres found for this movie. Please check the movie name.")
            else:
                for theatre in result["data"]:
                    st.write(f"• {theatre}")

        # ----------------------------
        # Show Selection
        # ----------------------------

        elif result["type"] == "show_selection":

            st.markdown("### 🎥 Available Shows")

            if not result.get("data"):
                st.warning("No shows found.")
            else:
                for show in result["data"]:
                    st.write(
                        f"📅 {show.get('date')} | "
                        f"🕒 {show.get('time')} | "
                        f"💰 ₹{show.get('ticket_price')}"
                    )

        # ----------------------------
        # Seat Selection
        # ----------------------------

        elif result["type"] == "seat_selection":

            st.markdown("### 💺 Available Seats")

            seat_numbers = [seat["seat_number"] for seat in result["data"]]
            st.write(", ".join(seat_numbers))

        # ----------------------------
        # Awaiting Email
        # ----------------------------

        elif result["type"] == "awaiting_email":

            st.info("📧 Type your email address in the chat to complete your booking.")

        # ----------------------------
        # Booking Confirmed
        # ----------------------------

        elif result["type"] == "booking_confirmed":

            booking      = result["booking"]
            email        = result.get("email", "")
            email_status = result.get("email_status", "failed")

            st.markdown("### 🎟 Booking Summary")
            st.write(f"🎬 **Movie:** {booking['movie_name']}")
            st.write(f"🎭 **Theatre:** {booking['theatre_name']}")
            st.write(f"📅 **Date:** {booking['date']}")
            st.write(f"🕒 **Time:** {booking['time']}")
            st.write(f"💺 **Seats:** {', '.join(booking['seats'])}")

            # Email delivery status — shown only when relevant
            if email_status == "sent":
                st.info(f"📧 Confirmation email sent to **{email}**.")
            elif email_status == "unverified":
                st.warning(
                    f"📧 We couldn't send the confirmation to **{email}** — "
                    "this email isn't verified yet in our system. "
                    "Download your ticket below to keep a copy."
                )
            # "failed" = silent, booking still succeeded — ticket download covers it

            st.markdown("---")

            ticket_url  = result.get("ticket_url")
            ticket_path = result.get("ticket_path")

            if ticket_url:
                st.markdown(
                    f'<a href="{ticket_url}" target="_blank" '
                    f'style="display:inline-block;background:#e50914;color:#fff;'
                    f'padding:10px 22px;border-radius:6px;text-decoration:none;'
                    f'font-weight:bold;font-size:15px;">📄 Download Ticket (Cloud)</a>',
                    unsafe_allow_html=True,
                )
                st.caption("🔒 Secure link — expires in 1 hour.")

            elif ticket_path:
                try:
                    with open(ticket_path, "rb") as pdf:
                        st.download_button(
                            label="📄 Download Ticket",
                            data=pdf,
                            file_name="CineBot_Ticket.pdf",
                            mime="application/pdf",
                        )
                    st.caption("⚠️ Downloading from local storage (cloud upload unavailable).")
                except FileNotFoundError:
                    st.warning("Ticket file not found. Please contact support.")

    # ----------------------------
    # Save Assistant Message
    # ----------------------------

    st.session_state.messages.append({"role": "assistant", "content": assistant_message})
