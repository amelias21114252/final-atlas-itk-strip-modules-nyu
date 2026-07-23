#!/usr/bin/env python3

# Run:
# python get_all_tests_categoryE_i_bnl.py --test_name "Module AMAC IV TC" --max_workers 6
#
# This version reads BNL ML serial numbers automatically from:
# serial_lists/bnl_ml_serials.txt


import os
import json
import argparse
import itkdb

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# Constants
# ============================================================

CATEGORY_E_I_COMMENT = "IV data unavailable or could not be processed."

EXPECTED_IV_TESTS = 24


# ============================================================
# Helpers
# ============================================================

def normalize_serial(serial):
    """
    Clean serial number and remove SN prefix if present.

    SN20USBML1235274 -> 20USBML1235274
    20USBML1235274   -> 20USBML1235274
    """
    serial = str(serial).strip()

    if serial.startswith("SN"):
        serial = serial[2:]

    return serial


def sn_format(serial):
    """
    Convert serial number to SN format.

    20USBML1235274   -> SN20USBML1235274
    SN20USBML1235274 -> SN20USBML1235274
    """
    serial = str(serial).strip()

    if serial.startswith("SN"):
        return serial

    return f"SN{serial}"


def load_serial_numbers(serial_file):
    """
    Read serial numbers from a text file.

    Expected file format:
        20USBML1235274
        20USBML1235275
        20USBML1235276

    Blank lines and comment lines starting with # are ignored.
    """

    serial_file = Path(serial_file)

    if not serial_file.exists():
        raise FileNotFoundError(
            f"Serial-number file not found: {serial_file}\n"
            f"First run:\n"
            f"python get_module_serial_numbers.py\n"
            f"This should create serial_lists/bnl_ml_serials.txt"
        )

    serial_numbers = []

    for line in serial_file.read_text().splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        serial_numbers.append(normalize_serial(line))

    # Remove duplicates but keep original order
    seen = set()
    unique_serial_numbers = []

    for serial in serial_numbers:
        if serial not in seen:
            unique_serial_numbers.append(serial)
            seen.add(serial)

    if not unique_serial_numbers:
        raise RuntimeError(f"No serial numbers found in {serial_file}")

    return unique_serial_numbers


def write_python_list(f, title, values):
    f.write(f"{title} = [\n")

    for serial in values:
        f.write(f'    "{serial}",\n')

    f.write("]\n\n")


def write_python_comment_dict(f, title, values, comment):
    f.write(f"{title} = {{\n")

    for serial in values:
        f.write(f'    "{sn_format(serial)}": "{comment}",\n')

    f.write("}\n\n")


def make_client(token):
    user = itkdb.core.UserBearer(bearer=token)
    client = itkdb.Client(user=user)
    return client


