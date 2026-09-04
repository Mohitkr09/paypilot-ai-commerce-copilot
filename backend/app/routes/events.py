import asyncio
import json

from fastapi import APIRouter
from fastapi.responses import StreamingResponse


router = APIRouter(
    prefix="/events",
    tags=["Events"],
)


# =========================================================
# CONNECTED SSE CLIENTS
# =========================================================

clients: set[asyncio.Queue] = set()


# =========================================================
# BROADCAST EVENT
# =========================================================

async def broadcast_event(
    event_type: str,
    data: dict,
):
    """
    Broadcast an event to all connected SSE clients.
    """

    message = {
        "event": event_type,
        "data": data,
    }

    # Copy the set so clients can safely disconnect
    # while broadcasting.
    for queue in list(clients):
        try:
            await queue.put(message)
        except Exception as exc:
            print(
                f"SSE broadcast error: {exc}"
            )


# =========================================================
# SSE EVENT GENERATOR
# =========================================================

async def event_generator(
    queue: asyncio.Queue,
):
    """
    Generate SSE messages for one connected client.
    """

    try:

        # -------------------------------------------------
        # Initial connection event
        # -------------------------------------------------

        yield (
            "event: connected\n"
            'data: {"message":"Connected to PayPilot events"}\n\n'
        )

        # -------------------------------------------------
        # Keep listening for events
        # -------------------------------------------------

        while True:

            message = await queue.get()

            event_type = message["event"]
            data = message["data"]

            yield (
                f"event: {event_type}\n"
                f"data: {json.dumps(data)}\n\n"
            )

    except asyncio.CancelledError:

        print(
            "SSE client disconnected."
        )

        raise


# =========================================================
# GET /events/orders
# =========================================================

@router.get("/orders")
async def order_events():

    queue = asyncio.Queue()

    clients.add(queue)

    print(
        f"SSE client connected. "
        f"Total clients: {len(clients)}"
    )

    async def stream():

        try:

            async for event in event_generator(
                queue
            ):
                yield event

        finally:

            clients.discard(queue)

            print(
                f"SSE client disconnected. "
                f"Total clients: {len(clients)}"
            )

    return StreamingResponse(
        stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )