from fastapi import FastAPI
from pydantic import BaseModel

try:
    # When run as part of the `backend` package (recommended)
    from .agent import agent_executor
    from .config import global_config
    from .rag.rag import init_or_update_knowledge_base
except ImportError:  # pragma: no cover
    # Fallback for running `python main.py` directly
    from agent import agent_executor
    from config import global_config
    from rag.rag import init_or_update_knowledge_base

app = FastAPI(title="Atome Customer Service API (Gemini Powered)")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    inputs = {"messages":[("user", request.message)]}
    config = {"configurable": {"thread_id": request.session_id}}
    
    # Trigger LangGraph and Gemini
    response = agent_executor.invoke(inputs, config=config)
    
    last_message = response["messages"][-1]
    raw_content = last_message.content
    
    ai_message = ""
    
    if isinstance(raw_content, list):
        # Iterate through the list, only concatenate the content with type 'text'
        for block in raw_content:
            if isinstance(block, dict) and block.get("type") == "text":
                ai_message += block.get("text", "")
            elif isinstance(block, str):
                ai_message += block
    else:
        # If it is already a regular string, assign it directly
        ai_message = str(raw_content)
        
    return {"reply": ai_message}

class ConfigUpdateRequest(BaseModel):
    kb_url: str
    guidelines: str

@app.post("/api/config")
async def update_config(request: ConfigUpdateRequest):
    # 1. Update the configuration in memory
    global_config.guidelines = request.guidelines
    
    # 2. If the URL changes, re-fetch the knowledge base
    if request.kb_url != global_config.kb_url:
        success = init_or_update_knowledge_base(request.kb_url)
        if success:
            global_config.kb_url = request.kb_url
        else:
            return {"status": "error", "message": "Failed to load new URL"}
            
    return {"status": "success", "message": "Bot configuration updated successfully"}

@app.get("/api/config")
async def get_config():
    return {
        "kb_url": global_config.kb_url,
        "guidelines": global_config.guidelines
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)