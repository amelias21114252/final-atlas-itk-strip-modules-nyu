#!/usr/bin/env python3
"""
plot_multi_inputnoise_LBNL_one_channel_subcategories.py

Analyze LBNL input-noise JSON files and save plots only for problem
module/stream combinations.

Run:
    python plot_multi_inputnoise_LBNL_one_channel_subcategories.py -i "LBNL/HX/SN*/*.json" -o "LBNL/HX"

Optional PDF-only run:
    python plot_multi_inputnoise_LBNL_one_channel_subcategories.py \
        -i "LBNL/HX/SN*/*.json" \
        -o "LBNL/HX" \
        --no_png

Category definitions handled by this input-noise script:
    Category B(i)  : Away stream has >= 10 channels above 1100 ENC.
    Category B(ii) : Under stream has >= 10 channels above 1100 ENC.
    Category C(i)  : Away stream has >= 10 channels below 600 ENC.
    Category C(ii) : Under stream has >= 10 channels below 600 ENC.
    Category D(ii) : Incomplete input-noise dataset.
    Category E(ii) : Input-noise data unavailable or could not be processed.

IV-only categories A, D(i), and E(i) are not evaluated by this script.

Expected input-noise dataset:
    25 JSON test files per hybrid/module.

Plot behavior:
    * Every module and both streams are analyzed.
    * A module-stream plot is saved when that stream has at least one
      channel above 1100 ENC, at least one channel below 600 ENC,
      or Category D(ii).
    * Category E(ii)-only streams are summarized but cannot be plotted when
      there are no valid curves.
    * Plots contain no dashed threshold lines or red category annotations.
    * Selected PDFs are saved in the normal module folder and shared folder.
    * Each PDF is copied into every matching subcategory folder under:
          LBNL/HX/problem_inputnoise_plots/

      Official categories:
          Category_B_i_away_high_inputnoise/
          Category_B_ii_under_high_inputnoise/
          Category_C_i_away_low_inputnoise/
          Category_C_ii_under_low_inputnoise/
          Category_D_ii_incomplete_inputnoise/

      Warning subcategories for 1-9 affected channels:
          Warning_B_i_away_1_to_9_high_channels/
          Warning_B_ii_under_1_to_9_high_channels/
          Warning_C_i_away_1_to_9_low_channels/
          Warning_C_ii_under_1_to_9_low_channels/
"""

import os
import re
import json
import shutil
import argparse
import datetime
from glob import glob
from pathlib import Path
from pprint import pprint
from collections import defaultdict, OrderedDict

import numpy as np

import matplotlib as mplt
mplt.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# Settings
# ============================================================

SITE = "LBNL"
DEFAULT_OUTPUT_DIR = "LBNL/HX"

EXPECTED_INPUTNOISE_TESTS = 25
KEEP_FIT_TYPE_CODE = 4

HIGH_NOISE_THRESHOLD_ENC = 1100.0
LOW_NOISE_THRESHOLD_ENC = 600.0
CATEGORY_MIN_CHANNELS = 10

CHANNEL_COUNT = 1280

SHARED_PROBLEM_PDF_FOLDER = "category_B_C_Dii_inputnoise_plots_pdf"

PROBLEM_PARENT_FOLDER = "problem_inputnoise_plots"

CATEGORY_PDF_FOLDERS = {
    "B(i)": "Category_B_i_away_high_inputnoise",
    "B(ii)": "Category_B_ii_under_high_inputnoise",
    "C(i)": "Category_C_i_away_low_inputnoise",
    "C(ii)": "Category_C_ii_under_low_inputnoise",
    "D(ii)": "Category_D_ii_incomplete_inputnoise",

    # Plot-trigger warning subcategories for 1-9 affected channels.
    "Warning B(i)": "Warning_B_i_away_1_to_9_high_channels",
    "Warning B(ii)": "Warning_B_ii_under_1_to_9_high_channels",
    "Warning C(i)": "Warning_C_i_away_1_to_9_low_channels",
    "Warning C(ii)": "Warning_C_ii_under_1_to_9_low_channels",
}


# ============================================================
# Helpers
# ============================================================

def flatten(input_data):
    """
    Recursively flatten numeric input-noise data.

    Accepts:
      * flat lists/tuples/NumPy arrays,
      * arbitrarily nested lists/tuples/arrays,
      * dictionaries whose values contain the numeric arrays.

    Booleans are rejected so they are not counted as 0/1 ENC values.
    """
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


