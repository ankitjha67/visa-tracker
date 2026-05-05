import os
from pathlib import Path
print("CI=", os.environ.get("CI"))
print("GITHUB_ACTIONS=", os.environ.get("GITHUB_ACTIONS"))
print("VISA_TRACKER_NO_PROMPT=", os.environ.get("VISA_TRACKER_NO_PROMPT"))
m = Path.home() / ".visa_tracker_acknowledged"
print("marker_path=", m)
print("marker_exists=", m.exists())
