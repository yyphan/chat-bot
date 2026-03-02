from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool
from backend.config import global_config

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")
vectorstore = None
retriever = None

def init_or_update_knowledge_base(url: str):
    global vectorstore, retriever
    print(f"🔄 Loading and parsing new knowledge base: {url}")
    try:
        loader = WebBaseLoader(url)
        docs = loader.load()
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        splits = text_splitter.split_documents(docs)
        
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
        retriever = vectorstore.as_retriever(search_kwargs={"k": 2})
        print("✅ Knowledge base updated successfully!")
        return True
    except Exception as e:
        print(f"❌ Knowledge base update failed: {e}")
        return False

# 启动时先加载一次默认 URL
init_or_update_knowledge_base(global_config.kb_url)

@tool
def search_knowledge_base(query: str) -> str:
    """If the user asks general questions, use the search_knowledge_base tool to query the knowledge base and answer."""
    if not retriever:
        return "The knowledge base has not been initialized."
    retrieved_docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in retrieved_docs)