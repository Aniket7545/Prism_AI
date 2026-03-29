#!/usr/bin/env python3
"""
Engagement Report CLI - Display engagement analytics for all published content
Shows which content pieces got the most likes, reactions, comments, and views
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from services.engagement_analytics import display_engagement_report, get_all_published_content
from services.database import audit_db


def print_engagement_dashboard():
    """Print a comprehensive engagement dashboard"""
    
    print("\n" + "█" * 120)
    print("█" + " " * 118 + "█")
    print("█" + "PRISM AI - CONTENT ENGAGEMENT DASHBOARD".center(118) + "█")
    print("█" + " " * 118 + "█")
    print("█" * 120)
    
    # Display the engagement report
    display_engagement_report(days=30)
    
    # Additional insights
    print("\nQUICK INSIGHTS:")
    print("-" * 120)
    
    content_list = get_all_published_content(days=30)
    
    if content_list:
        # Find best performing content
        best = max(content_list, key=lambda x: x["total_interactions"], default=None)
        if best and best["total_interactions"] > 0:
            print(f"🏆 BEST PERFORMER: \"{best['topic'][:60]}\"")
            print(f"   → {best['total_interactions']} total interactions ({best['reactions']} likes, {best['comments']} comments)")
            print(f"   → {best['views']} views | {best['engagement_rate']*100:.1f}% engagement rate")
        
        # Find most viewed
        most_viewed = max(content_list, key=lambda x: x["views"], default=None)
        if most_viewed and most_viewed["views"] > 0:
            print(f"\n👁️  MOST VIEWED: \"{most_viewed['topic'][:60]}\"")
            print(f"   → {most_viewed['views']} views | {most_viewed['total_interactions']} interactions")
        
        # Find most discussed
        most_discussed = max(content_list, key=lambda x: x["comments"], default=None)
        if most_discussed and most_discussed["comments"] > 0:
            print(f"\n💬 MOST DISCUSSED: \"{most_discussed['topic'][:60]}\"")
            print(f"   → {most_discussed['comments']} comments | {most_discussed['reactions']} reactions")
        
        # Engagement trends
        if len(content_list) > 1:
            recent_3 = content_list[:3]
            older_3 = content_list[-3:] if len(content_list) > 3 else content_list
            
            recent_avg = sum(c["engagement_rate"] for c in recent_3) / len(recent_3)
            older_avg = sum(c["engagement_rate"] for c in older_3) / len(older_3)
            
            trend = "📈 IMPROVING" if recent_avg > older_avg else "📉 DECLINING" if recent_avg < older_avg else "→ STABLE"
            print(f"\n{trend} ENGAGEMENT TREND")
            print(f"   → Recent avg engagement: {recent_avg*100:.1f}%")
            print(f"   → Historical avg engagement: {older_avg*100:.1f}%")
    
    print("\n" + "█" * 120 + "\n")


if __name__ == "__main__":
    print_engagement_dashboard()
