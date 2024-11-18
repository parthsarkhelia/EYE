from io import BytesIO

import starlette


def trim(item, depth=0, max_depth=100, max_length=1000):
    if depth > max_depth:
        return "..."

    if (
        isinstance(item, float)
        or isinstance(item, int)
        or isinstance(item, bool)
        or item is None
    ):
        return item
    elif isinstance(item, dict):
        return {k: trim(v, depth + 1) for k, v in item.items()}
    elif isinstance(item, list):
        return [trim(elem, depth + 1) for elem in item]
    elif isinstance(item, str):
        return (item[:max_length] + "...") if len(item) > max_length else item
    elif isinstance(item, starlette.datastructures.UploadFile):
        return trim(item.filename, depth + 1)
    elif isinstance(item, BytesIO):
        return trim(item.getvalue(), depth + 1)
    else:
        return type(item).__name__


async def get_request_body(request: starlette.requests.Request) -> dict:
    content_type = request.headers.get("content-type")
    if content_type is None:
        request_body = None
    elif content_type == "application/json":
        request_body = await request.json()
    elif (
        content_type.startswith("multipart/form-data")
        or content_type == "application/x-www-form-urlencoded"
    ):
        request_body = await request.form()
        request_body = {k: v for k, v in request_body.items()}
    else:
        request_body = None
    return request_body
