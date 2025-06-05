# fastmail-mcp-server

A basic MCP server that provides access to a Fastmail inbox.

## Prerequisites

- **Python 3.11+**. The project has been developed with Python 3.12.
- **Environment variables**
  - `BEARER_TOKEN` &ndash; static token required to authorize HTTP requests to the server. The server defaults to `default_token` if not set.

A Fastmail API token is also required for each request. See [Fastmail's API documentation](https://www.fastmail.help/hc/en-us/articles/360058752314) for instructions on creating a token (Settings → Password & Security → **API Tokens**).

## Installation

Install the dependencies using `pip`:

```bash
pip install -r requirements.txt
```

## Running the server

Export a bearer token and start the server:

```bash
export BEARER_TOKEN="my-secret-token"
python server.py
```

By default the server listens on `http://127.0.0.1:8000/mcp`.

## Example usage

The server exposes MCP tools. You can interact with them using the `fastmcp` client. The example below lists inbox emails:

```python
import asyncio
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client

async def main():
    transport = StreamableHttpTransport(
        "http://127.0.0.1:8000/mcp",
        headers={"fastmail-api-token": "<FASTMAIL_API_TOKEN>"},
        auth="Bearer my-secret-token",
    )
    client = Client(transport)
    async with client:
        result = await client.call_tool("list_inbox_emails")
        print(result)

asyncio.run(main())
```

Replace `<FASTMAIL_API_TOKEN>` with your personal Fastmail API token.
