import os
import sys
import uuid

import streamlit as st
from dotenv import load_dotenv


# Make `backend/` package importable in Streamlit Cloud
_REPO_ROOT = os.path.dirname(os.path.abspath(__file__))
_BACKEND_SRC = os.path.join(_REPO_ROOT, "backend", "src")
if _BACKEND_SRC not in sys.path:
    sys.path.insert(0, _BACKEND_SRC)


def _load_local_env() -> None:
    """Load local .env for development (ignored if missing)."""
    env_path = os.path.join(_REPO_ROOT, "backend", ".env")
    if os.path.exists(env_path):
        load_dotenv(env_path)


def _load_secrets_to_env() -> None:
    """Safely copy secrets (if present) into environment variables."""
    try:
        # Accessing st.secrets will raise on local if no secrets.toml exists.
        if "GOOGLE_API_KEY" in st.secrets and not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = str(st.secrets["GOOGLE_API_KEY"])
    except Exception:
        # No secrets configured (typical for local dev); just skip.
        return


_load_local_env()
_load_secrets_to_env()

from backend.config import global_config  # noqa: E402
from backend.rag.rag import init_or_update_knowledge_base  # noqa: E402
from backend.agent import agent_executor  # noqa: E402
from backend.fix import auto_fix_mistake  # noqa: E402


@st.cache_resource(show_spinner=False)
def _ensure_kb_loaded(url: str) -> bool:
    return bool(init_or_update_knowledge_base(url))


st.set_page_config(page_title="Atome Customer Service System", layout="wide")

# Make sidebar wide by default
st.markdown(
    """
    <style>
        [data-testid="stSidebar"] {
            min-width: 600px;
            max-width: 600px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []
if "report_target_index" not in st.session_state:
    st.session_state.report_target_index = None


# Initialize KB once per URL (won't re-run on every Streamlit rerun)
_ensure_kb_loaded(global_config.kb_url)


with st.sidebar:
    st.title("Manager Dashboard")
    st.caption("Edit the bot configuration here. Changes take effect immediately.")

    with st.form("config_form"):
        new_url = st.text_input("Knowledge Base URL", value=global_config.kb_url)
        new_guidelines = st.text_area("Guidelines", value=global_config.guidelines, height=180)
        submitted = st.form_submit_button("Update")

        if submitted:
            global_config.guidelines = new_guidelines

            if new_url != global_config.kb_url:
                with st.spinner("Reloading knowledge base..."):
                    ok = _ensure_kb_loaded(new_url)
                if ok:
                    global_config.kb_url = new_url
                    st.success("Configuration updated.")
                else:
                    st.error("Failed to load the new knowledge base URL.")
            else:
                st.success("Configuration updated.")


st.title("Atome Customer Service")

for i, msg in enumerate(st.session_state.messages):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        if msg["role"] == "assistant":
            if st.button("Report mistake", key=f"report_{i}"):
                st.session_state.report_target_index = i


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


# Report mistake flow (applies to any assistant message)
if st.session_state.report_target_index is not None:
    idx = st.session_state.report_target_index
    if 0 <= idx < len(st.session_state.messages):
        wrong_answer = st.session_state.messages[idx]["content"]
        # Find the most recent user question before this answer
        question = ""
        for j in range(idx - 1, -1, -1):
            if st.session_state.messages[j]["role"] == "user":
                question = st.session_state.messages[j]["content"]
                break

        with st.form("report_mistake_form"):
            st.markdown("### Report mistake")
            st.markdown("We will use your feedback to improve future answers.")
            st.markdown(f"**Question:** {question or '(not found)'}")
            st.markdown(f"**Bot answer:** {wrong_answer}")
            user_feedback = st.text_area("What was wrong? How should it respond instead?")
            submitted = st.form_submit_button("Submit feedback")

            if submitted:
                with st.spinner("Analyzing the mistake and updating internal rules..."):
                    new_rule = auto_fix_mistake(
                        question=question,
                        wrong_answer=wrong_answer,
                        user_feedback=user_feedback,
                    )
                st.success("Thank you! I have learned a new rule to avoid this mistake.")
                st.markdown(f"**New internal rule:** {new_rule}")
                st.session_state.report_target_index = None


if prompt := st.chat_input("Ask me anything about Atome..."):
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking..."):
            try:
                # Build dynamic system prompt with learned corrections
                system_prompt = global_config.guidelines.strip()
                if global_config.correction_rules:
                    corrections = "\n".join(
                        f"- {r}" for r in global_config.correction_rules
                    )
                    system_prompt += (
                        "\n\n[CRITICAL: Learned Lessons from Past Mistakes]:\n"
                        f"{corrections}"
                    )

                inputs = {
                    "messages": [
                        ("system", system_prompt),
                        ("user", prompt),
                    ]
                }
                config = {"configurable": {"thread_id": st.session_state.session_id}}
                response = agent_executor.invoke(inputs, config=config)

                last_message = response["messages"][-1]
                reply = _extract_text_content(last_message.content)
                st.markdown(reply)
                st.session_state.messages.append(
                    {"role": "assistant", "content": reply}
                )
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
