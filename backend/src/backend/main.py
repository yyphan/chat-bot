from fastapi import FastAPI
from pydantic import BaseModel
from .agent import agent_executor

app = FastAPI(title="Atome Customer Service API (Gemini Powered)")

class ChatRequest(BaseModel):
    message: str
    session_id: str = "default_session"

@app.post("/api/chat")
async def chat(request: ChatRequest):
    inputs = {"messages":[("user", request.message)]}
    config = {"configurable": {"thread_id": request.session_id}}
    
    # 触发 LangGraph 和 Gemini
    response = agent_executor.invoke(inputs, config=config)
    
    ai_message = response["messages"][-1].content
    
    return {"reply": ai_message}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)