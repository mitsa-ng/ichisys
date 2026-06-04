import asyncio
import json
from typing import Any

subscribers: list[asyncio.Queue] = []


async def subscribe() -> asyncio.Queue:
    q: asyncio.Queue = asyncio.Queue()
    subscribers.append(q)
    return q


def unsubscribe(q: asyncio.Queue):
    if q in subscribers:
        subscribers.remove(q)


async def broadcast(event: str, data: Any):
    payload = json.dumps({"event": event, "data": data})
    for q in subscribers[:]:
        try:
            await q.put(payload)
        except Exception:
            if q in subscribers:
                subscribers.remove(q)
