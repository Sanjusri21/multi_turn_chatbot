import re
import urllib.parse
from abc import ABC, abstractmethod
from typing import List, Optional
import httpx
from app.services.web_search_service import SearchResult, WebSearchService
from app.core.logging_config import logger

class RealtimeProvider(ABC):
    @abstractmethod
    def can_handle(self, query: str) -> bool:
        """Determines if this specialized provider can handle the query."""
        pass

    @abstractmethod
    async def fetch(self, query: str) -> List[SearchResult]:
        """Fetches structured current real-time data."""
        pass

class WeatherProvider(RealtimeProvider):
    """
    Keyless Weather Provider using Open-Meteo Geocoding & Forecast APIs.
    Returns authoritative current meteorological data.
    """
    GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
    FORECAST_URL = "https://api.open-meteo.com/v1/forecast"

    WEATHER_CODES = {
        0: "Clear sky",
        1: "Mainly clear",
        2: "Partly cloudy",
        3: "Overcast",
        45: "Foggy",
        48: "Depositing rime fog",
        51: "Light drizzle",
        53: "Moderate drizzle",
        55: "Dense drizzle",
        61: "Slight rain",
        63: "Moderate rain",
        65: "Heavy rain",
        71: "Slight snow fall",
        73: "Moderate snow fall",
        75: "Heavy snow fall",
        80: "Slight rain showers",
        81: "Moderate rain showers",
        82: "Violent rain showers",
        95: "Thunderstorm",
        96: "Thunderstorm with slight hail",
        99: "Thunderstorm with heavy hail"
    }

    def can_handle(self, query: str) -> bool:
        q = query.lower()
        patterns = [
            r"\bweather\b",
            r"\btemperature\b",
            r"\bforecast\b",
            r"\bclimate\b",
            r"\bவானிலை\b",
            r"\bவெப்பநிலை\b",
            r"\bमौसम\b",
            r"\bतापमान\b"
        ]
        return any(re.search(p, q) for p in patterns)

    def _extract_city(self, query: str) -> Optional[str]:
        # Match "weather in Coimbatore", "current temperature of Chennai", "London weather"
        q = query.strip()
        match = re.search(r"(?:in|at|of|for)\s+([A-Za-z\s]+?)(?:\s+(?:today|now|tonight|currently))?[?.]*$", q, re.IGNORECASE)
        if match:
            city = match.group(1).strip()
            # Avoid generic words
            if city.lower() not in ("the world", "india", "today", "now"):
                return city
        words = q.split()
        for w in words:
            if len(w) > 3 and w.lower() not in ("weather", "temperature", "forecast", "what", "is", "the", "in", "today", "now", "current"):
                return w
        return None

    async def fetch(self, query: str) -> List[SearchResult]:
        city = self._extract_city(query) or "Chennai"
        try:
            async with httpx.AsyncClient(timeout=8) as client:
                # 1. Geocode city
                geo_resp = await client.get(self.GEOCODING_URL, params={"name": city, "count": 1, "language": "en", "format": "json"})
                if geo_resp.status_code != 200:
                    return []
                geo_data = geo_resp.json()
                results = geo_data.get("results")
                if not results:
                    return []
                loc = results[0]
                lat = loc.get("latitude")
                lon = loc.get("longitude")
                city_name = loc.get("name", city)
                country = loc.get("country", "")

                # 2. Get current weather
                fc_resp = await client.get(
                    self.FORECAST_URL,
                    params={
                        "latitude": lat,
                        "longitude": lon,
                        "current": "temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,weather_code,wind_speed_10m",
                        "timezone": "auto"
                    }
                )
                if fc_resp.status_code != 200:
                    return []
                fc_data = fc_resp.json()
                curr = fc_data.get("current", {})
                temp = curr.get("temperature_2m")
                feels_like = curr.get("apparent_temperature")
                humidity = curr.get("relative_humidity_2m")
                wind = curr.get("wind_speed_10m")
                wcode = curr.get("weather_code", 0)
                condition = self.WEATHER_CODES.get(wcode, "Current conditions")

                snippet = (
                    f"Current weather in {city_name}, {country}: {condition}. "
                    f"Temperature: {temp}°C (feels like {feels_like}°C). "
                    f"Humidity: {humidity}%. Wind speed: {wind} km/h."
                )

                return [
                    SearchResult(
                        title=f"Live Weather Report for {city_name}, {country}",
                        url=f"https://open-meteo.com/en/docs?latitude={lat}&longitude={lon}",
                        snippet=snippet,
                        source_name="open-meteo.com",
                        relevance_score=3.5
                    )
                ]
        except Exception as e:
            logger.warning(f"WeatherProvider retrieval error: {e}")
            return []

