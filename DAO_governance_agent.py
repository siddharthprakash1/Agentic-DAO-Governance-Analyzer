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
    You are an *expert-level* DAO governance analyst agent. Your goal is to provide the *most detailed and actionable analysis possible* of the following governance proposal to enable informed decision-making.

    Proposal Title: {proposal_data['title']}
    Proposal Description: {proposal_data['description']}

    **Instructions for Analysis:**

    Perform a comprehensive analysis, focusing on the following key categories. For each category, provide specific details, examples, and actionable insights:

    1. **Strategic Alignment & Rationale:**
        * How well does this proposal align with the DAO's stated mission, values, and long-term strategic goals? Be specific.
        * Is the rationale for the proposal clearly and convincingly presented? Are there any gaps in the logic?
        * Are there alternative strategic approaches the DAO should consider instead of this proposal? Briefly suggest 1-2 alternatives if applicable.

    2. **Financial Implications & ROI:**
        * Conduct a detailed cost-benefit analysis (even if data is limited, make educated estimations based on the proposal description).
        * Identify all potential costs associated with the proposal (development, implementation, ongoing maintenance, risks, etc.). Be as specific as possible.
        * Estimate the potential Return on Investment (ROI) or other financial benefits. Quantify benefits where possible (e.g., potential revenue increase, cost savings, token value impact).
        * Are there any potential financial risks or downsides?  Detail them.
        * Suggest specific financial metrics that should be tracked to measure the success of this proposal if implemented.

    3. **Technical Feasibility & Implementation:**
        * Assess the technical feasibility of the proposal. Are there any obvious technical challenges or hurdles?
        * Evaluate the proposed implementation plan (if any). Is it realistic and well-defined? What's missing?
        * Identify any potential technical risks, dependencies, or vulnerabilities.
        * Suggest specific technical due diligence steps the DAO should take before proceeding.

    4. **Security & Risk Assessment:**
        * Conduct a thorough security risk assessment. Identify potential security vulnerabilities introduced by this proposal (technical, operational, governance-related).
        * Evaluate the proposal's consideration of security risks (if any). Is it sufficient?
        * Suggest concrete security mitigation strategies and best practices that should be implemented.
        * Are there any potential legal or regulatory risks associated with this proposal?

    5. **Community Impact & Governance:**
        * Analyze the potential impact of this proposal on the DAO community (positive and negative). Consider different user segments and stakeholders.
        * How does this proposal affect DAO governance processes or voting mechanisms? Are there any governance risks or improvements?
        * Assess community sentiment towards this type of proposal (if you have prior context or can infer from the description).
        * Suggest ways to improve community engagement and communication around this proposal to ensure broad understanding and buy-in.

    6. **Actionable Recommendations & Next Steps:**
        * Based on your comprehensive analysis, provide clear and actionable recommendations to the DAO.  Should they:
            * **Vote FOR the proposal?** (Under what conditions?)
            * **Vote AGAINST the proposal?** (Why?)
            * **Request MORE INFORMATION and revisions before voting?** (Specify exactly what information is needed and what revisions are recommended).
            * **ABSTAIN from voting at this stage?** (When might abstention be appropriate?)
        * Suggest concrete next steps the DAO should take based on your recommendations (e.g., "Conduct technical due diligence on Project XYZ's bridging technology," "Request a detailed cost breakdown from the proposer," "Hold a community forum to discuss security risks").

    **Output Format:**

    Structure your analysis report clearly, using headings and bullet points for each category.  Make it easy to read and understand for DAO members with varying levels of technical and financial expertise.  Aim for a report that is as detailed, insightful, and actionable as possible.  Your goal is to be the *ultimate* DAO governance analysis expert.

    Respond with your detailed analysis report.
    """
    response = gemini_pro.invoke([HumanMessage(content=prompt)])
    analysis_report = response.content
    log_message = f"Proposal Analyzer: Expert-Level Analysis Report for '{proposal_data['title']}': {analysis_report}"
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
