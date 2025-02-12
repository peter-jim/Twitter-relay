import time
import hmac
import hashlib
import requests
from urllib.parse import urlparse

def make_api_request(method: str, url: str, api_key: str, api_secret: str, data: dict|None = None) -> requests.Response:
    """
    common api request function, handle hmac signature
    """
    # generate timestamp
    timestamp = str(int(time.time()))

    # construct message for signature
    parsed_url = urlparse(url)
    message = f"{method}{parsed_url.path}{timestamp}"
    if data:
        import json
        message += json.dumps(data)

    # generate hmac signature
    signature = hmac.new(
        api_secret.encode(),
        message.encode(),
        hashlib.sha256
    ).hexdigest()

    # set request headers
    headers = {
        'X-API-Key': api_key,
        'X-Signature': signature,
        'X-Timestamp': timestamp
    }

    # send request
    return requests.request(
        method=method,
        url=url,
        headers=headers,
        json=data if data else None
    )
