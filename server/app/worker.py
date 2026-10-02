"""Durable print-event worker. Run separately from the HTTP API in production."""
import time
from .config import get_settings
from .db import SessionLocal
from .observability import configure_logging, logger
from .services.order_events import process_pending_prints
from .services.printer import MockPrinter


def run_once() -> int:
    settings = get_settings()
    with SessionLocal() as db:
        return process_pending_prints(db, MockPrinter(), max_attempts=settings.print_max_attempts, retry_delay_seconds=settings.print_retry_delay_seconds)


def main() -> None:
    settings = get_settings()
    settings.validate_runtime()
    configure_logging(settings.log_level)
    logger.info("print_worker_started interval_seconds=%s", settings.worker_poll_interval_seconds)
    while True:
        processed = run_once()
        if processed:
            logger.info("print_worker_processed count=%s", processed)
        time.sleep(settings.worker_poll_interval_seconds)


if __name__ == "__main__":
    main()
