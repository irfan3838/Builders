"""INR formatting with Indian digit grouping. Amounts are always integer paise."""


def format_inr(paise: int, *, symbol: bool = True) -> str:
    neg = paise < 0
    rupees, p = divmod(abs(int(paise)), 100)
    s = str(rupees)
    if len(s) > 3:
        head, tail = s[:-3], s[-3:]
        groups = []
        while len(head) > 2:
            groups.insert(0, head[-2:])
            head = head[:-2]
        if head:
            groups.insert(0, head)
        s = ",".join(groups + [tail])
    out = f"{'₹' if symbol else ''}{s}" + (f".{p:02d}" if p else "")
    return f"-{out}" if neg else out


def rupees_to_paise(rupees: float | int | str) -> int:
    from decimal import ROUND_HALF_UP, Decimal

    return int((Decimal(str(rupees)) * 100).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
