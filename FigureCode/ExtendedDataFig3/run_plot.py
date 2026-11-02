"""Render the current GIC concordance figure from explicitly prepared inputs."""
from pathlib import Path
import sys
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "_shared"))
from managed import run
if __name__ == "__main__":
    run(HERE)
