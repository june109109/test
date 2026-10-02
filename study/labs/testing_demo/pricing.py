"""Educational quote rules; inputs represent trusted server-side prices in cents."""
from dataclasses import dataclass

@dataclass(frozen=True)
class Line:
    sku: str
    quantity: int
    unit_cents: int


def quote(lines, discount_bps=0):
    if not lines:
        raise ValueError('at least one line required')
    if type(discount_bps) is not int or not 0 <= discount_bps <= 10000:
        raise ValueError('discount must be integer basis points from 0 to 10000')
    for line in lines:
        if not line.sku or type(line.quantity) is not int or line.quantity <= 0:
            raise ValueError('invalid sku or quantity')
        if type(line.unit_cents) is not int or line.unit_cents < 0:
            raise ValueError('invalid unit price')
    gross=sum(line.quantity*line.unit_cents for line in lines)
    discounted=gross*(10000-discount_bps)//10000
    shipping=0 if discounted >= 10000 else 599
    return {'subtotal_cents':discounted,'shipping_cents':shipping,'total_cents':discounted+shipping}