class CryptoProvider(RealtimeProvider):
    """
    Keyless Cryptocurrency Price Provider using CoinGecko public API.
    """
    API_URL = "https://api.coingecko.com/api/v3/simple/price"
    COIN_MAP = {
        "bitcoin": "bitcoin",
        "btc": "bitcoin",
        "ethereum": "ethereum",
        "eth": "ethereum",
        "solana": "solana",
        "sol": "solana",
        "dogecoin": "dogecoin",
        "doge": "dogecoin",
        "cardano": "cardano",
        "ada": "cardano",
        "ripple": "ripple",
        "xrp": "ripple"
    }

    def can_handle(self, query: str) -> bool:
        q = query.lower()
        has_crypto_word = any(w in q for w in ["crypto", "bitcoin", "btc", "ethereum", "eth", "solana", "doge", "coin price"])
        has_price_word = any(w in q for w in ["price", "rate", "cost", "value", "worth", "விலை", "कीमत"])
        return has_crypto_word and has_price_word

    async def fetch(self, query: str) -> List[SearchResult]:
        q = query.lower()
        matched_coin = "bitcoin"
        for alias, coin_id in self.COIN_MAP.items():
            if re.search(rf"\b{alias}\b", q):
                matched_coin = coin_id
                break

        try:
            async with httpx.AsyncClient(timeout=8) as client:
                resp = await client.get(
                    self.API_URL,
                    params={
                        "ids": matched_coin,
                        "vs_currencies": "usd,inr",
                        "include_24hr_change": "true"
                    }
                )
                if resp.status_code == 200:
                    data = resp.json().get(matched_coin, {})
                    usd = data.get("usd")
                    inr = data.get("inr")
                    change_24h = data.get("usd_24h_change")
                    coin_name = matched_coin.capitalize()
                    change_str = f" ({change_24h:+.2f}% in 24h)" if change_24h is not None else ""
                    snippet = (
                        f"Current {coin_name} price: ${usd:,.2f} USD (₹{inr:,.2f} INR){change_str}. "
                        f"Data verified via CoinGecko real-time market tracker."
                    )
                    return [
                        SearchResult(
                            title=f"{coin_name} Live Price & Market Data",
                            url=f"https://www.coingecko.com/en/coins/{matched_coin}",
                            snippet=snippet,
                            source_name="coingecko.com",
                            relevance_score=3.0
                        )
                    ]
        except Exception as e:
            logger.warning(f"CryptoProvider retrieval error: {e}")
        return []

class StockProvider(RealtimeProvider):
    """
    Extensible Stock Market Provider interface.
    Falls back gracefully to WebSearchService if market API keys are unconfigured.
    """
    def can_handle(self, query: str) -> bool:
        q = query.lower()
        has_stock = any(w in q for w in ["stock", "shares", "nasdaq", "nyse", "bse", "nse", "market cap"])
        has_price = any(w in q for w in ["price", "trading", "current", "today"])
        return has_stock and has_price

    async def fetch(self, query: str) -> List[SearchResult]:
        # Ready for AlphaVantage / Finnhub / Yahoo Finance API integration
        # Returns empty list so fallback web search handles it seamlessly
        return []

class RealtimeService:
    """
    Coordinates structured current-data providers (weather, crypto, stocks)
    and falls back to general WebSearchService.
    """
    def __init__(self, search_service: Optional[WebSearchService] = None):
        self.search_service = search_service or WebSearchService()
        self.specialized_providers: List[RealtimeProvider] = [
            WeatherProvider(),
            CryptoProvider(),
            StockProvider()
        ]

    async def get_realtime_data(self, query: str, category: Optional[str] = None) -> List[SearchResult]:
        """
        Retrieves real-time information:
        1. Attempts specialized structured API provider if query matches
        2. Falls back to WebSearchService
        """
        clean_query = query.strip()
        if not clean_query:
            return []

        # 1. Specialized providers
        for provider in self.specialized_providers:
            if provider.can_handle(clean_query):
                logger.info(f"[RealtimeAPI] Matched specialized provider: {provider.__class__.__name__}")
                spec_results = await provider.fetch(clean_query)
                if spec_results:
                    return spec_results

        # 2. General web search fallback
        return await self.search_service.search(clean_query)
