#!/usr/bin/env python3
"""
Script: plot_combined_inputnoise_LBNL_one_channel_subcategories.py

Usage:
    python plot_combined_inputnoise_LBNL_one_channel_subcategories.py -i "LBNL/HX/SN*/*.json" -o "LBNL/HX2"

    python plot_combined_inputnoise_LBNL_one_channel_subcategories.py \
        --serial_number 20USBHX2002657

Behavior:
    * Checks away and under streams independently.
    * Category B(i): away > 1100 ENC for at least 10 channels.
    * Category B(ii): under > 1100 ENC for at least 10 channels.
    * Category C(i): away < 600 ENC for at least 10 channels.
    * Category C(ii): under < 600 ENC for at least 10 channels.
    * Category D(ii): incomplete or invalid input-noise data.
    * Category E(ii): input-noise data unavailable or unprocessable.
    * A stream is plotted when at least one channel is above 1100 ENC,
      at least one channel is below 600 ENC, or Category D(ii) applies.
    * Official Category B/C assignment still requires at least 10 channels.
    * Clean streams are skipped.
    * No dashed mean lines are drawn.
    * No red skipped/error comments are drawn on plots.
    * Problem PDFs are copied into:
          LBNL/HX/problem_inputnoise_histograms/
              Category_B_i_away_high_inputnoise/
              Category_B_ii_under_high_inputnoise/
              Category_C_i_away_low_inputnoise/
              Category_C_ii_under_low_inputnoise/
              Category_D_ii_incomplete_inputnoise/
              Warning_B_i_away_1_to_9_high_channels/
              Warning_B_ii_under_1_to_9_high_channels/
              Warning_C_i_away_1_to_9_low_channels/
              Warning_C_ii_under_1_to_9_low_channels/
"""

import os
import re
import json
import glob
import shutil
import argparse
from pathlib import Path
from datetime import datetime
from collections import defaultdict, OrderedDict

import numpy as np

import matplotlib as mplt
mplt.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm


# ============================================================
# Settings
# ============================================================

SITE = "LBNL"
DEFAULT_OUTPUT_DIR = "LBNL/HX2"

EXPECTED_INPUTNOISE_TESTS = 25
KEEP_FIT_TYPE_CODE = 4

HIGH_NOISE_THRESHOLD_ENC = 1100.0
LOW_NOISE_THRESHOLD_ENC = 600.0
CATEGORY_MIN_CHANNELS = 10

PROBLEM_PARENT_FOLDER = "problem_inputnoise_histograms"

CATEGORY_PDF_FOLDERS = {
    "B(i)": "Category_B_i_away_high_inputnoise",
    "B(ii)": "Category_B_ii_under_high_inputnoise",
    "C(i)": "Category_C_i_away_low_inputnoise",
    "C(ii)": "Category_C_ii_under_low_inputnoise",
    "D(ii)": "Category_D_ii_incomplete_inputnoise",
    "Warning B(i)": "Warning_B_i_away_1_to_9_high_channels",
    "Warning B(ii)": "Warning_B_ii_under_1_to_9_high_channels",
    "Warning C(i)": "Warning_C_i_away_1_to_9_low_channels",
    "Warning C(ii)": "Warning_C_ii_under_1_to_9_low_channels",
}


# ============================================================
# Helpers
# ============================================================

def flatten(input_data):
    """Recursively flatten numeric lists, tuples, arrays, or dictionaries."""
    flattened = []

    def visit(value):
        if isinstance(value, (bool, np.bool_)):
            raise TypeError("Boolean value found in input-noise data")

        if isinstance(value, (int, float, np.integer, np.floating)):
            flattened.append(float(value))
            return

        if isinstance(value, np.ndarray):
            for item in value.ravel().tolist():
                visit(item)
            return

        if isinstance(value, (list, tuple)):
            for item in value:
                visit(item)
            return

        if isinstance(value, dict):
            for item in value.values():
                visit(item)
            return

        raise TypeError(
            f"Unsupported input-noise data element: {type(value)}"
        )

    visit(input_data)
    return flattened


