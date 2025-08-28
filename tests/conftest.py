from pathlib import Path
import sys

# Ensure the app directory is in the Python path for imports
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
