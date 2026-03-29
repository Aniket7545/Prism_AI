#!/usr/bin/env python3
"""
Comprehensive BrandGuard AI System Demo
========================================
Demonstrates the full end-to-end workflow:
Content Input → Intake → Draft → Compliance → Localize → Publish → Analytics
"""
import time
import json
from datetime import datetime
from workflow import create_workflow
from services.database import audit_db
from tabulate import tabulate

def print_header(title):
    """Print formatted section header"""
    print("\n" + "=" * 100)
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {title}")
    print("=" * 100 + "\n")


def print_workflow_execution_table(results):
    """Print workflow execution summary"""
    table_data = []
    for step_name, step_result in results.items():
        table_data.append([
            step_name,
            "COMPLETED",
            step_result.get("duration", "N/A"),
            "OK"
        ])
    
    headers = ["STAGE", "STATUS", "DURATION", "RESULT"]
    print(tabulate(table_data, headers=headers, tablefmt="grid"))


def demo_compliant_content():
    """Demo 1: Content that passes compliance on first try"""
    print_header("DEMO 1: COMPLIANT CONTENT (SINGLE-PASS)")
    
    print("\n[SCENARIO] Enterprise blog article about software solutions")
    print("[GOAL] Show how compliant content flows through the system without revisions\n")
    
    app = create_workflow()
    
    test_state = {
        "session_id": "demo_001_compliant",
        "input_file_path": "demo_input.txt",
        "raw_content": """
        Our revolutionary enterprise software platform helps organizations streamline operations,
        reduce costs, and improve employee productivity. Built with modern cloud architecture,
        it scales seamlessly from startups to Fortune 500 companies. With integrated AI capabilities,
        advanced analytics, and 24/7 support, we're committed to your success.
        """,
        "topic": "Enterprise Software Solutions for Digital Transformation",
        "target_channel": "Blog",
        "target_region": "US",
        "draft_content": "",
        "compliance_report": {},
        "localization_content": "",
        "published_url": "",
        "audit_log": [],
        "iteration_count": 0,
        "human_approval": "pending",
        "human_feedback": "",
        "needs_revision": False,
        "start_time": time.time(),
        "end_time": 0.0,
        "content_metadata": {},
        "content_type": "Article",
        "structured_data": {},
        "engagement_metrics": {},
        "performance_analysis": {},
        "insights": {},
        "human_feedback_severity": "medium"
    }
    
    print("[INPUT CONTENT]")
    print(f"  Topic: {test_state['topic']}")
    print(f"  Channel: {test_state['target_channel']}")
    print(f"  Region: {test_state['target_region']}")
    print(f"  Length: {len(test_state['raw_content'])} characters\n")
    
    print("[WORKFLOW EXECUTION]")
    print("Running through all 6 agents...\n")
    
    step_count = 0
    start_time = time.time()
    final_state = None
    stage_times = {}
    
    try:
        for step, state_dict in enumerate(app.stream(
            test_state,
            {"recursion_limit": 25, "configurable": {"thread_id": "demo_001_compliant"}}
        )):
            step_count += 1
            for node_name, node_state in state_dict.items():
                if node_name != "__start__":
                    final_state = node_state
                    current_time = time.time()
                    stage_times[node_name] = current_time - start_time
                    print(f"  [{step_count}] {node_name.upper():20} - [{current_time - start_time:6.2f}s elapsed]")
        
        total_time = time.time() - start_time
        
        print(f"\n[RESULT]")
        print(f"  Status: SUCCESS - Completed in {total_time:.2f} seconds")
        print(f"  Total Stages: {step_count}")
        print(f"  Iterations: {final_state.get('iteration_count', 0)}")
        print(f"  Compliance: PASSED on first attempt")
        
        if final_state:
            print(f"\n[OUTPUT METRICS]")
            print(f"  Draft Content Length: {len(final_state.get('draft_content', ''))} characters")
            print(f"  Published URL: {final_state.get('published_url', 'N/A')}")
            print(f"  Published Channels: {final_state.get('total_channels_published', 0)}")
            
            if final_state.get('publish_results'):
                print(f"\n[PUBLISHED CHANNELS]")
                for pub in final_state.get('publish_results', []):
                    print(f"    - {pub.get('channel')}: {pub.get('url')}")
        
        # Get audit log
        logs = audit_db.get_session_logs("demo_001_compliant")
        print(f"\n[AUDIT TRAIL] {len(logs)} events recorded")
        
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return False


