"""
行情服务
负责处理市场数据获取、行情分析等相关业务逻辑
"""
import json
import logging
from typing import Dict, List, Optional
from sqlalchemy.orm import Session
from models import UserConfig
from services.config_service import ConfigService

logger = logging.getLogger(__name__)

class MarketService:
    """行情服务类"""
    
    def __init__(self, session_local, config_service: ConfigService, create_okx_client_func):
        """
        初始化行情服务
        
        Args:
            session_local: SQLAlchemy会话工厂
            config_service: 配置服务实例
            create_okx_client_func: OKX客户端创建函数
        """
        self.SessionLocal = session_local
        self.config_service = config_service
        self.create_okx_client = create_okx_client_func
    
    def get_configured_coins_market_data(self) -> Dict:
        """
        获取配置币种的行情数据
        
        Returns:
            包含行情数据的字典
        """
        try:
            # 获取配置的币种列表
            selected_coins = self.config_service.get_coin_config()
            if not selected_coins:
                return {"code": "ERROR", "msg": "未配置交易币种", "data": []}
            
            # 处理币种格式：如果是 BTC-USDT 格式，转换为 BTC 格式
            processed_coins = []
            for coin in selected_coins:
                if '-USDT' in coin:
                    processed_coins.append(coin.replace('-USDT', ''))
                else:
                    processed_coins.append(coin)
            selected_coins = processed_coins
            
            # 获取API配置
            api_config = self.config_service.get_decrypted_api_config()
            if not api_config:
                return {"code": "ERROR", "msg": "未配置API密钥", "data": []}
            
            # 创建OKX客户端
            client = self.create_okx_client(
                api_config['api_key'], 
                api_config['secret_key'], 
                api_config['passphrase']
            )
            
            # 获取所有行情数据
            tickers_result = client.get_tickers('SPOT')
            
            if tickers_result.get('code') != '0':
                logger.error(f"获取行情数据失败: {tickers_result.get('msg', '未知错误')}")
                return {"code": "ERROR", "msg": f"获取行情数据失败: {tickers_result.get('msg', '未知错误')}", "data": []}
            
            # 筛选配置的币种
            market_data = []
            for ticker in tickers_result.get('data', []):
                inst_id = ticker.get('instId', '')
                
                # 检查是否为配置的币种
                for coin in selected_coins:
                    if inst_id == f"{coin}-USDT":
                        try:
                            # 解析价格数据
                            last_price = float(ticker.get('last', 0))
                            change_24h = float(ticker.get('sodUtc0', 0))
                            volume_24h = float(ticker.get('volCcy24h', 0))
                            
                            # 计算涨跌幅
                            if last_price > 0 and change_24h != 0:
                                change_percent = ((last_price - change_24h) / change_24h) * 100
                            else:
                                change_percent = 0
                            
                            market_data.append({
                                "symbol": inst_id,
                                "currency": coin,
                                "price": last_price,
                                "change24h": change_percent,
                                "volume24h": volume_24h,
                                "high24h": float(ticker.get('high24h', 0)),
                                "low24h": float(ticker.get('low24h', 0)),
                                "timestamp": ticker.get('ts', '')
                            })
                            
                        except (ValueError, TypeError) as e:
                            logger.warning(f"解析 {inst_id} 行情数据失败: {e}")
                            continue
                        break
            
            logger.info(f"获取配置币种行情数据成功: {len(market_data)}个币种")
            return {"code": "0", "msg": "success", "data": market_data}
            
        except Exception as e:
            logger.error(f"获取配置币种行情数据异常: {str(e)}")
            return {"code": "ERROR", "msg": f"获取行情数据异常: {str(e)}", "data": []}
    
    def get_ticker_info(self, symbol: str) -> Dict:
        """
        获取单个币种的行情信息
        
        Args:
            symbol: 交易对符号，如 BTC-USDT
            
        Returns:
            行情信息字典
        """
        try:
            # 获取API配置
            api_config = self.config_service.get_decrypted_api_config()
            if not api_config:
                return {"code": "ERROR", "msg": "未配置API密钥", "data": None}
            
            # 创建OKX客户端
            client = self.create_okx_client(
                api_config['api_key'], 
                api_config['secret_key'], 
                api_config['passphrase']
            )
            
            # 获取单个币种行情
            ticker_result = client.get_ticker(symbol)
            
            if ticker_result.get('code') != '0':
                logger.error(f"获取 {symbol} 行情失败: {ticker_result.get('msg', '未知错误')}")
                return {"code": "ERROR", "msg": f"获取行情失败: {ticker_result.get('msg', '未知错误')}", "data": None}
            
            ticker_data = ticker_result.get('data', [])
            if not ticker_data:
                return {"code": "ERROR", "msg": "未找到行情数据", "data": None}
            
            ticker = ticker_data[0]
            
            # 解析行情数据
            try:
                last_price = float(ticker.get('last', 0))
                change_24h = float(ticker.get('sodUtc0', 0))
                volume_24h = float(ticker.get('volCcy24h', 0))
                
                # 计算涨跌幅
                if last_price > 0 and change_24h != 0:
                    change_percent = ((last_price - change_24h) / change_24h) * 100
                else:
                    change_percent = 0
                
                result = {
                    "symbol": ticker.get('instId', symbol),
                    "price": last_price,
                    "change24h": change_percent,
                    "volume24h": volume_24h,
                    "high24h": float(ticker.get('high24h', 0)),
                    "low24h": float(ticker.get('low24h', 0)),
                    "timestamp": ticker.get('ts', '')
                }
                
                logger.info(f"获取 {symbol} 行情成功")
                return {"code": "0", "msg": "success", "data": result}
                
            except (ValueError, TypeError) as e:
                logger.error(f"解析 {symbol} 行情数据失败: {e}")
                return {"code": "ERROR", "msg": f"数据解析失败: {str(e)}", "data": None}
            
        except Exception as e:
            logger.error(f"获取 {symbol} 行情异常: {str(e)}")
            return {"code": "ERROR", "msg": f"获取行情异常: {str(e)}", "data": None}
    
    def get_market_summary(self) -> Dict:
        """
        获取市场概览数据
        
        Returns:
            市场概览信息
        """
        try:
            # 获取配置币种的行情数据
            market_data_result = self.get_configured_coins_market_data()
            
            if market_data_result.get('code') != '0':
                return {
                    "totalCoins": 0,
                    "gainers": 0,
                    "losers": 0,
                    "avgChange": 0,
                    "totalVolume": 0,
                    "error": market_data_result.get('msg', '获取数据失败')
                }
            
            market_data = market_data_result.get('data', [])
            
            if not market_data:
                return {
                    "totalCoins": 0,
                    "gainers": 0,
                    "losers": 0,
                    "avgChange": 0,
                    "totalVolume": 0,
                    "error": "无行情数据"
                }
            
            # 统计市场数据
            total_coins = len(market_data)
            gainers = sum(1 for coin in market_data if coin.get('change24h', 0) > 0)
            losers = sum(1 for coin in market_data if coin.get('change24h', 0) < 0)
            
            # 计算平均涨跌幅
            total_change = sum(coin.get('change24h', 0) for coin in market_data)
            avg_change = total_change / total_coins if total_coins > 0 else 0
            
            # 计算总交易量
            total_volume = sum(coin.get('volume24h', 0) for coin in market_data)
            
            result = {
                "totalCoins": total_coins,
                "gainers": gainers,
                "losers": losers,
                "avgChange": round(avg_change, 2),
                "totalVolume": round(total_volume, 2)
            }
            
            logger.info(f"获取市场概览成功: {result}")
            return result
            
        except Exception as e:
            logger.error(f"获取市场概览异常: {str(e)}")
            return {
                "totalCoins": 0,
                "gainers": 0,
                "losers": 0,
                "avgChange": 0,
                "totalVolume": 0,
                "error": f"获取市场概览异常: {str(e)}"
            }
    
    def search_coins(self, keyword: str, limit: int = 20) -> List[Dict]:
        """
        搜索币种
        
        Args:
            keyword: 搜索关键词
            limit: 返回数量限制
            
        Returns:
            匹配的币种列表
        """
        try:
            # 获取API配置
            api_config = self.config_service.get_decrypted_api_config()
            if not api_config:
                logger.warning("未配置API密钥，无法搜索币种")
                return []
            
            # 创建OKX客户端
            client = self.create_okx_client(
                api_config['api_key'], 
                api_config['secret_key'], 
                api_config['passphrase']
            )
            
            # 获取所有现货交易对
            instruments_result = client.get_instruments('SPOT')
            
            if instruments_result.get('code') != '0':
                logger.error(f"获取交易对列表失败: {instruments_result.get('msg', '未知错误')}")
                return []
            
            instruments = instruments_result.get('data', [])
            
            # 搜索匹配的币种
            keyword_upper = keyword.upper()
            matched_coins = []
            
            for instrument in instruments:
                inst_id = instrument.get('instId', '')
                base_ccy = instrument.get('baseCcy', '')
                quote_ccy = instrument.get('quoteCcy', '')
                
                # 只搜索USDT交易对
                if quote_ccy == 'USDT' and (
                    keyword_upper in base_ccy or 
                    keyword_upper in inst_id
                ):
                    matched_coins.append({
                        "symbol": inst_id,
                        "baseCurrency": base_ccy,
                        "quoteCurrency": quote_ccy,
                        "status": instrument.get('state', 'unknown')
                    })
                    
                    if len(matched_coins) >= limit:
                        break
            
            logger.info(f"搜索币种 '{keyword}' 找到 {len(matched_coins)} 个结果")
            return matched_coins
            
        except Exception as e:
            logger.error(f"搜索币种异常: {str(e)}")
            return []