# run.py
from workflow import create_workflow
from datetime import datetime
import json

def run_demo():
    print("🚀 Starting Enterprise Content Workflow...")
    app = create_workflow()
    
    initial_state = {
        "input_topic": "Q3 Financial Results",
        "input_raw_data": "Revenue up 15%, profit margin improved.",
        "target_channel": "LinkedIn",
        "target_audience": "Investors",
        "target_region": "India",
        "draft_content": "",
        "compliance_report": {},
        "needs_revision": False,
        "audit_log": [],
        "iteration_count": 0,
        "start_time": datetime.now().timestamp(),
        "end_time": 0
    }
    
    try:
        # Invoke the workflow
        config = {"configurable": {"thread_id": "demo_session_1"}}
        result = app.invoke(initial_state, config=config)
        
        result["end_time"] = datetime.now().timestamp()
        duration = result["end_time"] - result["start_time"]
        
        print("\n" + "="*50)
        print("✅ WORKFLOW COMPLETED")
        print("="*50)
        print(f"⏱️ Total Time: {duration:.2f} seconds")
        print(f"🔄 Draft Iterations: {result['iteration_count']}")
        print(f"🛡️ Compliance Risk: {result['compliance_report'].get('risk_level')}")
        print(f"\n📝 FINAL CONTENT:\n{result['draft_content'][:500]}...")
        print(f"\n📋 AUDIT LOG_ENTRIES: {len(result['audit_log'])}")
        
        # Save audit log to file for proof
        with open("audit_log.json", "w") as f:
            json.dump(result['audit_log'], f, indent=2)
        print("\n💾 Audit log saved to audit_log.json")
        
    except Exception as e:
        print(f"❌ Workflow Error: {e}")
        # Fallback for demo continuity
        print("Continuing with available state...")

if __name__ == "__main__":
    run_demo()