

from typing import Any, Awaitable, Callable

payload = []

def ws_payload(func: Callable[..., Awaitable[Any]]
               ) -> Callable[..., Awaitable[Any]]:
    async def wrapper(*args, **kwargs) -> Any:
        payload.append((args, kwargs))
        result = await func(*args, **kwargs)
        return result
    return wrapper