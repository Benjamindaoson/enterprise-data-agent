import uuid
from typing import Optional

import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel


app = FastAPI(title="DeepAgent Search API")


class TaskRequest(BaseModel):
    query: str
    thread_id: Optional[str] = None


class TaskResponse(BaseModel):
    status: str
    thread_id: str
    message: str


@app.get("/")
def home():
    return {"message": "deepagent-search is running"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/task", response_model=TaskResponse)
def create_task(request: TaskRequest):
    thread_id = request.thread_id or str(uuid.uuid4())

    return TaskResponse(
        status="started",
        thread_id=thread_id,
        message=f"Task received: {request.query}",
    )


def start_server():
    uvicorn.run(app, host="127.0.0.1", port=8000)