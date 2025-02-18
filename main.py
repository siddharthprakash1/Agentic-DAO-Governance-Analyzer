import os
from dotenv import load_dotenv
from langgraph.graph import StateGraph, MessageGraph
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.pregel import END
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from typing import Dict, List, Tuple, TypedDict, Optional
import random

load_dotenv()

# --- Define State ---
class AgentState(TypedDict):
    traffic_data: Optional[Dict[str, float]]  # VLAN ID -> traffic load (simulated)
    analysis_report: Optional[str]
    vlan_adjustment_decision: Optional[bool]
    vlan_config_commands: Optional[List[str]]
    logs: List[str]


# --- Gemini Flash Model ---
gemini_flash = ChatGoogleGenerativeAI(
    model="gemini-2.0-pro-exp-02-05",
  google_api_key=os.getenv("GOOGLE_API_KEY"),
    temperature=0.3  # Adjust temperature as needed
)

# --- Agent Functions ---

def monitor_traffic(state: AgentState) -> Dict[str, float]:
    """Simulates monitoring network traffic in VLANs."""
    # In a real application, this would fetch data from a network monitoring system.
    # For simulation, we'll generate random traffic loads for VLANs.
    vlan_traffic = {
        f"VLAN_{i}": random.uniform(10, 100) for i in range(1, 5)
    }  # Simulate 4 VLANs
    vlan_traffic["VLAN_1"] += random.uniform(50, 150)  # Simulate congestion in VLAN_1
    log_message = f"Traffic Monitor: Simulated traffic data: {vlan_traffic}"
    return {"traffic_data": vlan_traffic, "logs": [log_message]}


def analyze_traffic_gemini(state: AgentState) -> Dict[str, str]:
    """Analyzes traffic data using Gemini Flash to identify congestion and suggest adjustments."""
    traffic_data = state.get("traffic_data")
    if not traffic_data:
        return {"analysis_report": "No traffic data available for analysis.", "logs": ["Data Analyzer: No traffic data received."]}

    prompt = f"""
    You are a network analyst agent. Analyze the following network traffic data for VLANs.
    Identify any VLANs that are significantly congested (high traffic load) or have unusually high traffic compared to others.
    Suggest potential VLAN adjustments to alleviate congestion, if needed.
    If no adjustments are needed, state that clearly.

    Traffic Data:
    {traffic_data}

    Respond with a concise analysis report and VLAN adjustment recommendations (if any).
    """

    response = gemini_flash.invoke([HumanMessage(content=prompt)])
    analysis_report = response.content
    log_message = f"Data Analyzer (Gemini Flash): Analysis Report: {analysis_report}"
    return {"analysis_report": analysis_report, "logs": [log_message]}


def decide_vlan_adjustment(state: AgentState) -> Dict[str, Tuple[bool, Optional[List[str]]]]:
    """Decides whether to adjust VLANs based on the analysis report."""
    analysis_report = state.get("analysis_report")
    logs = []

    if not analysis_report:
        decision_message = "Decision Maker: No analysis report received, no VLAN adjustments."
        logs.append(decision_message)
        return {"vlan_adjustment_decision": False, "vlan_config_commands": None, "logs": logs}

    if "congested" in analysis_report.lower() or "high traffic" in analysis_report.lower():
        decision_message = "Decision Maker: Congestion detected, deciding to adjust VLANs based on analysis."
        logs.append(decision_message)
        vlan_config_commands = [
            "switch1: move user from VLAN_1 to VLAN_3 port 10",
            "switch2: update VLAN assignment for port 10 to VLAN_3"
        ]
        logs.append(f"Decision Maker: VLAN adjustment commands: {vlan_config_commands}")
        return {"vlan_adjustment_decision": True, "vlan_config_commands": vlan_config_commands, "logs": logs}
    else:
        decision_message = "Decision Maker: No significant congestion detected in analysis, no VLAN adjustments needed."
        logs.append(decision_message)
        return {"vlan_adjustment_decision": False, "vlan_config_commands": None, "logs": logs}


def configure_vlan(state: AgentState) -> Dict[str, str]:
    """Simulates configuring VLAN adjustments on network devices."""
    vlan_config_commands = state.get("vlan_config_commands")
    logs = []

    if vlan_config_commands:
        config_confirmation = f"VLAN Configurator: Simulated VLAN configuration applied: {vlan_config_commands}"
        logs.append(config_confirmation)
    else:
        config_confirmation = "VLAN Configurator: No VLAN configuration changes needed."
        logs.append(config_confirmation)

    return {"logs": logs}


def log_actions(state: AgentState) -> Dict[str, List[str]]:
    """Logs actions and decisions."""
    logs = state.get("logs", [])
    return {"logs": logs}


# --- Build the LangGraph ---
builder = StateGraph(AgentState)

builder.add_node("monitor_traffic", monitor_traffic)
builder.add_node("analyze_traffic", analyze_traffic_gemini)  # Gemini-powered analysis
builder.add_node("decide_vlan_adjustment", decide_vlan_adjustment)
builder.add_node("configure_vlan", configure_vlan)
builder.add_node("log_actions", log_actions)

builder.set_entry_point("monitor_traffic")

builder.add_edge("monitor_traffic", "analyze_traffic")
builder.add_edge("analyze_traffic", "decide_vlan_adjustment")
builder.add_edge("decide_vlan_adjustment", "configure_vlan")
builder.add_edge("configure_vlan", "log_actions")  # Log after configuration
builder.add_edge("log_actions", END)  # End graph after logging

graph = builder.compile()

# --- Run the Graph ---
initial_state: AgentState = {
    "traffic_data": None,
    "analysis_report": None,
    "vlan_adjustment_decision": None,
    "vlan_config_commands": None,
    "logs": []
}

for output in graph.stream(initial_state):  # Use the complete initial state
    print("--- Node Output ---")  # Separator for each node's output
    for key, value in output.items():
        print(f"Node '{key}':") # Indicate the node name
        if key == "log_actions":  # Final output from log_actions node (still print logs nicely)
            for log_entry in value["logs"]:
                print(f"  - {log_entry}")
        else: # For other nodes, print the entire output dictionary
            print(f"  {value}")

print("\nAgent workflow completed.")