"""Printer seam. A production provider calls the selected cloud printer API here."""
from dataclasses import dataclass


@dataclass
class PrintResult:
    success: bool
    message: str


class MockPrinter:
    def print_order(self, order_no: str, idempotency_key: str) -> PrintResult:
        return PrintResult(True, f"开发模拟打印成功：{order_no}")
