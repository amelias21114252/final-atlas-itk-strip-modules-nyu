#!/usr/bin/env python3
"""
Script: plot_detailed_inputnoise_histograms_per_file_BNL.py

Description:
    For each JSON file matching a pattern, this script:
    - Plots per-channel histograms for innse_under and innse_away
    - Plots one combined histogram for each stream
    - Saves plots inside BNL/HX2/SN.../detailedhistograms/
    - Writes a TXT summary with:
        Category B: all high input noise values > 1100
        Category C: all low input noise values < 600
        Category D: files skipped, empty, missing, or unreadable
        Category E: script did not run for entire module / no valid histograms

Usage:
    python plot_detailed_inputnoise_histograms_per_file_BNL.py -i 'BNL/HX/SN20USBHX2002099/SN20USBHX2002099_*.json'
    python plot_detailed_inputnoise_histograms_per_file_BNL.py -i 'BNL/HX/SN*/*.json'
    python plot_detailed_inputnoise_histograms_per_file_BNL.py --serial_number 20USBHX2002592
"""

import os
import json
import glob
import csv
import argparse
from collections import defaultdict

import numpy as np

import matplotlib as mplt
mplt.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# Global error summary
# ============================================================

error_summary = {
    "B": [],
    "C": [],
    "D": [],
    "E": [],
}


LOW_NOISE_THRESHOLD_ENC = 600.0
HIGH_NOISE_THRESHOLD_ENC = 1100.0
DEFAULT_OUTPUT_DIR = "BNL/HX2"



# ============================================================
# Helper functions
# ============================================================

def flatten(input_data):
    if isinstance(input_data, list) and all(isinstance(x, (int, float)) for x in input_data):
        return input_data

    if isinstance(input_data, list) and all(isinstance(x, list) for x in input_data):
        return [item for sublist in input_data for item in sublist]

    raise TypeError(f"Expected list of numbers or list of lists, got {type(input_data)}")


