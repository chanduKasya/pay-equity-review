"""
run_all.py - runs the whole workflow in order with one command.

    python3 src/run_all.py --scale starter
    python3 src/run_all.py --scale full

Steps: generate -> validate -> detect -> evaluate -> reproducibility check.
It stops at the first step that fails.
"""

import argparse
import os
import subprocess
import sys

import config


def main():
    parser = argparse.ArgumentParser(description="Run the full workflow.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    args = parser.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    steps = [
        ["generate.py", "--scale", args.scale, "--seed", str(args.seed)],
        ["validate.py", "--scale", args.scale],
        ["detect.py", "--scale", args.scale],
        ["evaluate.py", "--scale", args.scale],
        ["reproduce.py", "--scale", args.scale, "--seed", str(args.seed)],
    ]
    for step in steps:
        print("")
        print("=== " + step[0] + " ===")
        command = [sys.executable, os.path.join(here, step[0])] + step[1:]
        result = subprocess.run(command)
        if result.returncode != 0:
            print("Stopped: " + step[0] + " failed.")
            sys.exit(result.returncode)
    print("")
    print("All steps finished. See the output/" + args.scale + " folder.")


if __name__ == "__main__":
    main()