def json_to_dict(file_path):
    with open(file_path, "r") as infile:
        return json.load(infile)


def mkdir(path):
    os.makedirs(path, exist_ok=True)


def clean_serial(serial):
    serial = str(serial or "").strip()
    return serial[2:] if serial.startswith("SN") else serial


def ensure_sn(serial):
    serial = str(serial or "").strip()

    if not serial:
        return ""

    return serial if serial.startswith("SN") else f"SN{serial}"


def parse_timestamp(ts_str):
    try:
        ts_str = (
            str(ts_str)
            .replace("T", " ")
            .replace("Z", "")
            .split(".")[0]
            .strip()
        )
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.min


def clean_timestamp(raw_time):
    if not raw_time:
        return "Unknown Time"

    return (
        str(raw_time)
        .replace("T", " ")
        .split(".")[0]
        .replace("Z", "")
        .strip()
    )


def clean_parent_name(parent_name):
    if not parent_name or parent_name == "Unknown":
        return "Unknown"

    return ensure_sn(parent_name)


def get_run_number(file_path):
    basename = os.path.basename(file_path)
    match = re.search(r"_(\d+)\.json$", basename)

    if not match:
        return None

    return int(match.group(1))


def get_module_from_path(file_path):
    parts = os.path.normpath(file_path).split(os.sep)

    for part in parts:
        if part.startswith("SN20USB"):
            return part

    basename = os.path.basename(file_path)
    return os.path.splitext(basename)[0].split("_")[0]


def safe_get_module_name(file_path):
    try:
        data = json_to_dict(file_path)

        module_name = (
            data.get("component")
            or data.get("serial_number")
            or data.get("properties", {})
                  .get("det_info", {})
                  .get("name")
            or ""
        )

        return ensure_sn(module_name) if module_name else None

    except Exception:
        return None


def get_module_name(file_path):
    return safe_get_module_name(file_path) or get_module_from_path(file_path)


def normalize_fit_type_code(raw_fit_code):
    if raw_fit_code is None:
        return None

    try:
        return int(float(str(raw_fit_code).strip()))
    except (TypeError, ValueError):
        return None


def get_noise_result(results, stream):
    candidate_keys = (
        ("innse_under", "INNSE_UNDER", "inputnoise_under", "noise_under")
        if stream == "under"
        else ("innse_away", "INNSE_AWAY", "inputnoise_away", "noise_away")
    )

    for key in candidate_keys:
        if key in results:
            return results[key], key

    raise KeyError(
        f"Missing {stream}-stream input-noise data. "
        f"Tried keys: {', '.join(candidate_keys)}"
    )


def get_base_output_dir(input_files, fallback_output=DEFAULT_OUTPUT_DIR):
    if not input_files:
        return fallback_output

    first_file = os.path.normpath(input_files[0])
    parts = first_file.split(os.sep)

    if SITE in parts:
        idx = parts.index(SITE)

        if idx + 1 < len(parts):
            return os.path.join(parts[idx], parts[idx + 1])

    return fallback_output


def stream_category_names(stream):
    return ("B(i)", "C(i)") if stream == "away" else ("B(ii)", "C(ii)")


def format_run_list(run_numbers):
    if not run_numbers:
        return "None"

    return ", ".join(f"{run:02}" for run in sorted(run_numbers))


# ============================================================
# Result storage
# ============================================================

def make_empty_stream_result(module_name, stream):
    return {
        "module": module_name,
        "stream": stream,
        "file_data": [],
        "present_runs": set(),
        "valid_runs": set(),
        "invalid_runs": set(),
        "missing_runs": set(),
        "category_b_records": [],
        "category_c_records": [],
        "one_channel_high_records": [],
        "one_channel_low_records": [],
        "category_d_records": [],
        "category_e_records": [],
        "parent_name": "Unknown",
        "plot_saved": False,
        "plot_pdf": "",
        "plot_png": "",
        "category_pdf_copies": [],
    }


