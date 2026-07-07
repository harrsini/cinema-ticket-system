import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)

MODEL = "qwen/qwen3-32b"
import json
import re

def get_response(messages):

    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0
    )

    content = response.choices[0].message.content

    # Remove reasoning
    content = re.sub(
        r"<think>.*?</think>",
        "",
        content,
        flags=re.DOTALL
    ).strip()

    # Extract JSON
    match = re.search(r"\{.*\}", content, re.DOTALL)

    if not match:
        return {"intent": "general_chat"}

    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"intent": "general_chat"}