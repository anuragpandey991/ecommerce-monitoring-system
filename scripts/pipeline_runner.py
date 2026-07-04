import time
import subprocess
import sys

PYTHON = sys.executable

while True:

    subprocess.run([PYTHON, "-m", "scripts.run_cleaning"])
    subprocess.run([PYTHON, "-m", "scripts.run_aggregations"])

    print("pipeline cycle complete")

    time.sleep(60)