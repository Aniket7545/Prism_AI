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
    """Send a message to Discord via webhook."""
    if not ENABLE_DISCORD:
        return {"status": "disabled", "reason": "ENABLE_DISCORD=false"}
    if not DISCORD_WEBHOOK:
        return {"status": "error", "error": "Missing DISCORD_WEBHOOK"}
    content_preview = content[:400] + ("..." if len(content) > 400 else "")
    payload = {
        "content": f"**{topic}**\n\n{content_preview}" + (f"\n\n📎 Full article: {url}" if url else ""),
        "username": "BrandGuard AI",
    }
    try:
        resp = requests.post(DISCORD_WEBHOOK, json=payload, timeout=8)
        if 200 <= resp.status_code < 300:
            return {"status": "success", "http_status": resp.status_code}
        return {"status": "error", "http_status": resp.status_code, "error": resp.text}
    except Exception as exc:
        return {"status": "error", "error": str(exc)}
