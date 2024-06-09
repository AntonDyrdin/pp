import hmac
import hashlib
import json
import requests
import logging

def get_signature(api_secret, data):
    return hmac.new(
        api_secret.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha512
    ).hexdigest()

def api_query(api_key, api_secret, base_url, api_method, params={}):
    params['nonce'] = int(round(time.time() * 1000))
    params = json.dumps(params)

    headers = {
        'Content-Type': 'application/json',
        'Key': api_key,
        'Sign': get_signature(api_secret, params)
    }

    try:
        response = requests.post(base_url + api_method, headers=headers, data=params)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logging.error(f"Ошибка при запросе к API Exmo: {e}")
        return {}

def calculate_ema(prices, alpha=0.1):
    ema = [prices[0]]  # начальное значение EMA равно первому значению цены
    for price in prices[1:]:
        ema.append(ema[-1] + alpha * (price - ema[-1]))
    return ema[-1]