def add_record(result, key, file_path, run_number, message, **extra):
    record = {
        "module": result["module"],
        "stream": result["stream"],
        "file": os.path.basename(file_path) if file_path else "N/A",
        "run": run_number,
        "message": message,
    }
    record.update(extra)
    result[key].append(record)


def get_result_categories(result):
    """Return every official or warning subcategory applying to a stream."""
    categories = []
    stream = result["stream"]

    if result["category_b_records"]:
        categories.append("B(i)" if stream == "away" else "B(ii)")
    elif result["one_channel_high_records"]:
        categories.append(
            "Warning B(i)" if stream == "away" else "Warning B(ii)"
        )

    if result["category_c_records"]:
        categories.append("C(i)" if stream == "away" else "C(ii)")
    elif result["one_channel_low_records"]:
        categories.append(
            "Warning C(i)" if stream == "away" else "Warning C(ii)"
        )

    if result["category_d_records"]:
        categories.append("D(ii)")

    return categories


def has_any_channel_issue(result):
    return bool(
        result["one_channel_high_records"]
        or result["one_channel_low_records"]
    )


def is_problem_result(result):
    return bool(
        has_any_channel_issue(result)
        or result["category_d_records"]
    )


# ============================================================
# Grouping
# ============================================================

def group_files_by_module(input_files):
    grouped = defaultdict(list)
    unreadable = []

    for file_path in input_files:
        module_name = safe_get_module_name(file_path)

        if module_name:
            grouped[module_name].append(file_path)
        else:
            try:
                json_to_dict(file_path)
                module_name = get_module_from_path(file_path)
                grouped[module_name].append(file_path)
            except Exception as exc:
                unreadable.append((file_path, str(exc)))

    ordered = OrderedDict()

    for module_name in sorted(grouped):
        ordered[module_name] = sorted(
            grouped[module_name],
            key=lambda path: (
                get_run_number(path)
                if get_run_number(path) is not None
                else 999,
                os.path.basename(path),
            ),
        )

    return ordered, unreadable


# ============================================================
# Analysis
# ============================================================

