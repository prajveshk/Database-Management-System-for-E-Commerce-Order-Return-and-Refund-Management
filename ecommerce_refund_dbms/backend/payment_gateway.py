import uuid
from typing import Dict, Any

class MockPaymentGateway:
    """
    Mocked external payment gateway service.
    Returns provider reference IDs without handling sensitive credit card details.
    """
    
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

    @staticmethod
    def process_refund(payment_ref: str, refund_amount: float) -> Dict[str, Any]:
        refund_ref = f"MOCK-REF-{uuid.uuid4().hex[:12].upper()}"
        return {
            "success": True,
            "refund_reference": refund_ref,
            "original_payment_ref": payment_ref,
            "amount": refund_amount,
            "status": "Processed"
        }
