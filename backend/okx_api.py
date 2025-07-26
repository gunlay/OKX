import requests
import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Any, Optional

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
        """获取 ISO 格式的时间戳"""
        return str(int(time.time()))
    
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
        url = f"{self.base_url}{endpoint}"
        timestamp = self._get_timestamp()
        
        # 准备请求头
        headers = {
            'OK-ACCESS-KEY': self.api_key,
            'OK-ACCESS-SIGN': self._sign(timestamp, method, endpoint, json.dumps(data) if data else ''),
            'OK-ACCESS-TIMESTAMP': timestamp,
            'OK-ACCESS-PASSPHRASE': self.passphrase,
            'Content-Type': 'application/json'
        }
        
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
        return self._request('GET', '/account/balance')
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        return self._request('GET', '/account/balance')
    
    def get_trading_balance(self) -> Dict[str, Any]:
        """获取交易账户余额"""
        return self._request('GET', '/account/balance', params={'instType': 'SPOT'})
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取币种价格"""
        return self._request('GET', '/market/ticker', params={'instId': symbol})
    
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
        
        return self._request('POST', '/trade/order', data=data)
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """获取订单历史"""
        params = {'limit': limit}
        if symbol:
            params['instId'] = symbol
        
        return self._request('GET', '/trade/orders-history', params=params) 