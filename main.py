#!/usr/bin/env python3
"""
Pump.fun Token Listener System
A comprehensive monitoring and analysis system for Pump.fun tokens
"""

import asyncio
import json
import logging
import sys
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, asdict
from enum import Enum
import aiohttp
from solders.pubkey import Pubkey
from solders.rpc.responses import GetProgramAccountsResp
import base64

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pump_monitor.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class TokenStatus(Enum):
    """Token status enumeration"""
    LAUNCHED = "launched"
    TRADING = "trading"
    GRADUATED = "graduated"
    RUGGED = "rugged"
    DEAD = "dead"


@dataclass
class TokenMetrics:
    """Token metrics data class"""
    token_address: str
    name: str
    symbol: str
    creator: str
    initial_supply: float
    current_supply: float
    holders_count: int
    liquidity: float
    market_cap: float
    price_usd: float
    price_change_24h: float
    volume_24h: float
    status: TokenStatus
    created_at: datetime
    last_updated: datetime
    transaction_count: int
    buy_count: int
    sell_count: int


@dataclass
class PricePoint:
    """Price data point"""
    timestamp: datetime
    price: float
    volume: float
    liquidity: float


class PumpFunAPI:
    """Pump.fun API client"""
    
    BASE_URL = "https://api.pump.fun"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self.session: Optional[aiohttp.ClientSession] = None
        self.rate_limit_remaining = 1000
        self.rate_limit_reset = None
        
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.close()
    
    async def get_token_info(self, token_address: str) -> Optional[Dict]:
        """Fetch token information"""
        try:
            endpoint = f"{self.BASE_URL}/tokens/{token_address}"
            headers = self._get_headers()
            
            async with self.session.get(endpoint, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Failed to fetch token info: {resp.status}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching token info: {e}")
            return None
    
    async def get_recent_tokens(self, limit: int = 100) -> List[Dict]:
        """Fetch recently launched tokens"""
        try:
            endpoint = f"{self.BASE_URL}/tokens/recent"
            headers = self._get_headers()
            params = {"limit": limit}
            
            async with self.session.get(endpoint, headers=headers, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    logger.warning(f"Failed to fetch recent tokens: {resp.status}")
                    return []
        except Exception as e:
            logger.error(f"Error fetching recent tokens: {e}")
            return []
    
    async def get_token_price(self, token_address: str) -> Optional[float]:
        """Fetch current token price"""
        try:
            endpoint = f"{self.BASE_URL}/tokens/{token_address}/price"
            headers = self._get_headers()
            
            async with self.session.get(endpoint, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return data.get('price')
                else:
                    return None
        except Exception as e:
            logger.error(f"Error fetching token price: {e}")
            return None
    
    async def get_token_holders(self, token_address: str) -> List[Dict]:
        """Fetch token holders"""
        try:
            endpoint = f"{self.BASE_URL}/tokens/{token_address}/holders"
            headers = self._get_headers()
            
            async with self.session.get(endpoint, headers=headers, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return []
        except Exception as e:
            logger.error(f"Error fetching token holders: {e}")
            return []
    
    async def get_token_trades(self, token_address: str, limit: int = 50) -> List[Dict]:
        """Fetch recent trades for a token"""
        try:
            endpoint = f"{self.BASE_URL}/tokens/{token_address}/trades"
            headers = self._get_headers()
            params = {"limit": limit}
            
            async with self.session.get(endpoint, headers=headers, params=params, timeout=10) as resp:
                if resp.status == 200:
                    return await resp.json()
                else:
                    return []
        except Exception as e:
            logger.error(f"Error fetching token trades: {e}")
            return []
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers"""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers


class TokenAnalyzer:
    """Analyze token metrics and detect patterns"""
    
    def __init__(self):
        self.price_history: Dict[str, List[PricePoint]] = {}
        
    def analyze_token(self, token_data: Dict) -> TokenMetrics:
        """Analyze token data and generate metrics"""
        try:
            # Extract data with safe defaults
            token_address = token_data.get('address', 'unknown')
            name = token_data.get('name', 'Unknown Token')
            symbol = token_data.get('symbol', 'UNKNOWN')
            creator = token_data.get('creator', 'unknown')
            
            # Numerical fields
            initial_supply = float(token_data.get('initial_supply', 0))
            current_supply = float(token_data.get('current_supply', initial_supply))
            holders_count = int(token_data.get('holders', 0))
            liquidity = float(token_data.get('liquidity', 0))
            market_cap = float(token_data.get('market_cap', 0))
            price_usd = float(token_data.get('price', 0))
            price_change_24h = float(token_data.get('price_change_24h', 0))
            volume_24h = float(token_data.get('volume_24h', 0))
            transaction_count = int(token_data.get('transactions', 0))
            buy_count = int(token_data.get('buys', 0))
            sell_count = int(token_data.get('sells', 0))
            
            # Determine status
            status = self._determine_status(token_data)
            
            # Timestamps
            created_at = datetime.fromisoformat(token_data.get('created_at', datetime.utcnow().isoformat()))
            last_updated = datetime.utcnow()
            
            return TokenMetrics(
                token_address=token_address,
                name=name,
                symbol=symbol,
                creator=creator,
                initial_supply=initial_supply,
                current_supply=current_supply,
                holders_count=holders_count,
                liquidity=liquidity,
                market_cap=market_cap,
                price_usd=price_usd,
                price_change_24h=price_change_24h,
                volume_24h=volume_24h,
                status=status,
                created_at=created_at,
                last_updated=last_updated,
                transaction_count=transaction_count,
                buy_count=buy_count,
                sell_count=sell_count
            )
        except Exception as e:
            logger.error(f"Error analyzing token: {e}")
            raise
    
    def _determine_status(self, token_data: Dict) -> TokenStatus:
        """Determine token status based on metrics"""
        liquidity = float(token_data.get('liquidity', 0))
        market_cap = float(token_data.get('market_cap', 0))
        price = float(token_data.get('price', 0))
        
        # Check for rug pull indicators
        if token_data.get('is_rugged', False):
            return TokenStatus.RUGGED
        
        # Check if graduated (reached certain threshold)
        if token_data.get('is_graduated', False):
            return TokenStatus.GRADUATED
        
        # Check if trading actively
        if liquidity > 0 and market_cap > 1000:
            return TokenStatus.TRADING
        
        # Recently launched
        if token_data.get('is_launched', True):
            return TokenStatus.LAUNCHED
        
        return TokenStatus.DEAD
    
    def detect_pump_pattern(self, token_address: str) -> bool:
        """Detect pump pattern in price history"""
        if token_address not in self.price_history:
            return False
        
        history = self.price_history[token_address]
        if len(history) < 3:
            return False
        
        # Simple pump detection: rapid price increase
        recent_prices = [p.price for p in history[-10:]]
        if len(recent_prices) < 3:
            return False
        
        first = recent_prices[0]
        peak = max(recent_prices)
        
        if first > 0:
            increase_percent = ((peak - first) / first) * 100
            return increase_percent > 50  # 50% pump threshold
        
        return False
    
    def detect_dump_pattern(self, token_address: str) -> bool:
        """Detect dump pattern in price history"""
        if token_address not in self.price_history:
            return False
        
        history = self.price_history[token_address]
        if len(history) < 3:
            return False
        
        # Simple dump detection: rapid price decrease
        recent_prices = [p.price for p in history[-10:]]
        if len(recent_prices) < 3:
            return False
        
        peak = max(recent_prices)
        current = recent_prices[-1]
        
        if peak > 0:
            decrease_percent = ((peak - current) / peak) * 100
            return decrease_percent > 50  # 50% dump threshold
        
        return False
    
    def add_price_point(self, token_address: str, price: float, volume: float, liquidity: float):
        """Add price data point to history"""
        if token_address not in self.price_history:
            self.price_history[token_address] = []
        
        self.price_history[token_address].append(
            PricePoint(
                timestamp=datetime.utcnow(),
                price=price,
                volume=volume,
                liquidity=liquidity
            )
        )
        
        # Keep only last 1000 points per token to manage memory
        if len(self.price_history[token_address]) > 1000:
            self.price_history[token_address] = self.price_history[token_address][-1000:]


class TokenListener:
    """Main token listener system"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api = None
        self.api_key = api_key
        self.analyzer = TokenAnalyzer()
        self.monitored_tokens: Dict[str, TokenMetrics] = {}
        self.is_running = False
        
    async def start(self):
        """Start the listener"""
        logger.info("Starting Pump.fun Token Listener...")
        self.api = PumpFunAPI(api_key=self.api_key)
        await self.api.__aenter__()
        self.is_running = True
        
        try:
            await asyncio.gather(
                self._listen_for_new_tokens(),
                self._monitor_existing_tokens(),
                self._analyze_patterns()
            )
        except KeyboardInterrupt:
            logger.info("Listener interrupted by user")
        except Exception as e:
            logger.error(f"Listener error: {e}")
        finally:
            await self.stop()
    
    async def stop(self):
        """Stop the listener"""
        logger.info("Stopping Token Listener...")
        self.is_running = False
        if self.api:
            await self.api.__aexit__(None, None, None)
    
    async def _listen_for_new_tokens(self):
        """Listen for newly launched tokens"""
        logger.info("Starting new token listener...")
        
        while self.is_running:
            try:
                recent_tokens = await self.api.get_recent_tokens(limit=50)
                
                for token_data in recent_tokens:
                    token_address = token_data.get('address')
                    
                    if token_address and token_address not in self.monitored_tokens:
                        try:
                            metrics = self.analyzer.analyze_token(token_data)
                            self.monitored_tokens[token_address] = metrics
                            
                            logger.info(
                                f"New token detected: {metrics.name} ({metrics.symbol}) - "
                                f"Price: ${metrics.price_usd:.8f}, "
                                f"Market Cap: ${metrics.market_cap:,.2f}"
                            )
                            
                            await self._on_new_token(metrics)
                        except Exception as e:
                            logger.error(f"Error processing new token: {e}")
                
                # Check every 10 seconds
                await asyncio.sleep(10)
                
            except Exception as e:
                logger.error(f"Error in new token listener: {e}")
                await asyncio.sleep(30)
    
    async def _monitor_existing_tokens(self):
        """Monitor existing tokens"""
        logger.info("Starting existing token monitor...")
        
        while self.is_running:
            try:
                if not self.monitored_tokens:
                    await asyncio.sleep(5)
                    continue
                
                # Monitor each token concurrently
                tasks = [
                    self._update_token_metrics(token_address)
                    for token_address in list(self.monitored_tokens.keys())[:50]  # Limit concurrent requests
                ]
                
                await asyncio.gather(*tasks, return_exceptions=True)
                
                # Update every 30 seconds
                await asyncio.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in token monitor: {e}")
                await asyncio.sleep(30)
    
    async def _update_token_metrics(self, token_address: str):
        """Update metrics for a specific token"""
        try:
            token_data = await self.api.get_token_info(token_address)
            if token_data:
                metrics = self.analyzer.analyze_token(token_data)
                self.monitored_tokens[token_address] = metrics
                
                # Add price point to history
                self.analyzer.add_price_point(
                    token_address,
                    metrics.price_usd,
                    metrics.volume_24h,
                    metrics.liquidity
                )
                
        except Exception as e:
            logger.error(f"Error updating token metrics for {token_address}: {e}")
    
    async def _analyze_patterns(self):
        """Analyze patterns in monitored tokens"""
        logger.info("Starting pattern analyzer...")
        
        while self.is_running:
            try:
                for token_address, metrics in self.monitored_tokens.items():
                    # Check for pump pattern
                    if self.analyzer.detect_pump_pattern(token_address):
                        logger.warning(f"PUMP DETECTED: {metrics.name} ({metrics.symbol})")
                        await self._on_pump_detected(metrics)
                    
                    # Check for dump pattern
                    if self.analyzer.detect_dump_pattern(token_address):
                        logger.warning(f"DUMP DETECTED: {metrics.name} ({metrics.symbol})")
                        await self._on_dump_detected(metrics)
                
                # Analyze every 60 seconds
                await asyncio.sleep(60)
                
            except Exception as e:
                logger.error(f"Error in pattern analyzer: {e}")
                await asyncio.sleep(60)
    
    async def _on_new_token(self, metrics: TokenMetrics):
        """Handle new token detection"""
        logger.info(f"New token callback: {metrics.name}")
        # Implement custom logic here
    
    async def _on_pump_detected(self, metrics: TokenMetrics):
        """Handle pump pattern detection"""
        logger.warning(f"Pump detected callback: {metrics.name}")
        # Implement custom logic here
    
    async def _on_dump_detected(self, metrics: TokenMetrics):
        """Handle dump pattern detection"""
        logger.warning(f"Dump detected callback: {metrics.name}")
        # Implement custom logic here
    
    def get_monitored_tokens(self) -> List[TokenMetrics]:
        """Get list of monitored tokens"""
        return list(self.monitored_tokens.values())
    
    def get_token_metrics(self, token_address: str) -> Optional[TokenMetrics]:
        """Get metrics for specific token"""
        return self.monitored_tokens.get(token_address)
    
    def get_tokens_by_status(self, status: TokenStatus) -> List[TokenMetrics]:
        """Get tokens by status"""
        return [
            metrics for metrics in self.monitored_tokens.values()
            if metrics.status == status
        ]
    
    def export_metrics(self, filepath: str):
        """Export all metrics to JSON"""
        try:
            data = {
                'timestamp': datetime.utcnow().isoformat(),
                'total_tokens': len(self.monitored_tokens),
                'tokens': [asdict(metrics) for metrics in self.monitored_tokens.values()]
            }
            
            # Convert datetime and enum objects
            data['tokens'] = [
                {
                    **token,
                    'created_at': token['created_at'].isoformat(),
                    'last_updated': token['last_updated'].isoformat(),
                    'status': token['status'].value
                }
                for token in data['tokens']
            ]
            
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            
            logger.info(f"Metrics exported to {filepath}")
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")


async def main():
    """Main entry point"""
    logger.info("Initializing Pump.fun Token Listener System")
    
    # Initialize listener (provide API key if available)
    listener = TokenListener(api_key=None)
    
    try:
        # Start listening
        await listener.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
        await listener.stop()


if __name__ == "__main__":
    asyncio.run(main())
