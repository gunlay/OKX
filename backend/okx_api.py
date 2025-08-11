import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import hmac
import hashlib
import base64
import json
import time
from typing import Dict, Any, Optional, List
from datetime import datetime, timezone
import threading

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
        
        # 创建会话和连接池
        self.session = requests.Session()
        
        # 配置重试策略
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        # 配置HTTP适配器
        adapter = HTTPAdapter(
            pool_connections=10,
            pool_maxsize=20,
            max_retries=retry_strategy
        )
        
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # 设置默认超时
        self.timeout = 30
        
        # 请求缓存
        self._cache = {}
        self._cache_lock = threading.Lock()
        self._cache_ttl = 60  # 缓存60秒
    
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
    
    def _get_cache_key(self, method: str, endpoint: str, params: Optional[Dict] = None) -> str:
        """生成缓存键"""
        key_parts = [method, endpoint]
        if params:
            key_parts.append(str(sorted(params.items())))
        return "|".join(key_parts)
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """从缓存获取数据"""
        with self._cache_lock:
            if cache_key in self._cache:
                cached_data, timestamp = self._cache[cache_key]
                if time.time() - timestamp < self._cache_ttl:
                    return cached_data
                else:
                    # 缓存过期，删除
                    del self._cache[cache_key]
        return None
    
    def _set_cache(self, cache_key: str, data: Dict[str, Any]) -> None:
        """设置缓存"""
        with self._cache_lock:
            self._cache[cache_key] = (data, time.time())
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict] = None, data: Optional[Dict] = None, use_cache: bool = True) -> Dict[str, Any]:
        """发送请求"""
        # 确保endpoint不以斜杠开头，避免URL中出现双斜杠
        if endpoint.startswith('/'):
            endpoint = endpoint[1:]
        
        # 对于GET请求，尝试从缓存获取
        cache_key = None
        if method == 'GET' and use_cache:
            cache_key = self._get_cache_key(method, endpoint, params)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                return cached_result
            
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

        try:
            if method == 'GET':
                response = self.session.get(url, headers=headers, params=params, timeout=self.timeout)
            elif method == 'POST':
                response = self.session.post(url, headers=headers, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            response.raise_for_status()
            result = response.json()
            
            # 对于成功的GET请求，缓存结果
            if method == 'GET' and use_cache and result.get('code') == '0':
                self._set_cache(cache_key, result)
            
            return result

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
        # 不传递instType参数，获取所有余额
        return self._request('GET', 'account/balance')
    
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
    
    def get_order_detail(self, order_id: str) -> Dict[str, Any]:
        """获取订单详情"""
        params = {'ordId': order_id}
        return self._request('GET', 'trade/order', params=params)

    def get_order_fills(self, order_id: str) -> Dict[str, Any]:
        """获取订单成交明细"""
        params = {'ordId': order_id}
        return self._request('GET', 'trade/fills', params=params)
        
    def get_bills_details(self, inst_type: str = 'SPOT', begin_time: Optional[str] = None, end_time: Optional[str] = None) -> Dict[str, Any]:
        """获取账单流水详情（最近7天）"""
        params = {'instType': inst_type}
        if begin_time:
            params['begin'] = begin_time
        if end_time:
            params['end'] = end_time
        
        return self._request('GET', 'account/bills', params=params)
    
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