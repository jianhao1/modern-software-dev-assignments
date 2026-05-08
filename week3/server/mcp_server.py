from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import secrets
from datetime import UTC, datetime
from typing import Any

import httpx
from mcp.server.auth.provider import AccessToken, TokenVerifier
from mcp.server.auth.settings import AuthSettings
from mcp.server.fastmcp import FastMCP


logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
logger = logging.getLogger("binance-market-mcp")

BINANCE_API_BASE = os.getenv("BINANCE_API_BASE", "https://api.binance.com")
MCP_HTTP_HOST = os.getenv("MCP_HTTP_HOST", "127.0.0.1")
MCP_HTTP_PORT = int(os.getenv("MCP_HTTP_PORT", "8000"))
MCP_HTTP_PATH = os.getenv("MCP_HTTP_PATH", "/mcp")
MCP_API_KEY = os.getenv("MCP_API_KEY")
MCP_REQUIRED_SCOPE = os.getenv("MCP_REQUIRED_SCOPE", "market:read")
MCP_AUTH_ISSUER_URL = os.getenv("MCP_AUTH_ISSUER_URL", f"http://{MCP_HTTP_HOST}:{MCP_HTTP_PORT}")
MCP_RESOURCE_URL = os.getenv(
    "MCP_RESOURCE_URL", f"http://{MCP_HTTP_HOST}:{MCP_HTTP_PORT}{MCP_HTTP_PATH}"
)
USER_AGENT = "cs146s-week3-binance-mcp/1.0"
REQUEST_TIMEOUT_SECONDS = 10.0
MAX_RETRIES = 2

SYMBOL_PATTERN = re.compile(r"^[A-Z0-9]{2,20}$")
KLINE_INTERVALS = {
    "1s",
    "1m",
    "3m",
    "5m",
    "15m",
    "30m",
    "1h",
    "2h",
    "4h",
    "6h",
    "8h",
    "12h",
    "1d",
    "3d",
    "1w",
    "1M",
}


class StaticApiKeyVerifier(TokenVerifier):
    def __init__(self, api_key: str, required_scope: str, resource_url: str) -> None:
        self.api_key = api_key
        self.required_scope = required_scope
        self.resource_url = resource_url

    async def verify_token(self, token: str) -> AccessToken | None:
        if not secrets.compare_digest(token, self.api_key):
            return None

        return AccessToken(
            token=token,
            client_id="api-key-client",
            scopes=[self.required_scope],
            resource=self.resource_url,
        )


token_verifier = None
auth_settings = None
if MCP_API_KEY:
    token_verifier = StaticApiKeyVerifier(
        api_key=MCP_API_KEY,
        required_scope=MCP_REQUIRED_SCOPE,
        resource_url=MCP_RESOURCE_URL,
    )
    auth_settings = AuthSettings(
        issuer_url=MCP_AUTH_ISSUER_URL,
        resource_server_url=MCP_RESOURCE_URL,
        required_scopes=[MCP_REQUIRED_SCOPE],
    )


mcp = FastMCP(
    "binance-market-data",
    host=MCP_HTTP_HOST,
    port=MCP_HTTP_PORT,
    streamable_http_path=MCP_HTTP_PATH,
    stateless_http=True,
    json_response=True,
    token_verifier=token_verifier,
    auth=auth_settings,
)


class BinanceAPIError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _normalize_symbol(symbol: str) -> str:
    normalized = symbol.strip().upper()
    if not SYMBOL_PATTERN.fullmatch(normalized):
        raise ValueError(
            "symbol must be 2-20 uppercase letters or digits after normalization, "
            "for example BTCUSDT"
        )
    return normalized


def _validate_limit(name: str, value: int, minimum: int, maximum: int) -> int:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")
    return value


def _validate_time_range(start_time: int | None, end_time: int | None) -> None:
    if start_time is not None and start_time < 0:
        raise ValueError("start_time must be a Unix timestamp in milliseconds")
    if end_time is not None and end_time < 0:
        raise ValueError("end_time must be a Unix timestamp in milliseconds")
    if start_time is not None and end_time is not None and start_time >= end_time:
        raise ValueError("start_time must be earlier than end_time")


