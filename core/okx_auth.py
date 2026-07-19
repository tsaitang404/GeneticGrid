"""OKX API v5 认证工具 — 签名、加密、账户接口"""
import base64
import hashlib
import hmac
import json
import logging
from datetime import datetime, timezone
from typing import Optional

import requests
from cryptography.fernet import Fernet
from django.conf import settings

from core.proxy_config import get_proxy_dict

logger = logging.getLogger(__name__)

OKX_REAL_URL = 'https://www.okx.com'
# 模拟盘使用同一域名，但需要在请求头添加 x-simulated-trading: 1
# 参考: https://www.okx.com/docs-v5/en/#overview-demo-trading-services
OKX_DEMO_URL = 'https://www.okx.com'


_fernet: Fernet | None = None

def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = base64.urlsafe_b64encode(
            hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        )
        _fernet = Fernet(key)
    return _fernet


def encrypt_credential(plaintext: str) -> bytes:
    return _get_fernet().encrypt(plaintext.encode())


def decrypt_credential(ciphertext: bytes) -> str:
    return _get_fernet().decrypt(ciphertext).decode()


def hash_passphrase(plaintext: str) -> str:
    import bcrypt as _bcrypt
    return _bcrypt.hashpw(plaintext.encode(), _bcrypt.gensalt()).decode()


def verify_passphrase(plaintext: str, hashed: str) -> bool:
    import bcrypt as _bcrypt
    return _bcrypt.checkpw(plaintext.encode(), hashed.encode())


def _signature(secret_key: str, timestamp: str, method: str, path: str, body: str) -> str:
    sign_str = f"{timestamp}{method.upper()}{path}{body}"
    mac = hmac.new(
        secret_key.encode('utf-8'),
        sign_str.encode('utf-8'),
        digestmod=hashlib.sha256,
    )
    return base64.b64encode(mac.digest()).decode()


def _build_headers(api_key: str, passphrase: str, timestamp: str, signature: str) -> dict:
    return {
        'OK-ACCESS-KEY': api_key,
        'OK-ACCESS-SIGN': signature,
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
    }


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


def okx_api_request(
    method: str,
    path: str,
    api_key: str,
    secret_key: str,
    passphrase: str,
    params: Optional[dict] = None,
    body: Optional[dict] = None,
    timeout: int = 30,
    base_url: str = OKX_REAL_URL,
    is_demo: bool = False,
) -> dict:
    ts = _timestamp()
    body_str = json.dumps(body) if body else ''
    sig = _signature(secret_key, ts, method, path, body_str)
    headers = _build_headers(api_key, passphrase, ts, sig)
    if is_demo:
        headers['x-simulated-trading'] = '1'
    proxies = get_proxy_dict()
    url = f"{base_url}{path}"

    try:
        if method.upper() == 'GET':
            resp = requests.get(url, headers=headers, params=params, proxies=proxies, timeout=timeout)
        else:
            resp = requests.post(url, headers=headers, json=body, proxies=proxies, timeout=timeout)
        if resp.status_code != 200:
            try:
                err = resp.json()
                msg = err.get('msg', resp.reason)
            except Exception:
                msg = resp.reason
            raise Exception(f"OKX API 错误 ({path}): {msg} (code={resp.status_code})")
        return resp.json()
    except requests.exceptions.Timeout:
        raise Exception(f"OKX API 请求超时 ({path})")
    except requests.exceptions.RequestException as e:
        if 'OKX API 错误' in str(e):
            raise
        raise Exception(f"OKX API 请求失败 ({path}): {e}")


def fetch_account_info(api_key: str, secret_key: str, passphrase: str, base_url: str = OKX_REAL_URL, is_demo: bool = False) -> dict:
    result = okx_api_request('GET', '/api/v5/account/config', api_key, secret_key, passphrase, base_url=base_url, is_demo=is_demo)
    if result.get('code') != '0':
        raise Exception(f"获取账户配置失败: {result.get('msg', '未知错误')}")
    data = result.get('data', [{}])[0]
    return {
        'uid': data.get('uid', ''),
        'mainNet': data.get('mainNet', ''),
        'acctLv': data.get('acctLv', ''),
        'posMode': data.get('posMode', ''),
        'level': data.get('level', ''),
        'perm': data.get('perm', ''),
    }


