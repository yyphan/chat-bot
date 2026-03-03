from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate

from .config import global_config


def _extract_text_content(message_content) -> str:
    if isinstance(message_content, list):
        out = ""
        for block in message_content:
            if isinstance(block, dict) and block.get("type") == "text":
                out += block.get("text", "")
            elif isinstance(block, str):
                out += block
        return out
    return str(message_content)


def auto_fix_mistake(question: str, wrong_answer: str, user_feedback: str) -> str:
    """Self-healing engine: analyze a mistake and generate a corrective rule."""
    fixer_llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

    prompt = ChatPromptTemplate.from_template(
        """
You are an AI Quality Supervisor. A customer service bot made a mistake.

[User's Question]: {question}
[Bot's Wrong Answer]: {wrong_answer}
[What went wrong/User Feedback]: {user_feedback}

Task:
1. Analyze the mistake.
2. Write a short, powerful instruction to prevent this specific mistake in the future.
3. The instruction should be general enough to cover similar cases but specific enough to fix this error.

Return ONLY the new instruction text.
"""
    )

    chain = prompt | fixer_llm
    result = chain.invoke(
        {
            "question": question,
            "wrong_answer": wrong_answer,
            "user_feedback": user_feedback,
        }
    )
    new_rule = _extract_text_content(result.content)

    # Persist the new rule in global config
    global_config.correction_rules.append(new_rule)
    global_config.mistake_logs.append(
        {
            "question": question,
            "wrong_answer": wrong_answer,
            "feedback": user_feedback,
            "fix": new_rule,
        }
    )

    return new_rule

