# -----------------------------------------
# Conversation Memory
# -----------------------------------------

conversation_state = {
    "movie":    None,
    "theatre":  None,
    "show_id":  None,
    "date":     None,
    "time":     None,
    "seat_count": None,
    "seats":    [],
    "email":    None,       # collected before sending SES confirmation
    # Pending seats — held here while we wait for the customer's email
    "pending_seats": None,
}


def update_memory(data):
    """Update conversation memory with new values."""
    for key, value in data.items():
        if key in conversation_state and value is not None:
            conversation_state[key] = value


def get_memory():
    """Return the current conversation state."""
    return conversation_state


def reset_memory():
    """Reset conversation after booking or cancellation."""
    conversation_state.update({
        "movie":         None,
        "theatre":       None,
        "show_id":       None,
        "date":          None,
        "time":          None,
        "seat_count":    None,
        "seats":         [],
        "email":         None,
        "pending_seats": None,
    })
