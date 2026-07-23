#!/usr/bin/env python3

# Run:
# python get_all_tests_categoryDandE_ii_bnl.py --test_name "Response Curve TC" --max_workers 6
#
# This version reads BNL HX serial numbers automatically from:
# serial_lists/bnl_hx_serials.txt
#
# First run:
# python get_module_serial_numbers.py --max_workers 6
#
# That creates:
# serial_lists/bnl_hx_serials.txt

import re
import shutil
import argparse
import subprocess

from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed


# ============================================================
# Constants
# ============================================================

CATEGORY_D_II_COMMENT = "Incomplete input-noise dataset."
CATEGORY_E_II_COMMENT = "Input-noise data unavailable or could not be processed."

DEFAULT_EXPECTED_TOTAL_TESTS = 25


# ============================================================
# Serial-number helpers
# ============================================================

def normalize_serial(serial):
    """
    Clean serial number and remove SN prefix if present.

    SN20USBHX2002099 -> 20USBHX2002099
    20USBHX2002099   -> 20USBHX2002099
    """
    serial = str(serial).strip()

    if serial.startswith("SN"):
        serial = serial[2:]

    return serial


def sn_format(serial):
    """
    Convert serial number to SN format.

    20USBHX2002099   -> SN20USBHX2002099
    SN20USBHX2002099 -> SN20USBHX2002099
    """
    serial = str(serial).strip()

    if serial.startswith("SN"):
        return serial

    return f"SN{serial}"


def load_serial_numbers(serial_file):
    """
    Read HX serial numbers from a text file.

    Expected format:
        20USBHX2002099
        20USBHX2002020
        20USBHX2002301

    Blank lines and lines starting with # are ignored.

    Only HX serial numbers are kept.
    ML serial numbers are skipped because this is an input-noise script.
    """

    serial_file = Path(serial_file)

    if not serial_file.exists():
        raise FileNotFoundError(
            f"Serial-number file not found: {serial_file}\n\n"
            f"First run:\n"
            f"python get_module_serial_numbers.py --max_workers 6\n\n"
            f"That should create:\n"
            f"serial_lists/bnl_hx_serials.txt"
        )

    serial_numbers = []
    skipped = []

    for line in serial_file.read_text().splitlines():
        line = line.strip()

        if not line:
            continue

        if line.startswith("#"):
            continue

        serial = normalize_serial(line)

        if "USBHX" not in serial:
            skipped.append(serial)
            continue

        serial_numbers.append(serial)

    # Remove duplicates while keeping original order
    seen = set()
    unique_serial_numbers = []

    for serial in serial_numbers:
        if serial not in seen:
            unique_serial_numbers.append(serial)
            seen.add(serial)

    if skipped:
        print("=" * 80)
        print("WARNING: skipped non-HX serial numbers from serial file")
        print("=" * 80)
        for serial in skipped:
            print(f"Skipped: {serial}")
        print("=" * 80)

    if not unique_serial_numbers:
        raise RuntimeError(f"No HX serial numbers found in {serial_file}")

    return unique_serial_numbers


# ============================================================
# Output helpers
# ============================================================

def write_python_list(f, title, values):
    f.write(f"{title} = [\n")

    for serial in values:
        f.write(f'    "{serial}",\n')

    f.write("]\n\n")


def write_python_comment_dict(f, title, values, comment):
    """
    Write a ready-to-paste Python dictionary where each serial
    maps to the same category comment.
    """

    f.write(f"{title} = {{\n")

    for serial in values:
        f.write(f'    "{sn_format(serial)}": "{comment}",\n')

    f.write("}\n\n")


def extract_run_number(json_path):
    """
    Extract run number from files like:

    SN20USBHX2001234_01.json
    SN20USBHX2001234_25.json
    """

    match = re.search(r"_(\d+)\.json$", json_path.name)

    if not match:
        return None

    return int(match.group(1))


def get_missing_runs(json_files, expected_total_tests=25):
    found_runs = set()

    for json_file in json_files:
        run_number = extract_run_number(json_file)

        if run_number is not None:
            found_runs.add(run_number)

    expected_runs = set(range(1, expected_total_tests + 1))

    return sorted(expected_runs - found_runs)


def format_run_list(run_numbers):
    return ", ".join(f"{run:02}" for run in run_numbers)


def make_category_d_comment(successful_count, expected_total_tests, missing_runs):
    incomplete_count = expected_total_tests - successful_count

    skipped_text = format_run_list(missing_runs) if missing_runs else "unknown"

    if incomplete_count == 1:
        file_text = "1 input-noise test file is empty or missing"
    else:
        file_text = f"{incomplete_count} input-noise test files are empty or missing"

    return (
        f"Incomplete input-noise dataset. "
        f"{successful_count}/{expected_total_tests} tests ran successfully; "
        f"{file_text}. "
        f"Skipped runs: {skipped_text}."
    )