def json_to_dict(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def mkdir(path):
    os.makedirs(path, exist_ok=True)


def clean_serial(serial):
    return serial[2:] if serial.startswith("SN") else serial


def ensure_sn(serial):
    serial = str(serial)
    return serial if serial.startswith("SN") else f"SN{serial}"


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
        return data.get("properties", {}).get("det_info", {}).get("name", None)
    except Exception:
        return None


def get_module_name(file_path):
    module_name = safe_get_module_name(file_path)

    if module_name:
        return ensure_sn(module_name.replace("SN", ""))

    return get_module_from_path(file_path)


def get_base_output_dir(input_files, fallback_output="BNL/HX2"):
    if not input_files:
        return fallback_output

    first_file = os.path.normpath(input_files[0])
    parts = first_file.split(os.sep)

    if "BNL" in parts:
        idx = parts.index("BNL")

        if idx + 1 < len(parts):
            return os.path.join(parts[idx], parts[idx + 1])

    return fallback_output


def clean_timestamp(data):
    timestamp_raw = data.get("timestamp", data.get("date", "Unknown Time"))

    return (
        str(timestamp_raw)
        .replace("T", " ")
        .split(".")[0]
        .replace("Z", "")
        .strip()
    )


def clean_parent_name(parent_name):
    if not parent_name or parent_name == "Unknown":
        return "Unknown"

    parent_name = str(parent_name)

    if parent_name.startswith("SN"):
        return parent_name

    return f"SN{parent_name}"


def add_error(category, module_name, file_path, message, count=None, values=None, stream=None, plot_name=None):
    error_summary[category].append({
        "module": module_name or "Unknown",
        "file": os.path.basename(file_path) if file_path else "N/A",
        "stream": stream or "N/A",
        "plot": plot_name or "N/A",
        "message": message,
        "count": count,
        "values": values or [],
    })


def log_low_high_values(module_name, file_path, stream, plot_name, values):
    values = np.asarray(values, dtype=float).reshape(-1)
    values = values[np.isfinite(values)]

    low_vals = [
        float(v) for v in values
        if float(v) < LOW_NOISE_THRESHOLD_ENC
    ]
    high_vals = [
        float(v) for v in values
        if float(v) > HIGH_NOISE_THRESHOLD_ENC
    ]

    filename = os.path.basename(file_path)

    if high_vals:
        msg = (
            f"{filename} — {plot_name} — "
            f"high_count = {len(high_vals)}, high_values = {high_vals}"
        )
        print(f"⚠️ CATEGORY B: {msg}")
        add_error(
            "B",
            module_name,
            file_path,
            msg,
            count=len(high_vals),
            values=high_vals,
            stream=stream,
            plot_name=plot_name,
        )

    if low_vals:
        msg = (
            f"{filename} — {plot_name} — "
            f"low_count = {len(low_vals)}, low_values = {low_vals}"
        )
        print(f"⚠️ CATEGORY C: {msg}")
        add_error(
            "C",
            module_name,
            file_path,
            msg,
            count=len(low_vals),
            values=low_vals,
            stream=stream,
            plot_name=plot_name,
        )

    return low_vals, high_vals


def has_problem_values(values):
    """Return True when any finite channel is below 600 or above 1100 ENC."""
    try:
        arr = np.asarray(flatten(values), dtype=float).reshape(-1)
    except Exception:
        try:
            arr = np.asarray(values, dtype=float).reshape(-1)
        except Exception:
            return False

    arr = arr[np.isfinite(arr)]

    if arr.size == 0:
        return False

    return bool(
        np.any(arr < LOW_NOISE_THRESHOLD_ENC)
        or np.any(arr > HIGH_NOISE_THRESHOLD_ENC)
    )


def module_has_problem_values(file_paths):
    """Screen a module before plotting any detailed/channel histograms."""
    for file_path in file_paths:
        try:
            data = json_to_dict(file_path)
            results = data.get("results", {})

            for key in ("innse_under", "innse_away"):
                values = results.get(key, [])

                if values and has_problem_values(values):
                    return True

        except Exception:
            # Unreadable files remain Category D, but are not enough by
            # themselves to trigger problem-value plots.
            continue

    return False



# ============================================================
# File handling
# ============================================================

def filter_input_files(infiles, keep_fit_code=4):
    print(f"\nFiltering to keep fit_type_code = {keep_fit_code}")

    kept = []

    for f in infiles:
        try:
            data = json_to_dict(f)
            module_name = get_module_name(f)
            fit_code = data.get("properties", {}).get("fit_type_code")

            if fit_code == keep_fit_code:
                kept.append(f)
            else:
                msg = f"fit_type_code = {fit_code}"
                print(f"❌ CATEGORY D: {os.path.basename(f)} — {msg}")
                add_error("D", module_name, f, f"File skipped: {msg}")

        except Exception as e:
            module_name = get_module_from_path(f)
            msg = f"File skipped or unreadable: {e}"
            print(f"❌ CATEGORY D: {os.path.basename(f)} — {msg}")
            add_error("D", module_name, f, msg)

    print(f"Kept {len(kept)} files")
    print(f"Skipped {len(infiles) - len(kept)} files")

    return kept


def group_files_by_module(files):
    grouped = defaultdict(list)

    for f in files:
        module_name = get_module_name(f)
        grouped[module_name].append(f)

    return dict(grouped)


# ============================================================
# Plotting helpers
# ============================================================

def save_histogram(
    values,
    output_path,
    title,
    color,
    low_count,
    high_count,
    bins=20,
):
    values = np.array(values, dtype=float)

    if len(values) == 0:
        raise ValueError("cannot plot empty values")

    mean_val = float(np.mean(values))
    std_val = float(np.std(values))

    plt.figure(figsize=(8, 5))
    plt.hist(
        values,
        bins=bins,
        edgecolor="black",
        alpha=0.75,
        color=color,
    )

    plt.axvline(
        mean_val,
        color="red",
        linestyle="--",
        linewidth=1.5,
    )

    plt.text(
        0.98,
        0.95,
        f"(<{LOW_NOISE_THRESHOLD_ENC:.0f}: {low_count}, "
        f">{HIGH_NOISE_THRESHOLD_ENC:.0f}: {high_count})",
        transform=plt.gca().transAxes,
        ha="right",
        va="top",
        color="red",
        fontsize="small",
    )

    plt.title(title)
    plt.xlabel("Input Noise [ENC]")
    plt.ylabel("Frequency")
    plt.legend([
        f"Mean = {mean_val:.2f}",
        f"Std Dev = {std_val:.2f}",
    ])

    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()


# ============================================================
# Main plotting per file
# ============================================================

def plot_file_histograms(file_path, output_base_dir, module_name):
    try:
        data = json_to_dict(file_path)
    except Exception as e:
        msg = f"File unreadable: {e}"
        print(f"❌ CATEGORY D: {os.path.basename(file_path)} — {msg}")
        add_error("D", module_name, file_path, msg)
        return False

    try:
        base_name = os.path.splitext(os.path.basename(file_path))[0]
        timestamp_str = clean_timestamp(data)

        parent_name = clean_parent_name(data.get("parent_name", module_name))

        properties = data.get("properties", {})
        dcs = properties.get("DCS", {})

        ntcpb_temp = float(dcs.get("AMAC_NTCpb", 999))
        ntcx_temp = float(dcs.get("AMAC_NTCx", 999))

        is_warm = (ntcpb_temp > 10) and (ntcx_temp > 10)
        bar_color = "#ff7f0e" if is_warm else "#1f77b4"

        results = data.get("results", {})

        innse_under_list = results.get("innse_under", [])
        innse_away_list = results.get("innse_away", [])
        mean_under_list = results.get("innse_mean_under", [])
        mean_away_list = results.get("innse_mean_away", [])

        save_dir = os.path.join(output_base_dir, module_name, "detailedhistograms")
        mkdir(save_dir)

        title_prefix = f"{base_name}"

        if parent_name:
            title_prefix += f" ({parent_name})"

        made_plot = False
        low_high_rows = []

        # ========================================================
        # Per-channel innse_under
        # ========================================================

        if innse_under_list:
            if isinstance(innse_under_list, list) and all(isinstance(x, (int, float)) for x in innse_under_list):
                innse_under_list = [innse_under_list]

            for idx, arr in enumerate(innse_under_list):
                try:
                    arr = np.array(arr, dtype=float)

                    if len(arr) == 0:
                        raise ValueError("empty innse_under channel array")

                    plot_name = f"innse_under[{idx}]"
                    low_vals, high_vals = log_low_high_values(
                        module_name,
                        file_path,
                        "under",
                        plot_name,
                        arr,
                    )

                    print(
                        f"🔍 {base_name}_{plot_name}: "
                        f"<600: {len(low_vals)}, >1100: {len(high_vals)}"
                    )

                    if not (low_vals or high_vals):
                        print(
                            f"Skipping clean channel plot: "
                            f"{base_name}_{plot_name}"
                        )
                        continue

                    title = (
                        f"{title_prefix}\n"
                        f"{plot_name} "
                        f"(NTCpb={ntcpb_temp:.1f}C, NTCx={ntcx_temp:.1f}C)\n"
                        f"{timestamp_str}"
                    )

                    output_path = os.path.join(save_dir, f"{base_name}_innse_under_{idx}.pdf")

                    save_histogram(
                        arr,
                        output_path,
                        title,
                        bar_color,
                        len(low_vals),
                        len(high_vals),
                        bins=20,
                    )

                    low_high_rows.append({
                        "filename": os.path.basename(file_path),
                        "stream": "under",
                        "plot": plot_name,
                        "low_count": len(low_vals),
                        "low_values": low_vals,
                        "high_count": len(high_vals),
                        "high_values": high_vals,
                    })

                    made_plot = True

                except Exception as e:
                    msg = f"Could not plot innse_under[{idx}]: {e}"
                    print(f"❌ CATEGORY D: {base_name} — {msg}")
                    add_error("D", module_name, file_path, msg, stream="under", plot_name=f"innse_under[{idx}]")

        # ========================================================
        # Per-channel innse_away
        # ========================================================

        if innse_away_list:
            if isinstance(innse_away_list, list) and all(isinstance(x, (int, float)) for x in innse_away_list):
                innse_away_list = [innse_away_list]

            for idx, arr in enumerate(innse_away_list):
                try:
                    arr = np.array(arr, dtype=float)

                    if len(arr) == 0:
                        raise ValueError("empty innse_away channel array")

                    plot_name = f"innse_away[{idx}]"
                    low_vals, high_vals = log_low_high_values(
                        module_name,
                        file_path,
                        "away",
                        plot_name,
                        arr,
                    )

                    print(
                        f"🔍 {base_name}_{plot_name}: "
                        f"<600: {len(low_vals)}, >1100: {len(high_vals)}"
                    )

                    if not (low_vals or high_vals):
                        print(
                            f"Skipping clean channel plot: "
                            f"{base_name}_{plot_name}"
                        )
                        continue

                    title = (
                        f"{title_prefix}\n"
                        f"{plot_name} "
                        f"(NTCpb={ntcpb_temp:.1f}C, NTCx={ntcx_temp:.1f}C)\n"
                        f"{timestamp_str}"
                    )

                    output_path = os.path.join(save_dir, f"{base_name}_innse_away_{idx}.pdf")

                    save_histogram(
                        arr,
                        output_path,
                        title,
                        bar_color,
                        len(low_vals),
                        len(high_vals),
                        bins=20,
                    )

                    low_high_rows.append({
                        "filename": os.path.basename(file_path),
                        "stream": "away",
                        "plot": plot_name,
                        "low_count": len(low_vals),
                        "low_values": low_vals,
                        "high_count": len(high_vals),
                        "high_values": high_vals,
                    })

                    made_plot = True

                except Exception as e:
                    msg = f"Could not plot innse_away[{idx}]: {e}"
                    print(f"❌ CATEGORY D: {base_name} — {msg}")
                    add_error("D", module_name, file_path, msg, stream="away", plot_name=f"innse_away[{idx}]")

        # ========================================================
        # Combined innse_under
        # ========================================================

        try:
            if innse_under_list:
                all_under = flatten(innse_under_list)
                all_under = np.array(all_under, dtype=float)

                if len(all_under) > 0:
                    plot_name = "combined_innse_under"
                    low_vals, high_vals = log_low_high_values(
                        module_name,
                        file_path,
                        "under",
                        plot_name,
                        all_under,
                    )

                    print(
                        f"📊 {base_name}_{plot_name}: "
                        f"<600: {len(low_vals)}, >1100: {len(high_vals)}"
                    )

                    if not (low_vals or high_vals):
                        print(
                            f"Skipping clean combined plot: "
                            f"{base_name}_{plot_name}"
                        )
                    else:
                        title = (
                            f"{title_prefix}\n"
                            f"Combined innse_under "
                            f"(NTCpb={ntcpb_temp:.1f}C, NTCx={ntcx_temp:.1f}C)\n"
                            f"{timestamp_str}"
                        )

                        output_path = os.path.join(
                            save_dir,
                            f"{base_name}_combined_innse_under.pdf",
                        )

                        save_histogram(
                            all_under,
                            output_path,
                            title,
                            bar_color,
                            len(low_vals),
                            len(high_vals),
                            bins=30,
                        )

                        low_high_rows.append({
                            "filename": os.path.basename(file_path),
                            "stream": "under",
                            "plot": plot_name,
                            "low_count": len(low_vals),
                            "low_values": low_vals,
                            "high_count": len(high_vals),
                            "high_values": high_vals,
                        })

                        made_plot = True

        except Exception as e:
            msg = f"Could not plot combined_innse_under: {e}"
            print(f"❌ CATEGORY D: {base_name} — {msg}")
            add_error("D", module_name, file_path, msg, stream="under", plot_name="combined_innse_under")

        # ========================================================
        # Combined innse_away
        # ========================================================

        try:
            if innse_away_list:
                all_away = flatten(innse_away_list)
                all_away = np.array(all_away, dtype=float)

                if len(all_away) > 0:
                    plot_name = "combined_innse_away"
                    low_vals, high_vals = log_low_high_values(
                        module_name,
                        file_path,
                        "away",
                        plot_name,
                        all_away,
                    )

                    print(
                        f"📊 {base_name}_{plot_name}: "
                        f"<600: {len(low_vals)}, >1100: {len(high_vals)}"
                    )

                    if not (low_vals or high_vals):
                        print(
                            f"Skipping clean combined plot: "
                            f"{base_name}_{plot_name}"
                        )
                    else:
                        title = (
                            f"{title_prefix}\n"
                            f"Combined innse_away "
                            f"(NTCpb={ntcpb_temp:.1f}C, NTCx={ntcx_temp:.1f}C)\n"
                            f"{timestamp_str}"
                        )

                        output_path = os.path.join(
                            save_dir,
                            f"{base_name}_combined_innse_away.pdf",
                        )

                        save_histogram(
                            all_away,
                            output_path,
                            title,
                            bar_color,
                            len(low_vals),
                            len(high_vals),
                            bins=30,
                        )

                        low_high_rows.append({
                            "filename": os.path.basename(file_path),
                            "stream": "away",
                            "plot": plot_name,
                            "low_count": len(low_vals),
                            "low_values": low_vals,
                            "high_count": len(high_vals),
                            "high_values": high_vals,
                        })

                        made_plot = True

        except Exception as e:
            msg = f"Could not plot combined_innse_away: {e}"
            print(f"❌ CATEGORY D: {base_name} — {msg}")
            add_error("D", module_name, file_path, msg, stream="away", plot_name="combined_innse_away")

        # ========================================================
        # Per-file CSV/JSON summary
        # ========================================================

        if low_high_rows:
            csv_path = os.path.join(save_dir, f"{base_name}_low_high_values.csv")
            json_path = os.path.join(save_dir, f"{base_name}_low_high_values.json")

            with open(csv_path, mode="w", newline="") as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([
                    "filename",
                    "stream",
                    "plot",
                    "low_count",
                    "low_values",
                    "high_count",
                    "high_values",
                ])

                for row in low_high_rows:
                    writer.writerow([
                        row["filename"],
                        row["stream"],
                        row["plot"],
                        row["low_count"],
                        json.dumps(row["low_values"]),
                        row["high_count"],
                        json.dumps(row["high_values"]),
                    ])

            with open(json_path, "w") as jf:
                json.dump(low_high_rows, jf, indent=2)

            print(f"📝 Saved low/high CSV: {csv_path}")
            print(f"📝 Saved low/high JSON: {json_path}")

        if not made_plot:
            msg = f"No valid detailed histograms made for {base_name}"
            print(f"❌ CATEGORY E: {msg}")
            add_error("E", module_name, file_path, msg)
            return False

        return True

    except Exception as e:
        msg = f"Unexpected file-level failure: {e}"
        print(f"❌ CATEGORY D: {os.path.basename(file_path)} — {msg}")
        add_error("D", module_name, file_path, msg)
        return False


# ============================================================
# TXT summary
# ============================================================

def write_error_summary_txt(output_base_dir):
    mkdir(output_base_dir)

    summary_path = os.path.join(output_base_dir, "detailedhistograms_error_summary.txt")

    categories = {
        "B": "CATEGORY B — high input noise values greater than 1100",
        "C": "CATEGORY C — low input noise values less than 600",
        "D": "CATEGORY D — files skipped, empty, missing, or unreadable",
        "E": "CATEGORY E — script did not run for entire module / no valid detailed histograms plotted",
    }

    with open(summary_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("DETAILED INPUT NOISE HISTOGRAM ERROR SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        total_entries = sum(len(error_summary[key]) for key in error_summary)
        f.write(f"Total issue entries found: {total_entries}\n\n")

        for category, title in categories.items():
            entries = error_summary[category]

            f.write("\n" + "=" * 80 + "\n")
            f.write(title + "\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total entries: {len(entries)}\n")

            if category in ["B", "C"]:
                total_values = sum(entry.get("count") or 0 for entry in entries)
                f.write(f"Total values: {total_values}\n")

            f.write("\n")

            if not entries:
                f.write("None\n")
                continue

            grouped = defaultdict(list)

            for entry in entries:
                grouped[entry["module"]].append(entry)

            for module, module_entries in grouped.items():
                f.write(f"\nModule: {module}\n")
                f.write("-" * 80 + "\n")

                if category in ["B", "C"]:
                    module_total = sum(entry.get("count") or 0 for entry in module_entries)
                    f.write(f"Module total values: {module_total}\n\n")

                for entry in module_entries:
                    f.write(f"File: {entry['file']}\n")
                    f.write(f"Stream: {entry.get('stream', 'N/A')}\n")
                    f.write(f"Plot: {entry.get('plot', 'N/A')}\n")

                    if category == "B":
                        f.write(f"High count: {entry.get('count', 0)}\n")
                        f.write(f"High values: {entry.get('values', [])}\n\n")

                    elif category == "C":
                        f.write(f"Low count: {entry.get('count', 0)}\n")
                        f.write(f"Low values: {entry.get('values', [])}\n\n")

                    else:
                        f.write(f"Reason: {entry['message']}\n\n")

    print("\n" + "=" * 80)
    print("Saved error summary TXT file:")
    print(summary_path)
    print("=" * 80)


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Plot detailed input noise histograms per JSON file"
    )

    parser.add_argument(
        "--serial_number",
        help="Serial number, e.g. 20USBHX2002592",
    )

    parser.add_argument(
        "-i",
        "--input",
        help="Glob pattern, e.g. 'BNL/HX/SN20USBHX2002099/SN20USBHX2002099_*.json' or 'BNL/HX/SN*/*.json'",
    )

    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help="Output base directory. Default: BNL/HX2",
    )

    args = parser.parse_args()

    if args.input:
        input_files = sorted(glob.glob(args.input))

    elif args.serial_number:
        serial = clean_serial(args.serial_number)

        input_files = sorted(
            glob.glob(f"BNL/HX/SN{serial}/SN{serial}_*.json")
        )

        if not input_files:
            input_files = sorted(
                glob.glob(f"SN{serial}/SN{serial}_*.json")
            )

    else:
        parser.error("Please provide either --serial_number or -i/--input")

    output_base_dir = args.output or DEFAULT_OUTPUT_DIR

    print(f"\nFound {len(input_files)} input files")
    print(f"Output base directory: {output_base_dir}")

    if len(input_files) == 0:
        print("❌ CATEGORY E: No JSON files found.")
        add_error("E", "Unknown", None, "No JSON files found. Script did not run.")
        write_error_summary_txt(output_base_dir)
        return

    filtered_files = filter_input_files(input_files)
    grouped_files = group_files_by_module(filtered_files)

    print("\nModules:")
    for module_name, files in grouped_files.items():
        print(f"  {module_name}: {len(files)} files")

    if not grouped_files:
        print("❌ CATEGORY E: No modules found after filtering.")
        add_error("E", "Unknown", None, "No modules found after filtering.")
        write_error_summary_txt(output_base_dir)
        return

    module_plot_status = {}

    for module_name, files in grouped_files.items():
        if not module_has_problem_values(files):
            print(
                f"Skipping clean module {module_name}: "
                "no channel below 600 ENC or above 1100 ENC."
            )
            module_plot_status[module_name] = True
            continue

        print(
            f"Plotting problem module {module_name}: "
            "at least one channel is below 600 ENC or above 1100 ENC."
        )

        any_ok = False

        for file_path in files:
            ok = plot_file_histograms(
                file_path,
                output_base_dir,
                module_name,
            )

            any_ok = any_ok or ok

        module_plot_status[module_name] = any_ok

    for module_name, ok in module_plot_status.items():
        if not ok:
            add_error(
                "E",
                module_name,
                None,
                "Script did not successfully make any detailed histogram plot for this module.",
            )

    write_error_summary_txt(output_base_dir)


if __name__ == "__main__":
    main()