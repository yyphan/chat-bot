from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from .config import global_config
from .rag.rag import init_or_update_knowledge_base


@tool
def set_guidelines(guidelines: str) -> str:
    """
    Apply new guidelines (system prompt) to the customer service bot.
    Call this when the manager asks to generate or apply the configuration.

    Args:
        guidelines: The complete system prompt for the customer service bot.
    """
    global_config.guidelines = guidelines
    return "Guidelines applied to the bot."


@tool
def set_kb_url(url: str) -> str:
    """
    Set a new Zendesk Help Center URL as the knowledge base and reload it.
    Only call this if the manager explicitly provides a URL.

    Args:
        url: The Zendesk Help Center category URL.
    """
    success = init_or_update_knowledge_base(url)
    if success:
        global_config.kb_url = url
        return f"Knowledge base reloaded from {url}."
    return f"Failed to load the knowledge base from {url}."


META_SYSTEM_PROMPT = """\
You are a meta-agent that helps a customer service manager configure a customer service AI bot.

Workflow:
1. Read any reference documents provided and chat with the manager to understand requirements.
2. Clarify requirements through conversation — do NOT call any tools during normal conversation.
3. When the manager explicitly asks you to generate or apply the configuration, call:
   - set_guidelines (always): write a clear, comprehensive system prompt based on the \
conversation and documents.
   - set_kb_url (only if the manager provides a Zendesk Help Center URL): update the KB.

When writing guidelines, make them specific, professional, and actionable.\
"""

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0)

meta_agent_executor = create_react_agent(
    model=llm,
    tools=[set_guidelines, set_kb_url],
)
