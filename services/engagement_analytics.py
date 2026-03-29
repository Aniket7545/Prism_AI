"""
Engagement Analytics - Track and display engagement for all published content
Shows which content pieces got the most likes, reactions, comments, and views
"""
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from services.database import audit_db


def get_all_published_content(days: int = 7) -> List[Dict[str, Any]]:
    """Retrieve all published content from the last N days with engagement data"""
    
    try:
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        published_content = []
        
        # Get all content sessions that were published or are in progress
        # Include sessions with PublishAgent entries (have been published)
        cursor = audit_db.conn.cursor()
        cursor.execute("""
            SELECT DISTINCT cs.session_id, cs.created_at, cs.topic, cs.channel, cs.status
            FROM content_sessions cs
            LEFT JOIN audit_logs al ON cs.session_id = al.session_id 
                AND al.agent_name = 'PublishAgent'
            WHERE cs.created_at > ? 
                AND (cs.status IN ('completed', 'published', 'started')
                     OR al.agent_name IS NOT NULL)
            ORDER BY cs.created_at DESC
        """, (cutoff_date,))
        
        sessions = cursor.fetchall()
        cursor.close()
        
        for session in sessions:
            try:
                session_id, created_at, topic, channel, status = session
                
                engagement_metrics = {}
                published_url = ""
                
                # Get engagement metrics for this session
                try:
                    cursor = audit_db.conn.cursor()
                    cursor.execute("""
                        SELECT details
                        FROM audit_logs
                        WHERE session_id = ? AND agent_name = 'EngagementAgent'
                        ORDER BY timestamp DESC LIMIT 1
                    """, (session_id,))
                    
                    engagement_data = cursor.fetchone()
                    cursor.close()
                    
                    if engagement_data:
                        details = json.loads(engagement_data[0])
                        # Handle both old and new formats
                        if "total_engagement" in details:
                            engagement_metrics = {"total_engagement": details["total_engagement"]}
                        else:
                            engagement_metrics = details.get("engagement_metrics", {})
                except Exception as e:
                    print(f"Warning: Failed to get engagement metrics for {session_id}: {e}")
                    cursor.close() if cursor else None
                
                # Get the published URL
                try:
                    cursor = audit_db.conn.cursor()
                    cursor.execute("""
                        SELECT details
                        FROM audit_logs
                        WHERE session_id = ? AND agent_name = 'PublishAgent'
                        LIMIT 1
                    """, (session_id,))
                    
                    publish_data = cursor.fetchone()
                    cursor.close()
                    
                    if publish_data:
                        details = json.loads(publish_data[0])
                        published_url = details.get("url", "")
                except Exception as e:
                    print(f"Warning: Failed to get published URL for {session_id}: {e}")
                    cursor.close() if cursor else None
                
                # Calculate engagement score
                total_eng = engagement_metrics.get("total_engagement", {})
                views = total_eng.get("views", 0)
                reactions = total_eng.get("reactions", 0)
                comments = total_eng.get("comments", 0)
                shares = total_eng.get("shares", 0)
                
                # Calculate engagement rate
                total_interactions = reactions + comments + shares
                engagement_rate = (total_interactions / views * 100) if views > 0 else 0
                
                published_content.append({
                    "session_id": session_id,
                    "topic": topic or "Untitled",
                    "channel": channel,
                    "published_date": created_at,
                    "url": published_url,
                    "views": views,
                    "reactions": reactions,
                    "comments": comments,
                    "shares": shares,
                    "engagement_rate": engagement_rate / 100,  # Convert to decimal for consistency
                    "total_interactions": total_interactions,
                    "engagement_metrics": engagement_metrics
                })
            except Exception as e:
                print(f"Warning: Error processing session {session[0]}: {e}")
                continue
        
        return published_content
    except Exception as e:
        print(f"Error in get_all_published_content: {e}")
        return []