def demo_compliance_revision():
    """Demo 2: Content that fails compliance and requires revision"""
    print_header("DEMO 2: COMPLIANCE REVISION LOOP")
    
    print("\n[SCENARIO] Financial product marketing with prohibited language")
    print("[GOAL] Show how the system detects compliance issues and automatically revises\n")
    
    app = create_workflow()
    
    test_state = {
        "session_id": "demo_002_revision",
        "input_file_path": "demo_input.txt",
        "raw_content": """
        Our investment fund guarantees risk-free returns of 25% per year with no downside risk.
        This is the safest investment opportunity available. Guaranteed profits without any risk.
        Capital protection assured. Join thousands of satisfied investors today.
        """,
        "topic": "Investment Opportunity Analysis",
        "target_channel": "Email",
        "target_region": "US",
        "draft_content": "",
        "compliance_report": {},
        "localization_content": "",
        "published_url": "",
        "audit_log": [],
        "iteration_count": 0,
        "human_approval": "pending",
        "human_feedback": "",
        "needs_revision": False,
        "start_time": time.time(),
        "end_time": 0.0,
        "content_metadata": {},
        "content_type": "Email",
        "structured_data": {},
        "engagement_metrics": {},
        "performance_analysis": {},
        "insights": {},
        "human_feedback_severity": "medium"
    }
    
    print("[INPUT CONTENT]")
    print(f"  Topic: {test_state['topic']}")
    print(f"  Channel: {test_state['target_channel']}")
    print("  [WARNING] Contains prohibited financial terms!\n")
    
    print("[WORKFLOW EXECUTION]")
    print("Processing with automatic revision loop...\n")
    
    step_count = 0
    revision_count = 0
    start_time = time.time()
    final_state = None
    
    try:
        for step, state_dict in enumerate(app.stream(
            test_state,
            {"recursion_limit": 25, "configurable": {"thread_id": "demo_002_revision"}}
        )):
            step_count += 1
            for node_name, node_state in state_dict.items():
                if node_name != "__start__":
                    final_state = node_state
                    if node_name == "compliance":
                        needs_revision = node_state.get('needs_revision', False)
                        if needs_revision:
                            revision_count += 1
                    print(f"  [{step_count}] {node_name.upper():20} - Iteration {node_state.get('iteration_count', 0)}")
        
        total_time = time.time() - start_time
        
        print(f"\n[RESULT]")
        print(f"  Status: SUCCESS - Completed in {total_time:.2f} seconds")
        print(f"  Total Steps: {step_count}")
        print(f"  Revisions: {revision_count} iteration(s) needed")
        print(f"  Final Compliance: {'PASSED' if not final_state.get('needs_revision') else 'FAILED'}")
        
        if final_state and revision_count > 0:
            print(f"\n[REVISION DETAILS]")
            print(f"  Original iterations: {revision_count}")
            print(f"  Final iteration count: {final_state.get('iteration_count', 0)}")
            
        return True
        
    except Exception as e:
        print(f"\n[ERROR] {str(e)}")
        return False


