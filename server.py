"""FastAPI server with SSE streaming for the research navigator."""

import asyncio
import json
import os
from contextlib import asynccontextmanager
from dataclasses import asdict
from typing import AsyncGenerator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from agents_impl import build_agents
from env_loader import load_env
from main import OrchestratorConfig
from stream_events import StreamEvent, StreamEventTypes


# Load environment variables early (including CORS settings).
load_env()

# Global agents instance
_agents = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize agents on startup."""
    global _agents
    _agents = build_agents()
    yield
    _agents = None


app = FastAPI(
    title="Research Navigator API",
    description="Multi-agent research assistant with streaming support",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS for frontend
def _cors_origins() -> list[str]:
    raw = os.getenv("CORS_ORIGINS") or os.getenv("FRONTEND_ORIGIN")
    if raw:
        return [origin.strip() for origin in raw.split(",") if origin.strip()]
    return ["http://localhost:3000", "http://127.0.0.1:3000"]


app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class QueryRequest(BaseModel):
    query: str
    max_clarify_rounds: int = 2
    max_orchestrator_loops: int = 3
    skip_clarify: bool = False
    clarified_context: str | None = None


class ClarifyRequest(BaseModel):
    query: str


class OrchestratorRequest(BaseModel):
    clarified_context: str
    max_loops: int = 3


async def event_generator(events: AsyncGenerator[StreamEvent, None]) -> AsyncGenerator[str, None]:
    """Convert StreamEvents to SSE format."""
    try:
        async for event in events:
            data = json.dumps(event.to_dict(), ensure_ascii=False)
            yield f"data: {data}\n\n"
    except Exception as e:
        error_event = StreamEvent(
            type=StreamEventTypes.ERROR,
            payload={"error": str(e), "error_type": type(e).__name__},
            agent="server",
        )
        yield f"data: {json.dumps(error_event.to_dict())}\n\n"
    finally:
        yield "data: [DONE]\n\n"


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "agents_loaded": _agents is not None}


@app.post("/api/clarify/stream")
async def clarify_stream(request: ClarifyRequest):
    """Stream clarifier agent responses."""
    if _agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")

    if not hasattr(_agents.clarifier, "run_stream"):
        raise HTTPException(status_code=501, detail="Streaming not supported for clarifier")

    async def generate():
        async for event in _agents.clarifier.run_stream(request.query):
            data = json.dumps(event.to_dict(), ensure_ascii=False)
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/orchestrator/stream")
async def orchestrator_stream(request: OrchestratorRequest):
    """Stream orchestrator (search -> extract -> verify loop) responses."""
    if _agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")

    if not hasattr(_agents.orchestrator, "run_stream"):
        raise HTTPException(status_code=501, detail="Streaming not supported for orchestrator")

    config = OrchestratorConfig(
        max_loops=request.max_loops,
        require_plan_approval=False,
    )

    async def generate():
        async for event in _agents.orchestrator.run_stream(request.clarified_context, config):
            data = json.dumps(event.to_dict(), ensure_ascii=False)
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/visualize/stream")
async def visualize_stream(request: dict):
    """Stream visualizer agent responses."""
    if _agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")

    if not hasattr(_agents.visualizer, "run_stream"):
        raise HTTPException(status_code=501, detail="Streaming not supported for visualizer")

    context = json.dumps(request, ensure_ascii=False)

    async def generate():
        async for event in _agents.visualizer.run_stream(context):
            data = json.dumps(event.to_dict(), ensure_ascii=False)
            yield f"data: {data}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/run/stream")
async def run_full_pipeline_stream(request: QueryRequest):
    """Stream the full pipeline: clarify -> orchestrate -> visualize."""
    if _agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")

    async def generate():
        seq = 0

        # Emit pipeline start
        start_event = StreamEvent(
            type="pipeline_start",
            payload={"query": request.query},
            agent="pipeline",
            sequence=seq,
        )
        yield f"data: {json.dumps(start_event.to_dict())}\n\n"
        seq += 1

        try:
            clarified_context = None

            if request.skip_clarify and request.clarified_context:
                clarified_context = request.clarified_context
            else:
                # Phase 1: Clarify
                clarified_output = None
                if hasattr(_agents.clarifier, "run_stream"):
                    async for event in _agents.clarifier.run_stream(request.query):
                        event.sequence = seq
                        yield f"data: {json.dumps(event.to_dict())}\n\n"
                        seq += 1
                        if event.type == StreamEventTypes.AGENT_COMPLETE:
                            clarified_output = event.payload.get("output", {})
                else:
                    clarified_output = asdict(_agents.clarifier.run(request.query))

                if clarified_output is None:
                    raise RuntimeError("Clarifier did not produce output")

                clarified_context = json.dumps({
                    "original_query": request.query,
                    "final": clarified_output,
                })

            if clarified_context is None:
                raise RuntimeError("Clarified context is missing")

            # Phase 2: Orchestrate
            config = OrchestratorConfig(
                max_loops=request.max_orchestrator_loops,
                require_plan_approval=False,
            )

            orchestrator_output = None
            if hasattr(_agents.orchestrator, "run_stream"):
                async for event in _agents.orchestrator.run_stream(clarified_context, config):
                    event.sequence = seq
                    yield f"data: {json.dumps(event.to_dict())}\n\n"
                    seq += 1
                    if event.type == StreamEventTypes.AGENT_COMPLETE and event.agent == "orchestrator":
                        orchestrator_output = event.payload.get("output", {})
            else:
                orchestrator_output = asdict(_agents.orchestrator.run(clarified_context, config))

            # Phase 3: Visualize (if report available)
            if orchestrator_output and orchestrator_output.get("report"):
                report_context = json.dumps(orchestrator_output["report"])
                if hasattr(_agents.visualizer, "run_stream"):
                    async for event in _agents.visualizer.run_stream(report_context):
                        event.sequence = seq
                        yield f"data: {json.dumps(event.to_dict())}\n\n"
                        seq += 1

            # Emit pipeline complete
            complete_event = StreamEvent(
                type="pipeline_complete",
                payload={"success": True},
                agent="pipeline",
                sequence=seq,
            )
            yield f"data: {json.dumps(complete_event.to_dict())}\n\n"

        except Exception as e:
            error_event = StreamEvent(
                type=StreamEventTypes.ERROR,
                payload={"error": str(e), "error_type": type(e).__name__},
                agent="pipeline",
                sequence=seq,
            )
            yield f"data: {json.dumps(error_event.to_dict())}\n\n"

        yield "data: [DONE]\n\n"

    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


# Non-streaming endpoints for compatibility
@app.post("/api/clarify")
async def clarify(request: ClarifyRequest):
    """Non-streaming clarify endpoint."""
    if _agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")
    try:
        result = _agents.clarifier.run(request.query)
        return asdict(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/api/orchestrator")
async def orchestrate(request: OrchestratorRequest):
    """Non-streaming orchestrator endpoint."""
    if _agents is None:
        raise HTTPException(status_code=503, detail="Agents not initialized")

    config = OrchestratorConfig(
        max_loops=request.max_loops,
        require_plan_approval=False,
    )
    try:
        result = _agents.orchestrator.run(request.clarified_context, config)
        return asdict(result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
