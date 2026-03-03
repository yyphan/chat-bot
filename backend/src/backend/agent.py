from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent

from .mock.tools import mock_get_application_status, mock_get_transaction_status
from .rag.rag import search_knowledge_base

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
)

tools = [
    search_knowledge_base,
    mock_get_application_status,
    mock_get_transaction_status,
]

# Stateless agent — conversation history and system prompt are managed explicitly
# in streamlit_app.py so that guideline updates take effect immediately.
agent_executor = create_react_agent(model=llm, tools=tools)