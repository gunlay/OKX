import requests
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone
import hmac
import hashlib
import base64

logger = logging.getLogger("dca-service")

class OKXProxyClient:
    """OKX代理客户端，通过AWS服务器转发请求"""
    
    def __init__(self, api_key: str, secret_key: str, passphrase: str, proxy_base_url: str = None):
        import os
        self.api_key = api_key
        self.secret_key = secret_key
        self.passphrase = passphrase
        
        # 从环境变量获取代理地址，如果没有则使用默认值
        if proxy_base_url is None:
            proxy_base_url = os.getenv('PROXY_BASE_URL', 'http://13.158.74.102:8000')
        
        self.proxy_base_url = proxy_base_url.rstrip('/')
        self.timeout = 30
    
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
    
    def _proxy_request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None) -> Dict[str, Any]:
        """通过代理服务器发送请求"""
        try:
            # 构建代理请求的数据
            proxy_data = {
                'method': method,
                'endpoint': endpoint,
                'params': params or {},
                'data': data or {},
                'api_key': self.api_key,
                'secret_key': self.secret_key,
                'passphrase': self.passphrase
            }
            
            # 发送到代理服务器
            proxy_url = f"{self.proxy_base_url}/api/proxy/okx"
            response = requests.post(proxy_url, json=proxy_data, timeout=self.timeout)
            response.raise_for_status()
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"代理请求失败: {str(e)}")
            return {
                'code': 'ERROR',
                'msg': f'Proxy request failed: {str(e)}',
                'data': []
            }
    
    def test_connection(self) -> Dict[str, Any]:
        """测试 API 连接"""
        return self._proxy_request('GET', 'account/balance')
    
    def get_account_balance(self) -> Dict[str, Any]:
        """获取账户余额"""
        return self._proxy_request('GET', 'account/balance')
    
    def get_trading_balance(self) -> Dict[str, Any]:
        """获取交易账户余额"""
        return self._proxy_request('GET', 'account/balance')
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取币种价格"""
        return self._proxy_request('GET', 'market/ticker', params={'instId': symbol})
    
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
        
        return self._proxy_request('POST', 'trade/order', data=data)
    
    def get_order_history(self, symbol: Optional[str] = None, limit: int = 100) -> Dict[str, Any]:
        """获取订单历史"""
        params = {'limit': limit}
        if symbol:
            params['instId'] = symbol
        
        return self._proxy_request('GET', 'trade/orders-history', params=params)
    
    def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """获取订单详情"""
        params = {'ordId': order_id}
        return self._proxy_request('GET', 'trade/order', params=params)

    def get_order_fills(self, order_id: str) -> Dict[str, Any]:
        """获取订单成交明细"""
        params = {'ordId': order_id}
        return self._proxy_request('GET', 'trade/fills', params=params)
        
    def get_bills_details(self, inst_type: str = 'SPOT', begin_time: Optional[str] = None, end_time: Optional[str] = None) -> Dict[str, Any]:
        """获取账单流水详情（最近7天）"""
        params = {'instType': inst_type}
        if begin_time:
            params['begin'] = begin_time
        if end_time:
            params['end'] = end_time
        
        return self._proxy_request('GET', 'account/bills', params=params)
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None, use_cache: bool = True) -> Dict[str, Any]:
        """兼容原有接口的请求方法"""
        return self._proxy_request(method, endpoint, params, data)