# Week 3 Binance Market Data MCP Server

This project implements a custom Model Context Protocol (MCP) server that wraps the public Binance Spot REST API. It exposes market data tools for candlesticks and order book depth.

The server supports:

- Local MCP over STDIO, suitable for Claude Desktop or another local MCP client.
- Remote-style MCP over streamable HTTP, suitable for MCP-aware agent runtimes.
- Optional bearer-token authentication for HTTP mode with `MCP_API_KEY`.

## Prerequisites

- Python 3.10 or newer.
- Network access to `https://api.binance.com`.
- For local client integration: Claude Desktop or another MCP client that can launch STDIO servers.

Binance may restrict access from some regions or networks. If `api.binance.com` is unavailable from your environment, set `BINANCE_API_BASE` to a compatible Binance API base URL available to you.

## Environment Setup

From the repository root:

```bash
cd week3
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Optional environment variables:

| Name | Default | Description |
| --- | --- | --- |
| `BINANCE_API_BASE` | `https://api.binance.com` | Binance API base URL. |
| `LOG_LEVEL` | `INFO` | Python logging level. Logs go to stderr, which is safe for STDIO MCP. |
| `MCP_HTTP_HOST` | `127.0.0.1` | Host used by HTTP transport. |
| `MCP_HTTP_PORT` | `8000` | Port used by HTTP transport. |
| `MCP_HTTP_PATH` | `/mcp` | Streamable HTTP MCP path. |
| `MCP_API_KEY` | unset | Enables HTTP bearer-token auth when set. |

## Run Locally With STDIO

From the repository root:

```bash
week3/.venv/bin/python week3/server/main.py
```

This starts the MCP server on STDIO. It is intended to be launched by an MCP client rather than used directly in a terminal.

You can also run the module from inside `week3`:

```bash
source .venv/bin/activate
python server/main.py --transport stdio
```

## Configure Claude Desktop

Add an entry like this to your Claude Desktop MCP config file. Replace the paths if your repository is in a different location.

macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`  
Windows: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "binance-market-data": {
      "command": "/home/jianhao/modern-software-dev-assignments/week3/.venv/bin/python",
      "args": [
        "/home/jianhao/modern-software-dev-assignments/week3/server/main.py"
      ],
      "env": {
        "BINANCE_API_BASE": "https://api.binance.com",
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Restart Claude Desktop after editing the config. In a chat, ask for Binance market data, for example:

```text
Get the last 5 one-hour BTCUSDT candles.
```

Claude should discover and call `get_klines`.

## Run With HTTP Transport

HTTP mode is useful for remote deployment or local testing with an MCP-aware agent runtime.

```bash
cd week3
source .venv/bin/activate
python server/main.py --transport http
```

The default endpoint is:

```text
http://127.0.0.1:8000/mcp
```

To bind on all interfaces or change the port:

```bash
MCP_HTTP_HOST=0.0.0.0 MCP_HTTP_PORT=8080 python server/main.py --transport http
```

### HTTP Auth

Set `MCP_API_KEY` to require clients to send a bearer token:

```bash
MCP_API_KEY=dev-secret-key python server/main.py --transport http
```

Clients must include:

```text
Authorization: Bearer dev-secret-key
```

Example remote agent runtime configuration shape:

```json
{
  "mcp_servers": {
    "binance-market-data": {
      "url": "https://your-host.example.com/mcp",
      "headers": {
        "Authorization": "Bearer ${MCP_API_KEY}"
      }
    }
  }
}
```

Exact field names vary by agent runtime. The important values are the streamable HTTP URL and the bearer token header when auth is enabled.

## Tool Reference

All tools return formatted JSON strings. Successful responses include `"ok": true`; validation errors, Binance HTTP errors, timeouts, and network failures return `"ok": false` with an `"error"` message. Binance request-weight information is returned as `rate_limit_hint` when Binance includes it in response headers.

### `get_klines`

Gets Binance Spot candlestick/K-line data from `/api/v3/klines`.

Parameters:

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `symbol` | string | yes | none | Trading pair symbol. Input is trimmed and uppercased. Must be 2-20 letters or digits, for example `BTCUSDT`. |
| `interval` | string | yes | none | K-line interval. Allowed values: `1s`, `1m`, `3m`, `5m`, `15m`, `30m`, `1h`, `2h`, `4h`, `6h`, `8h`, `12h`, `1d`, `3d`, `1w`, `1M`. |
| `limit` | integer | no | `10` | Number of K-lines to return. Must be between `1` and `1000`. |
| `start_time` | integer or null | no | `null` | UTC start time as Unix milliseconds. |
| `end_time` | integer or null | no | `null` | UTC end time as Unix milliseconds. Must be after `start_time` when both are provided. |
| `time_zone` | string or null | no | `null` | Optional interval timezone, for example `0`, `8`, `-1:00`, or `05:45`. Must be between `-12:00` and `+14:00`. |

Example input:

```json
{
  "symbol": "BTCUSDT",
  "interval": "1h",
  "limit": 2
}
```

Example output:

```json
{
  "ok": true,
  "tool": "get_klines",
  "symbol": "BTCUSDT",
  "interval": "1h",
  "limit": 2,
  "rate_limit_hint": "Binance used request weight in the last minute: 1",
  "klines": [
    {
      "open_time": 1715097600000,
      "open_time_iso": "2024-05-07T16:00:00+00:00",
      "open": "63792.01000000",
      "high": "64000.00000000",
      "low": "63610.00000000",
      "close": "63850.00000000",
      "volume": "1234.56789000",
      "close_time": 1715101199999,
      "close_time_iso": "2024-05-07T16:59:59.999000+00:00",
      "quote_asset_volume": "78900000.00000000",
      "number_of_trades": 100000,
      "taker_buy_base_asset_volume": "600.00000000",
      "taker_buy_quote_asset_volume": "38300000.00000000"
    }
  ]
}
```

Expected behavior:

- Returns up to `limit` candles in Binance order.
- Converts `symbol` to uppercase before calling Binance.
- Returns an empty `klines` list with a message if Binance returns no candle data.
- Returns `"ok": false` for invalid symbols, unsupported intervals, invalid limits, invalid time ranges, invalid time zones, HTTP errors, or network failures.

Example validation error:

```json
{
  "ok": false,
  "tool": "get_klines",
  "error": "interval must be one of: 1M, 1d, 1h, 1m, 1s, 1w, 2h, 3d, 3m, 4h, 5m, 6h, 8h, 12h, 15m, 30m"
}
```

### `get_order_book_depth`

Gets Binance Spot order book depth from `/api/v3/depth`.

Parameters:

| Name | Type | Required | Default | Description |
| --- | --- | --- | --- | --- |
| `symbol` | string | yes | none | Trading pair symbol. Input is trimmed and uppercased. Must be 2-20 letters or digits, for example `ETHUSDT`. |
| `limit` | integer | no | `100` | Number of bid and ask levels to return. Must be between `1` and `5000`. Large limits have higher Binance request weight. |

Example input:

```json
{
  "symbol": "ETHUSDT",
  "limit": 5
}
```

Example output:

```json
{
  "ok": true,
  "tool": "get_order_book_depth",
  "symbol": "ETHUSDT",
  "limit": 5,
  "last_update_id": 123456789,
  "rate_limit_hint": "Binance used request weight in the last minute: 1",
  "warning": null,
  "bids": [
    {
      "price": "3050.12000000",
      "quantity": "4.25000000"
    }
  ],
  "asks": [
    {
      "price": "3050.13000000",
      "quantity": "1.80000000"
    }
  ]
}
```

Expected behavior:

- Returns current bid and ask levels for the requested symbol.
- Converts `symbol` to uppercase before calling Binance.
- Includes `last_update_id` from Binance.
- Adds a warning when `limit` is greater than `1000` because large depth requests use more Binance request weight.
- Returns empty `bids` and `asks` lists with a message if Binance returns no levels.
- Returns `"ok": false` for invalid symbols, invalid limits, HTTP errors, or network failures.

Example high-limit response shape:

```json
{
  "ok": true,
  "tool": "get_order_book_depth",
  "symbol": "BTCUSDT",
  "limit": 5000,
  "last_update_id": 123456789,
  "rate_limit_hint": "Binance used request weight in the last minute: 250",
  "warning": "Large depth limits have high Binance request weight. Use 100 or 500 for routine checks.",
  "bids": [],
  "asks": []
}
```

## Resilience And Error Handling

- Requests use a 10-second timeout.
- HTTP 429, HTTP 418, and 5xx responses are retried with short backoff up to two times.
- Binance error payloads are converted into user-facing messages.
- JSON decode failures, network errors, and timeouts return structured tool errors.
- Input validation runs before requests are sent to Binance.
