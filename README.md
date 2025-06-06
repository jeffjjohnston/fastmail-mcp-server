# fastmail-mcp-server

A basic MCP server that provides access to a Fastmail inbox, built with [FastMCP](https://gofastmcp.com) and [jmapc](https://github.com/smkent/jmapc).

## Prerequisites

- **Python 3.12+**. The project has been developed with Python 3.12.
- **Environment variables**
  - `BEARER_TOKEN`: A static token required to authorize HTTP requests to the server.

Along with the bearer token, a Fastmail API token must also be provided by MCP clients. See [Fastmail's API documentation](https://www.fastmail.com/dev/) for instructions on creating a token (Settings -> Privacy & Security -> **Connected apps & API tokens**).

## Installation

Clone the repo, then install the dependencies in a virtual environment:

```bash
git clone https://github.com/jeffjjohnston/fastmail-mcp-server.git
cd fastmail-mcp-server
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Tools

The server implements the following tools:

  - `list_inbox_emails`: Lists the emails in the Inbox (id, sender, subject, and date)
  - `get_email_content`: Retrieves the content of an email given an id. HTML content will be converted to text using [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/)

## Running the server

Export a bearer token and start the server:

```bash
export BEARER_TOKEN="my-secret-token"
python server.py
```

By default the server listens on `http://127.0.0.1:8000/mcp/`.

## Example usage (FastMCP client)

The server exposes MCP tools. You can interact with them using the `fastmcp` client. The example below lists inbox emails:

```python
import asyncio
from fastmcp.client.transports import StreamableHttpTransport
from fastmcp import Client

BEARER_TOKEN = "my-secret-token"
FASTMAIL_API_TOKEN = "<FASTMAIL_API_TOKEN>"

async def main():
    transport = StreamableHttpTransport(
        "http://127.0.0.1:8000/mcp/",
        headers={"fastmail-api-token": FASTMAIL_API_TOKEN},
        auth=f"Bearer {BEARER_TOKEN}",
    )
    client = Client(transport)
    async with client:
        result = await client.call_tool("list_inbox_emails")
        print(result)

asyncio.run(main())
```

Replace `<FASTMAIL_API_TOKEN>` with your personal Fastmail API token.

## Example usage (OpenAI)

Your server needs to be accessible from the Internet to use it with OpenAI's Remote MCP capabilities. A quick way to enable this for testing is to use Cloudflare's `cloudflared` tool to build a tunnel.

```bash
cloudflared tunnel --url http://127.0.0.1:8000
```

You will get back an HTTPS URL endpoint and can use it as the MCP server in an OpenAI API request (with `/mcp/` appended):

```python
from openai import OpenAI

BEARER_TOKEN = "my-secret-token"
FASTMAIL_API_TOKEN = "<FASTMAIL_API_TOKEN>"

# an OPENAI_API_KEY environment variable is required
client = OpenAI()

resp = client.responses.create(
    model="gpt-4o-mini",
    tools=[
        {
            "type": "mcp",
            "server_label": "Email",
            "server_url": "https://random-words-generated-here.trycloudflare.com/mcp/",
            "require_approval": "never",
            "headers": {
                "Authorization": f"Bearer {BEARER_TOKEN}",
                "fastmail-api-token": FASTMAIL_API_TOKEN,
            },
        },
    ],
    input="Summarize the newest message in my inbox.",
    instructions="Respond without formatting.",
)

print(resp.output_text)
```