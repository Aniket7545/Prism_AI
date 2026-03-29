# agents/analytics_agent.py
"""
Analytics Agent: Tracks engagement metrics, analyzes content performance, and provides insights.
- Collects engagement data from channels
- Analyzes patterns and trends
- Generates performance recommendations
- Tracks KPIs and ROI
"""

from services.database import audit_db
from services.integrations import fetch_engagement_via_n8n
from datetime import datetime
import random  # Mock data for now
import json

def analytics_agent(state):
    """
    Analyze content performance and generate insights.
    """
    print("\n" + "="*60)
    print("📊 ANALYTICS AGENT - Performance Analysis & Insights")
    print("="*60)
    
    session_id = state.get("session_id", "unknown")
    channel = state.get("target_channel", "")
    content = state.get("draft_content", "")
    
    print(f"📈 Analyzing: Session={session_id}, Channel={channel}")
    
    # Try fetching real engagement via n8n; fallback to simulation
    publish_results = state.get("publish_results", [])
    n8n_engagement = fetch_engagement_via_n8n(session_id, publish_results, channel)
    if n8n_engagement and n8n_engagement.get("status") == "success":
        engagement_payload = n8n_engagement.get("data", {})
        engagement_data = engagement_payload.get("engagement", engagement_payload)
        print(f"   ✓ Engagement data (n8n): {engagement_data}")
    else:
        engagement_data = simulate_engagement_collection(session_id, channel, content)
        print(f"   ✓ Engagement data (simulated): {engagement_data['views']} views, {engagement_data['engagements']} engagements")
    
    # Analyze performance
    analysis = analyze_performance(engagement_data, content)
    print(f"   ✓ Performance score: {analysis['performance_score']}/100")
    
    # Generate insights
    insights = generate_insights(engagement_data, analysis, content)
    print(f"   ✓ Generated {len(insights['recommendations'])} recommendations")
    
    # Calculate metrics
    metrics = calculate_metrics(session_id, engagement_data, analysis)
    print(f"   ✓ Calculated metrics: {list(metrics.keys())}")
    
    # Log to database
    audit_db.log_event(
        session_id,
        "AnalyticsAgent",
        "Analyze Performance",
        f"Channel: {channel}",
        f"Performance Score: {analysis['performance_score']}, Recommendations: {len(insights['recommendations'])}",
        "Success",
        {
            "engagement": engagement_data,
            "analysis": analysis,
            "insights": insights
        }
    )
    
    # Save metrics
    for metric_name, metric_value in metrics.items():
        audit_db.log_metric(session_id, metric_name, metric_value, {"channel": channel})
    
    # Return updated state merged with previous state to avoid dropping keys
    return {
        **state,
        "engagement_metrics": engagement_data,
        "performance_analysis": analysis,
        "insights": insights,
        "audit_log": state.get("audit_log", []) + [{
            "timestamp": datetime.now().isoformat(),
            "agent": "AnalyticsAgent",
            "action": "Analyze content performance",
            "status": "Success"
        }]
    }


def simulate_engagement_collection(session_id: str, channel: str, content: str) -> dict:
    """
    Simulate collecting engagement data from channel.
    In production: Call actual channel APIs (LinkedIn, Email, etc.)
    """
    
    # Base metrics depend on channel type
    channel_base_metrics = {
        "LinkedIn": {"views": 500, "engagements": 50, "shares": 15},
        "Blog": {"views": 2000, "engagements": 200, "shares": 50},
        "Email": {"views": 300, "engagements": 60, "shares": 5},
        "Press Release": {"views": 1000, "engagements": 100, "shares": 30},
        "Twitter": {"views": 800, "engagements": 120, "shares": 80}
    }
    
    base = channel_base_metrics.get(channel, {"views": 500, "engagements": 50, "shares": 10})
    
    # Add variance based on content length and keywords
    content_quality_factor = min(len(content) / 500, 1.5)  # Longer content might perform better
    keyword_factor = 1.0 + (content.count('opportunity') * 0.1)  # Positive sentiment boost
    
    multiplier = content_quality_factor * keyword_factor
    
    return {
        "views": max(100, int(base["views"] * multiplier)),
        "engagements": max(10, int(base["engagements"] * multiplier)),
        "shares": max(1, int(base["shares"] * multiplier)),
        "click_rate": round(random.uniform(0.02, 0.15), 3),
        "sentiment_score": round(random.uniform(0.6, 1.0), 2),
        "reach": max(500, int(base["views"] * multiplier * random.uniform(1, 3))),
        "impressions": max(1000, int(base["views"] * multiplier * random.uniform(2, 5))),
        "collection_time": datetime.now().isoformat()
    }


