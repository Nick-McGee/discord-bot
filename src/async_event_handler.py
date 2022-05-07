from typing import Any, Coroutine
from asyncio import AbstractEventLoop


subscribers = {}

def subscribe(event_type: str, function: Coroutine) -> None:
    if not event_type in subscribers:
        subscribers[event_type] = []
    subscribers[event_type].append(function)


def post_event(event_type: str, loop: AbstractEventLoop, data: Any = None) -> None:
    if not event_type in subscribers:
        return
    for function in subscribers[event_type]:
        if data:
            loop.create_task(function(data))
        else:
            loop.create_task(function())
