import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage
from langgraph.pregel import END
from typing import Dict, List, Tuple, TypedDict, Optional
import random

load_dotenv()

# --- Define State ---
class GovernanceAgentState(TypedDict):
    proposal_data: Optional[Dict[str, str]]  # Proposal title, description (simulated)
    analysis_report: Optional[str]
    voting_decision: Optional[str]  # "For", "Against", "Abstain"
    voting_action_taken: Optional[bool]  # Simulated vote cast
    logs: List[str]

# --- Gemini Flash Model ---
gemini_pro = ChatGoogleGenerativeAI(
    model="gemini-1.5-pro-latest", # Or "gemini-1.5-flash-latest" - you can try both
    google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.5  # Adjust temperature as needed for analysis
)

def monitor_proposals(state: GovernanceAgentState) -> Dict[str, Dict[str, str]]:
    """Simulates monitoring a DAO platform for new governance proposals."""
    proposals = {
        "Proposal_1": {
            "title": "Proposal to Increase Staking Rewards by 10%",
            "description": "This proposal suggests increasing the staking rewards for our token holders by 10%..."
        },
        "Proposal_2": {
            "title": "Proposal to Partner with Project XYZ",
            "description": "This proposal recommends a strategic partnership with Project XYZ..."
        }
    }
    selected_proposal_key = random.choice(list(proposals.keys()))
    selected_proposal = proposals[selected_proposal_key]

    log_message = f"Proposal Monitor: New proposal found: {selected_proposal['title']}"
    return {"proposal_data": selected_proposal, "logs": [log_message]}

def analyze_proposal_gemini(state: GovernanceAgentState) -> Dict[str, str]:
    """Analyzes the DAO governance proposal using Gemini Pro to understand its implications."""
    proposal_data = state.get("proposal_data")
    if not proposal_data:
        return {"analysis_report": "No proposal data available for analysis.", "logs": ["Proposal Analyzer: No proposal data received."]}

    prompt = f"""
    You are a DAO governance analyst agent. Analyze the following governance proposal.
    Understand its objectives, arguments for and against it (if mentioned in the description), and potential impacts on the DAO and its community.
    Identify any potential risks or benefits associated with the proposal.
    Provide a concise analysis report summarizing your understanding and insights about the proposal.

    Proposal Title: {proposal_data['title']}
    Proposal Description: {proposal_data['description']}

    Respond with a detailed analysis report.
    """

    response = gemini_pro.invoke([HumanMessage(content=prompt)])
    analysis_report = response.content
    log_message = f"Proposal Analyzer (Gemini Pro): Analysis Report for '{proposal_data['title']}': {analysis_report}"
    return {"analysis_report": analysis_report, "logs": [log_message]}


def decide_vote_strategy(state: GovernanceAgentState) -> Dict[str, str]:
    """Decides the voting strategy based on the analysis report."""
    analysis_report = state.get("analysis_report")
    proposal_data = state.get("proposal_data")
    logs = []

    if not analysis_report:
        decision_message = "Voting Strategy Agent: No analysis report received, abstaining from vote."
        logs.append(decision_message)
        return {"voting_decision": "Abstain", "logs": logs}

    # Simple Voting Strategy:
    # If analysis report is generally positive (contains keywords like "benefit", "positive", "improve", but not "risk", "negative", "harm"), vote "For".
    # Otherwise, vote "Against" or "Abstain" (let's abstain for now in uncertain cases).

    positive_keywords = ["benefit", "positive", "improve", "increase", "enhance", "good", "valuable"]
    negative_keywords = ["risk", "negative", "harm", "decrease", "reduce", "bad", "concern", "vulnerability"]

    positive_sentiment_score = sum(1 for keyword in positive_keywords if keyword in analysis_report.lower())
    negative_sentiment_score = sum(1 for keyword in negative_keywords if keyword in analysis_report.lower())

    if positive_sentiment_score > negative_sentiment_score:
        voting_decision = "For"
        decision_message = f"Voting Strategy Agent: Analysis is generally positive for '{proposal_data['title']}', voting 'For'."
    elif negative_sentiment_score > positive_sentiment_score:
        voting_decision = "Against"
        decision_message = f"Voting Strategy Agent: Analysis indicates potential risks for '{proposal_data['title']}', voting 'Against'."
    else:
        voting_decision = "Abstain" # Default to abstain if sentiment is neutral or mixed
        decision_message = f"Voting Strategy Agent: Mixed or neutral analysis for '{proposal_data['title']}', voting 'Abstain'."

    logs.append(decision_message)
    return {"voting_decision": voting_decision, "logs": logs}


def cast_vote(state: GovernanceAgentState) -> Dict[str, bool]:
    """Simulates casting a vote on the DAO governance platform."""
    voting_decision = state.get("voting_decision")
    proposal_data = state.get("proposal_data")
    logs = []

    if voting_decision:
        vote_confirmation = f"Voting Agent: Simulated vote cast for proposal '{proposal_data['title']}': Decision = '{voting_decision}'"
        logs.append(vote_confirmation)
        vote_action_taken = True # Simulate successful vote
    else:
        vote_confirmation = "Voting Agent: No voting decision made, no vote cast."
        logs.append(vote_confirmation)
        vote_action_taken = False

    return {"voting_action_taken": vote_action_taken, "logs": logs}


def log_actions(state: GovernanceAgentState) -> Dict[str, List[str]]:
    """Logs all actions and decisions."""
    logs = state.get("logs", [])
    return {"logs": logs}


# --- Build the LangGraph ---
builder = StateGraph(GovernanceAgentState)

builder.add_node("monitor_proposals", monitor_proposals)
builder.add_node("analyze_proposal", analyze_proposal_gemini) # Gemini powered analysis
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

# --- Run the Graph ---
initial_state: GovernanceAgentState = {
    "proposal_data": None,
    "analysis_report": None,
    "voting_decision": None,
    "voting_action_taken": None,
    "logs": []
}

for output in graph.stream(initial_state):
    print("--- Node Output ---")
    for key, value in output.items():
        print(f"Node '{key}':")
        if key == "log_actions":
            for log_entry in value["logs"]:
                print(f"  - {log_entry}")
        else:
            print(f"  {value}")

print("\nGovernance Agent Workflow Completed.")