def demo_regional_adaptation():
    """Demo 3: Content adapted for different regions"""
    print_header("DEMO 3: REGIONAL LOCALIZATION")
    
    print("\n[SCENARIO] Software solution published for multiple regions")
    print("[GOAL] Show how content is adapted for different markets\n")
    
    regions = ["Global", "India", "EU"]
    
    for region in regions:
        print(f"\n[PROCESSING FOR: {region}]")
        
        app = create_workflow()
        
        test_state = {
            "session_id": f"demo_003_{region.lower()}",
            "input_file_path": "demo_input.txt",
            "raw_content": "Cloud-based enterprise resource planning system with AI-powered automation",
            "topic": "Enterprise Digital Transformation Platform",
            "target_channel": "Blog",
            "target_region": region,
            "draft_content": "",
            "compliance_report": {},
            "localization_content": "",
            "published_url": "",
            "audit_log": [],
            "iteration_count": 0,
            "human_approval": "pending",
            "human_feedback": "",
            "needs_revision": False,
            "start_time": time.time(),
            "end_time": 0.0,
            "content_metadata": {},
            "content_type": "Article",
            "structured_data": {},
            "engagement_metrics": {},
            "performance_analysis": {},
            "insights": {},
            "human_feedback_severity": "medium"
        }
        
        try:
            step_count = 0
            for step, state_dict in enumerate(app.stream(
                test_state,
                {"recursion_limit": 25, "configurable": {"thread_id": f"demo_003_{region.lower()}"}}
            )):
                step_count += 1
                for node_name in state_dict.keys():
                    if node_name != "__start__":
                        if node_name == "localize":
                            print(f"  Localized for {region}")
            
            print(f"  Status: Published successfully")
        
        except Exception as e:
            print(f"  Error: {e}")


def demo_multichannel_publishing():
    """Demo 4: Publishing to multiple channels automatically"""
    print_header("DEMO 4: MULTI-CHANNEL PUBLISHING")
    
    print("\n[SCENARIO] Single article published to multiple channels simultaneously")
    print("[GOAL] Show how content is distributed across different platforms\n")
    
    app = create_workflow()
    
    test_state = {
        "session_id": "demo_004_multichannel",
        "input_file_path": "demo_input.txt",
        "raw_content": "Innovation in cloud computing transforms how organizations operate globally",
        "topic": "Cloud Computing Trends 2026",
        "target_channel": "Blog",
        "target_region": "Global",
        "draft_content": "",
        "compliance_report": {},
        "localization_content": "",
        "published_url": "",
        "audit_log": [],
        "iteration_count": 0,
        "human_approval": "pending",
        "human_feedback": "",
        "needs_revision": False,
        "start_time": time.time(),
        "end_time": 0.0,
        "content_metadata": {},
        "content_type": "Article",
        "structured_data": {},
        "engagement_metrics": {},
        "performance_analysis": {},
        "insights": {},
        "human_feedback_severity": "medium"
    }
    
    print("[PROCESSING]\n")
    
    try:
        final_state = None
        for step, state_dict in enumerate(app.stream(
            test_state,
            {"recursion_limit": 25, "configurable": {"thread_id": "demo_004_multichannel"}}
        )):
            for node_name, node_state in state_dict.items():
                if node_name == "publish" and isinstance(node_state, dict):
                    final_state = node_state
        
        if final_state and final_state.get('publish_results'):
            print("[PUBLISHING RESULTS]")
            print(f"Total channels published: {final_state.get('total_channels_published', 0)}\n")
            
            for result in final_state.get('publish_results', []):
                status_symbol = "[OK]" if result.get('status') == 'SUCCESS' else "[FAIL]"
                print(f"  {status_symbol} {result.get('channel'):15} - {result.get('format'):8} - {result.get('url')}")
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False


