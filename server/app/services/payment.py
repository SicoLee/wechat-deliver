"""Payment confirmation and WeChat Pay v3 callback verification boundary."""
import base64
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Mapping
from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy import select
from sqlalchemy.orm import Session
from ..models import Order, OrderStatus, PaymentStatus
from .order_audit import record_order_audit
from .order_events import enqueue_receipt_print


class PaymentVerificationError(ValueError):
    pass


def confirm_payment(db: Session, order: Order, provider: str, transaction_id: str) -> bool:
    """Atomically record a provider transaction and enqueue downstream fulfilment once."""
    existing = db.scalar(select(Order).where(Order.payment_transaction_id == transaction_id))
    if existing and existing.id != order.id:
        raise PaymentVerificationError("payment transaction belongs to another order")
    if order.payment_status == PaymentStatus.PAID:
        if order.payment_transaction_id != transaction_id:
            raise PaymentVerificationError("order already paid by another transaction")
        return False
    previous_status = order.status.value
    order.status = OrderStatus.PAID
    order.payment_status = PaymentStatus.PAID
    order.payment_provider = provider
    order.payment_transaction_id = transaction_id
    order.paid_at = datetime.now()
    enqueue_receipt_print(db, order)
    record_order_audit(db, order, "PAYMENT_CONFIRMED", from_status=previous_status, to_status=order.status.value)
    db.commit()
    return True


class WechatPayV3CallbackVerifier:
    """Verifies WeChat's signature before decrypting its API v3 callback resource."""
    def __init__(self, api_v3_key: str, platform_cert_path: str, max_age_seconds: int = 300):
        if len(api_v3_key.encode("utf-8")) != 32:
            raise ValueError("WECHAT_PAY_API_V3_KEY must be exactly 32 bytes")
        self.api_v3_key = api_v3_key.encode("utf-8")
        self.max_age_seconds = max_age_seconds
        certificate = x509.load_pem_x509_certificate(Path(platform_cert_path).read_bytes())
        self.public_key = certificate.public_key()

    def verify_and_decrypt(self, headers: Mapping[str, str], raw_body: bytes) -> dict:
        try:
            timestamp = headers["Wechatpay-Timestamp"]
            nonce = headers["Wechatpay-Nonce"]
            signature = headers["Wechatpay-Signature"]
        except KeyError as error:
            raise PaymentVerificationError("missing WeChat Pay signature header") from error
        if abs(time.time() - int(timestamp)) > self.max_age_seconds:
            raise PaymentVerificationError("stale WeChat Pay callback")
        message = f"{timestamp}\n{nonce}\n{raw_body.decode('utf-8')}\n".encode("utf-8")
        try:
            self.public_key.verify(base64.b64decode(signature), message, padding.PKCS1v15(), hashes.SHA256())
            envelope = json.loads(raw_body)
            resource = envelope["resource"]
            plaintext = AESGCM(self.api_v3_key).decrypt(
                resource["nonce"].encode("utf-8"),
                base64.b64decode(resource["ciphertext"]),
                resource.get("associated_data", "").encode("utf-8"),
            )
            return json.loads(plaintext)
        except Exception as error:
            raise PaymentVerificationError("invalid WeChat Pay callback") from error
