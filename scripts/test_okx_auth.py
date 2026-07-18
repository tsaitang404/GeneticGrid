#!/usr/bin/env python3
"""Standalone OKX API v5 签名测试（无需 Django）"""
import os
import base64
import hashlib
import hmac
import json
from datetime import datetime, timezone

import requests


def sign(secret_key: str, timestamp: str, method: str, path: str, body: str) -> str:
    sign_str = f"{timestamp}{method.upper()}{path}{body}"
    mac = hmac.new(secret_key.encode(), sign_str.encode(), digestmod=hashlib.sha256)
    return base64.b64encode(mac.digest()).decode()


def timestamp() -> str:
    return datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'


OKX_REAL = 'https://www.okx.com'
OKX_DEMO = 'https://www.okx.cab'

def okx_request(method: str, path: str, api_key: str, secret_key: str, passphrase: str, params: dict = None, base_url: str = OKX_REAL):
    ts = timestamp()
    body_str = ''
    sig = sign(secret_key, ts, method, path, body_str)
    headers = {
        'OK-ACCESS-KEY': api_key,
        'OK-ACCESS-SIGN': sig,
        'OK-ACCESS-TIMESTAMP': ts,
        'OK-ACCESS-PASSPHRASE': passphrase,
        'Content-Type': 'application/json',
    }
    url = f'{base_url}{path}'
    print('\n=== Request ===')
    print(f'URL: {method} {url}')
    print(f'Timestamp: {ts}')
    print(f'Signature: {sig[:32]}...')
    print(f'Headers: OK-ACCESS-KEY={api_key[:8]}... OK-ACCESS-PASSPHRASE={passphrase[:4]}...')
    
    try:
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        print(f'Status: {resp.status_code}')
        data = resp.json()
        print(f'Response: {json.dumps(data, indent=2)[:500]}')
        return data
    except Exception as e:
        print(f'Error: {e}')
        return None


# ── 配置 ──
import sys
if len(sys.argv) >= 4:
    API_KEY = sys.argv[1]
    SECRET_KEY = sys.argv[2]
    PASSPHRASE = sys.argv[3]
else:
    API_KEY = os.environ.get('OKX_API_KEY', '')
    SECRET_KEY = os.environ.get('OKX_SECRET_KEY', '')
    PASSPHRASE = os.environ.get('OKX_PASSPHRASE', '')

if not all([API_KEY, SECRET_KEY, PASSPHRASE]):
    print('❌ 提供参数: python test_okx_auth.py <api_key> <secret_key> <passphrase>')
    print('   或设置环境变量: OKX_API_KEY, OKX_SECRET_KEY, OKX_PASSPHRASE')
    exit(1)

# 1. 测试公开接口（无需签名）
print('\n=== 1. 公开接口 (public/time) ===')
r = requests.get('https://www.okx.com/api/v5/public/time', timeout=15)
print(f'Status: {r.status_code} -> {r.json()}')

# 2. 测试账户配置（需要签名）
print('\n=== 2. 账户配置 (account/config) ===')
result = okx_request('GET', '/api/v5/account/config', API_KEY, SECRET_KEY, PASSPHRASE)
if result and result.get('code') == '0':
    print('\n✅ 认证成功！')
    print(f'账户信息: {json.dumps(result, indent=2, ensure_ascii=False)}')
elif result:
    print(f'\n❌ 失败: {result.get("msg", "未知错误")}')
    if result.get('code') == '50119':
        print('  ⚠️ 可能是 passphrase 错误')
    elif result.get('code') == '50101':
        print('  ⚠️ API Key 不存在或已禁用')
    elif result.get('code') == '50121':
        print('  ⚠️ 签名参数错误（检查 secret key 是否正确）')
else:
    print('\n❌ 请求失败，请检查网络或代理配置')

# 3. 尝试模拟盘
print('\n\n=== 3. 测试模拟盘环境 (okx.cab) ===')
result_demo = okx_request('GET', '/api/v5/account/config', API_KEY, SECRET_KEY, PASSPHRASE, base_url=OKX_DEMO)
if result_demo and result_demo.get('code') == '0':
    print('\n✅ 模拟盘认证成功！')
    print(f'账户信息: {json.dumps(result_demo, indent=2, ensure_ascii=False)}')
elif result_demo:
    print(f'\n❌ 失败: {result_demo.get("msg", "未知错误")}')
