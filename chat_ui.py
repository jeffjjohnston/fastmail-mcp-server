from __future__ import annotations

"""Simple Flask chat interface using OpenAI and the Fastmail MCP server."""

import os
from flask import Flask, request, render_template_string, session, redirect, url_for
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

BEARER_TOKEN = os.getenv("BEARER_TOKEN")
FASTMAIL_API_KEY = os.getenv("FASTMAIL_API_KEY")
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp/")

if not BEARER_TOKEN or not FASTMAIL_API_KEY:
    raise RuntimeError(
        "BEARER_TOKEN and FASTMAIL_API_KEY environment variables are required"
    )

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "replace-this-secret")

client = OpenAI()


def build_tools() -> list[dict]:
    """Return the tool configuration for the Fastmail MCP server."""
    return [
        {
            "type": "mcp",
            "server_label": "Email",
            "server_url": MCP_SERVER_URL,
            "require_approval": "never",
            "headers": {
                "Authorization": f"Bearer {BEARER_TOKEN}",
                "fastmail-api-token": FASTMAIL_API_KEY,
            },
        }
    ]


HTML_TEMPLATE = """
<!doctype html>
<title>Fastmail Chat</title>
<h1>Fastmail Chat</h1>
<form method=post>
    <input type=text name=message autofocus>
    <button type=submit>Send</button>
    <button type=submit name=clear value=1>Clear</button>
</form>
<ul>
{% for m in conversation %}
    <li><strong>{{ m.role }}:</strong> {{ m.content }}</li>
{% endfor %}
</ul>
"""


@app.route("/", methods=["GET", "POST"])
def index():
    if "conversation" not in session:
        session["conversation"] = []

    if request.method == "POST":
        if request.form.get("clear"):
            session["conversation"] = []
            return redirect(url_for("index"))

        user_message = request.form["message"]
        conversation: list[dict] = session["conversation"]
        conversation.append({"role": "user", "content": user_message})

        resp = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=conversation,
            tools=build_tools(),
        )
        assistant = resp.choices[0].message.content
        conversation.append({"role": "assistant", "content": assistant})
        session["conversation"] = conversation

    return render_template_string(HTML_TEMPLATE, conversation=session["conversation"])


if __name__ == "__main__":
    app.run(debug=True)
