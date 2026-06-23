import asyncio
import json
import os
from concurrent.futures import ThreadPoolExecutor

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from dotenv import load_dotenv

load_dotenv()

import agentc
import agentc_langgraph.agent
from agentc_langgraph.agent import State as AgentState
from agentc_core.activity.models.content import UserContent, AssistantContent
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver
import langchain_openai

executor = ThreadPoolExecutor(max_workers=4)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

catalog = None
_span_ctx = None
root_span = None
travel_agent = None


class TravelAssistant(agentc_langgraph.agent.ReActAgent):
    def __init__(self, cat, span):
        chat_model = langchain_openai.ChatOpenAI(model="gpt-4o", temperature=0)
        self.memory = MemorySaver()
        super().__init__(
            chat_model=chat_model,
            catalog=cat,
            span=span,
            prompt_name="travel_agent",
        )

    def stream_chunks(self, span, state, config):
        react = self.create_react_agent(span, checkpointer=self.memory)
        yield from react.stream(input=state, config=config, stream_mode="values")


@app.on_event("startup")
async def startup():
    global catalog, _span_ctx, root_span, travel_agent
    catalog = agentc.Catalog()
    _span_ctx = catalog.Span(name="web_session")
    root_span = _span_ctx.__enter__()
    travel_agent = TravelAssistant(cat=catalog, span=root_span)


@app.on_event("shutdown")
async def shutdown():
    if _span_ctx:
        _span_ctx.__exit__(None, None, None)


class ChatRequest(BaseModel):
    message: str
    thread_id: str = "traveler_1"


@app.post("/api/chat")
async def chat(request: ChatRequest):
    loop = asyncio.get_event_loop()
    q: asyncio.Queue = asyncio.Queue()

    config = {
        "recursion_limit": 25,
        "configurable": {"thread_id": request.thread_id},
    }
    state: AgentState = {"messages": [HumanMessage(content=request.message)]}

    def run():
        final_message = None
        try:
            root_span.log(content=UserContent(value=request.message))
        except Exception:
            pass
        try:
            for chunk in travel_agent.stream_chunks(root_span, state, config):
                msg = chunk["messages"][-1]
                if hasattr(msg, "tool_calls") and msg.tool_calls:
                    for tc in msg.tool_calls:
                        asyncio.run_coroutine_threadsafe(
                            q.put({"type": "tool_call", "name": tc["name"], "args": tc["args"]}),
                            loop,
                        ).result()
                elif msg.type == "ai" and not getattr(msg, "tool_calls", None):
                    final_message = msg
            if final_message:
                try:
                    root_span.log(content=AssistantContent(value=final_message.content))
                except Exception:
                    pass
                asyncio.run_coroutine_threadsafe(
                    q.put({"type": "message", "content": final_message.content}),
                    loop,
                ).result()
        except Exception as e:
            asyncio.run_coroutine_threadsafe(
                q.put({"type": "error", "content": str(e)}),
                loop,
            ).result()
        finally:
            asyncio.run_coroutine_threadsafe(q.put({"type": "done"}), loop).result()

    async def generate():
        fut = loop.run_in_executor(executor, run)
        while True:
            item = await q.get()
            yield f"data: {json.dumps(item, default=str)}\n\n"
            if item["type"] in ("done", "error"):
                break
        await fut

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health():
    return {"status": "ok"}
