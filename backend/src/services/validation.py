from __future__ import annotations

from datetime import datetime, timezone, timedelta
from decimal import Decimal, InvalidOperation
from typing import Optional

from models.receipts import (
    Receipt,
    ReceiptStatus,
    Severity,
    ValidationMessage,
    ValidationReport,
)


DEFAULT_CONFIDENCE_THRESHOLD = 0.6
ROUNDING_TOLERANCE = Decimal("0.02")  # allow minor rounding difference
KNOWN_VAT_RATES = {6, 12, 25}


def _validate_vat_breakdown(receipt: Receipt) -> tuple[Decimal, list[ValidationMessage]]:
    messages: list[ValidationMessage] = []
    vat_sum = Decimal("0")
    if not receipt.vat_breakdown:
        return vat_sum, messages

    for rate, amt in receipt.vat_breakdown.items():
        # Validate VAT rate keys
        try:
            rate_int = int(rate)
        except Exception:
            messages.append(
                ValidationMessage(
                    message=f"Invalid VAT rate key: {rate}",
                    severity=Severity.WARNING,
                    field_ref="vat_breakdown",
                )
            )
            rate_int = None

        if rate_int is not None and rate_int not in KNOWN_VAT_RATES:
            messages.append(
                ValidationMessage(
                    message=f"Unknown VAT rate {rate_int}%",
                    severity=Severity.WARNING,
                    field_ref="vat_breakdown",
                )
            )

        dec_amt = _as_decimal(amt)
        if dec_amt is None:
            messages.append(
                ValidationMessage(
                    message=f"Non-numeric VAT amount for rate {rate}",
                    severity=Severity.ERROR,
                    field_ref="vat_breakdown",
                )
            )
            continue
        if dec_amt < 0:
            messages.append(
                ValidationMessage(
                    message=f"Negative VAT amount for rate {rate}",
                    severity=Severity.ERROR,
                    field_ref="vat_breakdown",
                )
            )
        vat_sum += dec_amt

    return vat_sum, messages


def _validate_amounts(
    gross: Optional[Decimal],
    net: Optional[Decimal],
    vat_sum: Decimal,
) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    if gross is None:
        messages.append(
            ValidationMessage(
                message="Gross amount missing",
                severity=Severity.WARNING,
                field_ref="gross_amount",
            )
        )
    if net is None:
        messages.append(
            ValidationMessage(
                message="Net amount missing",
                severity=Severity.WARNING,
                field_ref="net_amount",
            )
        )
    if gross is None or net is None:
        return messages

    if gross < net:
        messages.append(
            ValidationMessage(
                message="Gross amount less than net amount",
                severity=Severity.ERROR,
                field_ref="gross_amount",
            )
        )
    diff = gross - (net + vat_sum)
    if abs(diff) > ROUNDING_TOLERANCE:
        messages.append(
            ValidationMessage(
                message="Gross != Net + VAT breakdown",
                severity=Severity.ERROR,
                field_ref="gross_amount",
            )
        )
    elif abs(diff) > Decimal("0.00"):
        messages.append(
            ValidationMessage(
                message="Minor rounding difference between gross and net+VAT",
                severity=Severity.INFO,
                field_ref="gross_amount",
            )
        )
    return messages


def _validate_confidence(receipt: Receipt, confidence_threshold: float) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    if (
        receipt.confidence_summary is not None
        and receipt.confidence_summary < confidence_threshold
    ):
        messages.append(
            ValidationMessage(
                message=(
                    f"Confidence {receipt.confidence_summary:.2f} below threshold "
                    f"{confidence_threshold:.2f}"
                ),
                severity=Severity.WARNING,
                field_ref="confidence_summary",
            )
        )
    return messages


def _validate_date(receipt: Receipt) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    if receipt.purchase_datetime is None:
        messages.append(
            ValidationMessage(
                message="Purchase date missing",
                severity=Severity.WARNING,
                field_ref="purchase_datetime",
            )
        )
        return messages

    now = datetime.now(timezone.utc)
    # Normalize naive datetimes as UTC for comparison
    pd = receipt.purchase_datetime
    if pd.tzinfo is None:
        pd = pd.replace(tzinfo=timezone.utc)
    if pd - now > timedelta(days=1):
        messages.append(
            ValidationMessage(
                message="Purchase date is in the future",
                severity=Severity.ERROR,
                field_ref="purchase_datetime",
            )
        )
    elif now - pd > timedelta(days=365 * 10):
        messages.append(
            ValidationMessage(
                message="Purchase date is unusually old (>10 years)",
                severity=Severity.WARNING,
                field_ref="purchase_datetime",
            )
        )
    return messages


def _validate_merchant(receipt: Receipt) -> list[ValidationMessage]:
    messages: list[ValidationMessage] = []
    if not receipt.merchant_name:
        messages.append(
            ValidationMessage(
                message="Merchant name missing",
                severity=Severity.WARNING,
                field_ref="merchant_name",
            )
        )
    return messages


def _as_decimal(val: Optional[object]) -> Optional[Decimal]:
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError):
        return None


def validate_receipt(
    receipt: Receipt, confidence_threshold: float = DEFAULT_CONFIDENCE_THRESHOLD
) -> ValidationReport:
    messages: list[ValidationMessage] = []

    gross = _as_decimal(receipt.gross_amount)
    net = _as_decimal(receipt.net_amount)

    vat_sum, vat_msgs = _validate_vat_breakdown(receipt)
    messages.extend(vat_msgs)
    messages.extend(_validate_amounts(gross, net, vat_sum))
    messages.extend(_validate_confidence(receipt, confidence_threshold))
    messages.extend(_validate_date(receipt))
    messages.extend(_validate_merchant(receipt))

    if any(m.severity == Severity.ERROR for m in messages):
        status = ReceiptStatus.FAILED
    elif any(m.severity == Severity.WARNING for m in messages):
        status = ReceiptStatus.MANUAL_REVIEW
    else:
        status = ReceiptStatus.PASSED

    return ValidationReport(
        id=None,
        receipt_id=receipt.id or "",
        status=status,
        messages=messages,
    )
