"""Minimal, privacy-aware operational logging for a single-service deployment."""
import logging
import time
from uuid import uuid4
from fastapi import Request, Response

logger = logging.getLogger("wechat_deliver")


def configure_logging(level: str) -> None:
    logging.basicConfig(
        level=level.upper(),
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
        force=True,
    )


async def request_log_middleware(request: Request, call_next) -> Response:
    request_id = request.headers.get("X-Request-ID", "")[:64] or uuid4().hex
    started_at = time.perf_counter()
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "http_request request_id=%s method=%s path=%s status=%s duration_ms=%d",
        request_id,
        request.method,
        request.url.path,
        response.status_code,
        (time.perf_counter() - started_at) * 1000,
    )
    return response
