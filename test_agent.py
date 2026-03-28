# test_agents.py
from agents.compliance_agent import compliance_agent
from datetime import datetime

def test_compliance():
    test_state = {
        "input_topic": "Investment Scheme",
        "input_raw_data": "Data...",
        "target_channel": "LinkedIn",
        "messages": [],
        "draft_content": "This investment is risk-free and guarantees 100% profit.",
        "compliance_report": {},
        "next_step": "",
        "approval_status": "pending",
        "human_feedback": "",
        "audit_log": [],
        "start_time": datetime.now().timestamp(),
        "end_time": 0
    }
    
    result = compliance_agent(test_state)
    print("\n--- COMPLIANCE TEST RESULT ---")
    print(f"Status: {result['compliance_report'].get('status')}")
    print(f"Risk Score: {result['compliance_report'].get('risk_score')}")
    print(f"Flags: {result['compliance_report'].get('flags', [])}")
    print(f"Reasoning: {result['compliance_report'].get('reasoning')}")

if __name__ == "__main__":
    test_compliance()