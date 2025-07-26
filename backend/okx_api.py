import requests
import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone

class OKXClient:
    def __init__(self, api_key: str, secret_key: str, passphrase: str, sandbox: bool = False):
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        # 选择环境
        if sandbox:
            self.base_url = "https://www.okx.com/api/v5/sandbox"
        else:
            self.base_url = "https://www.okx.com/api/v5"
    
    def _get_timestamp(self):
        """获取 ISO8601 毫秒格式的时间戳，符合OKX要求"""
        return datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z')
    
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = ''):
        """生成签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf-8'),
            digestmod='sha256'
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """发送请求"""
        # 确保endpoint不以斜杠开头，避免URL中出现双斜杠
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
            
        url = f"{self.base_url}/{endpoint}"
        # 获取请求路径，用于签名
        request_path = f"/api/v5/{endpoint}"
        timestamp = self._get_timestamp()

        # 准备请求头
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._sign(timestamp, method, request_path, json.dumps(data) if data else ''),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }

        # 打印请求头和参数，便于和 curl 对比
        print("[OKX DEBUG] 请求URL:", url)
        print("[OKX DEBUG] 请求路径(签名用):", request_path)
        print("[OKX DEBUG] 请求方法:", method)
        print("[OKX DEBUG] 请求头:", headers)
        print("[OKX DEBUG] 请求params:", params)
        print("[OKX DEBUG] 请求data:", data)

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, params=params)
            elif method == 'POST':
                response = requests.post(url, headers=headers, json=data)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            return response.json()

        except requests.exceptions.RequestException as e:
            return {
                'code': 'ERROR',
                'msg': f'Request failed: {str(e)}',
                'data': []
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """测试 API 连接"""
        return self._request('GET', 'account/balance')
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        return self._request('GET', 'account/balance')
    
    def get_trading_balance(self) -> Dict[str, Any]:
        """获取交易账户余额"""
        return self._request('GET', 'account/balance', params={'instType': 'SPOT'})
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取币种价格"""
        return self._request('GET', 'market/ticker', params={'instId': symbol})
    
    def place_order(self, symbol: str, side: str, order_type: str, size: str, price: Optional[str] = None) -> Dict[str, Any]:
        """下单"""
        data = {
            'instId': symbol,
            'tdMode': 'cash',
            'side': side,
            'ordType': order_type,
            'sz': size
        }
        if price:
            data['px'] = price
        
        return self._request('POST', 'trade/order', data=data)
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """获取订单历史"""
        params = {'limit': limit}
        if symbol:
            params['instId'] = symbol
        
        return self._request('GET', 'trade/orders-history', params=params)
    
    def get_popular_coins(self, limit: int = 100) -> List[str]:
        """获取热门币种列表
        
        由于OKX API没有直接提供热门币种接口，我们获取交易量最大的USDT交易对
        """
        try:
            # 获取所有USDT交易对的Ticker
            params = {'instType': 'SPOT'}
            result = self._request('GET', 'market/tickers', params=params)
            
            if result.get('code') != '0':
                return []
            
            # 筛选USDT交易对
            usdt_pairs = []
            for item in result.get('data', []):
                inst_id = item.get('instId', '')
                if inst_id.endswith('-USDT'):
                    # 计算24小时交易量（以USDT计）
                    vol_24h = float(item.get('vol24h', 0)) * float(item.get('last', 0))
                    usdt_pairs.append({
                        'symbol': inst_id,
                        'volume': vol_24h
                    })
            
            # 按交易量排序
            usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
            
            # 返回前limit个
            return [pair['symbol'] for pair in usdt_pairs[:limit]]
        
        except Exception as e:
            print(f"获取热门币种异常: {str(e)}")
            return []

# 无需API密钥的公共方法
def get_popular_coins_public(limit: int = 100) -> List[str]:
    """获取热门币种列表（公共API，无需认证）"""
    try:
        url = "https://www.okx.com/api/v5/market/tickers?instType=SPOT"
        response = requests.get(url)
        result = response.json()
        
        if result.get('code') != '0':
            return []
        
        # 筛选USDT交易对
        usdt_pairs = []
        for item in result.get('data', []):
            inst_id = item.get('instId', '')
            if inst_id.endswith('-USDT'):
                # 计算24小时交易量（以USDT计）
                vol_24h = float(item.get('vol24h', 0)) * float(item.get('last', 0))
                usdt_pairs.append({
                    'symbol': inst_id,
                    'volume': vol_24h
                })
        
        # 按交易量排序
        usdt_pairs.sort(key=lambda x: x['volume'], reverse=True)
        
        # 返回前limit个
        return [pair['symbol'] for pair in usdt_pairs[:limit]]
    
    except Exception as e:
        print(f"获取热门币种异常: {str(e)}")
        return [] 