def display_engagement_report(days: int = 7):
    """Print a formatted engagement report for all published content"""
    
    content_list = get_all_published_content(days=days)
    
    if not content_list:
        print(f"\nNo published content found in the last {days} days.\n")
        return
    
    print("\n" + "="*120)
    print(f"ENGAGEMENT REPORT - Last {days} Days")
    print("="*120)
    
    # Sort by total interactions
    content_list.sort(key=lambda x: x["total_interactions"], reverse=True)
    
    # Header
    print(f"\n{'TOPIC':<35} {'VIEWS':<8} {'LIKES':<8} {'COMMENTS':<9} {'SHARES':<7} {'ENGAGEMENT':<12} {'TOTAL':<8}")
    print("-" * 120)
    
    # Content rows
    for i, content in enumerate(content_list, 1):
        topic = content["topic"][:33] if content["topic"] else "Unknown"
        views = str(content["views"])
        reactions = str(content["reactions"])
        comments = str(content["comments"])
        shares = str(content["shares"])
        engagement_pct = f"{content['engagement_rate']*100:.1f}%"
        total = str(content["total_interactions"])
        
        print(f"{topic:<35} {views:<8} {reactions:<8} {comments:<9} {shares:<7} {engagement_pct:<12} {total:<8}")
        
        # Show engagement insights
        if content["total_interactions"] > 0:
            if content["reactions"] > content["comments"]:
                print(f"  ➜ Audience favored reactions ({content['reactions']} likes)")
            elif content["comments"] > content["reactions"]:
                print(f"  ➜ Strong discussion ({content['comments']} comments)")
        
        if content["views"] > 100:
            print(f"  ➜ Excellent reach ({content['views']} views)")
        elif content["views"] == 0 and content["channel"] == "Blog":
            print(f"  ➜ Still building reach...")
    
    print("\n" + "="*120)
    
    # Summary statistics
    if content_list:
        total_views = sum(c["views"] for c in content_list)
        total_interactions = sum(c["total_interactions"] for c in content_list)
        avg_engagement = sum(c["engagement_rate"] for c in content_list) / len(content_list) if content_list else 0
        
        print(f"\nSUMMARY:")
        print(f"  Total Content Pieces: {len(content_list)}")
        print(f"  Total Views: {total_views:,}")
        print(f"  Total Interactions: {total_interactions} (likes + comments + shares)")
        print(f"  Average Engagement Rate: {avg_engagement*100:.1f}%")
        
        # Top performers
        top_3 = content_list[:3]
        if top_3:
            print(f"\nTOP PERFORMERS:")
            for i, content in enumerate(top_3, 1):
                print(f"  {i}. \"{content['topic'][:50]}...\" → {content['total_interactions']} interactions, {content['views']} views")
        
        print("\n" + "="*120 + "\n")


def get_content_engagement(session_id: str) -> Dict[str, Any]:
    """Get detailed engagement data for a specific published content"""
    
    try:
        # Get the content information
        cursor = audit_db.conn.cursor()
        cursor.execute("""
            SELECT topic, created_at, channel, status
            FROM content_sessions
            WHERE session_id = ?
        """, (session_id,))
        
        session = cursor.fetchone()
        cursor.close()
        
        if not session:
            return {"error": f"Session {session_id} not found"}
        
        topic, created_at, channel, status = session
        
        # Get engagement metrics and insights
        engagement_metrics = {}
        insights = []
        
        try:
            cursor = audit_db.conn.cursor()
            cursor.execute("""
                SELECT details
                FROM audit_logs
                WHERE session_id = ? AND agent_name = 'EngagementAgent'
                ORDER BY timestamp DESC LIMIT 1
            """, (session_id,))
            
            engagement_data = cursor.fetchone()
            cursor.close()
            
            if engagement_data:
                details = json.loads(engagement_data[0])
                engagement_metrics = details.get("engagement_metrics", {})
                insights = details.get("insights", [])
        except Exception as e:
            print(f"Warning: Failed to get engagement data for {session_id}: {e}")
        
        return {
            "session_id": session_id,
            "topic": topic,
            "published_date": created_at,
            "channel": channel,
            "status": status,
            "engagement_metrics": engagement_metrics,
            "insights": insights
        }
    except Exception as e:
        print(f"Error in get_content_engagement: {e}")
        return {"error": str(e)}


if __name__ == "__main__":
    # Display engagement report when run directly
    display_engagement_report(days=30)
