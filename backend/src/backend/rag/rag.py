import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from langchain_community.document_loaders import WebBaseLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool
from ..config import global_config

# Global RAG state
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
vectorstore = None
retriever = None

def get_all_links(url: str, keyword: str) -> set:
    """Fetch a web page and extract all full hyperlinks that contain the given keyword."""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8'
    }
    links = set()
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        for a_tag in soup.find_all('a', href=True):
            href = a_tag['href']
            # Zendesk links are often relative paths (e.g. /hc/en-gb/articles/...)
            if keyword in href.lower():
                full_url = urljoin(url, href)
                links.add(full_url)
    except Exception as e:
        print(f"[warning] Failed to fetch {url}: {e}")
    return links

def init_or_update_knowledge_base(url: str):
    global vectorstore, retriever
    print(f"\n[info] Deeply parsing knowledge base from: {url}")
    
    try:
        article_urls = set()
        
        # 1. If the user directly provides an article URL, include it as‑is
        if '/articles/' in url.lower():
            article_urls.add(url)
        else:
            # 2. From the current page, find all directly exposed articles
            article_urls.update(get_all_links(url, '/articles/'))
            
            # 3. From the current page, find all section URLs
            section_urls = get_all_links(url, '/sections/')
            print(f"[info] Found {len(section_urls)} subsections, crawling them for articles...")
            
            # 4. Visit each section and collect the articles inside
            for sec_url in section_urls:
                sub_articles = get_all_links(sec_url, '/articles/')
                article_urls.update(sub_articles)

        urls_to_load = list(article_urls)
        
        # Fallback: if nothing was found, just crawl the given URL itself
        if not urls_to_load:
            print("[warning] No article links found, falling back to single‑page mode.")
            urls_to_load = [url]
            
        print(f"[info] Discovery finished. Found {len(urls_to_load)} article URLs. Loading and indexing...")
        
        # Bulk‑load all article pages
        # Note: we simply pass the list for now; concurrency limits can be added later if needed
        loader = WebBaseLoader(urls_to_load)
        docs = loader.load()
        
        print(f"[info] Downloaded {len(docs)} documents, splitting and embedding...")
        
        # Zendesk articles are usually well structured, slightly larger chunks work better
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        splits = text_splitter.split_documents(docs)
        
        global embeddings
        vectorstore = Chroma.from_documents(documents=splits, embedding=embeddings)
        
        # k=4 means the model will see the top 4 most relevant chunks for each query
        retriever = vectorstore.as_retriever(search_kwargs={"k": 4}) 
        
        print("[success] Knowledge base has been fully updated and vectorized.\n")
        return True
        
    except Exception as e:
        print(f"[error] Fatal error while updating knowledge base: {e}")
        return False

@tool
def search_knowledge_base(query: str) -> str:
    """
    Query the Atome Card knowledge base for general questions, rules, and usage help.

    Args:
        query (str): The customer's concrete question.
    """
    if not retriever:
        # Lazily initialize on first use (and return a friendly message if it fails)
        if not init_or_update_knowledge_base(global_config.kb_url):
            return "Knowledge base is not available right now."
    retrieved_docs = retriever.invoke(query)
    # Concatenate all retrieved document snippets for the model to read
    return "\n\n---\n\n".join(doc.page_content for doc in retrieved_docs)