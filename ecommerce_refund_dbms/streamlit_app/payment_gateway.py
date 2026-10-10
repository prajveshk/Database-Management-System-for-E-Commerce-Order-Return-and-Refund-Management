"""Deterministic mock payment gateway (no real bank network, no card data stored)."""
import uuid
from typing import Dict, Any


class MockPaymentGateway:
    """Returns synthetic provider references for order payments."""

    @staticmethod
    def process_payment(amount: float, order_id: int) -> Dict[str, Any]:
        provider_ref = f"MOCK-PAY-{uuid.uuid4().hex[:12].upper()}"
        return {
            "success": True,
            "provider_reference": provider_ref,
            "amount": amount,
            "order_id": order_id,
            "status": "Completed"
        }
