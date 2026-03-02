from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool

DEFAULT_URL = "https://help.atome.ph/hc/en-gb/categories/4439682039065-Atome-Card"
print("Loading Knowledge Base...")
loader = WebBaseLoader(DEFAULT_URL)
docs = loader.load()

text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
splits = text_splitter.split_documents(docs)

embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
retriever = vectorstore.as_retriever(search_kwargs={"k": 2})

@tool
def search_knowledge_base(query: str) -> str:
    """
    Search the knowledge base for the given query.
    """
    retrieved_docs = retriever.invoke(query)
    return "\n\n".join(doc.page_content for doc in retrieved_docs)