def analyze_module_both_streams(module_name, input_files):
    stream_results = {
        "away": make_empty_stream_result(module_name, "away"),
        "under": make_empty_stream_result(module_name, "under"),
    }

    expected_runs = set(range(1, EXPECTED_INPUTNOISE_TESTS + 1))

    for file_path in input_files:
        basename = os.path.basename(file_path)
        run_number = get_run_number(file_path)

        for result in stream_results.values():
            if run_number is not None:
                result["present_runs"].add(run_number)

        try:
            data = json_to_dict(file_path)
            properties = data.get("properties", {})

            raw_fit_code = properties.get("fit_type_code")
            fit_code = normalize_fit_type_code(raw_fit_code)

            if raw_fit_code is not None and fit_code != KEEP_FIT_TYPE_CODE:
                message = (
                    f"{basename} — fit_type_code={raw_fit_code!r}; "
                    f"normalized={fit_code}; expected {KEEP_FIT_TYPE_CODE}"
                )

                for result in stream_results.values():
                    if run_number is not None:
                        result["invalid_runs"].add(run_number)

                    add_record(
                        result,
                        "category_d_records",
                        file_path,
                        run_number,
                        message,
                    )

                continue

            parent_name = clean_parent_name(
                data.get("parent_name", module_name)
            )

            for result in stream_results.values():
                if result["parent_name"] == "Unknown":
                    result["parent_name"] = parent_name

            results_dict = data.get("results", {})
            dcs = properties.get("DCS", {})
            temp = float(dcs.get("AMAC_NTCpb", 999))

            timestamp_raw = data.get(
                "timestamp",
                data.get("date", "Unknown Time"),
            )
            timestamp_clean = clean_timestamp(timestamp_raw)

            for stream in ("away", "under"):
                result = stream_results[stream]

                try:
                    noise_raw, matched_key = get_noise_result(
                        results_dict,
                        stream,
                    )

                    if noise_raw is None:
                        raise ValueError(
                            f"noise data is None for key '{matched_key}'"
                        )

                    noise = np.asarray(
                        flatten(noise_raw),
                        dtype=float,
                    ).reshape(-1)

                    if noise.size == 0:
                        raise ValueError("noise array is empty")

                    finite_mask = np.isfinite(noise)
                    nonfinite_count = int(
                        np.count_nonzero(~finite_mask)
                    )

                    if nonfinite_count:
                        noise = noise[finite_mask]

                    if noise.size == 0:
                        raise ValueError(
                            "noise array has no finite values"
                        )

                    high_count = int(
                        np.count_nonzero(
                            noise > HIGH_NOISE_THRESHOLD_ENC
                        )
                    )
                    low_count = int(
                        np.count_nonzero(
                            noise < LOW_NOISE_THRESHOLD_ENC
                        )
                    )

                    mean_val = float(np.mean(noise))
                    std_val = float(np.std(noise))
                    min_val = float(np.min(noise))
                    max_val = float(np.max(noise))

                    print(
                        f"CHECK {module_name} {stream} run "
                        f"{run_number if run_number is not None else '?'}: "
                        f"channels={noise.size}, "
                        f">1100={high_count}, <600={low_count}, "
                        f"mean={mean_val:.1f}, std={std_val:.1f}"
                    )

                    category_b_name, category_c_name = (
                        stream_category_names(stream)
                    )

                    if high_count >= 1:
                        warning_message = (
                            f"{basename} — {high_count} channel"
                            f"{'s' if high_count != 1 else ''} above "
                            f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC."
                        )
                        add_record(
                            result,
                            "one_channel_high_records",
                            file_path,
                            run_number,
                            warning_message,
                            channel_count=high_count,
                            mean=mean_val,
                        )

                    if high_count >= CATEGORY_MIN_CHANNELS:
                        message = (
                            f"{basename} — Category {category_b_name}: "
                            f"{high_count} channels above "
                            f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC."
                        )
                        add_record(
                            result,
                            "category_b_records",
                            file_path,
                            run_number,
                            message,
                            category=category_b_name,
                            channel_count=high_count,
                            mean=mean_val,
                        )

                    if low_count >= 1:
                        warning_message = (
                            f"{basename} — {low_count} channel"
                            f"{'s' if low_count != 1 else ''} below "
                            f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC."
                        )
                        add_record(
                            result,
                            "one_channel_low_records",
                            file_path,
                            run_number,
                            warning_message,
                            channel_count=low_count,
                            mean=mean_val,
                        )

                    if low_count >= CATEGORY_MIN_CHANNELS:
                        message = (
                            f"{basename} — Category {category_c_name}: "
                            f"{low_count} channels below "
                            f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC."
                        )
                        add_record(
                            result,
                            "category_c_records",
                            file_path,
                            run_number,
                            message,
                            category=category_c_name,
                            channel_count=low_count,
                            mean=mean_val,
                        )

                    result["file_data"].append({
                        "file_path": file_path,
                        "file": basename,
                        "run": run_number,
                        "temp": temp,
                        "noise": noise,
                        "timestamp": timestamp_clean,
                        "mean": mean_val,
                        "std": std_val,
                        "min": min_val,
                        "max": max_val,
                        "high_count": high_count,
                        "low_count": low_count,
                    })

                    if run_number is not None:
                        result["valid_runs"].add(run_number)

                except Exception as stream_exc:
                    if run_number is not None:
                        result["invalid_runs"].add(run_number)

                    add_record(
                        result,
                        "category_d_records",
                        file_path,
                        run_number,
                        (
                            f"{basename} — {stream}-stream error: "
                            f"{stream_exc}"
                        ),
                    )

        except Exception as file_exc:
            for stream, result in stream_results.items():
                if run_number is not None:
                    result["invalid_runs"].add(run_number)

                add_record(
                    result,
                    "category_d_records",
                    file_path,
                    run_number,
                    (
                        f"{basename} — file could not be processed "
                        f"for {stream} stream: {file_exc}"
                    ),
                )

    for stream, result in stream_results.items():
        missing_runs = expected_runs - result["present_runs"]
        result["missing_runs"] = missing_runs

        for run_number in sorted(missing_runs):
            filename = f"{module_name}_{run_number:02}.json"

            add_record(
                result,
                "category_d_records",
                None,
                run_number,
                f"{filename} — missing",
            )
            result["category_d_records"][-1]["file"] = filename

        if not result["file_data"]:
            add_record(
                result,
                "category_e_records",
                None,
                None,
                (
                    f"No valid combined-histogram data for "
                    f"{module_name}, stream {stream}."
                ),
            )

    return stream_results