# ============================================================
# Main worker
# ============================================================

def run_one_module(
    serial,
    script_path,
    hx_output_dir,
    expected_total_tests,
    test_name,
):
    """
    Run get_test_run2.py for one HX serial.

    Returns a result dictionary.
    """

    serial = normalize_serial(serial)
    sn_serial = sn_format(serial)

    final_module_dir = hx_output_dir / sn_serial
    temp_dir = hx_output_dir / f"temp_{sn_serial}"

    if temp_dir.exists():
        shutil.rmtree(temp_dir)

    temp_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = subprocess.run(
            [
                "python",
                str(script_path),
                "--serial_number",
                serial,
                "--test_name",
                test_name,
            ],
            check=False,
            capture_output=True,
            text=True,
            cwd=temp_dir,
        )

        stdout = result.stdout or ""
        stderr = result.stderr or ""

        json_files = sorted(temp_dir.rglob("*.json"))

        if json_files:
            final_module_dir.mkdir(parents=True, exist_ok=True)

            moved_files = []

            for item in json_files:
                target = final_module_dir / item.name

                if target.exists():
                    target.unlink()

                shutil.move(str(item), str(target))
                moved_files.append(target)

            moved_count = len(moved_files)

            missing_runs = get_missing_runs(
                moved_files,
                expected_total_tests=expected_total_tests,
            )

            if moved_count == expected_total_tests:
                status = "passed"
                comment = ""
            else:
                status = "category_d_ii"
                comment = make_category_d_comment(
                    successful_count=moved_count,
                    expected_total_tests=expected_total_tests,
                    missing_runs=missing_runs,
                )

            return {
                "serial": serial,
                "sn_serial": sn_serial,
                "status": status,
                "successful_count": moved_count,
                "expected_total_tests": expected_total_tests,
                "missing_count": expected_total_tests - moved_count,
                "missing_runs": missing_runs,
                "comment": comment,
                "final_module_dir": str(final_module_dir),
                "stdout": stdout,
                "stderr": stderr,
                "error": "",
            }

        return {
            "serial": serial,
            "sn_serial": sn_serial,
            "status": "category_e_ii",
            "successful_count": 0,
            "expected_total_tests": expected_total_tests,
            "missing_count": expected_total_tests,
            "missing_runs": list(range(1, expected_total_tests + 1)),
            "comment": CATEGORY_E_II_COMMENT,
            "final_module_dir": str(final_module_dir),
            "stdout": stdout,
            "stderr": stderr,
            "error": "",
        }

    except Exception as e:
        return {
            "serial": serial,
            "sn_serial": sn_serial,
            "status": "category_e_ii",
            "successful_count": 0,
            "expected_total_tests": expected_total_tests,
            "missing_count": expected_total_tests,
            "missing_runs": list(range(1, expected_total_tests + 1)),
            "comment": CATEGORY_E_II_COMMENT,
            "final_module_dir": str(final_module_dir),
            "stdout": "",
            "stderr": "",
            "error": str(e),
        }

    finally:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Run ITkDB Response Curve TC extraction for BNL HX serials"
    )

    parser.add_argument(
        "--test_name",
        default="Response Curve TC",
        help="Test name. For HX input noise, use 'Response Curve TC'.",
    )

    parser.add_argument(
        "--output_dir",
        default="BNL",
        help="Main output directory",
    )

    parser.add_argument(
        "--serial_file",
        default="serial_lists/bnl_hx_serials.txt",
        help="Text file containing BNL HX serial numbers",
    )

    parser.add_argument(
        "--script_path",
        default="get_test_run2.py",
        help="Path to get_test_run2.py",
    )

    parser.add_argument(
        "--max_workers",
        type=int,
        default=6,
        help="Number of parallel workers. Safe values: 4, 6, or 8.",
    )

    parser.add_argument(
        "--expected_total_tests",
        type=int,
        default=DEFAULT_EXPECTED_TOTAL_TESTS,
        help="Expected number of input-noise JSON files per HX module",
    )

    args = parser.parse_args()

    serial_numbers = load_serial_numbers(args.serial_file)

    expected_total_tests = args.expected_total_tests

    base_output_dir = Path(args.output_dir)
    hx_output_dir = base_output_dir / "HX"
    hx_output_dir.mkdir(parents=True, exist_ok=True)

    script_path = Path(args.script_path).resolve()

    if not script_path.exists():
        raise FileNotFoundError(
            f"Could not find script_path: {script_path}\n"
            f"Make sure get_test_run2.py is in this folder, or pass:\n"
            f"--script_path /path/to/get_test_run2.py"
        )

    passed = []
    category_d_failed = []
    category_e_ii_failed = []

    category_d_details = {}
    category_e_ii_details = {}

    results = []

    print("=" * 80)
    print("BNL HX INPUT-NOISE JSON GENERATION")
    print("=" * 80)
    print(f"Serial file: {args.serial_file}")
    print(f"Loaded HX modules: {len(serial_numbers)}")
    print(f"Test name: {args.test_name}")
    print(f"Output directory: {base_output_dir}")
    print(f"Script path: {script_path}")
    print(f"Expected tests per module: {expected_total_tests}")
    print(f"Parallel workers: {args.max_workers}")
    print("=" * 80)

    with ThreadPoolExecutor(max_workers=args.max_workers) as executor:

        future_to_serial = {
            executor.submit(
                run_one_module,
                serial,
                script_path,
                hx_output_dir,
                expected_total_tests,
                args.test_name,
            ): serial
            for serial in serial_numbers
        }

        for i, future in enumerate(as_completed(future_to_serial), start=1):

            serial = future_to_serial[future]
            result = future.result()
            results.append(result)

            print("=" * 80)
            print(f"[{i}/{len(serial_numbers)}] Finished {serial}")

            if result["stdout"]:
                print(result["stdout"])

            if result["stderr"]:
                print(result["stderr"])

            if result["error"]:
                print(f"Error: {result['error']}")

            if result["status"] == "passed":
                passed.append(serial)

                print(
                    f"✅ PASSED: {serial} — "
                    f"all {expected_total_tests} JSON files saved to {result['final_module_dir']}"
                )

            elif result["status"] == "category_d_ii":
                category_d_failed.append(serial)

                category_d_details[result["sn_serial"]] = {
                    "successful_count": result["successful_count"],
                    "expected_total_tests": result["expected_total_tests"],
                    "missing_count": result["missing_count"],
                    "missing_runs": result["missing_runs"],
                    "comment": result["comment"],
                }

                print(
                    f"⚠️ CATEGORY D(ii): {serial} — "
                    f"{result['successful_count']}/{expected_total_tests} JSON files; "
                    f"skipped runs: "
                    f"{format_run_list(result['missing_runs']) if result['missing_runs'] else 'unknown'}"
                )

            else:
                category_e_ii_failed.append(serial)

                category_e_ii_details[result["sn_serial"]] = {
                    "successful_count": result["successful_count"],
                    "expected_total_tests": result["expected_total_tests"],
                    "missing_count": result["missing_count"],
                    "missing_runs": result["missing_runs"],
                    "comment": result["comment"],
                }

                print(
                    f"❌ CATEGORY E(ii): {serial} — "
                    f"{result['comment']}"
                )

    # Keep output ordered like input serial_numbers
    passed = [s for s in serial_numbers if s in passed]
    category_d_failed = [s for s in serial_numbers if s in category_d_failed]
    category_e_ii_failed = [s for s in serial_numbers if s in category_e_ii_failed]

    # ============================================================
    # Summary page
    # ============================================================

    summary_path = hx_output_dir / "summary_page_bnl_HX.txt"

    with open(summary_path, "w") as f:

        f.write("=" * 80 + "\n")
        f.write("BNL HX FINAL SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"SERIAL FILE: {args.serial_file}\n")
        f.write(f"TEST NAME: {args.test_name}\n")
        f.write(f"EXPECTED TESTS PER MODULE: {expected_total_tests}\n\n")

        f.write(f"TOTAL MODULES CHECKED: {len(serial_numbers)}\n")
        f.write(f"PASSED MODULES 25/25 JSON FILES: {len(passed)}\n")
        f.write(f"CATEGORY D(ii) MODULES 1-24/25 JSON FILES: {len(category_d_failed)}\n")
        f.write(f"CATEGORY E(ii) MODULES 0/25 JSON FILES: {len(category_e_ii_failed)}\n\n")

        write_python_list(f, "passed_modules", passed)
        write_python_list(f, "category_d_ii_modules", category_d_failed)

        write_python_comment_dict(
            f,
            "category_e_ii_comments",
            category_e_ii_failed,
            CATEGORY_E_II_COMMENT,
        )

        f.write("=" * 80 + "\n")
        f.write("CATEGORY D(ii) DETAILS\n")
        f.write("=" * 80 + "\n\n")

        for serial in category_d_failed:
            sn_serial = sn_format(serial)
            details = category_d_details.get(sn_serial)

            if not details:
                continue

            f.write(f"{sn_serial}\n")
            f.write("-" * 80 + "\n")
            f.write(
                f"Successful tests: {details['successful_count']}/"
                f"{details['expected_total_tests']}\n"
            )
            f.write(f"Missing/empty tests: {details['missing_count']}\n")
            f.write(
                f"Skipped runs: "
                f"{format_run_list(details['missing_runs']) if details['missing_runs'] else 'unknown'}\n"
            )
            f.write(f"Comment: {details['comment']}\n\n")

        f.write("=" * 80 + "\n")
        f.write("CATEGORY E(ii) DETAILS\n")
        f.write("=" * 80 + "\n\n")

        for serial in category_e_ii_failed:
            sn_serial = sn_format(serial)
            details = category_e_ii_details.get(sn_serial)

            if not details:
                details = {
                    "successful_count": 0,
                    "expected_total_tests": expected_total_tests,
                    "missing_count": expected_total_tests,
                    "missing_runs": list(range(1, expected_total_tests + 1)),
                    "comment": CATEGORY_E_II_COMMENT,
                }

            f.write(f"{sn_serial}\n")
            f.write("-" * 80 + "\n")
            f.write(
                f"Successful tests: {details['successful_count']}/"
                f"{details['expected_total_tests']}\n"
            )
            f.write(f"Missing/empty tests: {details['missing_count']}\n")
            f.write("Skipped runs: all or unknown\n")
            f.write(f"Comment: {details['comment']}\n\n")

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY D(ii) COMMENTS\n")
        f.write("=" * 80 + "\n\n")

        f.write("category_d_ii_comments = {\n")

        for serial in category_d_failed:
            sn_serial = sn_format(serial)
            details = category_d_details.get(sn_serial)

            if not details:
                continue

            f.write(f'    "{sn_serial}": "{details["comment"]}",\n')

        f.write("}\n\n")

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY E(ii) COMMENTS\n")
        f.write("=" * 80 + "\n\n")

        f.write("category_e_ii_comments = {\n")

        for serial in category_e_ii_failed:
            sn_serial = sn_format(serial)
            details = category_e_ii_details.get(sn_serial)

            comment = (
                details["comment"]
                if details and details.get("comment")
                else CATEGORY_E_II_COMMENT
            )

            f.write(f'    "{sn_serial}": "{comment}",\n')

        f.write("}\n\n")

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY_DEFINITIONS FORMAT\n")
        f.write("=" * 80 + "\n\n")

        f.write('"modules": {\n')

        for serial in category_d_failed:
            serial_no_sn = normalize_serial(serial)
            sn_serial = sn_format(serial)
            details = category_d_details.get(sn_serial)

            if not details:
                continue

            f.write(f'    "{serial_no_sn}": "{details["comment"]}",\n')

        for serial in category_e_ii_failed:
            serial_no_sn = normalize_serial(serial)
            sn_serial = sn_format(serial)
            details = category_e_ii_details.get(sn_serial)

            comment = (
                details["comment"]
                if details and details.get("comment")
                else CATEGORY_E_II_COMMENT
            )

            f.write(f'    "{serial_no_sn}": "{comment}",\n')

        f.write("}\n")

    # ============================================================
    # Print final summary
    # ============================================================

    print("\n" + "=" * 80)
    print("BNL HX FINAL SUMMARY")
    print("=" * 80)

    print(f"\n✅ PASSED MODULES 25/25 JSON FILES ({len(passed)}):")

    for serial in passed:
        print(f"  ✅ {serial}")

    print(f"\n⚠️ CATEGORY D(ii) MODULES 1-24/25 JSON FILES ({len(category_d_failed)}):")

    for serial in category_d_failed:
        sn_serial = sn_format(serial)
        details = category_d_details.get(sn_serial)

        if details:
            print(
                f"  ⚠️ {serial} — "
                f"{details['successful_count']}/{details['expected_total_tests']} tests ran successfully; "
                f"skipped runs: "
                f"{format_run_list(details['missing_runs']) if details['missing_runs'] else 'unknown'}; "
                f"{details['comment']}"
            )
        else:
            print(f"  ⚠️ {serial}")

    print(f"\n❌ CATEGORY E(ii) MODULES 0/25 JSON FILES ({len(category_e_ii_failed)}):")

    for serial in category_e_ii_failed:
        sn_serial = sn_format(serial)
        details = category_e_ii_details.get(sn_serial)

        comment = (
            details["comment"]
            if details and details.get("comment")
            else CATEGORY_E_II_COMMENT
        )

        print(f"  ❌ {serial} — {comment}")

    print(f"\n📄 Summary saved to: {summary_path}")
    print(f"📁 HX modules saved inside: {hx_output_dir}")