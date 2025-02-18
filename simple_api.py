# enhanced_api.py
from flask import Flask, jsonify
import random
import threading
import time

app = Flask(__name__)

# A global list to act as a proposal queue
proposals_queue = []

def generate_proposal():
    """Simulate generating a new proposal."""
    proposals = [
        {
            "title": "Proposal to Increase Staking Rewards by 10%",
            "description": "This proposal suggests increasing staking rewards to incentivize participation and secure the network."
        },
        {
            "title": "Proposal to Partner with Project XYZ",
            "description": "This proposal recommends a strategic partnership with Project XYZ to expand our ecosystem."
        },
        {
            "title": "Proposal to Launch a New Product Feature",
            "description": "This proposal suggests developing a new feature to boost user engagement and competitive advantage."
        }
    ]
    return random.choice(proposals)

def proposal_generator():
    """Continuously generate new proposals every 10 seconds."""
    while True:
        new_proposal = generate_proposal()
        # Add a timestamp to the proposal
        new_proposal["timestamp"] = time.strftime("%Y-%m-%d %H:%M:%S")
        proposals_queue.append(new_proposal)
        print(f"[Generator] New proposal added: {new_proposal['title']} at {new_proposal['timestamp']}")
        time.sleep(10)

@app.route('/proposal', methods=['GET'])
def get_latest_proposal():
    """Return the oldest proposal from the queue, if available."""
    if proposals_queue:
        proposal = proposals_queue.pop(0)
        return jsonify(proposal)
    else:
        return jsonify({"message": "No proposals available"}), 404

if __name__ == '__main__':
    # Start the background proposal generator thread
    generator_thread = threading.Thread(target=proposal_generator, daemon=True)
    generator_thread.start()
    app.run(port=5000)
