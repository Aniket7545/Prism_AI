"""CLI runner for the full workflow without hardcoded demo content.

Usage examples:
  python run.py --file path/to/input.txt --topic "Q2 earnings" --channel Blog --region US
  python run.py --content "raw text here" --topic "Launch" --auto-approve
"""

import argparse
import time
import uuid
import os
from workflow import create_workflow
from utils.loaders import extract_text_from_file


def parse_args():
    parser = argparse.ArgumentParser(description="Run the BrandGuard AI workflow")
    parser.add_argument("--file", help="Path to input file (txt/pdf)")
    parser.add_argument("--content", help="Raw content string (overrides --file if set)")
    parser.add_argument("--topic", required=True, help="Content topic")
    parser.add_argument("--channel", default="Blog", help="Target channel (Blog/Email/LinkedIn/etc)")
    parser.add_argument("--region", default="Global", help="Target region")
    parser.add_argument("--content-type", dest="content_type", default="Article", help="Content type label")
    parser.add_argument("--auto-approve", action="store_true", help="Skip manual approval step")
    parser.add_argument("--human-feedback", dest="human_feedback", default="", help="Optional human feedback before approval")
    return parser.parse_args()


def build_initial_state(args, raw_content: str) -> dict:
    session_id = str(uuid.uuid4())
    return {
        "session_id": session_id,
        "input_file_path": args.file or "cli_input",
        "raw_content": raw_content,
        "topic": args.topic,
        "target_channel": args.channel,
        "target_region": args.region,
        "draft_content": "",
        "compliance_report": {},
        "localization_content": "",
        "published_url": "",
        "audit_log": [],
        "iteration_count": 0,
        "human_approval": "pending",
        "human_feedback": "",
        "human_feedback_severity": "medium",
        "needs_revision": False,
        "start_time": time.time(),
        "end_time": 0,
        "content_metadata": {},
        "content_type": args.content_type,
        "structured_data": {},
        "engagement_metrics": {},
        "performance_analysis": {},
        "insights": {},
    }


def run_workflow_cli():
    args = parse_args()
    app = create_workflow()

    if args.content:
        raw_content = args.content
    elif args.file:
        if not os.path.exists(args.file):
            raise FileNotFoundError(f"Input file not found: {args.file}")
        raw_content = extract_text_from_file(args.file)
    else:
        raise ValueError("Provide --content or --file")

    initial_state = build_initial_state(args, raw_content)
    config = {"configurable": {"thread_id": initial_state["session_id"]}}

    print("🚀 Starting workflow", initial_state["session_id"])
    print(f"   Topic: {args.topic} | Channel: {args.channel} | Region: {args.region}")

    # Run until human gate interrupt
    paused_state = app.invoke(initial_state, config=config)
    print("\n⏸️ Workflow paused for Human Approval.")
    print(f"Compliance Report: {paused_state.get('compliance_report')}")

    # Human decision
    if args.auto_approve:
        approval = "approved"
    else:
        user_input = input("Approve draft? (y/n): ").strip().lower()
        approval = "approved" if user_input in {"y", "yes", ""} else "rejected"

    feedback = args.human_feedback
    if approval == "rejected" and not feedback:
        feedback = input("Enter feedback for revision: ")

    app.update_state(config, {"human_approval": approval, "human_feedback": feedback})

    final_state = app.invoke(None, config=config)
    final_state["end_time"] = time.time()

    print("\n✅ Workflow Completed.")
    print(f"Published URL: {final_state.get('published_url')}")
    print(f"Publish Results: {final_state.get('publish_results')}")
    print(f"Analytics: {final_state.get('engagement_metrics')}")
    print(f"Duration: {final_state['end_time'] - final_state['start_time']:.2f}s")


if __name__ == "__main__":
    run_workflow_cli()