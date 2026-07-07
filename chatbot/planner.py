from chatbot.prompts import SYSTEM_PROMPT
from chatbot.llm import get_response


def plan(user_input):

    messages = [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        },
        {
            "role": "user",
            "content": user_input
        }
    ]

    return get_response(messages)