def with_sn(serial):
    if serial is None:
        return ""

    serial = str(serial).strip()

    if not serial:
        return ""

    return serial if serial.startswith("SN") else f"SN{serial}"


def strip_sn(serial):
    serial = str(serial or "").strip()
    return serial[2:] if serial.startswith("SN") else serial


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

        return with_sn(module_name) if module_name else None

    except Exception:
        return None


def get_run_number(file_path):
    """
    Example:
        SN20USBHX2002099_03.json -> 3
    """
    basename = os.path.basename(file_path)
    match = re.search(r"_(\d+)\.json$", basename)

    if not match:
        return None

    return int(match.group(1))


def get_file_number(file_path):
    run_number = get_run_number(file_path)

    if run_number is not None:
        return f"{run_number:02}"

    basename = os.path.basename(file_path)
    return os.path.splitext(basename)[0].split("_")[-1]


def clean_parent_name(parent_name):
    if not parent_name or parent_name == "Unknown":
        return "Unknown"

    return with_sn(parent_name)


def format_timestamp(raw_timestamp):
    if not raw_timestamp:
        return "Unknown"

    return (
        str(raw_timestamp)
        .replace("T", " ")
        .split(".")[0]
        .replace("Z", "")
        .strip()
    )


def stream_category_names(stream):
    if stream == "away":
        return "B(i)", "C(i)"

    return "B(ii)", "C(ii)"


def format_run_list(run_numbers):
    if not run_numbers:
        return "None"

    return ", ".join(f"{run:02}" for run in sorted(run_numbers))


def normalize_fit_type_code(raw_fit_code):
    """
    Normalize fit_type_code values such as 4, "4", 4.0, or "4.0".

    Returns:
        int value when conversion is possible, otherwise None.
    """
    if raw_fit_code is None:
        return None

    try:
        return int(float(str(raw_fit_code).strip()))
    except (TypeError, ValueError):
        return None


def get_noise_result(results, stream):
    """
    Retrieve the requested stream using known key variants.
    """
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


# ============================================================
# Error/result storage
# ============================================================

