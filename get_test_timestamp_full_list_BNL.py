#!/usr/bin/env python3

# ============================================================
# get_test_timestamp_full_list_BNL.py
#
# Purpose:
#   Get Response Curve TC timestamps for BNL HX serial numbers.
#
# Reads:
#   bnl_hx_serials.txt
#   bnl_ml_serials.txt
#   all_module_hybrid_pairs.csv
#
# Writes:
#   timestamps_list_bnl.json
#   formatted_timestamps_bnl.txt
#
# Run:
#   export ITK_DB_AUTH=YOUR_TOKEN
#
#   python get_test_timestamp_full_list_BNL.py
#
# Optional:
#   python get_test_timestamp_full_list_BNL.py \
#       --hx_file bnl_hx_serials.txt \
#       --ml_file bnl_ml_serials.txt \
#       --pairs_csv all_module_hybrid_pairs.csv \
#       --max_workers 12
# ============================================================

import os
import re
import csv
import json
import argparse
from pathlib import Path
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

import itkdb


# ============================================================
# Helper functions
# ============================================================

def add_sn_prefix(serial):
    """
    Convert:
        20USBHX2001619   -> SN20USBHX2001619
        SN20USBHX2001619 -> SN20USBHX2001619
    """

    if serial is None:
        return ""

    serial = str(serial).strip()

    if not serial:
        return ""

    if serial.lower() == "nan":
        return ""

    if serial.upper() in ["MISSING_HX", "NONE", "NULL"]:
        return ""

    if serial.startswith("SN"):
        return serial

    return f"SN{serial}"


def remove_sn_prefix(serial):
    """
    Convert:
        SN20USBHX2001619 -> 20USBHX2001619
        20USBHX2001619   -> 20USBHX2001619
    """

    if serial is None:
        return ""

    serial = str(serial).strip()

    if not serial:
        return ""

    if serial.lower() == "nan":
        return ""

    if serial.upper() in ["MISSING_HX", "NONE", "NULL"]:
        return ""

    if serial.startswith("SN"):
        serial = serial[2:]

    return serial


def format_timestamp(timestamp):
    """
    Convert:
        2025-05-29T18:47:56.395Z

    Into:
        2025-05-29 18:47:56
    """

    if not timestamp:
        return ""

    try:
        timestamp_no_ms = str(timestamp).split(".")[0].replace("Z", "")

        dt = datetime.strptime(
            timestamp_no_ms,
            "%Y-%m-%dT%H:%M:%S",
        )

        return dt.strftime("%Y-%m-%d %H:%M:%S")

    except Exception:
        return (
            str(timestamp)
            .split(".")[0]
            .replace("T", " ")
            .replace("Z", "")
        )


def read_serial_file(serial_file, serial_type):
    """
    Read one serial per line from a text file.

    serial_type:
        "HX" or "ML"

    Keeps original order and removes duplicates.
    """

    serial_file = Path(serial_file)

    if not serial_file.exists():
        raise FileNotFoundError(f"Serial file not found: {serial_file}")

    serials = []
    seen = set()

    if serial_type.upper() == "HX":
        pattern = r"(?:SN)?(20USBHX\d+)"
    elif serial_type.upper() == "ML":
        pattern = r"(?:SN)?(20USBML\d+)"
    else:
        raise ValueError("serial_type must be HX or ML")

    with serial_file.open("r") as f:
        for line in f:
            line = line.strip()

            if not line:
                continue

            # Remove comments like:
            # 20USBHX2001619  # comment
            line = line.split("#")[0].strip()

            if not line:
                continue

            match = re.search(pattern, line)

            if not match:
                continue

            serial = remove_sn_prefix(match.group(1))

            if serial and serial not in seen:
                serials.append(serial)
                seen.add(serial)

    return serials


