from dotenv import load_dotenv
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from langgraph.checkpoint.memory import MemorySaver

from mock.tools import mock_get_application_status, mock_get_transaction_status
from rag.rag import search_knowledge_base

system_prompt = """
You are a professional customer service AI assistant for Atome. Please follow the following rules:
1. If the user asks general questions, use the search_knowledge_base tool to query the knowledge base and answer.
2. If the user asks about card application status, use the mock_get_application_status tool.
3. If the user asks about failed transactions, you must first confirm whether there is a transaction_id. If there is no transaction_id, politely ask the user for it. If there is a transaction_id, use the mock_get_transaction_status tool to query.
4. Be polite and professional.
""" 

llm = ChatGoogleGenerativeAI(
    model="gemini-2.5-flash",
    temperature=0,
    system_instruction=system_prompt,
)

tools =[
    search_knowledge_base, 
    mock_get_application_status, 
    mock_get_transaction_status
]

memory = MemorySaver()

agent_executor = create_react_agent(
    model=llm,
    tools=tools,
    checkpointer=memory,
)