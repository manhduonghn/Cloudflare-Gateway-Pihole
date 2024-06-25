import json
import ssl
import http.client
import gzip
import zlib
from io import BytesIO
from typing import Optional, Tuple
from src import (
    CF_API_TOKEN, CF_IDENTIFIER, rate_limited_request,
    retry, stop_never, wait_random_exponential, retry_if_exception_type
)
from src.colorlog import logger

class HTTPException(Exception):
    pass

def send_request(method: str, endpoint: str, body: Optional[str] = None) -> Tuple[int, dict]:
    context = ssl.create_default_context()
    
    conn = http.client.HTTPSConnection("api.cloudflare.com", context=context)
    
    headers = {
        "Authorization": f"Bearer {CF_API_TOKEN}",
        "Content-Type": "application/json",
        "Accept-Encoding": "gzip, deflate"
    }
    
    url = f"/client/v4/accounts/{CF_IDENTIFIER}/gateway{endpoint}"
    full_url = f"https://api.cloudflare.com{url}"
    
    try:
        conn.request(method, url, body, headers)
        response = conn.getresponse()
        data = response.read()
        status = response.status

        if status >= 400:
            error_message = get_error_message(status, full_url)
            logger.info(error_message)
            raise HTTPException(error_message)

        if response.getheader('Content-Encoding') == 'gzip':
            buf = BytesIO(data)
            with gzip.GzipFile(fileobj=buf) as f:
                data = f.read()
        elif response.getheader('Content-Encoding') == 'deflate':
            data = zlib.decompress(data)

        return response.status, json.loads(data.decode('utf-8'))

    except Exception as e:
        logger.info(f"Request failed: {e}")
        raise e

def get_error_message(status: int, url: str) -> str:
    error_messages = {
        400: "400 Client Error: Bad Request",
        401: "401 Client Error: Unauthorized",
        403: "403 Client Error: Forbidden",
        404: "404 Client Error: Not Found",
        429: "429 Client Error: Too Many Requests"
    }
    if status in error_messages:
        return f"{error_messages[status]} for url: {url}"
    elif status >= 500:
        return f"{status} Server Error for url: {url}"
    else:
        return f"HTTP request failed with status {status} for url: {url}"

# Tenacity settings
retry_config = {
    'stop': stop_never,
    'wait': lambda attempt_number: wait_random_exponential(
        attempt_number, multiplier=1, max_wait=10
    ),
    'retry': retry_if_exception_type((HTTPException, Exception)),
    'after': lambda retry_state: logger.info(
        f"Retrying ({retry_state['attempt_number']}): {retry_state['outcome']}"
    ),
    'before_sleep': lambda retry_state: logger.info(
        f"Sleeping before next retry ({retry_state['attempt_number']})"
    )
}

@retry(**retry_config)
def get_lists(name_prefix: str):
    status, response = send_request("GET", "/lists")
    lists = response["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**retry_config)
@rate_limited_request
def create_list(name: str, domains: list[str]):
    body = json.dumps({
        "name": name,
        "description": "Ads & Tracking Domains",
        "type": "DOMAIN",
        "items": [{"value": domain} for domain in domains],
    })
    status, response = send_request("POST", "/lists", body)
    return response["result"]

@retry(**retry_config)
@rate_limited_request
def delete_list(name: str, list_id: str):
    status, response = send_request("DELETE", f"/lists/{list_id}")
    return response["result"]

@retry(**retry_config)
def get_firewall_policies(name_prefix: str):
    status, response = send_request("GET", "/rules")
    lists = response["result"] or []
    return [l for l in lists if l["name"].startswith(name_prefix)]

@retry(**retry_config)
def create_gateway_policy(name: str, list_ids: list[str]):
    body = json.dumps({
        "name": name,
        "description": "Block Ads & Tracking",
        "action": "block",
        "enabled": True,
        "filters": ["dns"],
        "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
        "rule_settings": {
            "block_page_enabled": False,
        },
    })
    status, response = send_request("POST", "/rules", body)
    return response["result"]

@retry(**retry_config)
def update_gateway_policy(name: str, policy_id: str, list_ids: list[str]):
    body = json.dumps({
        "name": name,
        "description": "Block Ads & Tracking",
        "action": "block",
        "enabled": True,
        "filters": ["dns"],
        "traffic": "or".join([f"any(dns.domains[*] in ${l})" for l in list_ids]),
        "rule_settings": {
            "block_page_enabled": False,
        },
    })
    status, response = send_request("PUT", f"/rules/{policy_id}", body)
    return response["result"]

@retry(**retry_config)
def delete_gateway_policy(policy_id: str):    
    status, response = send_request("DELETE", f"/rules/{policy_id}")
    return response["result"]