def analyze_performance(engagement_data: dict, content: str) -> dict:
    """
    Analyze engagement data and provide detailed performance metrics.
    """
    views = engagement_data.get("views", 0)
    engagements = engagement_data.get("engagements", 0)
    shares = engagement_data.get("shares", 0)
    
    # Calculate engagement rate
    engagement_rate = (engagements / max(views, 1)) * 100
    share_rate = (shares / max(views, 1)) * 100
    
    # Determine performance tier
    if engagement_rate > 10:
        tier = "Excellent"
        score = 90
    elif engagement_rate > 5:
        tier = "Good"
        score = 75
    elif engagement_rate > 2:
        tier = "Average"
        score = 60
    else:
        tier = "Below Average"
        score = 40
    
    # Content quality assessment
    content_quality = assess_content_quality(content)
    if content_quality["readability"] > 70:
        score += 10
    
    return {
        "performance_score": min(100, score),
        "performance_tier": tier,
        "engagement_rate": round(engagement_rate, 2),
        "share_rate": round(share_rate, 2),
        "sentiment_alignment": engagement_data.get("sentiment_score", 0.7),
        "content_quality": content_quality,
        "trending_potential": "High" if engagement_rate > 8 else "Medium" if engagement_rate > 3 else "Low"
    }


def assess_content_quality(content: str) -> dict:
    """Assess content quality metrics."""
    words = content.split()
    sentences = [s for s in content.split('.') if s.strip()]
    
    word_count = len(words)
    avg_word_length = sum(len(w) for w in words) / max(word_count, 1)
    avg_sentence_length = word_count / max(len(sentences), 1)
    
    # Readability scoring
    readability = 206.835 - 1.015 * avg_sentence_length - 84.6 * (avg_word_length / 5)
    readability = max(0, min(100, readability))
    
    return {
        "word_count": word_count,
        "sentence_count": len(sentences),
        "avg_sentence_length": round(avg_sentence_length, 1),
        "avg_word_length": round(avg_word_length, 1),
        "readability": round(readability, 1),
        "has_structure": len([s for s in content.split('\n') if s.strip()]) > 2,
        "keyword_density": calculate_keyword_density(content)
    }


def calculate_keyword_density(content: str) -> float:
    """Calculate keyword density."""
    words = set(content.lower().split())
    important_words = {w for w in words if len(w) > 4}
    
    return round(len(important_words) / max(len(words), 1) * 100, 2)


def generate_insights(engagement_data: dict, analysis: dict, content: str) -> dict:
    """Generate actionable insights and recommendations."""
    recommendations = []
    warnings = []
    opportunities = []
    
    # Calculate engagement rate if not present
    engagement_rate = engagement_data.get("engagement_rate", 0)
    if not engagement_rate and "views" in engagement_data and "engagements" in engagement_data:
        engagement_rate = (engagement_data.get("engagements", 0) / max(engagement_data.get("views", 1), 1)) * 100
    
    # Recommendations based on engagement
    if engagement_rate < 3:
        recommendations.append("Low engagement rate - consider more engaging headlines or CTAs")
        recommendations.append("Add more value-driven content or case studies")
    
    if engagement_data.get("sentiment_score", 0.5) < 0.6:
        warnings.append("Sentiment score is lower than optimal - review tone")
    
    # Readability insights
    quality = analysis["content_quality"]
    if quality["readability"] < 50:
        recommendations.append("Simplify sentence structure - current readability is difficult")
    
    if quality["avg_sentence_length"] > 25:
        recommendations.append("Break down long sentences for better readability")
    
    # Opportunity insights
    if analysis["performance_score"] > 80:
        opportunities.append("Content performed exceptionally - consider repurposing across channels")
    
    if engagement_data.get("share_rate", 0) > 5:
        opportunities.append("High share rate detected - content is highly shareable")
    
    # Trending insights
    if analysis["trending_potential"] == "High":
        opportunities.append("Content has potential to trend - increase promotion")
    
    return {
        "recommendations": recommendations,
        "warnings": warnings,
        "opportunities": opportunities,
        "next_iteration_suggestions": [
            f"Try similar content structure next time",
            f"Focus on audience segment: high earners" if "investment" in content.lower() else "Maintain current tone"
        ]
    }


def calculate_metrics(session_id: str, engagement_data: dict, analysis: dict) -> dict:
    """Calculate comprehensive metrics."""
    views = engagement_data.get("views", 0)
    engagements = engagement_data.get("engagements", 0)
    
    # Estimated time saved (assuming manual process takes 4 hours)
    estimated_manual_time = 4.0  # hours
    processing_time = 0.25  # hours (our system takes ~15 mins)
    time_saved = estimated_manual_time - processing_time
    
    return {
        "engagement_rate": (engagements / max(views, 1)) * 100,
        "performance_score": analysis["performance_score"],
        "time_saved_hours": time_saved,
        "content_quality_score": analysis["content_quality"]["readability"],
        "sentiment_alignment": engagement_data.get("sentiment_score", 0.7),
        "roi_factor": (views / max(engagement_data.get("impressions", views), 1)),
        "trending_score": 1.0 if analysis["trending_potential"] == "High" else 0.6 if analysis["trending_potential"] == "Medium" else 0.3
    }