def _validate_timezone(time_zone: str | None) -> str | None:
    if time_zone is None:
        return None

    value = time_zone.strip()
    if not value:
        raise ValueError("time_zone cannot be empty")

    match = re.fullmatch(r"([+-]?)(\d{1,2})(?::([0-5]\d))?", value)
    if not match:
        raise ValueError("time_zone must look like 0, 8, -1:00, or 05:45")

    sign_text, hour_text, minute_text = match.groups()
    sign = -1 if sign_text == "-" else 1
    hour = int(hour_text)
    minute = int(minute_text or "0")
    total_minutes = sign * (hour * 60 + minute)

    if total_minutes < -12 * 60 or total_minutes > 14 * 60:
        raise ValueError("time_zone must be in the range [-12:00, +14:00]")

    return value


def _to_iso8601(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).isoformat()


def _rate_limit_hint(response: httpx.Response) -> str | None:
    used_weight = response.headers.get("x-mbx-used-weight-1m") or response.headers.get(
        "X-MBX-USED-WEIGHT-1M"
    )
    if used_weight is None:
        return None

    try:
        weight = int(used_weight)
    except ValueError:
        return f"Binance reported used request weight in the last minute: {used_weight}"

    if weight >= 1000:
        return (
            "Binance reported high request weight usage in the last minute "
            f"({weight}); slow down requests to avoid rate limiting."
        )
    return f"Binance used request weight in the last minute: {weight}"


async def _binance_get(path: str, params: dict[str, Any]) -> tuple[Any, str | None]:
    url = f"{BINANCE_API_BASE.rstrip('/')}{path}"
    headers = {"Accept": "application/json", "User-Agent": USER_AGENT}

    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT_SECONDS) as client:
        last_error: Exception | None = None
        for attempt in range(MAX_RETRIES + 1):
            try:
                response = await client.get(url, params=params, headers=headers)
                if response.status_code in {418, 429} or 500 <= response.status_code < 600:
                    if attempt < MAX_RETRIES:
                        retry_after = response.headers.get("Retry-After")
                        delay = float(retry_after) if retry_after else 0.5 * (2**attempt)
                        logger.warning(
                            "Retrying Binance request after HTTP %s in %.2fs",
                            response.status_code,
                            delay,
                        )
                        await asyncio.sleep(delay)
                        continue

                if response.status_code >= 400:
                    raise BinanceAPIError(
                        _extract_binance_error(response), status_code=response.status_code
                    )

                data = response.json()
                return data, _rate_limit_hint(response)
            except (httpx.TimeoutException, httpx.NetworkError) as exc:
                last_error = exc
                if attempt < MAX_RETRIES:
                    delay = 0.5 * (2**attempt)
                    logger.warning("Retrying Binance request after network error in %.2fs", delay)
                    await asyncio.sleep(delay)
                    continue
                raise BinanceAPIError(f"Binance request failed: {exc}") from exc
            except httpx.HTTPError as exc:
                raise BinanceAPIError(f"Binance request failed: {exc}") from exc
            except json.JSONDecodeError as exc:
                raise BinanceAPIError("Binance returned a non-JSON response") from exc

        raise BinanceAPIError(f"Binance request failed: {last_error}")


def _extract_binance_error(response: httpx.Response) -> str:
    try:
        payload = response.json()
    except json.JSONDecodeError:
        return f"Binance returned HTTP {response.status_code}: {response.text[:200]}"

    code = payload.get("code")
    message = payload.get("msg") or payload.get("message") or "Unknown Binance error"
    if code is None:
        return f"Binance returned HTTP {response.status_code}: {message}"
    return f"Binance returned HTTP {response.status_code} with code {code}: {message}"


def _json_response(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2)


def _format_error(tool: str, exc: Exception) -> str:
    logger.exception("%s failed", tool)
    return _json_response({"ok": False, "tool": tool, "error": str(exc)})


def _format_kline(item: list[Any]) -> dict[str, Any]:
    return {
        "open_time": item[0],
        "open_time_iso": _to_iso8601(item[0]),
        "open": item[1],
        "high": item[2],
        "low": item[3],
        "close": item[4],
        "volume": item[5],
        "close_time": item[6],
        "close_time_iso": _to_iso8601(item[6]),
        "quote_asset_volume": item[7],
        "number_of_trades": item[8],
        "taker_buy_base_asset_volume": item[9],
        "taker_buy_quote_asset_volume": item[10],
    }


