"""
Asks an LLM to explain the prescription in plain English, grounded in
whatever we pulled from the drug knowledge base and the interaction
graph. Always writes in English - sarvam_translator.py handles turning
it into the patient's language afterward.

Backend is picked by config.CHAT_PROVIDER ("claude" or "gemini") - this
step is text-only, no vision needed, so Gemini's free tier is a
straightforward option here too. Same privacy note as OCR_PROVIDER
applies - see README.
"""
from langchain_anthropic import ChatAnthropic
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate

import config

SYSTEM_PROMPT = """You are PresciMate, explaining a prescription to an
Indian patient in simple, plain English (a translation step happens
afterward, so always write in English here).

- Write at a level a non-medical family member would understand.
- Only use facts from the context given to you - don't invent anything.
- Mention what each medicine is for, how to take it, and anything to
  watch out for.
- If interaction warnings are given, explain them calmly and tell the
  patient to check with their doctor or pharmacist.
- Never suggest changing a dose or stopping a medicine on your own.
- End with a short reminder to follow the doctor's instructions."""

_prompt = ChatPromptTemplate.from_messages([("system", SYSTEM_PROMPT), ("human", "{user_prompt}")])


def _llm():
    if config.CHAT_PROVIDER == "gemini":
        if not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not set - check your .env file.")
        return ChatGoogleGenerativeAI(
            model=config.GEMINI_MODEL, google_api_key=config.GEMINI_API_KEY, max_output_tokens=1200
        )

    if not config.ANTHROPIC_API_KEY:
        raise RuntimeError("ANTHROPIC_API_KEY is not set - check your .env file.")
    return ChatAnthropic(model=config.CHAT_MODEL, max_tokens=1200, api_key=config.ANTHROPIC_API_KEY)


def _chain():
    return _prompt | _llm() | StrOutputParser()


def write_explanation(medicines: list[dict], drug_context: str, interactions: list[dict]) -> str:
    medicine_list = "\n".join(
        f"- {m['name']} ({m.get('dosage') or 'dose not specified'}, "
        f"{m.get('frequency') or 'frequency not specified'})"
        for m in medicines
    )
    interaction_text = (
        "\n".join(f"- {i['drug_a']} + {i['drug_b']} ({i['severity']}): {i['description']}" for i in interactions)
        if interactions else "None found."
    )

    user_prompt = f"""Medicines on this prescription:
{medicine_list}

Reference info from the drug knowledge base:
{drug_context}

Interaction warnings (from the interaction graph):
{interaction_text}

Write the explanation now, in English."""

    return _chain().invoke({"user_prompt": user_prompt})


def answer_question(question: str, drug_context: str) -> str:
    user_prompt = f"""Reference info from the drug knowledge base:
{drug_context}

Patient's question: "{question}"

Answer in English, using only the info above. If it's not enough to
answer, say so and suggest they ask their doctor or pharmacist."""
    return _chain().invoke({"user_prompt": user_prompt})
