import json
from urllib.error import URLError
from urllib.request import Request, urlopen

from django.core.cache import cache
from django.http import JsonResponse

from .constants import BUDGET_CURRENCY_CHOICES, DEFAULT_BUDGET_CURRENCY

VALID_BUDGET_CURRENCIES = {code for code, _ in BUDGET_CURRENCY_CHOICES}
EXCHANGE_RATES_CACHE_KEY = 'portal:budget_exchange_rates_usd_v2'
EXCHANGE_RATES_CACHE_SECONDS = 60 * 60
FRANKFURTER_URL = 'https://api.frankfurter.dev/v1/latest?base=USD&symbols=EUR,GBP,PLN'


def normalize_budget_currency(currency):
    currency = (currency or '').strip().upper()
    if currency == 'ZL':
        currency = 'PLN'
    if currency in VALID_BUDGET_CURRENCIES:
        return currency
    return DEFAULT_BUDGET_CURRENCY


def save_budget_fields(academic, request):
    academic.budget_expectations = request.POST.get('budget_expectations', '').strip()
    academic.budget_currency = normalize_budget_currency(
        request.POST.get('budget_currency', DEFAULT_BUDGET_CURRENCY)
    )


def fetch_exchange_rates():
    cached = cache.get(EXCHANGE_RATES_CACHE_KEY)
    if cached:
        return cached

    try:
        request = Request(
            FRANKFURTER_URL,
            headers={'User-Agent': 'EdunadePlatform/1.0', 'Accept': 'application/json'},
        )
        with urlopen(request, timeout=8) as response:
            data = json.loads(response.read().decode())
    except (URLError, OSError, json.JSONDecodeError, KeyError, TypeError, ValueError):
        return None

    payload = {
        'date': data.get('date', ''),
        'rates': {
            'USD': 1.0,
            'EUR': float(data['rates']['EUR']),
            'GBP': float(data['rates']['GBP']),
            'PLN': float(data['rates']['PLN']),
        },
    }
    cache.set(EXCHANGE_RATES_CACHE_KEY, payload, EXCHANGE_RATES_CACHE_SECONDS)
    return payload


def budget_exchange_rates_response():
    payload = fetch_exchange_rates()
    if not payload:
        return JsonResponse({'error': 'Rates unavailable'}, status=503)
    return JsonResponse(payload)
