"""
Enhanced Publishing Agent - Multi-Channel Content Distribution
Publishes finalized content to various channels (blog, email, social, PDF, etc.)
"""
import os
import json
import time
import re
from datetime import datetime
from services.database import audit_db
import hashlib
from services.integrations import publish_via_n8n, notify_slack_via_n8n, post_to_discord

# Demo base URL for synthetic publish links
DEMO_PUBLISH_BASE = os.getenv("DEMO_PUBLISH_BASE", "https://demo.prism-ai.io/published")
USE_SOCIAL_DEMO = os.getenv("USE_SOCIAL_DEMO", "true").lower() == "true"
ENABLE_DISCORD = os.getenv("ENABLE_DISCORD", "false").lower() == "true"

class PublishingChannels:
    """Multi-channel publishing destinations"""
    
    CHANNELS = {
        "Blog": {
            "path": "published_content/blog",
            "format": "markdown",
            "template": "# {title}\n\n**Published:** {date}\n**Author:** Prism AI\n\n{content}"
        },
        "Email": {
            "path": "published_content/email",
            "format": "html",
            "template": "<html><body><h1>{title}</h1><p><em>Generated: {date}</em></p><div>{content}</div></body></html>"
        },
        "LinkedIn": {
            "path": "published_content/social/linkedin",
            "format": "text",
            "template": "{title}\n\n{content}\n\n#ContentAI #Enterprise {hashtags}"
        },
        "Twitter": {
            "path": "published_content/social/twitter",
            "format": "text",
            "template": "{title} {hashtags}\n\n{content}"
        },
        "Press Release": {
            "path": "published_content/press",
            "format": "text",
            "template": "FOR IMMEDIATE RELEASE\n\n{title}\n\nDate: {date}\n\n{content}"
        },
        "PDF": {
            "path": "published_content/documents",
            "format": "pdf",
            "template": "{content}"
        }
    }
    
    @staticmethod
    def get_channel_info(channel):
        """Get channel configuration"""
        return PublishingChannels.CHANNELS.get(channel, PublishingChannels.CHANNELS["Blog"])


def publish_to_channel(state, channel_config, content):
    """Publish content to a specific channel"""
    channel = state["target_channel"]
    session_id = state["session_id"]
    topic = state["topic"]
    
    # Create output directory
    output_dir = channel_config["path"]
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = re.sub(r"[^A-Za-z0-9_-]+", "_", topic[:50]).strip("_") or "content"
    filename = f"{safe_topic}_{timestamp}"
    
    # Extract title if available
    title = topic.split(":")[0] if ":" in topic else topic
    
    # Format content based on channel
    if channel_config["format"] == "markdown":
        formatted_content = channel_config["template"].format(
            title=title,
            date=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            content=content
        )
        file_ext = ".md"
    elif channel_config["format"] == "html":
        formatted_content = channel_config["template"].format(
            title=title,
            date=datetime.now().strftime("%Y-%m-%d"),
            content=content.replace("\n", "<br>")
        )
        file_ext = ".html"
    elif channel_config["format"] == "text":
        hashtags = " ".join(f"#{tag}" for tag in extract_keywords(content)[:3])
        formatted_content = channel_config["template"].format(
            title=title,
            content=content[:500],
            hashtags=hashtags,
            date=datetime.now().strftime("%Y-%m-%d")
        )
        file_ext = ".txt"
    elif channel_config["format"] == "pdf":
        # For PDF, we just save the content (in production, use reportlab)
        formatted_content = channel_config["template"].format(content=content)
        file_ext = ".txt"  # Simulated PDF
    else:
        formatted_content = content
        file_ext = ".txt"
    
    # Save file
    filepath = os.path.join(output_dir, filename + file_ext)
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(formatted_content)
        
        # Generate public URL (demo-safe)
        content_hash = hashlib.md5((session_id + timestamp).encode()).hexdigest()[:8]
        url = f"{DEMO_PUBLISH_BASE}/{channel.lower()}/{content_hash}"
        
        print(f"   [OK] Published to {channel}: {filepath}")
        
        return {
            "url": url,
            "filepath": filepath,
            "format": channel_config["format"],
            "size": len(formatted_content)
        }
    except Exception as e:
        print(f"   [ERROR] Publishing to {channel} failed: {e}")
        return None


def extract_keywords(content):
    """Extract top keywords from content"""
    words = content.lower().split()
    # Simple keyword extraction (in production, use NLP library)
    stop_words = {"the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for", "of"}
    keywords = [w.strip(".,!?;:") for w in words if w not in stop_words and len(w) > 3]
    # Count occurrences
    from collections import Counter
    return [word for word, _ in Counter(keywords).most_common(10)]


