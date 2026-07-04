import json
import os

DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data.dat')

def init_data():
    """Create data.dat if it doesn't exist."""
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump({
                "properties": [],
                "clients":    [],
                "employees":  [],
                "finance":    []
            }, f, indent=2)
        print(f"[SERENIA] Created data.dat at {DATA_FILE}")

def load_data():
    """Load and return all data from data.dat."""
    with open(DATA_FILE, 'r') as f:
        return json.load(f)

def save_data(data):
    """Write data dict back to data.dat."""
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=2)
