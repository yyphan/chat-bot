import os
import sys

import streamlit as st
import streamlit.components.v1 as components
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
        if "GOOGLE_API_KEY" in st.secrets and not os.getenv("GOOGLE_API_KEY"):
            os.environ["GOOGLE_API_KEY"] = str(st.secrets["GOOGLE_API_KEY"])
    except Exception:
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

# Fix the left config column at 600 px regardless of screen width;
# stretch the config form to match the chat box height.
st.markdown(
    """
    <style>
        div[data-testid="stForm"] {
            min-height: 600px;
        }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Session state ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []
if "report_target_index" not in st.session_state:
    st.session_state.report_target_index = None

# Initialize KB once per URL (won't re-run on every Streamlit rerun)
_ensure_kb_loaded(global_config.kb_url)


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


# ── Tabs ──────────────────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Customer Service Bot", "Agent Builder"])


# ── Tab 1: Customer Service Bot (Part 1) ─────────────────────────────────────
with tab1:
    col_cfg, col_chat = st.columns([0.618, 1])

    # Left column: manager config panel (fixed at 600px via CSS above)
    with col_cfg:
        st.title("Manager Dashboard")

        with st.form("config_form"):
            new_url = st.text_input("Knowledge Base URL", value=global_config.kb_url)
            new_guidelines = st.text_area(
                "Guidelines", value=global_config.guidelines, height=300
            )
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

        st.caption("Edit the bot configuration here. Changes take effect immediately.")

    # Right column: chat interface
    with col_chat:
        st.title("Atome Customer Service")

        chat_box = st.container(height=600)
        with chat_box:
            for i, msg in enumerate(st.session_state.messages):
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

                    if msg["role"] == "assistant":
                        if st.button("Report mistake", key=f"report_{i}"):
                            st.session_state.report_target_index = i

        # Report mistake form — rendered inside chat_box so it pushes history up
        if st.session_state.report_target_index is not None:
            idx = st.session_state.report_target_index
            if 0 <= idx < len(st.session_state.messages):
                wrong_answer = st.session_state.messages[idx]["content"]
                question = ""
                for j in range(idx - 1, -1, -1):
                    if st.session_state.messages[j]["role"] == "user":
                        question = st.session_state.messages[j]["content"]
                        break

                with chat_box:
                    with st.form("report_mistake_form"):
                        st.markdown("### Report mistake")
                        st.markdown("We will use your feedback to improve future answers.")
                        st.markdown(f"**Question:** {question or '(not found)'}")
                        st.markdown(f"**Bot answer:** {wrong_answer}")
                        user_feedback = st.text_area(
                            "What was wrong? How should it respond instead?"
                        )
                        submitted = st.form_submit_button("Submit feedback")

                        if submitted:
                            with st.spinner(
                                "Analyzing the mistake and updating internal rules..."
                            ):
                                new_rule = auto_fix_mistake(
                                    question=question,
                                    wrong_answer=wrong_answer,
                                    user_feedback=user_feedback,
                                )
                            st.success(
                                "Thank you! I have learned a new rule to avoid this mistake."
                            )
                            st.markdown(f"**New internal rule:** {new_rule}")
                            st.session_state.report_target_index = None

        # Scroll the chat box to the bottom after every render
        components.html(
            """
            <script>
                window.parent.document
                    .querySelectorAll('[data-testid="stVerticalBlockBorderWrapper"]')
                    .forEach(el => { el.scrollTop = el.scrollHeight; });
            </script>
            """,
            height=0,
        )

        if prompt := st.chat_input(
            "Ask me anything about Atome...", key="chat_input_tab1"
        ):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with chat_box:
                with st.chat_message("user"):
                    st.markdown(prompt)

                with st.chat_message("assistant"):
                    with st.spinner("Thinking..."):
                        try:
                            system_content = global_config.guidelines.strip()
                            if global_config.correction_rules:
                                corrections = "\n".join(
                                    f"- {r}" for r in global_config.correction_rules
                                )
                                system_content += (
                                    "\n\n[CRITICAL: Learned Lessons from Past Mistakes]:\n"
                                    + corrections
                                )
                            messages = [("system", system_content)]
                            for msg in st.session_state.messages:
                                role = "human" if msg["role"] == "user" else "assistant"
                                messages.append((role, msg["content"]))
                            response = agent_executor.invoke({"messages": messages})

                            last_message = response["messages"][-1]
                            reply = _extract_text_content(last_message.content)
                            st.markdown(reply)
                            st.session_state.messages.append(
                                {"role": "assistant", "content": reply}
                            )
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")


# ── Tab 2: Agent Builder (Part 2) ─────────────────────────────────────────────
with tab2:
    st.title("Agent Builder")
    st.info(
        "Upload documents and chat with the meta-agent to configure the customer service bot. Coming in the next step."
    )
