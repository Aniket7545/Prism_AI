from workflow import create_workflow
from utils.loaders import extract_text_from_file
from datetime import datetime
import time, uuid, os

def run_demo():
    print("🚀 Starting Enterprise Content Workflow...")
    app = create_workflow()
    
    # Create a dummy text file for testing if none exists
    test_file = "./data/inputs/test_input.txt"
    os.makedirs("./data/inputs", exist_ok=True)
    if not os.path.exists(test_file):
        with open(test_file, "w") as f:
            f.write("Revenue grew 20%. We guarantee risk-free returns for investors.")
    
    initial_state = {
        "session_id": str(uuid.uuid4()),
        "input_file_path": test_file,
        "raw_content": extract_text_from_file(test_file),
        "topic": "Investment Update",
        "target_channel": "LinkedIn",
        "target_region": "India",
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
        "end_time": 0
    }
    
    config = {"configurable": {"thread_id": initial_state["session_id"]}}
    
    try:
        # Run until interrupt
        result = app.invoke(initial_state, config=config)
        print("\n⏸️ Workflow paused for Human Approval.")
        print(f"Compliance Report: {result['compliance_report']}")
        
        # Simulate Human Approval
        input("\nPress Enter to Approve & Publish...")
        
        result["human_approval"] = "approved"
        final_result = app.invoke(None, config=config)
        final_result["end_time"] = time.time()
        
        print("\n✅ Workflow Completed.")
        print(f"Published URL: {final_result.get('published_url')}")
        print(f"Duration: {final_result['end_time'] - final_result['start_time']:.2f}s")
        
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    run_demo()