# ============================================================
# Plotting
# ============================================================

def plot_problem_combined_stream(
    result,
    output_base_dir,
    save_png=True,
):
    if not is_problem_result(result):
        print(
            f"Skipping clean histogram: "
            f"{result['module']} {result['stream']}"
        )
        return False

    if not result["file_data"]:
        print(
            f"Cannot plot {result['module']} {result['stream']}: "
            "no valid histogram data."
        )
        return False

    module_name = result["module"]
    stream = result["stream"]
    parent_name = result["parent_name"]

    cold_data = sorted(
        [d for d in result["file_data"] if d["temp"] <= 10],
        key=lambda item: parse_timestamp(item["timestamp"]),
    )
    warm_data = sorted(
        [d for d in result["file_data"] if d["temp"] > 10],
        key=lambda item: parse_timestamp(item["timestamp"]),
    )

    cold_cmap = cm.get_cmap("Blues", max(len(cold_data), 1))
    warm_cmap = cm.get_cmap("Oranges", max(len(warm_data), 1))

    fig, ax = plt.subplots(figsize=(14, 6))

    legend_entries = []
    first_timestamp = None

    for entry in result["file_data"]:
        if entry["timestamp"] != "Unknown Time":
            first_timestamp = entry["timestamp"]
            break

    if first_timestamp:
        legend_entries.append(f"Timestamp: {first_timestamp}")

    for idx, entry in enumerate(cold_data):
        color = cold_cmap(idx)
        label = (
            f"cold_{idx + 1:02d} "
            f"T={entry['temp']:.1f}C | "
            f"mu={entry['mean']:.1f}, sigma={entry['std']:.1f}"
        )

        ax.hist(
            entry["noise"],
            bins=40,
            alpha=0.5,
            color=color,
            edgecolor="black",
            linewidth=0.3,
        )
        legend_entries.append(label)

    for idx, entry in enumerate(warm_data):
        color = warm_cmap(idx)
        label = (
            f"warm_{idx + 1:02d} "
            f"T={entry['temp']:.1f}C | "
            f"mu={entry['mean']:.1f}, sigma={entry['std']:.1f}"
        )

        ax.hist(
            entry["noise"],
            bins=40,
            alpha=0.5,
            color=color,
            edgecolor="black",
            linewidth=0.3,
        )
        legend_entries.append(label)

    ax.set_xlabel("Input Noise [ENC]")
    ax.set_ylabel("Counts")
    ax.grid(True)
    # Show the complete problem range, including values below 600 ENC
    # and high-noise values up to 2000 ENC.
    ax.set_xlim(600, 1200)

    title_str = (
        f"Module: {module_name} | Parent: {parent_name}\n"
        f"Overlaid {stream} Histograms"
    )

    if first_timestamp:
        title_str += f"\nTimestamp: {first_timestamp}"

    ax.set_title(title_str)

    if legend_entries:
        ax.legend(
            legend_entries,
            fontsize="x-small",
            loc="center left",
            bbox_to_anchor=(-0.02, 0.5),
        )

    plt.tight_layout()

    normal_dir = (
        Path(output_base_dir)
        / module_name
        / "histograms_combined"
    )
    normal_dir.mkdir(parents=True, exist_ok=True)

    save_base = normal_dir / f"{module_name}_combined-{stream}"
    normal_pdf = Path(f"{save_base}.pdf")
    normal_png = Path(f"{save_base}.png")

    print(f"Saving problem histogram PDF: {normal_pdf}")
    plt.savefig(normal_pdf, format="pdf")

    category_pdf_copies = []

    for category_name in get_result_categories(result):
        category_dir = (
            Path(output_base_dir)
            / PROBLEM_PARENT_FOLDER
            / CATEGORY_PDF_FOLDERS[category_name]
        )
        category_dir.mkdir(parents=True, exist_ok=True)

        category_pdf = (
            category_dir
            / f"{module_name}_combined-{stream}.pdf"
        )
        shutil.copy2(normal_pdf, category_pdf)
        category_pdf_copies.append(str(category_pdf))

        print(
            f"Copied Category {category_name} PDF to: "
            f"{category_pdf}"
        )

    if save_png:
        print(f"Saving problem histogram PNG: {normal_png}")
        plt.savefig(normal_png, format="png", dpi=300)

    plt.close(fig)

    result["plot_saved"] = True
    result["plot_pdf"] = str(normal_pdf)
    result["plot_png"] = str(normal_png) if save_png else ""
    result["category_pdf_copies"] = category_pdf_copies

    return True


