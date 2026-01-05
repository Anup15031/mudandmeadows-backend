from fastapi import APIRouter, Request
from fastapi.responses import StreamingResponse
import asyncio
import json
import logging

router = APIRouter(tags=["events"])

logger = logging.getLogger("resort_backend.events")

# In-memory broadcaster: list of asyncio.Queue objects, one per subscriber
_subscribers: list[asyncio.Queue] = []

def publish_event(evt: dict):
    """Publish an event to all subscribers. Non-blocking."""
    data = evt.copy()
    data["ts"] = asyncio.get_event_loop().time()
    payload = json.dumps(data)
    for q in list(_subscribers):
        try:
            # use put_nowait to avoid blocking
            q.put_nowait(payload)
        except Exception:
            logger.exception("Failed to enqueue event for a subscriber")

async def _event_generator(q: asyncio.Queue):
    try:
        while True:
            payload = await q.get()
            yield f"data: {payload}\n\n"
    except asyncio.CancelledError:
        return


@router.get("/events/stream")
async def events_stream(request: Request):
    """SSE endpoint that streams JSON events as `data: ...` lines.

    Note: this broadcaster is in-memory and only works for a single process.
    """
    q: asyncio.Queue = asyncio.Queue()
    _subscribers.append(q)

    async def cleanup():
        try:
            _subscribers.remove(q)
        except ValueError:
            pass

    generator = _event_generator(q)
    # StreamingResponse will iterate the async generator
    resp = StreamingResponse(generator, media_type="text/event-stream")

    # When client disconnects, StreamingResponse won't call cleanup automatically;
    # rely on background task when generator completes. Wrap generator to ensure cleanup.
    async def wrapper_gen():
        try:
            async for chunk in generator:
                yield chunk
        finally:
            await cleanup()

    return StreamingResponse(wrapper_gen(), media_type="text/event-stream")