@mcp.tool()
async def get_klines(
    symbol: str,
    interval: str,
    limit: int = 10,
    start_time: int | None = None,
    end_time: int | None = None,
    time_zone: str | None = None,
) -> str:
    """Get Binance spot candlestick/K-line data.

    Args:
        symbol: Trading pair symbol, for example BTCUSDT.
        interval: K-line interval, for example 1m, 5m, 1h, 1d, or 1M.
        limit: Number of K-lines to return, 1-1000. Defaults to 10.
        start_time: Optional UTC start time in Unix milliseconds.
        end_time: Optional UTC end time in Unix milliseconds.
        time_zone: Optional interval timezone, for example 0, 8, -1:00, or 05:45.
    """
    tool = "get_klines"
    try:
        normalized_symbol = _normalize_symbol(symbol)
        if interval not in KLINE_INTERVALS:
            raise ValueError(f"interval must be one of: {', '.join(sorted(KLINE_INTERVALS))}")
        normalized_limit = _validate_limit("limit", limit, 1, 1000)
        _validate_time_range(start_time, end_time)
        normalized_time_zone = _validate_timezone(time_zone)

        params: dict[str, Any] = {
            "symbol": normalized_symbol,
            "interval": interval,
            "limit": normalized_limit,
        }
        if start_time is not None:
            params["startTime"] = start_time
        if end_time is not None:
            params["endTime"] = end_time
        if normalized_time_zone is not None:
            params["timeZone"] = normalized_time_zone

        data, rate_limit_hint = await _binance_get("/api/v3/klines", params)
        if not data:
            return _json_response(
                {
                    "ok": True,
                    "tool": tool,
                    "symbol": normalized_symbol,
                    "interval": interval,
                    "klines": [],
                    "message": "No K-line data returned for this query.",
                    "rate_limit_hint": rate_limit_hint,
                }
            )

        return _json_response(
            {
                "ok": True,
                "tool": tool,
                "symbol": normalized_symbol,
                "interval": interval,
                "limit": normalized_limit,
                "rate_limit_hint": rate_limit_hint,
                "klines": [_format_kline(item) for item in data],
            }
        )
    except Exception as exc:
        return _format_error(tool, exc)


@mcp.tool()
async def get_order_book_depth(symbol: str, limit: int = 100) -> str:
    """Get Binance spot order book depth.

    Args:
        symbol: Trading pair symbol, for example BTCUSDT.
        limit: Number of bid/ask levels to return, 1-5000. Defaults to 100.
    """
    tool = "get_order_book_depth"
    try:
        normalized_symbol = _normalize_symbol(symbol)
        normalized_limit = _validate_limit("limit", limit, 1, 5000)
        warning = None
        if normalized_limit > 1000:
            warning = (
                "Large depth limits have high Binance request weight. "
                "Use 100 or 500 for routine checks."
            )

        data, rate_limit_hint = await _binance_get(
            "/api/v3/depth", {"symbol": normalized_symbol, "limit": normalized_limit}
        )
        bids = data.get("bids", [])
        asks = data.get("asks", [])
        if not bids and not asks:
            return _json_response(
                {
                    "ok": True,
                    "tool": tool,
                    "symbol": normalized_symbol,
                    "last_update_id": data.get("lastUpdateId"),
                    "bids": [],
                    "asks": [],
                    "message": "No order book levels returned for this query.",
                    "rate_limit_hint": rate_limit_hint,
                    "warning": warning,
                }
            )

        return _json_response(
            {
                "ok": True,
                "tool": tool,
                "symbol": normalized_symbol,
                "limit": normalized_limit,
                "last_update_id": data.get("lastUpdateId"),
                "rate_limit_hint": rate_limit_hint,
                "warning": warning,
                "bids": [{"price": price, "quantity": quantity} for price, quantity in bids],
                "asks": [{"price": price, "quantity": quantity} for price, quantity in asks],
            }
        )
    except Exception as exc:
        return _format_error(tool, exc)


def run_stdio() -> None:
    mcp.run(transport="stdio")


def run_http() -> None:
    mcp.run(transport="streamable-http")