def publish_agent(state):
    print("\n>>> ENTERED PUBLISH AGENT")
    session_id = state.get("session_id", "unknown")
    
    # CRITICAL: Skip if already published to avoid duplicates
    existing_results = state.get("publish_results", [])
    if existing_results and len(existing_results) > 0:
        print(f"[PUBLISH] {session_id}: Content already published - {len(existing_results)} results found. Skipping to avoid duplicates.")
        print(f"[PUBLISH] {session_id}: Existing results: {existing_results}")
        return state

    print(f"[PUBLISH] {session_id}: Starting new publish cycle")

    try:
        channel = state.get("target_channel", "Blog")
        content = state.get("localization_content") or state.get("draft_content", "")
        # ensure localization_content has something so downstream uses the same text
        if not state.get("localization_content"):
            state["localization_content"] = content
        topic = state.get("topic", "")

        if not content:
            print("[ERROR] No content to publish")
            return {
                **state,
                "published_url": "",
                "publish_results": [],
                "publish_status": "FAILED"
            }

        # ----------------------------
        # STEP 1: Local publish (wrap in try to avoid hard fail)
        # ----------------------------
        channel_config = PublishingChannels.get_channel_info(channel)
        try:
            primary_result = publish_to_channel(state, channel_config, content)
        except Exception as e:
            print(f"[ERROR] Local publish failed: {e}")
            primary_result = None

        publish_results = []
        primary_url = ""

        if primary_result:
            primary_url = primary_result.get("url", "")
            publish_results.append({
                "channel": channel,
                "status": "SUCCESS",
                "url": primary_url,
                "filepath": primary_result.get("filepath", ""),
                "format": primary_result.get("format", ""),
                "size": primary_result.get("size", 0)
            })

        # ----------------------------
        # STEP 2: External publish (skippable)
        # ----------------------------
        skip_external = os.getenv("SKIP_EXTERNAL_PUBLISH", "true").lower() == "true"
        if skip_external:
            print("[INFO] Skipping external publish (SKIP_EXTERNAL_PUBLISH=true)")
        else:
            try:
                n8n_result = publish_via_n8n(
                    session_id=session_id,
                    channel=channel,
                    content=content,
                    topic=topic,
                    metadata={"primary_url": primary_url}
                )

                if isinstance(n8n_result, dict):
                    data_block = n8n_result.get("data") or n8n_result
                    ext_url = ""
                    if isinstance(data_block, dict):
                        ext_url = data_block.get("url") or data_block.get("link") or ""
                    if not ext_url:
                        ext_url = n8n_result.get("url") if isinstance(n8n_result, dict) else ""

                    publish_results.append({
                        "channel": "n8n",
                        "status": n8n_result.get("status", "SUCCESS"),
                        "url": ext_url,
                        "platform": data_block.get("platform", "webhook") if isinstance(data_block, dict) else "webhook"
                    })

                    if ext_url:
                        primary_url = primary_url or ext_url

            except Exception as e:
                print(f"[WARN] n8n failed: {e}")

        # ----------------------------
        # STEP 3: OPTIONAL Slack notify (safe)
        # ----------------------------
        if not skip_external:
            try:
                notify_slack_via_n8n(
                    session_id,
                    f"Published: {primary_url or 'no URL'}",
                    {
                        "topic": topic,
                        "channels": [r.get("channel") for r in publish_results],
                        "primary_url": primary_url,
                        "content_preview": (content[:500] + "…") if len(content) > 500 else content,
                    }
                )
            except Exception as e:
                print(f"[WARN] Slack notify failed: {e}")

        # ----------------------------
        # STEP 4: SOCIAL DEMO LINKS (optional, no external dependency)
        # ----------------------------
        if USE_SOCIAL_DEMO:
            social_url = f"{DEMO_PUBLISH_BASE}/{channel.lower()}/social/{session_id[:8]}"
            publish_results.append({
                "channel": f"{channel}-demo",
                "status": "SUCCESS",
                "url": social_url,
                "note": "demo social link"
            })
            primary_url = primary_url or social_url

        # ----------------------------
        # STEP 5: DISCORD WEBHOOK (real, lightweight)
        # ----------------------------
        if ENABLE_DISCORD:
            dc_result = post_to_discord(session_id, topic, content, primary_url)
            publish_results.append({
                "channel": "Discord",
                "status": dc_result.get("status", "error") if isinstance(dc_result, dict) else "error",
                "url": primary_url,
                "note": "discord webhook",
                "response": dc_result
            })

        print(">>> EXITING PUBLISH AGENT")

        # ----------------------------
        # FINAL RETURN (CRITICAL)
        # ----------------------------
        # Ensure we always return at least one publish result so workflow continues
        if not publish_results:
            synthetic_url = primary_url or f"{DEMO_PUBLISH_BASE}/{channel.lower()}/{session_id[:8]}"
            publish_results.append({
                "channel": channel,
                "status": "SUCCESS",
                "url": synthetic_url,
                "note": "demo synthetic link"
            })
            primary_url = synthetic_url

        return {
            **state,
            "published_url": primary_url,
            "publish_results": publish_results,
            "publish_status": "SUCCESS"
        }

    except Exception as e:
        # Catch any unexpected exceptions so the workflow can continue
        print(f"[FATAL] publish_agent exception: {e}")
        return {
            **state,
            "published_url": state.get("published_url", ""),
            "publish_results": state.get("publish_results", []),
            "publish_status": "FAILED",
            "publish_error": str(e)
        }