"""
reproduce.py - proves the generator is reproducible.

It generates the dataset twice with the same seed into two temporary folders
and compares the row count and SHA-256 checksum of every file. It then
generates once more with a different seed to show the seed really matters.

Run:  python3 src/reproduce.py --scale starter
Exit code is 0 when both same-seed runs are identical, 1 otherwise.
"""

import argparse
import os
import sys
import tempfile

import config
import generate
import io_utils


def generate_into(folder, seed, scale):
    """Generate one dataset and return: file name -> (rows, checksum)."""
    data_folder = os.path.join(folder, "data")
    truth_folder = os.path.join(folder, "ground_truth")
    tables, ground_truth = generate.build_dataset(seed, config.SCALES[scale])
    manifest = generate.write_dataset(tables, ground_truth, seed, scale, data_folder, truth_folder)

    result = {}
    for relative in sorted(manifest["files"].keys()):
        rows = ""
        if relative.endswith(".csv"):
            if relative.startswith("ground_truth/"):
                path = os.path.join(truth_folder, os.path.basename(relative))
            else:
                path = os.path.join(data_folder, relative)
            rows = len(io_utils.read_csv(path))
        result[relative] = (rows, manifest["files"][relative])
    return result


def main():
    parser = argparse.ArgumentParser(description="Generate twice and compare checksums.")
    parser.add_argument("--scale", choices=list(config.SCALES.keys()), default="starter")
    parser.add_argument("--seed", type=int, default=config.DEFAULT_SEED)
    parser.add_argument("--data", default="data")
    parser.add_argument("--out", default="output")
    args = parser.parse_args()

    with tempfile.TemporaryDirectory() as folder_a, tempfile.TemporaryDirectory() as folder_b, \
            tempfile.TemporaryDirectory() as folder_c:
        run_a = generate_into(folder_a, args.seed, args.scale)
        run_b = generate_into(folder_b, args.seed, args.scale)
        run_c = generate_into(folder_c, args.seed + 1, args.scale)

    identical = 0
    different_with_new_seed = 0
    lines = ["| File | Rows | Run 1 checksum | Run 2 checksum | Same? |", "|---|---|---|---|---|"]
    for name in sorted(run_a.keys()):
        same = run_a[name] == run_b[name]
        if same:
            identical = identical + 1
        if run_a[name][1] != run_c[name][1]:
            different_with_new_seed = different_with_new_seed + 1
        lines.append("| " + name + " | " + str(run_a[name][0]) + " | " + run_a[name][1][0:16] + " | "
                     + run_b[name][1][0:16] + " | " + ("YES" if same else "NO") + " |")
    all_identical = identical == len(run_a)

    # Also compare with the dataset saved in the repository, if present.
    committed_note = "No saved dataset was found to compare against."
    manifest_path = os.path.join(args.data, args.scale, "manifest.json")
    if os.path.exists(manifest_path):
        import json
        with open(manifest_path, "r", encoding="utf-8") as f:
            saved = json.load(f)
        if saved["seed"] == args.seed:
            matching = 0
            for name in run_a:
                if saved["files"].get(name) == run_a[name][1]:
                    matching = matching + 1
            committed_note = (str(matching) + " of " + str(len(run_a))
                              + " files also match the checksums saved in " + manifest_path + ".")
            if matching != len(run_a):
                all_identical = False

    text = "# Reproducibility check (" + args.scale + ", seed " + str(args.seed) + ")\n\n"
    text = text + "Two runs with the same seed: " + str(identical) + " of " + str(len(run_a)) + " files identical.\n\n"
    text = text + committed_note + "\n\n"
    text = text + "A third run with seed " + str(args.seed + 1) + " changed " + str(different_with_new_seed)
    text = text + " files, which shows the seed controls the data. Files that do not change are the fixed master tables.\n\n"
    text = text + "Checksums are SHA-256, shortened to 16 characters here.\n\n" + "\n".join(lines) + "\n"
    io_utils.write_text(os.path.join(args.out, args.scale, "reproducibility.md"), text)

    print("Reproducibility (" + args.scale + "):", identical, "of", len(run_a), "files identical across two runs")
    print(" ", committed_note)
    print("  Different seed changed", different_with_new_seed, "files")
    if not all_identical:
        print("  FAIL: runs are not identical")
        sys.exit(1)


if __name__ == "__main__":
    main()
