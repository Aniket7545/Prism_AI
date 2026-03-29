"""
Integration helpers for external systems (e.g., n8n, social APIs).
These functions let us push publishing and engagement tasks to automation
platforms without hardcoding vendor SDKs here. If env vars are not set,
we fall back to local behavior.
"""
from __future__ import annotations
import os
import json
import requests
import time
from typing import Any, Dict, Optional

# Env flags (default off to avoid external dependency stalls)
ENABLE_N8N_PUBLISH = os.getenv("ENABLE_N8N_PUBLISH", "false").lower() == "true"
ENABLE_N8N_ENGAGEMENT = os.getenv("ENABLE_N8N_ENGAGEMENT", "false").lower() == "true"
ENABLE_N8N_SLACK = os.getenv("ENABLE_N8N_SLACK", "false").lower() == "true"

ENABLE_DISCORD = os.getenv("ENABLE_DISCORD", "false").lower() == "true"
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "")

N8N_PUBLISH_WEBHOOK = os.getenv("N8N_PUBLISH_WEBHOOK", "")
N8N_ENGAGEMENT_WEBHOOK = os.getenv("N8N_ENGAGEMENT_WEBHOOK", "")
N8N_SLACK_WEBHOOK = os.getenv("N8N_SLACK_WEBHOOK", "")

def _call_webhook(url: str, payload: Dict[str, Any], timeout: int = 8) -> Dict[str, Any]:
    """Post payload to webhook and parse JSON safely (short timeout to avoid blocking publish)."""
    if not url:
        return {"status": "disabled", "reason": "no_url"}
    started = time.time()
    try:
        resp = requests.post(url, json=payload, timeout=timeout)
        elapsed = round(time.time() - started, 3)
        resp.raise_for_status()
        try:
            data = resp.json()
        except Exception:
            data = {"raw": resp.text}
        print(f"   [n8n] webhook ok in {elapsed}s -> {resp.status_code}")
        return {"status": "success", "data": data, "http_status": resp.status_code, "elapsed": elapsed}
    except Exception as exc:
        elapsed = round(time.time() - started, 3)
        print(f"   [n8n] webhook error after {elapsed}s: {exc}")
        return {"status": "error", "error": str(exc), "elapsed": elapsed}


def publish_via_n8n(session_id: str, channel: str, content: str, topic: str, metadata: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Send publish request to n8n if enabled."""
    if not ENABLE_N8N_PUBLISH:
        print("   [n8n] publish disabled (ENABLE_N8N_PUBLISH=false)")
        return None
    payload = {
        "session_id": session_id,
        "channel": channel,
        "topic": topic,
        "content": content,
        "text": content,  # for Slack/Text-based nodes
        "summary": topic,
        "metadata": metadata or {},
    }
    return _call_webhook(N8N_PUBLISH_WEBHOOK, payload)


def fetch_engagement_via_n8n(session_id: str, publish_results: Optional[Any] = None, channel: str = "") -> Optional[Dict[str, Any]]:
    """Fetch engagement metrics via n8n if enabled."""
    if not ENABLE_N8N_ENGAGEMENT:
        print("   [n8n] engagement disabled (ENABLE_N8N_ENGAGEMENT=false)")
        return None
    payload = {
        "session_id": session_id,
        "channel": channel,
        "publish_results": publish_results or [],
    }
    return _call_webhook(N8N_ENGAGEMENT_WEBHOOK, payload)


def notify_slack_via_n8n(session_id: str, summary: str, details: Optional[Dict[str, Any]] = None) -> Optional[Dict[str, Any]]:
    """Send a Slack notification via n8n webhook."""
    if not ENABLE_N8N_SLACK:
        print("   [n8n] slack disabled (ENABLE_N8N_SLACK=false)")
        return None
    payload = {
        "session_id": session_id,
        "summary": summary,
        "details": details or {},
        "text": details.get("content_preview", "") if isinstance(details, dict) else "",
    }
    return _call_webhook(N8N_SLACK_WEBHOOK, payload)


def post_to_discord(session_id: str, topic: str, content: str, url: str = "") -> Dict[str, Any]:
    """Send a message to Discord via webhook using embeds for better formatting."""
    if not ENABLE_DISCORD:
        return {"status": "disabled", "reason": "ENABLE_DISCORD=false"}
    if not DISCORD_WEBHOOK:
        return {"status": "error", "error": "Missing DISCORD_WEBHOOK"}
    
    # Extract title from content if it starts with markdown heading (# or ##)
    lines = content.split('\n')
    
    # Check for proper markdown heading (# or ##)
    is_heading = lines and lines[0].startswith(('#', '- **'))
    if is_heading and lines[0].startswith('#'):
        # Extract title from markdown heading, removing # characters
        title = lines[0].replace('#', '').strip()
        body = '\n'.join(lines[1:]).strip()
    elif is_heading and lines[0].startswith('- **'):
        # Handle bullet point with bold (sometimes used as title)
        title = lines[0].replace('- ', '').replace('**', '').strip()
        body = '\n'.join(lines[1:]).strip()
    else:
        # No proper heading found, use topic and keep full content
        title = topic
        body = content
    
    # Truncate description to 4096 characters (Discord embed limit)
    description = body[:4096] if len(body) > 4096 else body
    if len(body) > 4096:
        description = description.rsplit('\n', 1)[0] + "\n\n[Content truncated - see full article for complete text]"
    
    # Use Discord embed for better formatting and larger content support
    payload = {
        "username": "Prism AI",
        "embeds": [
            {
                "title": title,
                "description": description,
                "color": 3447003,  # Blue
                "url": url if url else None,
                "footer": {
                    "text": f"Published by Prism AI | Session: {session_id[:8]}"
                }
            }
        ]
    }
    
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=8)
        if 200 <= resp.status_code < 300:
            return {"status": "success", "http_status": resp.status_code}
        return {"status": "error", "http_status": resp.status_code, "error": resp.text}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