def make_empty_result(module_name, stream):
    return {
        "module": module_name,
        "stream": stream,
        "valid_curves": [],
        "present_runs": set(),
        "valid_runs": set(),
        "missing_runs": set(),
        "invalid_runs": set(),
        "category_b_records": [],
        "category_c_records": [],
        "one_channel_high_records": [],
        "one_channel_low_records": [],
        "category_d_records": [],
        "category_e_records": [],
        "timestamp": "Unknown",
        "parent_name": "Unknown",
        "plot_saved": False,
        "plot_pdf": "",
        "shared_pdf": "",
        "category_pdf_copies": [],
        "plot_png": "",
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


# ============================================================
# File filtering and grouping
# ============================================================

def inspect_and_group_input_files(input_files):
    """
    Read enough metadata to group files by module.

    Files with the wrong fit_type_code are retained in the module's file list
    so that they can be reported as an incomplete D(ii) dataset instead of
    disappearing silently.
    """
    module_files = defaultdict(list)
    unreadable_files = []

    for file_path in input_files:
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

            if not module_name:
                unreadable_files.append(
                    (file_path, "Could not determine module name")
                )
                continue

            module_files[with_sn(module_name)].append(file_path)

        except Exception as exc:
            unreadable_files.append((file_path, str(exc)))

    ordered = OrderedDict()

    for module_name in sorted(module_files):
        ordered[module_name] = sorted(
            module_files[module_name],
            key=lambda path: (
                get_run_number(path) if get_run_number(path) is not None else 999,
                os.path.basename(path),
            ),
        )

    return ordered, unreadable_files


# ============================================================
# Analysis
# ============================================================

def analyze_module_both_streams(module_name, input_files):
    """
    Analyze BOTH input-noise streams for one module.

    Every JSON file is opened once. The away and under arrays are then checked
    independently using the official channel-count definitions:

      B(i)  away  > 1100 ENC for >= 10 channels
      B(ii) under > 1100 ENC for >= 10 channels
      C(i)  away  <  600 ENC for >= 10 channels
      C(ii) under <  600 ENC for >= 10 channels

    Returns:
        {
            "away": away_result,
            "under": under_result,
        }
    """
    stream_results = {
        "away": make_empty_result(module_name, "away"),
        "under": make_empty_result(module_name, "under"),
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

            # Accept 4, "4", and "4.0". If absent, continue processing.
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

            raw_timestamp = data.get("timestamp", data.get("date"))
            parent_name = clean_parent_name(
                data.get("parent_name", "Unknown")
            )

            for result in stream_results.values():
                if result["timestamp"] == "Unknown":
                    result["timestamp"] = format_timestamp(raw_timestamp)

                if result["parent_name"] == "Unknown":
                    result["parent_name"] = parent_name

            results_dict = data.get("results", {})

            # Process away and under independently.
            for stream in ("away", "under"):
                result = stream_results[stream]

                try:
                    noise_raw, matched_result_key = get_noise_result(
                        results_dict,
                        stream,
                    )

                    if noise_raw is None:
                        raise ValueError(
                            f"noise data is None for key "
                            f"'{matched_result_key}'"
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
                        print(
                            f"WARNING {basename} {stream}: removing "
                            f"{nonfinite_count} non-finite channel value(s)"
                        )
                        noise = noise[finite_mask]

                    if noise.size == 0:
                        raise ValueError(
                            "noise array has no finite channel values"
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
                        f">1100={high_count}, "
                        f"<600={low_count}, "
                        f"min={min_val:.1f}, "
                        f"max={max_val:.1f}, "
                        f"mean={mean_val:.1f}"
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
                            f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC "
                            f"(minimum {CATEGORY_MIN_CHANNELS}). "
                            f"Mean={mean_val:.1f} ENC."
                        )

                        print(f"FLAGGED {message}")

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
                            f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC "
                            f"(minimum {CATEGORY_MIN_CHANNELS}). "
                            f"Mean={mean_val:.1f} ENC."
                        )

                        print(f"FLAGGED {message}")

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

                    temp = float(
                        properties
                        .get("DCS", {})
                        .get("AMAC_NTCpb", 999)
                    )

                    result["valid_curves"].append({
                        "file_path": file_path,
                        "run": run_number,
                        "noise": noise,
                        "mean": mean_val,
                        "std": std_val,
                        "min": min_val,
                        "max": max_val,
                        "high_count": high_count,
                        "low_count": low_count,
                        "temperature": temp,
                    })

                    if run_number is not None:
                        result["valid_runs"].add(run_number)

                except Exception as stream_exc:
                    if run_number is not None:
                        result["invalid_runs"].add(run_number)

                    message = (
                        f"{basename} — {stream}-stream error: "
                        f"{stream_exc}"
                    )

                    add_record(
                        result,
                        "category_d_records",
                        file_path,
                        run_number,
                        message,
                    )

        except Exception as file_exc:
            # File-level failure affects both streams.
            for stream, result in stream_results.items():
                if run_number is not None:
                    result["invalid_runs"].add(run_number)

                message = (
                    f"{basename} — file could not be processed "
                    f"for {stream} stream: {file_exc}"
                )

                add_record(
                    result,
                    "category_d_records",
                    file_path,
                    run_number,
                    message,
                )

    for stream, result in stream_results.items():
        missing_runs = expected_runs - result["present_runs"]
        result["missing_runs"] = missing_runs

        for run_number in sorted(missing_runs):
            filename = f"{module_name}_{run_number:02}.json"
            message = f"{filename} — missing"

            add_record(
                result,
                "category_d_records",
                None,
                run_number,
                message,
            )
            result["category_d_records"][-1]["file"] = filename

        if not result["valid_curves"]:
            message = (
                f"No valid {stream}-stream input-noise curves "
                f"could be processed for {module_name}."
            )

            add_record(
                result,
                "category_e_records",
                None,
                None,
                message,
            )

    return stream_results


def get_result_categories(result):
    """
    Return all folder categories that apply to this stream result.

    Official categories:
      B(i), B(ii), C(i), C(ii), D(ii)

    Warning subcategories:
      Warning B(i)  = away, 1-9 channels above 1100 ENC
      Warning B(ii) = under, 1-9 channels above 1100 ENC
      Warning C(i)  = away, 1-9 channels below 600 ENC
      Warning C(ii) = under, 1-9 channels below 600 ENC
    """
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
    """
    Return True when at least one channel is outside the allowed range.

    This is a plotting trigger only. Official Category B/C assignment still
    requires at least CATEGORY_MIN_CHANNELS affected channels.
    """
    return bool(
        result["one_channel_high_records"]
        or result["one_channel_low_records"]
    )


def is_problem_result(result):
    """
    Plot a stream when it has:
      * at least one channel above 1100 ENC,
      * at least one channel below 600 ENC, or
      * Category D(ii) incomplete/invalid data.

    Category E(ii)-only results have no valid data to plot.
    """
    return bool(
        has_any_channel_issue(result)
        or result["category_d_records"]
    )


# ============================================================
# Plotting
# ============================================================

def plot_problem_module_stream(
    result,
    output_base_dir,
    save_png=True,
    force_plot=False,
):
    module_name = result["module"]
    stream = result["stream"]

    if not force_plot and not is_problem_result(result):
        print(f"Skipping clean plot: {module_name}, stream={stream}")
        return False

    if not result["valid_curves"]:
        print(
            f"Cannot plot {module_name}, stream={stream}: "
            "no valid curves are available."
        )
        return False

    print(f"Plotting problem module: {module_name}, stream={stream}")

    fig, ax = plt.subplots(figsize=(16, 9))

    curves = sorted(
        result["valid_curves"],
        key=lambda curve: (
            curve["run"] if curve["run"] is not None else 999,
            os.path.basename(curve["file_path"]),
        ),
    )

    n_curves = max(len(curves), 1)
    blues = mplt.cm.Blues(np.linspace(0.4, 0.9, n_curves))
    oranges = mplt.cm.Oranges(np.linspace(0.4, 0.9, n_curves))

    for idx, curve in enumerate(curves):
        temp = curve["temperature"]
        temp_label = "+20C" if temp > 10 else "-35C"
        color = oranges[idx] if temp > 10 else blues[idx]

        run_number = curve["run"]
        file_number = (
            f"{run_number:02}"
            if run_number is not None
            else get_file_number(curve["file_path"])
        )

        issue_text = ""

        ax.plot(
            range(len(curve["noise"])),
            curve["noise"],
            lw=1,
            ls="-",
            c=color,
            label=(
                f"{temp_label} file {file_number} "
                f"[mu: {curve['mean']:.1f}]"
                f"{issue_text}"
            ),
        )

    ax.set_xlim(0, CHANNEL_COUNT)
    ax.set_ylim(0, 2000)

    ax.set_xlabel("Channel number", labelpad=15, fontsize=38)
    ax.set_ylabel("Input noise [ENC]", labelpad=15, fontsize=38)

    ax.tick_params(axis="both", labelsize=28)
    ax.set_xticks(list(range(0, CHANNEL_COUNT + 1, 128)))

    handles, labels = ax.get_legend_handles_labels()
    seen = set()
    unique = []

    for handle, label in zip(handles, labels):
        if label not in seen:
            unique.append((handle, label))
            seen.add(label)

    if unique:
        ax.legend(
            *zip(*unique),
            loc="upper center",
            bbox_to_anchor=(0.5, 0.995),
            ncol=4,
            prop={"size": 14},
            frameon=False,
        )

    fig.text(
        0.15,
        0.31,
        r"3 point gain response curve, $-$350V, times UTC",
        color="k",
        size=22,
    )
    fig.text(
        0.15,
        0.27,
        f"{module_name}, Stream: {stream}",
        color="k",
        size=28,
    )
    fig.text(
        0.15,
        0.23,
        f"Parent Module: {result['parent_name']}",
        color="k",
        size=22,
    )
    fig.text(
        0.15,
        0.19,
        f"Timestamp: {result['timestamp']}",
        color="k",
        size=22,
    )

    plt.tight_layout(pad=0.3)
    plt.subplots_adjust(top=0.88, bottom=0.12, left=0.11, right=0.97)

    normal_dir = Path(output_base_dir) / module_name / "inputnoise"
    normal_dir.mkdir(parents=True, exist_ok=True)

    shared_dir = Path(output_base_dir) / SHARED_PROBLEM_PDF_FOLDER
    shared_dir.mkdir(parents=True, exist_ok=True)

    normal_pdf = normal_dir / f"{module_name}-{stream}.pdf"
    normal_png = normal_dir / f"{module_name}-{stream}.png"
    shared_pdf = shared_dir / f"{module_name}-{stream}.pdf"

    print(f"Saving problem PDF: {normal_pdf}")
    plt.savefig(normal_pdf, format="pdf")

    shutil.copy2(normal_pdf, shared_pdf)
    print(f"Copied problem PDF to: {shared_pdf}")

    category_pdf_copies = []

    for category_name in get_result_categories(result):
        category_folder_name = CATEGORY_PDF_FOLDERS[category_name]
        category_dir = Path(output_base_dir) / PROBLEM_PARENT_FOLDER / category_folder_name
        category_dir.mkdir(parents=True, exist_ok=True)

        category_pdf = category_dir / f"{module_name}-{stream}.pdf"
        shutil.copy2(normal_pdf, category_pdf)
        category_pdf_copies.append(str(category_pdf))

        print(
            f"Copied Category {category_name} PDF to: "
            f"{category_pdf}"
        )

    if save_png:
        print(f"Saving problem PNG: {normal_png}")
        plt.savefig(normal_png, format="png", dpi=200)

    plt.close(fig)

    result["plot_saved"] = True
    result["plot_pdf"] = str(normal_pdf)
    result["shared_pdf"] = str(shared_pdf)
    result["category_pdf_copies"] = category_pdf_copies
    result["plot_png"] = str(normal_png) if save_png else ""

    return True


# ============================================================
# Summary helpers
# ============================================================

def group_records(results, record_key):
    records = []

    for result in results:
        records.extend(result[record_key])

    return records


def unique_problem_modules(results):
    return {
        result["module"]
        for result in results
        if is_problem_result(result)
        or result["category_e_records"]
    }


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
        key = (record["module"], record["stream"])
        grouped[key].append(record)

    for module_name, stream in sorted(grouped):
        outfile.write(f"\nModule: {module_name}\n")
        outfile.write(f"Stream: {stream}\n")
        outfile.write("-" * 80 + "\n")

        for record in grouped[(module_name, stream)]:
            outfile.write(f"File: {record['file']}\n")
            outfile.write(f"Reason: {record['message']}\n\n")


def build_module_comments(results):
    comments = {
        "B(i)": OrderedDict(),
        "B(ii)": OrderedDict(),
        "C(i)": OrderedDict(),
        "C(ii)": OrderedDict(),
        "D(ii)": OrderedDict(),
        "E(ii)": OrderedDict(),
    }

    for result in sorted(results, key=lambda item: (item["module"], item["stream"])):
        module_name = result["module"]
        stream = result["stream"]
        category_b_name, category_c_name = stream_category_names(stream)

        if result["category_b_records"]:
            affected_runs = {
                record["run"]
                for record in result["category_b_records"]
                if record["run"] is not None
            }
            maximum_count = max(
                record.get("channel_count", 0)
                for record in result["category_b_records"]
            )
            comments[category_b_name][module_name] = (
                f"{stream.capitalize()}-stream input noise greater than "
                f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC for "
                f"{CATEGORY_MIN_CHANNELS} or more channels. "
                f"{len(affected_runs)}/{EXPECTED_INPUTNOISE_TESTS} tests affected. "
                f"Maximum high-channel count: {maximum_count}. "
                f"Affected runs: {format_run_list(affected_runs)}."
            )

        if result["category_c_records"]:
            affected_runs = {
                record["run"]
                for record in result["category_c_records"]
                if record["run"] is not None
            }
            maximum_count = max(
                record.get("channel_count", 0)
                for record in result["category_c_records"]
            )
            comments[category_c_name][module_name] = (
                f"{stream.capitalize()}-stream input noise less than "
                f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC for "
                f"{CATEGORY_MIN_CHANNELS} or more channels. "
                f"{len(affected_runs)}/{EXPECTED_INPUTNOISE_TESTS} tests affected. "
                f"Maximum low-channel count: {maximum_count}. "
                f"Affected runs: {format_run_list(affected_runs)}."
            )

        if result["category_d_records"]:
            affected_runs = {
                record["run"]
                for record in result["category_d_records"]
                if record["run"] is not None
            }

            existing = comments["D(ii)"].get(module_name, [])
            existing.append(
                f"{stream.capitalize()} stream: "
                f"{len(result['valid_runs'])}/{EXPECTED_INPUTNOISE_TESTS} "
                f"tests processed successfully; "
                f"incomplete/invalid runs: {format_run_list(affected_runs)}."
            )
            comments["D(ii)"][module_name] = existing

        if result["category_e_records"]:
            existing = comments["E(ii)"].get(module_name, [])
            existing.append(result["category_e_records"][0]["message"])
            comments["E(ii)"][module_name] = existing

    for category_name in ["D(ii)", "E(ii)"]:
        normalized = OrderedDict()

        for module_name, pieces in comments[category_name].items():
            normalized[module_name] = " ".join(pieces)

        comments[category_name] = normalized

    return comments


def write_error_summary_txt(results, output_dir, unreadable_files):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "inputnoise_error_summary_lbnl.txt"

    b_records = group_records(results, "category_b_records")
    c_records = group_records(results, "category_c_records")
    one_high_records = group_records(results, "one_channel_high_records")
    one_low_records = group_records(results, "one_channel_low_records")
    d_records = group_records(results, "category_d_records")
    e_records = group_records(results, "category_e_records")

    problem_modules = unique_problem_modules(results)
    plotted_streams = sum(1 for result in results if result["plot_saved"])

    with summary_path.open("w") as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("LBNL INPUT NOISE ERROR SUMMARY\n")
        outfile.write("=" * 80 + "\n\n")

        outfile.write(
            f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        outfile.write(
            f"High threshold: > {HIGH_NOISE_THRESHOLD_ENC:.0f} ENC for "
            f">= {CATEGORY_MIN_CHANNELS} channels\n"
        )
        outfile.write(
            f"Low threshold: < {LOW_NOISE_THRESHOLD_ENC:.0f} ENC for "
            f">= {CATEGORY_MIN_CHANNELS} channels\n"
        )
        outfile.write(
            f"Expected tests per module: {EXPECTED_INPUTNOISE_TESTS}\n\n"
        )

        outfile.write("FINAL SUMMARY\n")
        outfile.write("-" * 80 + "\n")
        outfile.write(
            f"TOTAL MODULES CHECKED: {len({r['module'] for r in results})}\n"
        )
        outfile.write(f"PROBLEM MODULES: {len(problem_modules)}\n")
        outfile.write(f"PROBLEM MODULE-STREAM PLOTS SAVED: {plotted_streams}\n")
        outfile.write(f"UNREADABLE / UNASSIGNED FILES: {len(unreadable_files)}\n\n")

        write_record_section(
            outfile,
            "CATEGORY B(i) / B(ii) — high input-noise channel counts",
            b_records,
        )
        write_record_section(
            outfile,
            "CATEGORY C(i) / C(ii) — low input-noise channel counts",
            c_records,
        )
        write_record_section(
            outfile,
            "ONE-CHANNEL HIGH WARNINGS — at least one channel above 1100 ENC",
            one_high_records,
        )
        write_record_section(
            outfile,
            "ONE-CHANNEL LOW WARNINGS — at least one channel below 600 ENC",
            one_low_records,
        )
        write_record_section(
            outfile,
            "CATEGORY D(ii) — incomplete input-noise dataset",
            d_records,
        )
        write_record_section(
            outfile,
            "CATEGORY E(ii) — input-noise data unavailable or unprocessable",
            e_records,
        )

        if unreadable_files:
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write("UNREADABLE / UNASSIGNED INPUT FILES\n")
            outfile.write("=" * 80 + "\n")

            for file_path, reason in unreadable_files:
                outfile.write(f"File: {file_path}\n")
                outfile.write(f"Reason: {reason}\n\n")

    print(f"Saved input-noise error summary: {summary_path}")
    return summary_path


def write_comment_dict(outfile, variable_name, comments):
    outfile.write(f"{variable_name} = {{\n")

    for module_name, comment in comments.items():
        outfile.write(f'    "{module_name}": "{comment}",\n')

    outfile.write("}\n\n")


def write_modules_format(outfile, comments):
    outfile.write('"modules": {\n')

    for module_name, comment in comments.items():
        outfile.write(
            f'    "{strip_sn(module_name)}": "{comment}",\n'
        )

    outfile.write("}\n\n")


def write_category_summary_txt(results, output_dir):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    summary_path = output_dir / "inputnoise_category_summary_lbnl.txt"
    comments = build_module_comments(results)

    with summary_path.open("w") as outfile:
        outfile.write("=" * 80 + "\n")
        outfile.write("LBNL INPUT NOISE CATEGORY SUMMARY\n")
        outfile.write("=" * 80 + "\n\n")

        outfile.write(
            "Category B(i): Away-stream input noise greater than "
            f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC for "
            f"{CATEGORY_MIN_CHANNELS} or more channels.\n"
        )
        outfile.write(
            "Category B(ii): Under-stream input noise greater than "
            f"{HIGH_NOISE_THRESHOLD_ENC:.0f} ENC for "
            f"{CATEGORY_MIN_CHANNELS} or more channels.\n"
        )
        outfile.write(
            "Category C(i): Away-stream input noise less than "
            f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC for "
            f"{CATEGORY_MIN_CHANNELS} or more channels.\n"
        )
        outfile.write(
            "Category C(ii): Under-stream input noise less than "
            f"{LOW_NOISE_THRESHOLD_ENC:.0f} ENC for "
            f"{CATEGORY_MIN_CHANNELS} or more channels.\n"
        )
        outfile.write("Category D(ii): Incomplete input-noise dataset.\n")
        outfile.write(
            "Category E(ii): Input-noise data unavailable or could not "
            "be processed.\n"
        )
        outfile.write(
            "Plot trigger: save a stream plot when at least one channel "
            "is above 1100 ENC or below 600 ENC. Official Category B/C "
            "still requires 10 or more affected channels.\n\n"
        )

        outfile.write("FINAL MODULE COUNTS\n")
        outfile.write("-" * 80 + "\n")

        for category_name, category_comments in comments.items():
            outfile.write(
                f"Category {category_name} modules: "
                f"{len(category_comments)}\n"
            )

        warning_folder_counts = {
            "Warning B(i)": set(),
            "Warning B(ii)": set(),
            "Warning C(i)": set(),
            "Warning C(ii)": set(),
        }

        for result in results:
            stream = result["stream"]

            if (
                result["one_channel_high_records"]
                and not result["category_b_records"]
            ):
                key = (
                    "Warning B(i)"
                    if stream == "away"
                    else "Warning B(ii)"
                )
                warning_folder_counts[key].add(result["module"])

            if (
                result["one_channel_low_records"]
                and not result["category_c_records"]
            ):
                key = (
                    "Warning C(i)"
                    if stream == "away"
                    else "Warning C(ii)"
                )
                warning_folder_counts[key].add(result["module"])

        for warning_name, modules in warning_folder_counts.items():
            outfile.write(
                f"{warning_name} modules: {len(modules)}\n"
            )

        outfile.write("\n")

        for category_name, category_comments in comments.items():
            outfile.write("=" * 80 + "\n")
            outfile.write(f"CATEGORY {category_name} MODULE SERIALS\n")
            outfile.write("=" * 80 + "\n\n")

            for module_name in category_comments:
                outfile.write(f'    "{strip_sn(module_name)}",\n')

            outfile.write("\n")

        variable_names = {
            "B(i)": "category_b_i_comments",
            "B(ii)": "category_b_ii_comments",
            "C(i)": "category_c_i_comments",
            "C(ii)": "category_c_ii_comments",
            "D(ii)": "category_d_ii_comments",
            "E(ii)": "category_e_ii_comments",
        }

        for category_name, category_comments in comments.items():
            outfile.write("=" * 80 + "\n")
            outfile.write(
                f"READY-TO-PASTE CATEGORY {category_name} COMMENTS\n"
            )
            outfile.write("=" * 80 + "\n\n")
            write_comment_dict(
                outfile,
                variable_names[category_name],
                category_comments,
            )

            outfile.write(
                f"CATEGORY {category_name} CATEGORY_DEFINITIONS FORMAT\n"
            )
            outfile.write("-" * 80 + "\n\n")
            write_modules_format(outfile, category_comments)

    print(f"Saved input-noise category summary: {summary_path}")
    return summary_path


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Analyze both LLBNL input-noise streams and save only the "
            "specific away or under stream that has Category B, "
            "C, or D(ii)."
        )
    )

    parser.add_argument(
        "--serial_number",
        help="Serial number, for example 20USBHX2002592",
    )

    parser.add_argument(
        "-i",
        "--input",
        help="Glob pattern, for example 'LBNL/HX/SN*/*.json'",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory. Default: {DEFAULT_OUTPUT_DIR}",
    )

    parser.add_argument(
        "--no_png",
        action="store_true",
        help="Save only PDFs, not PNGs.",
    )

    args = parser.parse_args()

    if args.input:
        input_files = sorted(glob(args.input))

    elif args.serial_number:
        serial = strip_sn(args.serial_number)
        pattern = f"{args.output}/SN{serial}/SN{serial}_*.json"
        input_files = sorted(glob(pattern))

    else:
        parser.error("Provide either --serial_number or -i/--input")

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    shared_pdf_dir = output_dir / SHARED_PROBLEM_PDF_FOLDER
    shared_pdf_dir.mkdir(parents=True, exist_ok=True)

    category_pdf_dirs = {}

    for category_name, folder_name in CATEGORY_PDF_FOLDERS.items():
        category_dir = output_dir / PROBLEM_PARENT_FOLDER / folder_name
        category_dir.mkdir(parents=True, exist_ok=True)
        category_pdf_dirs[category_name] = category_dir

    print("\n" + "=" * 80)
    print("LBNL INPUT NOISE — ONE-CHANNEL PLOT TRIGGER")
    print("=" * 80)
    print(f"Input files found: {len(input_files)}")
    print(f"Output folder: {output_dir}")
    print(f"Shared problem PDF folder: {shared_pdf_dir}")
    print("Category PDF folders:")

    for category_name, category_dir in category_pdf_dirs.items():
        print(f"  {category_name}: {category_dir}")

    print(f"Save PNG: {not args.no_png}")
    print("=" * 80 + "\n")

    if not input_files:
        print("No JSON files found.")
        empty_result = make_empty_result("Unknown", "under")
        add_record(
            empty_result,
            "category_e_records",
            None,
            None,
            "No JSON files found. Input-noise analysis could not run.",
        )
        results = [empty_result]
        write_error_summary_txt(results, output_dir, [])
        write_category_summary_txt(results, output_dir)
        return

    pprint(input_files)

    module_file_map, unreadable_files = inspect_and_group_input_files(
        input_files
    )

    print(f"\nModules found: {len(module_file_map)}")
    print(f"Unreadable/unassigned files: {len(unreadable_files)}")

    if not module_file_map:
        empty_result = make_empty_result("Unknown", "under")
        add_record(
            empty_result,
            "category_e_records",
            None,
            None,
            "No module names could be determined from the input files.",
        )
        results = [empty_result]
        write_error_summary_txt(results, output_dir, unreadable_files)
        write_category_summary_txt(results, output_dir)
        return

    results = []

    for module_name, module_files in module_file_map.items():
        stream_results = analyze_module_both_streams(
            module_name,
            module_files,
        )

        away_result = stream_results["away"]
        under_result = stream_results["under"]

        away_has_problem = is_problem_result(away_result)
        under_has_problem = is_problem_result(under_result)

        if away_has_problem:
            print(
                f"Problem away stream found: {module_name}. "
                "Saving away graph only."
            )
            plot_problem_module_stream(
                away_result,
                output_base_dir=output_dir,
                save_png=not args.no_png,
                force_plot=False,
            )
        else:
            print(
                f"Clean away stream: {module_name}. "
                "Skipping away graph."
            )

        if under_has_problem:
            print(
                f"Problem under stream found: {module_name}. "
                "Saving under graph only."
            )
            plot_problem_module_stream(
                under_result,
                output_base_dir=output_dir,
                save_png=not args.no_png,
                force_plot=False,
            )
        else:
            print(
                f"Clean under stream: {module_name}. "
                "Skipping under graph."
            )

        results.extend([away_result, under_result])

    results.sort(key=lambda item: (item["module"], item["stream"]))

    error_summary_path = write_error_summary_txt(
        results,
        output_dir,
        unreadable_files,
    )
    category_summary_path = write_category_summary_txt(
        results,
        output_dir,
    )

    plotted_results = [
        result for result in results if result["plot_saved"]
    ]
    plotted_modules = {
        result["module"]
        for result in plotted_results
    }
    clean_results = [
        result
        for result in results
        if not is_problem_result(result)
        and not result["category_e_records"]
    ]
    e_only_results = [
        result
        for result in results
        if result["category_e_records"]
        and not result["plot_saved"]
    ]

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
    print(f"Modules analyzed: {len(module_file_map)}")
    print(f"Problem modules represented: {len(plotted_modules)}")
    print(f"Problem stream plots saved: {len(plotted_results)}")
    print(f"Clean module-stream plots skipped: {len(clean_results)}")
    print(f"E(ii)-only streams without plottable data: {len(e_only_results)}")
    print(f"Normal plot folders: {output_dir}/SN20USBHX.../inputnoise/")
    print(f"Shared problem PDFs: {shared_pdf_dir}")
    print("Category-specific PDF folders:")

    for category_name, category_dir in category_pdf_dirs.items():
        print(f"  {category_name}: {category_dir}")

    print(f"Saved: {error_summary_path}")
    print(f"Saved: {category_summary_path}")
    print("=" * 80)


if __name__ == "__main__":
    main()
