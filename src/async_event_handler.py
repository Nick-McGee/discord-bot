import logging
from typing import Any, Coroutine
from asyncio import AbstractEventLoop, iscoroutinefunction

subscribers = {}

def subscribe(event_type: str, function: Coroutine) -> None:
    if not event_type in subscribers:
        subscribers[event_type] = []
    subscribers[event_type].append(function)


def post_event(event_type: str, loop: AbstractEventLoop, *args) -> None:
    if not event_type in subscribers:
        return
    for function in subscribers[event_type]:
        if iscoroutinefunction(function):
            try:
                loop.create_task(function(*args))
            except TypeError as error:
                logging.error('Unable to create task for %s: %s', function, error)
        elif callable(function):
            try:
                function(*args)
            except TypeError as error:
                logging.error('Unable to run function for %s: %s', function, error)
        else:
            logging.error('%s not detected to be a valid callable or coroutine', function)