def fetch_balance(api_key: str, secret_key: str, passphrase: str, base_url: str = OKX_REAL_URL, is_demo: bool = False) -> dict:
    result = okx_api_request('GET', '/api/v5/account/balance', api_key, secret_key, passphrase, base_url=base_url, is_demo=is_demo)
    if result.get('code') != '0':
        raise Exception(f"获取余额失败: {result.get('msg', '未知错误')}")
    data_raw = result.get('data') or [{}]
    data_item = data_raw[0]
    return {
        'totalEq': data_item.get('totalEq', '0'),
        'totalPnl': data_item.get('totalPnl', '0'),
        'details': [
            {
                'ccy': d.get('ccy'),
                'eq': d.get('eq'),
                'eqUsd': d.get('eqUsd'),
                'availBal': d.get('availBal'),
                'frozenBal': d.get('frozenBal'),
            }
            for d in data_item.get('details', [])
        ],
    }


def fetch_positions(api_key: str, secret_key: str, passphrase: str, base_url: str = OKX_REAL_URL, is_demo: bool = False) -> list:
    result = okx_api_request('GET', '/api/v5/account/positions', api_key, secret_key, passphrase, base_url=base_url, is_demo=is_demo)
    if result.get('code') != '0':
        raise Exception(f"获取持仓失败: {result.get('msg', '未知错误')}")
    positions = []
    for pos in result.get('data', []):
        pos_qty = float(pos.get('pos', 0))
        if pos_qty != 0:
            positions.append({
                'symbol': pos.get('instId', ''),
                'positionQty': pos_qty,
                'notionalValue': float(pos.get('notionalUsd', 0)),
                'markPrice': float(pos.get('markPx', 0)),
                'leverage': float(pos.get('lever', 0)),
                'mgnMode': pos.get('mgnMode', ''),
                'side': pos.get('posSide', ''),
                'available': float(pos.get('availPos', pos_qty)),
                'frozenQty': float(pos.get('frozenQty', 0)),
                'unrealizedPnl': float(pos.get('upl', 0)),
                'unrealizedPnlRatio': float(pos.get('uplRatio', 0)),
                'timestamp': pos.get('uTime', ''),
            })
    return positions


def has_trade_permission(account_info: dict | None) -> bool:
    if not account_info:
        return False
    perm = account_info.get('perm', '')
    return 'trade' in perm.split(',')


def post_order(
    api_key: str,
    secret_key: str,
    passphrase: str,
    inst_id: str,
    td_mode: str,
    side: str,
    ord_type: str,
    sz: str,
    px: str | None = None,
    pos_side: str | None = None,
    lever: str | None = None,
    is_demo: bool = False,
) -> dict:
    body = {
        'instId': inst_id,
        'tdMode': td_mode,
        'side': side,
        'ordType': ord_type,
        'sz': sz,
    }
    if px is not None:
        body['px'] = px
    if pos_side is not None:
        body['posSide'] = pos_side
    if lever is not None:
        body['lever'] = lever
    result = okx_api_request('POST', '/api/v5/trade/order', api_key, secret_key, passphrase, body=body, is_demo=is_demo)
    if result.get('code') != '0':
        raise Exception(f"下单失败: {result.get('msg', '未知错误')}")
    return result.get('data', [{}])[0] if result.get('data') else {}


def cancel_order(
    api_key: str,
    secret_key: str,
    passphrase: str,
    inst_id: str,
    ord_id: str,
    is_demo: bool = False,
) -> dict:
    body = {'instId': inst_id, 'ordId': ord_id}
    result = okx_api_request('POST', '/api/v5/trade/cancel-order', api_key, secret_key, passphrase, body=body, is_demo=is_demo)
    if result.get('code') != '0':
        raise Exception(f"撤单失败: {result.get('msg', '未知错误')}")
    return result.get('data', [{}])[0] if result.get('data') else {}