def read_pairs_csv(pairs_csv, institute="BNL"):
    """
    Read all_module_hybrid_pairs.csv.

    Expected columns:
        institute
        ml_serial_with_sn
        hx_serial_with_sn
        ml_serial
        hx_serial

    Returns:
        hx_to_ml dictionary:
            {
                "20USBHX2001619": "20USBML1235091",
                ...
            }

        ml_to_hx dictionary:
            {
                "20USBML1235091": "20USBHX2001619",
                ...
            }
    """

    pairs_csv = Path(pairs_csv)

    if not pairs_csv.exists():
        raise FileNotFoundError(f"Pairs CSV not found: {pairs_csv}")

    hx_to_ml = {}
    ml_to_hx = {}

    institute = institute.upper().strip()

    with pairs_csv.open("r", newline="") as f:
        reader = csv.DictReader(f)

        for row in reader:
            row_institute = str(row.get("institute", "")).upper().strip()

            if row_institute != institute:
                continue

            ml = remove_sn_prefix(
                row.get("ml_serial")
                or row.get("ml_serial_with_sn")
                or ""
            )

            hx = remove_sn_prefix(
                row.get("hx_serial")
                or row.get("hx_serial_with_sn")
                or ""
            )

            if ml and hx:
                hx_to_ml[hx] = ml
                ml_to_hx[ml] = hx

    return hx_to_ml, ml_to_hx


def make_client():
    token = os.getenv("ITK_DB_AUTH")

    if not token:
        raise RuntimeError(
            "ITK_DB_AUTH is not set.\n\n"
            "Run:\n"
            "    export ITK_DB_AUTH=YOUR_TOKEN"
        )

    user = itkdb.core.UserBearer(bearer=token)

    return itkdb.Client(user=user)


# ============================================================
# ITkDB timestamp lookup
# ============================================================

def get_hx_timestamp_entry(hx_serial, hx_to_ml, test_name):
    """
    Query ITkDB using HX serial number.

    Output format:
        ("SN20USBHX...", "SN20USBML...", "YYYY-MM-DD HH:MM:SS")
    """

    client = make_client()

    hx = remove_sn_prefix(hx_serial)
    ml = hx_to_ml.get(hx, "")

    try:
        component = client.get(
            "getComponent",
            json={"component": hx},
        )

        test_ids = [
            test_run["id"]
            for test_group in component.get("tests", [])
            for test_run in test_group.get("testRuns", [])
            if test_group.get("name") == test_name
        ]

        if not test_ids:
            return {
                "entry": (
                    add_sn_prefix(hx),
                    add_sn_prefix(ml),
                    "",
                ),
                "status": "NO TEST FOUND",
            }

        # Use the first matching test run.
        # If you later want newest test run, we can sort by stateTs.
        test_run = client.get(
            "getTestRun",
            json={"testRun": test_ids[0]},
        )

        raw_timestamp = ""

        if test_run.get("components"):
            raw_timestamp = test_run["components"][0].get("stateTs", "")

        timestamp = format_timestamp(raw_timestamp)

        return {
            "entry": (
                add_sn_prefix(hx),
                add_sn_prefix(ml),
                timestamp,
            ),
            "status": "OK",
        }

    except Exception as error:
        return {
            "entry": (
                add_sn_prefix(hx),
                add_sn_prefix(ml),
                "",
            ),
            "status": f"ERROR: {error}",
        }


def make_ml_only_entry(ml_serial):
    """
    Keep ML serials that do not have a matching HX in the CSV.
    """

    ml = remove_sn_prefix(ml_serial)

    return {
        "entry": (
            "",
            add_sn_prefix(ml),
            "",
        ),
        "status": "NO HX FOUND FOR ML",
    }


# ============================================================
# Save outputs
# ============================================================

def save_json(results, output_json):
    entries = [item["entry"] for item in results]

    output_json = Path(output_json)

    with output_json.open("w") as f:
        json.dump(entries, f, indent=2)

    print(f"✅ Saved JSON output to {output_json}")


def save_txt(results, output_txt, test_name):
    output_txt = Path(output_txt)

    with output_txt.open("w") as f:
        f.write("=" * 80 + "\n")
        f.write("BNL TIMESTAMP LIST\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Test name: {test_name}\n\n")

        f.write("Tuple format:\n")
        f.write('("SN20USBHX...", "SN20USBML...", "YYYY-MM-DD HH:MM:SS"),\n\n')

        f.write("Results:\n")
        f.write("-" * 80 + "\n")

        for item in results:
            hx, ml, timestamp = item["entry"]

            f.write(f'("{hx}", "{ml}", "{timestamp}"),')

            if item["status"] != "OK":
                f.write(f"  # {item['status']}")

            f.write("\n")

    print(f"✅ Saved TXT output to {output_txt}")


# ============================================================
# Print helpers
# ============================================================