# ============================================================
# Summary writers
# ============================================================

def collect_records(results, key):
    records = []

    for result in results:
        records.extend(result[key])

    return records


def write_record_section(outfile, title, records):
    outfile.write("\n" + "=" * 80 + "\n")
    outfile.write(title + "\n")
    outfile.write("=" * 80 + "\n")
    outfile.write(f"Total records: {len(records)}\n\n")

    if not records:
        outfile.write("None\n")
        return

    grouped = defaultdict(list)

    for record in records:
        grouped[(record["module"], record["stream"])].append(record)

    for module_name, stream in sorted(grouped):
        outfile.write(f"\nModule: {module_name}\n")
        outfile.write(f"Stream: {stream}\n")
        outfile.write("-" * 80 + "\n")

        for record in grouped[(module_name, stream)]:
            outfile.write(f"File: {record['file']}\n")
            outfile.write(f"Reason: {record['message']}\n\n")


def write_error_summary_txt(results, output_base_dir, unreadable_files):
    output_base_dir = Path(output_base_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    summary_path = (
        output_base_dir
        / "histograms_combined_error_summary.txt"
    )

    with summary_path.open("w") as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("LBNL COMBINED INPUT-NOISE HISTOGRAM SUMMARY\n")
        outfile.write("=" * 80 + "\n\n")
        outfile.write(
            f"Category B threshold: > "
            f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC for >= "
            f"{CATEGORY_MIN_CHANNELS} channels\n"
        )
        outfile.write(
            f"Category C threshold: < "
            f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC for >= "
            f"{CATEGORY_MIN_CHANNELS} channels\n"
        )
        outfile.write(
            f"Expected tests: {EXPECTED_INPUTNOISE_TESTS}\n"
        )
        outfile.write(
            "Plot trigger: at least one channel above 1100 ENC or below "
            "600 ENC, or Category D(ii). Official Category B/C still "
            "requires 10 or more affected channels.\n\n"
        )

        write_record_section(
            outfile,
            "CATEGORY B(i) / B(ii)",
            collect_records(results, "category_b_records"),
        )
        write_record_section(
            outfile,
            "CATEGORY C(i) / C(ii)",
            collect_records(results, "category_c_records"),
        )
        write_record_section(
            outfile,
            "ONE-CHANNEL HIGH WARNINGS — at least one channel above 1100 ENC",
            collect_records(results, "one_channel_high_records"),
        )
        write_record_section(
            outfile,
            "ONE-CHANNEL LOW WARNINGS — at least one channel below 600 ENC",
            collect_records(results, "one_channel_low_records"),
        )
        write_record_section(
            outfile,
            "CATEGORY D(ii)",
            collect_records(results, "category_d_records"),
        )
        write_record_section(
            outfile,
            "CATEGORY E(ii)",
            collect_records(results, "category_e_records"),
        )

        if unreadable_files:
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write("UNREADABLE / UNASSIGNED FILES\n")
            outfile.write("=" * 80 + "\n")

            for file_path, reason in unreadable_files:
                outfile.write(f"File: {file_path}\n")
                outfile.write(f"Reason: {reason}\n\n")

    print(f"Saved summary: {summary_path}")
    return summary_path


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Plot combined LBNL input-noise histograms for streams with "
            "at least one out-of-range channel or Category D(ii)."
        )
    )

    parser.add_argument(
        "--serial_number",
        help="Serial number, e.g. 20USBHX2002657",
    )

    parser.add_argument(
        "-i",
        "--input",
        help="Glob pattern, e.g. 'LBNL/HX/SN*/*.json'",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output base directory. Default is inferred from input "
            "or LBNL/HX2."
        ),
    )

    parser.add_argument(
        "--no_png",
        action="store_true",
        help="Save PDFs only.",
    )

    args = parser.parse_args()

    if args.input:
        input_files = sorted(glob.glob(args.input))

    elif args.serial_number:
        serial = clean_serial(args.serial_number)

        input_files = sorted(
            glob.glob(
                f"LBNL/HX/SN{serial}/SN{serial}_*.json"
            )
        )

        if not input_files:
            input_files = sorted(
                glob.glob(f"SN{serial}/SN{serial}_*.json")
            )

    else:
        parser.error("Provide either --serial_number or -i/--input")

    output_base_dir = (
        args.output
        or get_base_output_dir(input_files, DEFAULT_OUTPUT_DIR)
    )

    output_base_dir = Path(output_base_dir)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    for folder_name in CATEGORY_PDF_FOLDERS.values():
        (
            output_base_dir
            / PROBLEM_PARENT_FOLDER
            / folder_name
        ).mkdir(parents=True, exist_ok=True)

    print("\n" + "=" * 80)
    print("LBNL COMBINED INPUT-NOISE PROBLEM HISTOGRAMS")
    print("=" * 80)
    print(f"Input files found: {len(input_files)}")
    print(f"Output base directory: {output_base_dir}")
    print(
        f"Problem category parent folder: "
        f"{output_base_dir / PROBLEM_PARENT_FOLDER}"
    )
    print("=" * 80 + "\n")

    if not input_files:
        print("No JSON files found.")
        return

    grouped_files, unreadable_files = group_files_by_module(
        input_files
    )

    if not grouped_files:
        print("No modules found.")
        return

    results = []

    for module_name, files in grouped_files.items():
        stream_results = analyze_module_both_streams(
            module_name,
            files,
        )

        away_result = stream_results["away"]
        under_result = stream_results["under"]

        if is_problem_result(away_result):
            plot_problem_combined_stream(
                away_result,
                output_base_dir,
                save_png=not args.no_png,
            )
        else:
            print(
                f"Skipping clean away histogram: {module_name}"
            )

        if is_problem_result(under_result):
            plot_problem_combined_stream(
                under_result,
                output_base_dir,
                save_png=not args.no_png,
            )
        else:
            print(
                f"Skipping clean under histogram: {module_name}"
            )

        results.extend([away_result, under_result])

    results.sort(key=lambda item: (item["module"], item["stream"]))

    summary_path = write_error_summary_txt(
        results,
        output_base_dir,
        unreadable_files,
    )

    plotted_results = [
        result for result in results if result["plot_saved"]
    ]

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
    print(f"Modules processed: {len(grouped_files)}")
    print(
        f"Problem stream histograms saved: "
        f"{len(plotted_results)}"
    )
    print(
        f"Category folders: "
        f"{output_base_dir / PROBLEM_PARENT_FOLDER}"
    )
    print(f"Saved summary: {summary_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()