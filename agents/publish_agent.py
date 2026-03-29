"""
Enhanced Publishing Agent - Multi-Channel Content Distribution
Publishes finalized content to various channels (blog, email, social, PDF, etc.)
"""
import os
import json
from datetime import datetime
from services.database import audit_db
import hashlib

class PublishingChannels:
    """Multi-channel publishing destinations"""
    
    CHANNELS = {
        "Blog": {
            "path": "published_content/blog",
            "format": "markdown",
            "template": "# {title}\n\n**Published:** {date}\n**Author:** BrandGuard AI\n\n{content}"
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


def publish_to_channel(state, channel_config):
    """Publish content to a specific channel"""
    channel = state["target_channel"]
    content = state["localization_content"]
    session_id = state["session_id"]
    topic = state["topic"]
    
    # Create output directory
    output_dir = channel_config["path"]
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_topic = topic[:30].replace(" ", "_").lower()
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
        
        # Generate public URL (simulated)
        content_hash = hashlib.md5((session_id + timestamp).encode()).hexdigest()[:8]
        url = f"https://cms.brandguard.ai/published/{channel.lower()}/{content_hash}"
        
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
    """
    Enhanced Publishing Agent - Distributes content across multiple channels
    Handles: Blog, Email, LinkedIn, Twitter, Press Releases, PDFs
    """
    print("\n" + "=" * 80)
    print("[PUBLISH] Multi-Channel Publishing Agent")
    print("=" * 80)
    
    session_id = state.get("session_id", "unknown")
    channel = state.get("target_channel", "Blog")
    content = state.get("localization_content", "")
    topic = state.get("topic", "")
    
    print(f"\n[INPUT] Publishing to: {channel}")
    print(f"   Session: {session_id}")
    print(f"   Topic: {topic[:60]}...")
    print(f"   Content Length: {len(content)} characters")
    
    if not content:
        print("[ERROR] No content to publish!")
        return {
            "published_url": "",
            "publish_results": [],
            "publish_status": "FAILED"
        }
    
    # Get channel configuration
    channel_config = PublishingChannels.get_channel_info(channel)
    
    # Publish to primary channel
    print(f"\n[STEP 1] Publishing to primary channel: {channel}")
    primary_result = publish_to_channel(state, channel_config)
    
    publish_results = []
    if primary_result:
        publish_results.append({
            "channel": channel,
            "status": "SUCCESS",
            "url": primary_result["url"],
            "filepath": primary_result.get("filepath", ""),
            "format": primary_result.get("format", ""),
            "size": primary_result.get("size", 0)
        })
        primary_url = primary_result["url"]
    else:
        primary_url = ""
    
    # Publish to secondary channels based on content type
    print(f"\n[STEP 2] Publishing to secondary channels for cross-distribution")
    secondary_channels = ["Blog", "Email"]  # Default secondary channels
    
    # Add social media if suitable
    if len(content) < 1000:
        secondary_channels.extend(["LinkedIn", "Twitter"])
    
    # Always include Press Release for official announcements
    if "announcement" in topic.lower() or "release" in topic.lower():
        secondary_channels.append("Press Release")
    
    # Remove duplicates and primary channel
    secondary_channels = list(set(secondary_channels) - {channel})
    
    for secondary in secondary_channels:
        sec_config = PublishingChannels.get_channel_info(secondary)
        sec_result = publish_to_channel(state, sec_config)
        if sec_result:
            publish_results.append({
                "channel": secondary,
                "status": "SUCCESS",
                "url": sec_result["url"],
                "filepath": sec_result.get("filepath", ""),
                "format": sec_result.get("format", ""),
                "size": sec_result.get("size", 0)
            })
    
    print(f"\n[SUMMARY] Published to {len([r for r in publish_results if r['status'] == 'SUCCESS'])} channels")
    
    # Log to audit database
    audit_db.log_event(
        session_id,
        "PublishAgent",
        "Multi-Channel Publishing",
        topic[:50],
        primary_url,
        "Success" if primary_result else "Failed",
        {
            "primary_channel": channel,
            "total_channels": len(publish_results),
            "channels": [r["channel"] for r in publish_results],
            "publish_metadata": publish_results
        }
    )
    
    print("\n" + "=" * 80)
    
    return {
        "published_url": primary_url,
        "publish_results": publish_results,
        "publish_status": "SUCCESS" if publish_results else "FAILED",
        "publish_timestamp": datetime.now().isoformat(),
        "total_channels_published": len(publish_results)
    }
