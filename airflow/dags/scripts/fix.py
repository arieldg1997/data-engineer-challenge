from decimal import Decimal
import requests
import logging

logger = logging.getLogger(__name__)

fx_cache = {}

def get_fx_rate_to_usd(currency):

    if currency == "USD":
        return Decimal("1.0")

    if currency in fx_cache:
        return fx_cache[currency]

    try:
        response = requests.get(
            f"https://api.exchangerate-api.com/v4/latest/{currency}",
            timeout=10
        )

        response.raise_for_status()

        rate = Decimal(str(response.json()["rates"]["USD"]))

        fx_cache[currency] = rate
        return rate

    except Exception:
        logger.warning(f"Invalid or unsupported currency {currency}. Using FX rate = 1.0")
        return Decimal("1.0")
        