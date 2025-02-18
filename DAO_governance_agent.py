import os
import requests
import json
import time
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.pregel import END
from typing import Dict, List, TypedDict, Optional

load_dotenv()

# --- Define State ---
class GovernanceAgentState(TypedDict):
    proposal_data: Optional[Dict[str, str]]
    analysis_report: Optional[str]
    voting_decision: Optional[str]
    voting_action_taken: Optional[bool]
    logs: List[str]

# --- Gemini Flash Model ---
gemini_pro = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest",
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.5
)

def monitor_proposals(state: GovernanceAgentState) -> Dict[str, Dict[str, str]]:
    try:
        response = requests.get("http://localhost:5000/proposal")
        if response.status_code == 200:
            selected_proposal = response.json()
            log_message = f"Proposal Monitor: New proposal found: {selected_proposal['title']}"
            return {"proposal_data": selected_proposal, "logs": [log_message]}
        else:
            log_message = f"Proposal Monitor: Failed to fetch proposal. Status code: {response.status_code}"
            return {"proposal_data": None, "logs": [log_message]}
    except Exception as e:
        log_message = f"Proposal Monitor: Exception occurred: {str(e)}"
        return {"proposal_data": None, "logs": [log_message]}

def analyze_proposal_gemini(state: GovernanceAgentState) -> Dict[str, str]:
    proposal_data = state.get("proposal_data")
    if not proposal_data:
        return {"analysis_report": "No proposal data available for analysis.", "logs": ["Proposal Analyzer: No proposal data received."]}
    
    prompt = f"""
    You are a DAO governance analyst agent. Analyze the following governance proposal.
    
    Proposal Title: {proposal_data['title']}
    Proposal Description: {proposal_data['description']}
    
    Respond with a detailed analysis report.
    """
    response = gemini_pro.invoke([HumanMessage(content=prompt)])
    analysis_report = response.content
    log_message = f"Proposal Analyzer: Analysis Report for '{proposal_data['title']}': {analysis_report}"
    return {"analysis_report": analysis_report, "logs": [log_message]}

def decide_vote_strategy(state: GovernanceAgentState) -> Dict[str, str]:
    analysis_report = state.get("analysis_report")
    proposal_data = state.get("proposal_data")
    logs = []

    if not analysis_report:
        logs.append("Voting Strategy Agent: No analysis report received, abstaining from vote.")
        return {"voting_decision": "Abstain", "logs": logs}

    positive_keywords = ["benefit", "positive", "improve", "increase", "enhance", "good", "valuable"]
    negative_keywords = ["risk", "negative", "harm", "decrease", "reduce", "bad", "concern", "vulnerability"]

    positive_sentiment_score = sum(1 for keyword in positive_keywords if keyword in analysis_report.lower())
    negative_sentiment_score = sum(1 for keyword in negative_keywords if keyword in analysis_report.lower())

    if positive_sentiment_score > negative_sentiment_score:
        decision_message = f"Voting Strategy: Positive analysis for '{proposal_data['title']}', voting 'For'."
        voting_decision = "For"
    elif negative_sentiment_score > positive_sentiment_score:
        decision_message = f"Voting Strategy: Negative analysis for '{proposal_data['title']}', voting 'Against'."
        voting_decision = "Against"
    else:
        decision_message = f"Voting Strategy: Mixed/neutral analysis for '{proposal_data['title']}', voting 'Abstain'."
        voting_decision = "Abstain"
    
    logs.append(decision_message)
    return {"voting_decision": voting_decision, "logs": logs}

def cast_vote(state: GovernanceAgentState) -> Dict[str, bool]:
    voting_decision = state.get("voting_decision")
    proposal_data = state.get("proposal_data")
    logs = []

    if voting_decision:
        vote_confirmation = f"Voting Agent: Vote cast for proposal '{proposal_data['title']}': {voting_decision}"
        logs.append(vote_confirmation)
        vote_action_taken = True
    else:
        logs.append("Voting Agent: No vote cast.")
        vote_action_taken = False

    return {"voting_action_taken": vote_action_taken, "logs": logs}

def log_actions(state: GovernanceAgentState) -> Dict[str, List[str]]:
    logs = state.get("logs", [])
    return {"logs": logs}

# --- Build the LangGraph ---
builder = StateGraph(GovernanceAgentState)
builder.add_node("monitor_proposals", monitor_proposals)
builder.add_node("analyze_proposal", analyze_proposal_gemini)
builder.add_node("decide_vote_strategy", decide_vote_strategy)
builder.add_node("cast_vote", cast_vote)
builder.add_node("log_actions", log_actions)
builder.set_entry_point("monitor_proposals")
builder.add_edge("monitor_proposals", "analyze_proposal")
builder.add_edge("analyze_proposal", "decide_vote_strategy")
builder.add_edge("decide_vote_strategy", "cast_vote")
builder.add_edge("cast_vote", "log_actions")
builder.add_edge("log_actions", END)
graph = builder.compile()

# --- Continuous Run ---
initial_state: GovernanceAgentState = {
    "proposal_data": None,
    "analysis_report": None,
    "voting_decision": None,
    "voting_action_taken": None,
    "logs": []
}

print("Starting continuous LangGraph workflow...\n")
while True:
    for output in graph.stream(initial_state):
        print("=" * 50)
        print("Cycle Output:")
        for node, value in output.items():
            print(f"\nNode: {node}")
            print(json.dumps(value, indent=2))
        print("=" * 50, "\n")
    # Wait a bit before the next cycle (adjust as needed)
    time.sleep(5)