def get_test_run(serial_number, test_name, base_output_dir, token):
    """
    Run ITkDB Module AMAC IV extraction for one ML serial.

    Designed to run safely inside a thread.
    """

    serial_number = normalize_serial(serial_number)

    try:
        client = make_client(token)

        component = client.get(
            "getComponent",
            json={"component": serial_number},
        )

        test_ids = [
            y["id"]
            for x in component["tests"]
            for y in x["testRuns"]
            if x["name"] == test_name
        ]

        if not test_ids:
            return {
                "serial": serial_number,
                "sn_serial": sn_format(serial_number),
                "status": "category_e_i",
                "comment": CATEGORY_E_I_COMMENT,
                "written_count": 0,
                "output_dir": "",
                "test_id": "",
                "timestamp": "",
                "error": "No IV test run found.",
            }

        test_id = test_ids[0]

        test_run = client.get(
            "getTestRun",
            json={"testRun": test_id},
        )

        timestamp = test_run["components"][0]["stateTs"]

        innse_under = []
        innse_away = []
        current = []
        voltage = []

        for result in test_run["results"]:
            if result.get("name") == "innse_under":
                innse_under = result.get("value", [])

            elif result.get("name") == "innse_away":
                innse_away = result.get("value", [])

            elif result.get("code") == "CURRENT":
                current = result.get("value", [])

            elif result.get("code") == "VOLTAGE":
                voltage = result.get("value", [])

        if not current or not voltage:
            return {
                "serial": serial_number,
                "sn_serial": sn_format(serial_number),
                "status": "category_e_i",
                "comment": CATEGORY_E_I_COMMENT,
                "written_count": 0,
                "output_dir": "",
                "test_id": test_id,
                "timestamp": timestamp,
                "error": "CURRENT or VOLTAGE data missing.",
            }

        props = test_run["properties"][0]["value"] if test_run.get("properties") else {}

        amac_pb = props.get("AMAC_NTCpb")
        amac_x = props.get("AMAC_NTCx")
        amac_y = props.get("AMAC_NTCy")

        output_dir = base_output_dir / "ML" / sn_format(serial_number)
        output_dir.mkdir(parents=True, exist_ok=True)

        written_files = []

        for i in range(EXPECTED_IV_TESTS):
            json_data = {
                "serial_number": serial_number,
                "test_name": test_name,
                "test_id": test_id,
                "timestamp": timestamp,
                "properties": {
                    "DCS": {
                        "AMAC_NTCpb": amac_pb[i] if amac_pb and i < len(amac_pb) else None,
                        "AMAC_NTCx": amac_x[i] if amac_x and i < len(amac_x) else None,
                        "AMAC_NTCy": amac_y[i] if amac_y and i < len(amac_y) else None,
                    },
                    "det_info": {
                        "Address": list(range(10)),
                        "Channel": list(range(1, 11)),
                        "name": sn_format(serial_number),
                    },
                    "fit_type_code": 4,
                },
                "index": i,
                "results": {
                    "innse_under": innse_under[i] if i < len(innse_under) else None,
                    "innse_away": innse_away[i] if i < len(innse_away) else None,
                    "current": current[i] if i < len(current) else None,
                    "voltage": voltage[i] if i < len(voltage) else None,
                },
            }

            filename = output_dir / f"{sn_format(serial_number)}_{i + 1:02}.json"

            with open(filename, "w") as f:
                json.dump(json_data, f, indent=2)

            written_files.append(str(filename))

        return {
            "serial": serial_number,
            "sn_serial": sn_format(serial_number),
            "status": "passed",
            "comment": "",
            "written_count": len(written_files),
            "output_dir": str(output_dir),
            "test_id": test_id,
            "timestamp": timestamp,
            "error": "",
        }

    except Exception as e:
        return {
            "serial": serial_number,
            "sn_serial": sn_format(serial_number),
            "status": "category_e_i",
            "comment": CATEGORY_E_I_COMMENT,
            "written_count": 0,
            "output_dir": "",
            "test_id": "",
            "timestamp": "",
            "error": str(e),
        }


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Run ITkDB Module AMAC IV extraction for BNL ML serials"
    )

    parser.add_argument(
        "--test_name",
        default="Module AMAC IV TC",
        help="Test name",
    )

    parser.add_argument(
        "--output_dir",
        default="BNL",
        help="Main output directory",
    )

    parser.add_argument(
        "--serial_file",
        default="serial_lists/bnl_ml_serials.txt",
        help="Text file containing BNL ML serial numbers",
    )

    parser.add_argument(
        "--max_workers",
        type=int,
        default=6,
        help="Number of parallel workers. Safe values: 4, 6, or 8.",
    )

    args = parser.parse_args()

    token = os.getenv("ITK_DB_AUTH")

    if not token:
        raise RuntimeError(
            "ITK_DB_AUTH environment variable not set.\n"
            "Run:\n"
            "export ITK_DB_AUTH=YOUR_TOKEN"
        )

    serial_numbers = load_serial_numbers(args.serial_file)

    base_output_dir = Path(args.output_dir)
    ml_output_dir = base_output_dir / "ML"
    ml_output_dir.mkdir(parents=True, exist_ok=True)

    passed = []
    category_e_i_failed = []
    category_e_i_details = {}
    results = []

    print("=" * 80)
    print("BNL ML IV JSON GENERATION")
    print("=" * 80)
    print(f"Serial file: {args.serial_file}")
    print(f"Loaded ML modules: {len(serial_numbers)}")
    print(f"Test name: {args.test_name}")
    print(f"Output directory: {base_output_dir}")
    print(f"Parallel workers: {args.max_workers}")
    print("=" * 80)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:

        future_to_serial = {
            executor.submit(
                get_test_run,
                serial,
                args.test_name,
                base_output_dir,
                token,
            ): serial
            for serial in serial_numbers
        }

        for i, future in enumerate(as_completed(future_to_serial), start=1):

            serial = future_to_serial[future]
            result = future.result()
            results.append(result)

            print("\n" + "=" * 80)
            print(f"[{i}/{len(serial_numbers)}] Finished {serial}")

            if result["status"] == "passed":
                passed.append(serial)

                print(
                    f"✅ PASSED: {serial} — "
                    f"{result['written_count']} IV JSON files saved to {result['output_dir']}"
                )

            else:
                category_e_i_failed.append(serial)

                category_e_i_details[sn_format(serial)] = {
                    "comment": result["comment"],
                    "error": result["error"],
                    "test_id": result.get("test_id", ""),
                    "timestamp": result.get("timestamp", ""),
                }

                print(
                    f"❌ CATEGORY E(i): {serial} — "
                    f"{result['comment']}"
                )

                if result["error"]:
                    print(f"Error: {result['error']}")

    # Keep output ordered like input serial_numbers
    passed = [s for s in serial_numbers if s in passed]
    category_e_i_failed = [s for s in serial_numbers if s in category_e_i_failed]

    # ============================================================
    # Summary page
    # ============================================================

    summary_path = ml_output_dir / "summary_page_bnl_ml.txt"

    with open(summary_path, "w") as f:

        f.write("=" * 80 + "\n")
        f.write("BNL ML FINAL SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"SERIAL FILE: {args.serial_file}\n")
        f.write(f"TEST NAME: {args.test_name}\n\n")

        f.write(f"TOTAL MODULES CHECKED: {len(serial_numbers)}\n")
        f.write(f"WORKING MODULES: {len(passed)}\n")
        f.write(f"NOT WORKING MODULES: {len(category_e_i_failed)}\n")
        f.write(f"CATEGORY E(i) MODULES: {len(category_e_i_failed)}\n\n")

        write_python_list(f, "working_modules", passed)
        write_python_list(f, "not_working_modules", category_e_i_failed)

        f.write("=" * 80 + "\n")
        f.write("CATEGORY E(i) DETAILS\n")
        f.write("=" * 80 + "\n\n")

        for serial in category_e_i_failed:
            sn_serial = sn_format(serial)
            details = category_e_i_details.get(sn_serial, {})

            f.write(f"{sn_serial}\n")
            f.write("-" * 80 + "\n")
            f.write(f"Comment: {CATEGORY_E_I_COMMENT}\n")

            if details.get("test_id"):
                f.write(f"Test ID: {details['test_id']}\n")

            if details.get("timestamp"):
                f.write(f"Timestamp: {details['timestamp']}\n")

            if details.get("error"):
                f.write(f"Error: {details['error']}\n")

            f.write("\n")

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY E(i) COMMENTS\n")
        f.write("=" * 80 + "\n\n")

        write_python_comment_dict(
            f,
            "category_e_i_comments",
            category_e_i_failed,
            CATEGORY_E_I_COMMENT,
        )

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY_DEFINITIONS FORMAT\n")
        f.write("=" * 80 + "\n\n")

        f.write('"modules": {\n')

        for serial in category_e_i_failed:
            serial_no_sn = normalize_serial(serial)
            f.write(f'    "{serial_no_sn}": "{CATEGORY_E_I_COMMENT}",\n')

        f.write("}\n")

    # ============================================================
    # Print final summary
    # ============================================================

    print("\n" + "=" * 80)
    print("BNL ML FINAL SUMMARY")
    print("=" * 80)

    print(f"\n✅ WORKING MODULES ({len(passed)}):")
    print("[")
    for serial in passed:
        print(f'    "{serial}",')
    print("]")

    print(f"\n❌ CATEGORY E(i) MODULES ({len(category_e_i_failed)}):")
    print("category_e_i_comments = {")
    for serial in category_e_i_failed:
        print(f'    "{sn_format(serial)}": "{CATEGORY_E_I_COMMENT}",')
    print("}")

    print(f"\n❌ NOT WORKING MODULES ({len(category_e_i_failed)}):")
    print("[")
    for serial in category_e_i_failed:
        print(f'    "{serial}",  # {CATEGORY_E_I_COMMENT}')
    print("]")

    print(f"\n📄 Summary saved to: {summary_path}")
    print(f"📁 ML modules saved inside: {ml_output_dir}")