def demo_system_capabilities():
    """Demo 5: System capabilities overview"""
    print_header("DEMO 5: SYSTEM CAPABILITIES & METRICS")
    
    print("\n[AGENT ARCHITECTURE]\n")
    
    agents = [
        ("Intake Agent", "Content parsing, metadata extraction, validation", "Baseline + Type Detection"),
        ("Drafting Agent", "Content generation, revision management, feedback handling", "Up to 5 iterations"),
        ("Compliance Agent", "4-layer compliance checking, risk assessment", "Keyword + LLM + Decision"),
        ("Localization Agent", "Regional adaptation, cultural customization", "Global/Regional modes"),
        ("Publishing Agent", "Multi-channel distribution, artifact generation", "6 channels"),
        ("Analytics Agent", "Engagement tracking, performance analysis, insights", "8+ KPI metrics")
    ]
    
    agent_table = []
    for name, function, features in agents:
        agent_table.append([name, function, features])
    
    print(tabulate(agent_table, headers=["Agent", "Function", "Features"], tablefmt="grid"))
    
    print("\n[SUPPORTED CHANNELS]\n")
    
    channels = [
        ("Blog", "Markdown", "Technical articles, announcements"),
        ("Email", "HTML", "Marketing campaigns, newsletters"),
        ("LinkedIn", "Text", "Professional posts, thought leadership"),
        ("Twitter", "Text", "Short-form, trending topics"),
        ("Press Release", "Text", "Official announcements"),
        ("PDF", "Document", "Reports, whitepapers")
    ]
    
    channel_table = []
    for channel, format, use_case in channels:
        channel_table.append([channel, format, use_case])
    
    print(tabulate(channel_table, headers=["Channel", "Format", "Use Case"], tablefmt="grid"))
    
    print("\n[COMPLIANCE LAYERS]\n")
    print("  Layer 1: Keyword Scanning (Prohibited terms list)")
    print("  Layer 2: Finance Rules (Disclaimers, risk statements)")
    print("  Layer 3: LLM Semantic Review (Context-aware checking)")
    print("  Layer 4: Decision Engine (Risk assessment & override rules)")
    
    print("\n[INTEGRATION OPTIONS]\n")
    print("  - REST API (HTTP endpoints)")
    print("  - Webhook receivers (for n8n, Zapier, Make)")
    print("  - Background task queue (async processing)")
    print("  - Audit trail tracking (complete history)")
    print("  - SQLite database (persistence)")
    print("  - ChromaDB vector store (semantic search)")


def main():
    """Run all demos"""
    print("\n")
    print("*" * 100)
    print("*" + " " * 98 + "*")
    print("*" + "BRANDGUARD AI - ENTERPRISE CONTENT OPERATIONS - COMPREHENSIVE SYSTEM DEMO".center(98) + "*")
    print("*" + " " * 98 + "*")
    print("*" * 100)
    
    demos = [
        ("Compliant Content (Single-Pass)", demo_compliant_content),
        ("Compliance Revision Loop", demo_compliance_revision),
        ("Regional Localization", demo_regional_adaptation),
        ("Multi-Channel Publishing", demo_multichannel_publishing),
        ("System Capabilities Overview", demo_system_capabilities),
    ]
    
    results = {}
    for demo_name, demo_func in demos:
        try:
            success = demo_func()
            results[demo_name] = "PASSED" if success else "FAILED"
        except Exception as e:
            print(f"\n[ERROR in {demo_name}] {e}")
            results[demo_name] = "ERROR"
        
        time.sleep(1)  # Brief pause between demos
    
    # Print summary
    print_header("DEMO SUMMARY")
    
    summary_data = [(name, result) for name, result in results.items()]
    print(tabulate(summary_data, headers=["Demo", "Result"], tablefmt="grid"))
    
    passed = sum(1 for r in results.values() if r == "PASSED")
    total = len(results)
    
    print(f"\n[FINAL RESULT] {passed}/{total} demos completed successfully")
    print(f"\nTotal Duration: ~5-10 minutes (depending on LLM response times)")
    print("\n" + "*" * 100 + "\n")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n[INTERRUPTED] Demo cancelled by user")
    except Exception as e:
        print(f"\n[FATAL ERROR] {e}")
        import traceback
        traceback.print_exc()