def print_formatted_output(results):
    print("\nFormatted output:\n")

    for item in results:
        hx, ml, timestamp = item["entry"]
        print(f'("{hx}", "{ml}", "{timestamp}"),')


def print_summary(results):
    complete = []
    missing = []

    for item in results:
        hx, ml, timestamp = item["entry"]

        if hx and ml and timestamp:
            complete.append(item)
        else:
            missing.append(item)

    print("\n" + "=" * 80)
    print("FINAL SUMMARY")
    print("=" * 80)

    print(f"✅ COMPLETE HX + ML + TIMESTAMP: {len(complete)}")
    print(f"❌ MISSING / INCOMPLETE: {len(missing)}")

    if missing:
        print("\nMissing or incomplete entries:\n")

        for item in missing:
            hx, ml, timestamp = item["entry"]

            print(
                f'("{hx}", "{ml}", "{timestamp}"),'
                f'   # {item["status"]}'
            )


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Get BNL HX Response Curve TC timestamps and pair HX with ML."
    )

    parser.add_argument(
        "--hx_file",
        default="serial_lists/bnl_hx_serials.txt",
        help="Text file with one BNL HX serial per line",
    )

    parser.add_argument(
        "--ml_file",
        default="serial_lists/bnl_ml_serials.txt",
        help="Text file with one BNL ML serial per line",
    )

    parser.add_argument(
        "--pairs_csv",
        default="serial_lists/all_module_hybrid_pairs.csv",
        help="CSV file with ML-HX pairs",
    )

    parser.add_argument(
        "--test_name",
        default="Response Curve TC",
        help="ITkDB test name",
    )

    parser.add_argument(
        "--output_json",
        default="timestamps_list_bnl.json",
        help="Output JSON file",
    )

    parser.add_argument(
        "--output_txt",
        default="formatted_timestamps_bnl.txt",
        help="Output formatted TXT file",
    )

    parser.add_argument(
        "--max_workers",
        type=int,
        default=12,
        help="Number of parallel workers",
    )

    args = parser.parse_args()

    if not os.getenv("ITK_DB_AUTH"):
        raise RuntimeError(
            "ITK_DB_AUTH is not set.\n\n"
            "Run:\n"
            "    export ITK_DB_AUTH=YOUR_TOKEN"
        )

    hx_serials = read_serial_file(args.hx_file, serial_type="HX")
    ml_serials = read_serial_file(args.ml_file, serial_type="ML")

    hx_to_ml, ml_to_hx = read_pairs_csv(
        pairs_csv=args.pairs_csv,
        institute="BNL",
    )

    print("=" * 80)
    print("BNL TIMESTAMP LOOKUP")
    print("=" * 80)
    print(f"HX file: {args.hx_file}")
    print(f"ML file: {args.ml_file}")
    print(f"Pairs CSV: {args.pairs_csv}")
    print(f"Total HX serials loaded: {len(hx_serials)}")
    print(f"Total ML serials loaded: {len(ml_serials)}")
    print(f"Total HX→ML pairs loaded from CSV: {len(hx_to_ml)}")
    print(f"Test name: {args.test_name}")
    print(f"Parallel workers: {args.max_workers}")
    print("=" * 80)

    results_by_index = {}

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:
        future_to_index = {
            executor.submit(
                get_hx_timestamp_entry,
                hx,
                hx_to_ml,
                args.test_name,
            ): index
            for index, hx in enumerate(hx_serials)
        }

        for future in as_completed(future_to_index):
            index = future_to_index[future]
            item = future.result()
            results_by_index[index] = item

            hx, ml, timestamp = item["entry"]

            print(
                f'[{len(results_by_index)}/{len(hx_serials)}] '
                f'("{hx}", "{ml}", "{timestamp}") '
                f'-> {item["status"]}'
            )

    # Preserve HX file order.
    results = [
        results_by_index[index]
        for index in range(len(hx_serials))
    ]

    # Add ML-only rows if an ML exists in bnl_ml_serials.txt
    # but has no matching HX in the CSV.
    for ml in ml_serials:
        if ml not in ml_to_hx:
            results.append(make_ml_only_entry(ml))

    save_json(results, args.output_json)
    save_txt(results, args.output_txt, args.test_name)

    print_formatted_output(results)
    print_summary(results)

    print("\nDone.")


if __name__ == "__main__":
    main()