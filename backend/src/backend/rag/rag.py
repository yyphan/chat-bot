import requests
from urllib.parse import urlparse

from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_core.tools import tool

from ..config import global_config


# Global RAG state
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
vectorstore = None
retriever = None


def _build_zendesk_api_base(category_url: str) -> tuple[str, str]:
    """
    Given a Help Center category URL, derive the API base and category id.

    Example:
        https://help.atome.ph/hc/en-gb/categories/4439682039065-Atome-Card
        -> api_base: https://help.atome.ph/api/v2/help_center
           category_id: 4439682039065
    """
    parsed = urlparse(category_url)
    base = f"{parsed.scheme}://{parsed.netloc}/api/v2/help_center"
    parts = [p for p in parsed.path.split("/") if p]
    # Expect ".../categories/{id-and-slug}"
    cat_segment = parts[-1]
    category_id = cat_segment.split("-")[0]
    return base, category_id


def _fetch_category_articles(category_url: str) -> list[dict]:
    """Fetch all public articles in a Zendesk Help Center category using the official API."""
    api_base, category_id = _build_zendesk_api_base(category_url)
    url = f"{api_base}/categories/{category_id}/articles.json"
    headers = {
        "Accept": "application/json",
        "User-Agent": "atome-rag-bot/1.0",
    }

    articles: list[dict] = []
    while url:
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        batch = data.get("articles", [])
        articles.extend(batch)
        url = data.get("next_page")

    return articles


def init_or_update_knowledge_base(url: str) -> bool:
    """Use Zendesk Help Center API to fetch and index all articles under the given category URL."""
    global vectorstore, retriever
    print(f"\n[info] Deeply parsing knowledge base from: {url}")

    try:
        articles = _fetch_category_articles(url)
        if not articles:
            print("[warning] No articles returned from Zendesk API.")
            return False

        texts = []
        metadatas = []
        for art in articles:
            body = art.get("body", "") or ""
            if not body.strip():
                continue
            texts.append(body)
            metadatas.append(
                {
                    "title": art.get("title", ""),
                    "url": art.get("html_url", ""),
                    "id": art.get("id"),
                }
            )

        if not texts:
            print("[warning] All fetched articles were empty; nothing to index.")
            return False

        print(f"[info] Downloaded {len(texts)} non-empty article bodies, embedding and indexing...")

        global embeddings
        vectorstore = Chroma.from_texts(texts=texts, embedding=embeddings, metadatas=metadatas)

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