#!/usr/bin/env python3
"""
python generate_categoryBandC_BNL_from_inputnoise_summary.py

Reads:
    BNL/HX2/inputnoise_error_summary_bnl.txt (preferred)
    BNL/HX/inputnoise_error_summary.txt (fallback)

Writes:
    BNL/HX2/inputnoise_category_summary_bnl.txt

This generator parses the per-stream input-noise error-summary format.

Official category definitions:
    B(i)  away stream: more than 10 total channel values above 1100 ENC
          across all 25 tests.
    B(ii) under stream: more than 10 total channel values above 1100 ENC
          across all 25 tests.
    C(i)  away stream: more than 10 total channel values below 600 ENC
          across all 25 tests.
    C(ii) under stream: more than 10 total channel values below 600 ENC
          across all 25 tests.
    D(ii) incomplete or invalid input-noise dataset.
    E(ii) input-noise data unavailable or could not be processed.

Warning definitions:
    Warning B(i)  away stream: 1-10 total channel values above 1100 ENC.
    Warning B(ii) under stream: 1-10 total channel values above 1100 ENC.
    Warning C(i)  away stream: 1-10 total channel values below 600 ENC.
    Warning C(ii) under stream: 1-10 total channel values below 600 ENC.

The official B/C decision is based on the SUM of affected channel values
across all tests for one module and one stream. It is not based on whether
one individual JSON test contains more than 10 affected channels.

Run:
    python generate_categoryBandC_BNL_from_inputnoise_summary.py

Optional:
    python generate_categoryBandC_BNL_from_inputnoise_summary.py \
        --input_file BNL/HX/inputnoise_error_summary.txt \
        --output_file BNL/HX/inputnoise_category_summary_bnl.txt
"""

import re
import argparse
from pathlib import Path
from collections import OrderedDict, defaultdict


SITE = "BNL"

HIGH_NOISE_THRESHOLD = 1100
LOW_NOISE_THRESHOLD = 600

# "More than 10" means official Category B/C begins at 11 total values.
CATEGORY_TOTAL_VALUE_THRESHOLD = 10

TOTAL_EXPECTED_TESTS = 25


RUN_TEMPERATURE = {
    1: "warm",
    2: "cold",
    3: "cold",
    4: "warm",
    5: "cold",
    6: "warm",
    7: "cold",
    8: "warm",
    9: "cold",
    10: "warm",
    11: "cold",
    12: "warm",
    13: "cold",
    14: "warm",
    15: "cold",
    16: "warm",
    17: "cold",
    18: "warm",
    19: "cold",
    20: "warm",
    21: "cold",
    22: "warm",
    23: "cold",
    24: "cold",
    25: "warm",
}


# ============================================================
# Serial/run helpers
# ============================================================

def strip_sn(serial):
    serial = str(serial or "").strip()
    return serial[2:] if serial.startswith("SN") else serial


def with_sn(serial):
    serial = str(serial or "").strip()

    if not serial:
        return ""

    return serial if serial.startswith("SN") else f"SN{serial}"


def get_run_number(filename):
    match = re.search(r"_(\d+)\.json", str(filename))
    return int(match.group(1)) if match else None


def get_temperature_class(run_number):
    if run_number is None:
        return "unknown"

    return RUN_TEMPERATURE.get(run_number, "unknown")


def unique_affected_runs(records):
    return sorted({
        record["run"]
        for record in records
        if record.get("run") is not None
    })


def format_run_list(records):
    runs = unique_affected_runs(records)
    return ", ".join(f"{run:02}" for run in runs) if runs else "unknown"


def temperature_summary(records):
    modes = {
        record["temperature"]
        for record in records
        if record.get("temperature") in {"warm", "cold"}
    }

    if modes == {"warm"}:
        return "Warm-only."

    if modes == {"cold"}:
        return "Cold-only."

    if modes == {"warm", "cold"}:
        return "Warm/cold."

    return "Temperature unknown."


def concentration_summary(records):
    affected_test_count = len(unique_affected_runs(records))

    if affected_test_count == 1:
        return "Only 1 affected test."

    if affected_test_count == 2:
        return "Only 2 affected tests."

    return ""


# ============================================================
# Summary parser
# ============================================================

