from __future__ import annotations
from typing import List, Dict

RECOMMENDATION_SYSTEM = (
    "You are Smart Librarian, a helpful assistant that recommends books.\n"
    "Respond in English only.\n"
    "Use ONLY the provided context about the selected book.\n"
    "Do not invent titles or plot details. Keep the tone warm and concise.\n"
    "Avoid spoilers and do not include the full plot.\n"
    "If the user asked for specific themes, briefly explain how the book matches them.\n"
)


def extract_short_summary_from_doc(document: str) -> str:
    """
    Our ingest stores docs like:
        Title: The Hobbit
        Summary: Bilbo joins dwarves...
    This returns just the short summary part.
    """
    parts = document.split("Summary:", 1)
    return parts[1].strip() if len(parts) == 2 else document.strip()


def make_recommendation_messages(
    user_query: str, title: str, retrieved_document: str
) -> List[Dict[str, str]]:
    """
    Compose OpenAI chat messages for generating a conversational recommendation
    for the chosen `title`, using the short summary from the retrieved document.
    """
    short_summary = extract_short_summary_from_doc(retrieved_document)
    user_msg = (
        f"User interests: {user_query}\n\n"
        f"Selected book: {title}\n"
        f"Book context (short summary): {short_summary}\n\n"
        "Write a brief, friendly recommendation (2 sentences, 50 words maximum) that explains why this book "
        "fits the user's interests. Do not include spoilers or a full plot."
        "A detailed summary follows separately."
    )
    return [
        {"role": "system", "content": RECOMMENDATION_SYSTEM},
        {"role": "user", "content": user_msg},
    ]
