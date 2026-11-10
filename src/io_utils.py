"""
io_utils.py - small helper functions for writing files.
"""

import csv
import os


def write_csv(rows, folder, file_name, field_names):
    """
    Write a list of dictionaries to a CSV file.

    rows        : list of dictionaries, one dictionary per row
    folder      : folder to write into (created if it does not exist)
    file_name   : for example "role.csv"
    field_names : list of column names, in the order they should appear
    """
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, file_name)

    # newline="" and lineterminator="\n" make the file identical on
    # Windows, Mac and Linux. This matters for the checksum comparison.
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=field_names, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)

    return path