def split_summary_sections(text):
    """
    Return section-title -> section-body for blocks delimited by '=' lines.
    """
    pattern = re.compile(
        r"^={20,}\s*\n"
        r"(?P<title>[^\n]+)\n"
        r"={20,}\s*\n"
        r"(?P<body>.*?)(?=^={20,}\s*\n|\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )

    sections = OrderedDict()

    for match in pattern.finditer(text):
        sections[match.group("title").strip()] = match.group("body")

    return sections


def parse_record_section(section_body):
    """
    Parse records written as:

        Module: SN...
        Stream: away
        ----------------------------------------------------------------
        File: SN..._01.json
        Reason: ...

    Multiple file/reason pairs may appear in one module/stream block.
    """
    records = []

    block_pattern = re.compile(
        r"Module:\s*(SN20USBHX\d+)\s*\n"
        r"Stream:\s*(away|under)\s*\n"
        r"-{20,}\s*\n"
        r"(.*?)(?=\nModule:\s*SN20USBHX\d+\s*\nStream:|\Z)",
        flags=re.IGNORECASE | re.DOTALL,
    )

    pair_pattern = re.compile(
        r"File:\s*(.*?)\s*\n"
        r"Reason:\s*(.*?)(?=\nFile:|\Z)",
        flags=re.DOTALL,
    )

    for block_match in block_pattern.finditer(section_body):
        module = with_sn(block_match.group(1))
        stream = block_match.group(2).lower()
        block = block_match.group(3)

        for pair_match in pair_pattern.finditer(block):
            filename = pair_match.group(1).strip()
            reason = " ".join(pair_match.group(2).split())
            run = get_run_number(filename)

            records.append({
                "module": module,
                "stream": stream,
                "file": filename,
                "reason": reason,
                "run": run,
                "temperature": get_temperature_class(run),
            })

    return records


def extract_channel_count(reason, direction):
    """
    Extract the number of affected channel values in one test record.

    Supported examples:
        "12 channels above 1100 ENC"
        "12 channel values above 1100 ENC"
        "high_count = 12"
        "channel_count = 12"
    """
    if direction == "high":
        patterns = (
            r"Category\s+B\([^)]*\):\s*(\d+)\s+channel(?:s|\s+values?)?\s+above",
            r"(\d+)\s+channel(?:s|\s+values?)?\s+above",
            r"high_count\s*=\s*(\d+)",
            r"channel_count\s*=\s*(\d+)",
        )
    else:
        patterns = (
            r"Category\s+C\([^)]*\):\s*(\d+)\s+channel(?:s|\s+values?)?\s+below",
            r"(\d+)\s+channel(?:s|\s+values?)?\s+below",
            r"low_count\s*=\s*(\d+)",
            r"channel_count\s*=\s*(\d+)",
        )

    for pattern in patterns:
        match = re.search(pattern, reason, flags=re.IGNORECASE)

        if match:
            return int(match.group(1))

    return 0


def deduplicate_records(records):
    """
    Deduplicate repeated warning/official records.

    The same run can appear in both the official Category section and the
    one-channel warning section. Classification uses the warning sections,
    which contain every run having at least one affected value.
    """
    seen = set()
    unique = []

    for record in records:
        key = (
            record["module"],
            record["stream"],
            record["file"],
            record["reason"],
        )

        if key not in seen:
            unique.append(record)
            seen.add(key)

    return unique


def build_grouped_records(records, direction):
    grouped = defaultdict(list)

    for record in deduplicate_records(records):
        copied = dict(record)
        copied["channel_count"] = extract_channel_count(
            copied["reason"],
            direction,
        )

        # Ignore parser matches that did not produce a positive count.
        if copied["channel_count"] <= 0:
            continue

        grouped[(copied["module"], copied["stream"])].append(copied)

    return grouped


# ============================================================
# Comment builders
# ============================================================

def make_noise_comment(stream, direction, records):
    affected_runs = unique_affected_runs(records)
    affected_test_count = len(affected_runs)

    total_values = sum(
        record.get("channel_count", 0)
        for record in records
    )

    threshold = (
        HIGH_NOISE_THRESHOLD
        if direction == "high"
        else LOW_NOISE_THRESHOLD
    )

    comparison = "greater than" if direction == "high" else "less than"
    value_name = "high" if direction == "high" else "low"

    error_rate = (
        100.0 * affected_test_count / TOTAL_EXPECTED_TESTS
        if TOTAL_EXPECTED_TESTS
        else 0.0
    )

    comment = (
        f"{stream} stream: {total_values} {value_name} values "
        f"{comparison} {threshold} ENC in "
        f"{affected_test_count}/{TOTAL_EXPECTED_TESTS} tests. "
        f"Error rate: {error_rate:.2f}%. "
        f"{temperature_summary(records)} "
        f"Affected runs: {format_run_list(records)}."
    )

    extra = concentration_summary(records)

    if extra:
        comment += f" {extra}"

    return comment


def make_d_comment(module_records):
    stream_parts = []
    by_stream = defaultdict(list)

    for record in module_records:
        by_stream[record["stream"]].append(record)

    for stream in ("away", "under"):
        records = by_stream.get(stream, [])

        if not records:
            continue

        affected_runs = unique_affected_runs(records)

        if affected_runs:
            successful = max(
                TOTAL_EXPECTED_TESTS - len(affected_runs),
                0,
            )

            stream_parts.append(
                f"{stream.capitalize()} stream: "
                f"{successful}/{TOTAL_EXPECTED_TESTS} tests processed; "
                f"incomplete/invalid runs: "
                f"{', '.join(f'{run:02}' for run in affected_runs)}."
            )
        else:
            stream_parts.append(
                f"{stream.capitalize()} stream: "
                f"{records[0]['reason']}"
            )

    return " ".join(stream_parts)


def make_e_comment(module_records):
    pieces = []
    seen = set()

    for record in module_records:
        text = (
            f"{record['stream'].capitalize()} stream: "
            f"{record['reason']}"
        )

        if text not in seen:
            pieces.append(text)
            seen.add(text)

    return " ".join(pieces)


# ============================================================
# Build official categories and warnings
# ============================================================

def parse_inputnoise_error_summary(text):
    sections = split_summary_sections(text)

    def find_section(prefix):
        for title, body in sections.items():
            if title.upper().startswith(prefix.upper()):
                return body

        return ""

    # These sections contain every run having at least one affected value.
    # They are therefore the source of truth for aggregate totals.
    all_high_records = parse_record_section(
        find_section("ONE-CHANNEL HIGH WARNINGS")
    )
    all_low_records = parse_record_section(
        find_section("ONE-CHANNEL LOW WARNINGS")
    )

    d_records = parse_record_section(
        find_section("CATEGORY D(ii)")
    )
    e_records = parse_record_section(
        find_section("CATEGORY E(ii)")
    )

    all_high = build_grouped_records(
        all_high_records,
        "high",
    )
    all_low = build_grouped_records(
        all_low_records,
        "low",
    )

    parsed = {
        "category_b_i_comments": OrderedDict(),
        "category_b_ii_comments": OrderedDict(),
        "category_c_i_comments": OrderedDict(),
        "category_c_ii_comments": OrderedDict(),
        "warning_b_i_comments": OrderedDict(),
        "warning_b_ii_comments": OrderedDict(),
        "warning_c_i_comments": OrderedDict(),
        "warning_c_ii_comments": OrderedDict(),
        "category_d_ii_comments": OrderedDict(),
        "category_e_ii_comments": OrderedDict(),
    }

    # --------------------------------------------------------
    # Category B / high-value warnings
    # --------------------------------------------------------
    for (module, stream), records in sorted(all_high.items()):
        total_values = sum(
            record.get("channel_count", 0)
            for record in records
        )

        official_key = (
            "category_b_i_comments"
            if stream == "away"
            else "category_b_ii_comments"
        )
        warning_key = (
            "warning_b_i_comments"
            if stream == "away"
            else "warning_b_ii_comments"
        )

        comment = make_noise_comment(
            stream,
            "high",
            records,
        )

        # Official category is strictly MORE THAN 10 total values.
        if total_values > CATEGORY_TOTAL_VALUE_THRESHOLD:
            parsed[official_key][module] = comment
        elif total_values > 0:
            parsed[warning_key][module] = comment

    # --------------------------------------------------------
    # Category C / low-value warnings
    # --------------------------------------------------------
    for (module, stream), records in sorted(all_low.items()):
        total_values = sum(
            record.get("channel_count", 0)
            for record in records
        )

        official_key = (
            "category_c_i_comments"
            if stream == "away"
            else "category_c_ii_comments"
        )
        warning_key = (
            "warning_c_i_comments"
            if stream == "away"
            else "warning_c_ii_comments"
        )

        comment = make_noise_comment(
            stream,
            "low",
            records,
        )

        # Official category is strictly MORE THAN 10 total values.
        if total_values > CATEGORY_TOTAL_VALUE_THRESHOLD:
            parsed[official_key][module] = comment
        elif total_values > 0:
            parsed[warning_key][module] = comment

    # --------------------------------------------------------
    # Category D(ii)
    # --------------------------------------------------------
    d_by_module = defaultdict(list)

    for record in d_records:
        d_by_module[record["module"]].append(record)

    for module in sorted(d_by_module):
        parsed["category_d_ii_comments"][module] = make_d_comment(
            d_by_module[module]
        )

    # --------------------------------------------------------
    # Category E(ii)
    # --------------------------------------------------------
    e_by_module = defaultdict(list)

    for record in e_records:
        e_by_module[record["module"]].append(record)

    for module in sorted(e_by_module):
        parsed["category_e_ii_comments"][module] = make_e_comment(
            e_by_module[module]
        )

    return parsed


# ============================================================
# Output helpers
# ============================================================

def write_comment_dict(outfile, variable_name, comments):
    outfile.write(f"{variable_name} = {{\n")

    for module, comment in comments.items():
        outfile.write(f'    "{module}": "{comment}",\n')

    outfile.write("}\n\n")


def write_serial_list(outfile, variable_name, comments):
    outfile.write(f"{variable_name} = [\n")

    for module in comments:
        outfile.write(f'    "{strip_sn(module)}",\n')

    outfile.write("]\n\n")


def write_modules_format(outfile, comments):
    outfile.write('"modules": {\n')

    for module, comment in comments.items():
        outfile.write(
            f'    "{strip_sn(module)}": "{comment}",\n'
        )

    outfile.write("}\n\n")


def merge_comment_maps(comment_maps):
    """
    Merge comments without silently losing multiple category comments for the
    same module. Comments for the same module are joined with a space.
    """
    merged = OrderedDict()

    for comments in comment_maps:
        for module, comment in comments.items():
            if module in merged:
                merged[module] = f"{merged[module]} {comment}"
            else:
                merged[module] = comment

    return merged


def write_outputs(output_file, parsed):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    labels = OrderedDict([
        ("B(i)", "category_b_i_comments"),
        ("B(ii)", "category_b_ii_comments"),
        ("C(i)", "category_c_i_comments"),
        ("C(ii)", "category_c_ii_comments"),
        ("Warning B(i)", "warning_b_i_comments"),
        ("Warning B(ii)", "warning_b_ii_comments"),
        ("Warning C(i)", "warning_c_i_comments"),
        ("Warning C(ii)", "warning_c_ii_comments"),
        ("D(ii)", "category_d_ii_comments"),
        ("E(ii)", "category_e_ii_comments"),
    ])

    variable_lists = {
        "B(i)": "category_b_i_noise_high",
        "B(ii)": "category_b_ii_noise_high",
        "C(i)": "category_c_i_noise_low",
        "C(ii)": "category_c_ii_noise_low",
        "Warning B(i)": "warning_b_i_noise_high",
        "Warning B(ii)": "warning_b_ii_noise_high",
        "Warning C(i)": "warning_c_i_noise_low",
        "Warning C(ii)": "warning_c_ii_noise_low",
        "D(ii)": "category_d_ii_modules",
        "E(ii)": "category_e_ii_modules",
    }

    with output_file.open("w") as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write(f"{SITE} INPUT NOISE CATEGORY SUMMARY\n")
        outfile.write("=" * 80 + "\n\n")

        outfile.write(
            f"Official Category B threshold: more than "
            f"{CATEGORY_TOTAL_VALUE_THRESHOLD} total channel values "
            f"greater than {HIGH_NOISE_THRESHOLD} ENC across all "
            f"{TOTAL_EXPECTED_TESTS} tests for one stream.\n"
        )
        outfile.write(
            f"Official Category C threshold: more than "
            f"{CATEGORY_TOTAL_VALUE_THRESHOLD} total channel values "
            f"less than {LOW_NOISE_THRESHOLD} ENC across all "
            f"{TOTAL_EXPECTED_TESTS} tests for one stream.\n"
        )
        outfile.write(
            f"Warning threshold: 1-{CATEGORY_TOTAL_VALUE_THRESHOLD} "
            f"total affected channel values across all tests.\n"
        )
        outfile.write(
            f"Expected input-noise tests per module: "
            f"{TOTAL_EXPECTED_TESTS}\n\n"
        )

        outfile.write("FINAL MODULE COUNTS\n")
        outfile.write("-" * 80 + "\n")

        for label, key in labels.items():
            outfile.write(
                f"{label} modules: {len(parsed[key])}\n"
            )

        outfile.write("\n")

        for label, key in labels.items():
            comments = parsed[key]

            outfile.write("=" * 80 + "\n")
            outfile.write(f"{label.upper()} MODULE SERIALS\n")
            outfile.write("=" * 80 + "\n\n")

            write_serial_list(
                outfile,
                variable_lists[label],
                comments,
            )

            outfile.write("=" * 80 + "\n")
            outfile.write(
                f"READY-TO-PASTE {label.upper()} COMMENTS\n"
            )
            outfile.write("=" * 80 + "\n\n")

            write_comment_dict(
                outfile,
                key,
                comments,
            )

            outfile.write(
                f"{label.upper()} CATEGORY_DEFINITIONS FORMAT\n"
            )
            outfile.write("-" * 80 + "\n\n")

            write_modules_format(
                outfile,
                comments,
            )

        combined_official = merge_comment_maps([
            parsed["category_b_i_comments"],
            parsed["category_b_ii_comments"],
            parsed["category_c_i_comments"],
            parsed["category_c_ii_comments"],
            parsed["category_d_ii_comments"],
            parsed["category_e_ii_comments"],
        ])

        combined_warnings = merge_comment_maps([
            parsed["warning_b_i_comments"],
            parsed["warning_b_ii_comments"],
            parsed["warning_c_i_comments"],
            parsed["warning_c_ii_comments"],
        ])

        outfile.write("=" * 80 + "\n")
        outfile.write(
            "COMBINED OFFICIAL B + C + D(ii) + E(ii) "
            "CATEGORY_DEFINITIONS FORMAT\n"
        )
        outfile.write("=" * 80 + "\n\n")

        write_modules_format(
            outfile,
            combined_official,
        )

        outfile.write("=" * 80 + "\n")
        outfile.write(
            "COMBINED 1-10 TOTAL-VALUE WARNING "
            "ADDITIONAL_COMMENTS FORMAT\n"
        )
        outfile.write("=" * 80 + "\n\n")

        write_modules_format(
            outfile,
            combined_warnings,
        )

    print(f"Saved: {output_file}")


def print_counts(parsed):
    print("=" * 80)
    print(f"{SITE} INPUT NOISE CATEGORY COUNTS")
    print("=" * 80)

    for key in (
        "category_b_i_comments",
        "category_b_ii_comments",
        "category_c_i_comments",
        "category_c_ii_comments",
        "warning_b_i_comments",
        "warning_b_ii_comments",
        "warning_c_i_comments",
        "warning_c_ii_comments",
        "category_d_ii_comments",
        "category_e_ii_comments",
    ):
        print(f"{key}: {len(parsed[key])}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Generate BNL input-noise category comments using total "
            "affected channel values across all tests."
        )
    )

    parser.add_argument(
        "--input_file",
        default=None,
        help=(
            "Input inputnoise_error_summary.txt file. If omitted, the script "
            "checks BNL/HX2 first and then BNL/HX."
        ),
    )

    parser.add_argument(
        "--output_file",
        default="BNL/HX2/inputnoise_category_summary_bnl.txt",
        help=(
            "Output input-noise category summary file. "
            "Default: BNL/HX2/inputnoise_category_summary_bnl.txt"
        ),
    )

    args = parser.parse_args()

    if args.input_file:
        input_candidates = [Path(args.input_file)]
    else:
        input_candidates = [
            Path("BNL/HX2/inputnoise_error_summary_bnl.txt"),
            Path("BNL/HX/inputnoise_error_summary.txt"),
        ]

    input_path = next(
        (candidate for candidate in input_candidates if candidate.is_file()),
        None,
    )

    if input_path is None:
        checked = "\n".join(f"  - {path}" for path in input_candidates)
        raise FileNotFoundError(
            "Input-noise error summary was not found. Checked:\n"
            f"{checked}\n"
            "Run the BNL input-noise plotting script first, and make sure its "
            "-o/--output directory matches the folder used here."
        )

    output_path = Path(args.output_file)

    print(f"Reading: {input_path}")
    print(f"Writing: {output_path}")

    text = input_path.read_text(encoding="utf-8")
    parsed = parse_inputnoise_error_summary(text)

    print_counts(parsed)
    write_outputs(output_path, parsed)


if __name__ == "__main__":
    main()
