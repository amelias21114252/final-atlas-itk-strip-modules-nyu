#!/usr/bin/env python3
"""


Usage:
python plot_combined_inputnoise_LBNL.py -i 'LBNL/HX/SN20USBHX2002099/SN20USBHX2002099_*.json'
python plot_combined_inputnoise_LBNL.py -i 'LBNL/HX/SN*/*.json'
python plot_combined_inputnoise_LBNL.py --serial_number 20USBHX2002657
"""

import os
import json
import glob
import argparse
from datetime import datetime
from collections import defaultdict

import numpy as np

import matplotlib as mplt
mplt.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import cm


error_summary = {
    "B": [],
    "C": [],
    "D": [],
    "E": [],
}


module_plot_status = {}


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

    parent_name = str(parent_name)

    if parent_name.startswith("SN"):
        return parent_name

    return f"SN{parent_name}"


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


def get_base_output_dir(input_files, fallback_output="LBNL/HX3"):
    """Always save generated outputs under the LBNL/HX3 tree."""
    return fallback_output


def add_error(category, module_name, file_path, message, count=None, values=None, stream=None):
    error_summary[category].append({
        "module": module_name or "Unknown",
        "file": os.path.basename(file_path) if file_path else "N/A",
        "stream": stream or "N/A",
        "message": message,
        "count": count,
        "values": values or [],
    })


def log_low_high_values(module_name, file_path, stream, values):
    filename = os.path.basename(file_path)

    low_vals = [float(v) for v in values if float(v) < 600]
    high_vals = [float(v) for v in values if float(v) > 1100]

    if high_vals:
        msg = f"{filename} — high_count = {len(high_vals)}, high_values = {high_vals}"
        print(f"⚠️ CATEGORY B: {msg}")
        add_error(
            "B",
            module_name,
            file_path,
            msg,
            count=len(high_vals),
            values=high_vals,
            stream=stream,
        )

    if low_vals:
        msg = f"{filename} — low_count = {len(low_vals)}, low_values = {low_vals}"
        print(f"⚠️ CATEGORY C: {msg}")
        add_error(
            "C",
            module_name,
            file_path,
            msg,
            count=len(low_vals),
            values=low_vals,
            stream=stream,
        )

    return low_vals, high_vals


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


def get_parent_name_from_files(json_paths, module_name):
    for path in json_paths:
        try:
            data = json_to_dict(path)
            return clean_parent_name(data.get("parent_name", module_name))
        except Exception:
            continue

    return module_name


def plot_combined_stream(json_paths, stream, output_base_dir, module_name):
    file_data = []
    warm_noise_values = []
    cold_noise_values = []
    skipped_files = []

    parent_name = get_parent_name_from_files(json_paths, module_name)

    result_key = "innse_under" if stream == "under" else "innse_away"

    for path in json_paths:
        filename = os.path.basename(path)

        try:
            data = json_to_dict(path)

            results = data.get("results", {})
            properties = data.get("properties", {})
            dcs = properties.get("DCS", {})

            if result_key not in results:
                raise KeyError(f"Missing results['{result_key}']")

            noise_raw = results[result_key]

            if noise_raw is None:
                raise ValueError("noise data is None")

            noise = flatten(noise_raw)
            noise = np.array(noise, dtype=float)

            if len(noise) == 0:
                raise ValueError("noise array is empty")

            log_low_high_values(module_name, path, stream, noise)

            temp = float(dcs.get("AMAC_NTCpb", 999))
            mean_val = float(np.mean(noise))
            std_val = float(np.std(noise))

            if mean_val > 1100 or mean_val < 0 or std_val > 300:
                msg = f"{filename} — skipped from plot: mean={mean_val:.1f}, std={std_val:.1f}"
                print(f"⚠️ CATEGORY D: {msg}")
                skipped_files.append(msg)
                add_error("D", module_name, path, msg, stream=stream)
                continue

            timestamp_raw = data.get("timestamp", data.get("date", "Unknown Time"))
            timestamp_clean = clean_timestamp(timestamp_raw)

            file_data.append({
                "file": filename,
                "temp": temp,
                "noise": noise,
                "timestamp": timestamp_clean,
            })

            if temp > 10:
                warm_noise_values.extend(noise)
            else:
                cold_noise_values.extend(noise)

        except Exception as e:
            msg = f"{filename} — skipped: {e}"
            print(f"❌ CATEGORY D: {msg}")
            skipped_files.append(msg)
            add_error("D", module_name, path, msg, stream=stream)
            continue

    if not file_data:
        msg = f"No valid histogram data for {module_name}, stream {stream}"
        print(f"❌ CATEGORY E: {msg}")
        add_error("E", module_name, None, msg, stream=stream)
        return False

    cold_data = sorted(
        [d for d in file_data if d["temp"] <= 10],
        key=lambda x: parse_timestamp(x["timestamp"]),
    )

    warm_data = sorted(
        [d for d in file_data if d["temp"] > 10],
        key=lambda x: parse_timestamp(x["timestamp"]),
    )

    cold_cmap = cm.get_cmap("Blues", max(len(cold_data), 1))
    warm_cmap = cm.get_cmap("Oranges", max(len(warm_data), 1))

    cold_mean = np.mean(cold_noise_values) if cold_noise_values else np.nan
    warm_mean = np.mean(warm_noise_values) if warm_noise_values else np.nan
    cold_std = np.std(cold_noise_values) if cold_noise_values else np.nan
    warm_std = np.std(warm_noise_values) if warm_noise_values else np.nan

    plt.figure(figsize=(14, 6))

    legend_entries = []

    first_timestamp = None

    for entry in file_data:
        if entry["timestamp"] != "Unknown Time":
            first_timestamp = entry["timestamp"]
            break

    if first_timestamp:
        legend_entries.append(f"Timestamp: {first_timestamp}")

    for i, entry in enumerate(cold_data):
        color = cold_cmap(i)
        mean_val = np.mean(entry["noise"])
        std_val = np.std(entry["noise"])

        label = (
            f"cold_{i + 1:02d} "
            f"T={entry['temp']:.1f}C | "
            f"mu={mean_val:.1f}, sigma={std_val:.1f}"
        )

        plt.hist(
            entry["noise"],
            bins=40,
            alpha=0.5,
            color=color,
            edgecolor="black",
            linewidth=0.3,
        )

        plt.axvline(
            mean_val,
            color=color,
            linestyle="dashed",
            linewidth=1,
        )

        legend_entries.append(label)

    for i, entry in enumerate(warm_data):
        color = warm_cmap(i)
        mean_val = np.mean(entry["noise"])
        std_val = np.std(entry["noise"])

        label = (
            f"warm_{i + 1:02d} "
            f"T={entry['temp']:.1f}C | "
            f"mu={mean_val:.1f}, sigma={std_val:.1f}"
        )

        plt.hist(
            entry["noise"],
            bins=40,
            alpha=0.5,
            color=color,
            edgecolor="black",
            linewidth=0.3,
        )

        plt.axvline(
            mean_val,
            color=color,
            linestyle="dashed",
            linewidth=1,
        )

        legend_entries.append(label)

    if not np.isnan(cold_mean):
        plt.axvline(
            cold_mean,
            color="blue",
            linestyle="dashed",
            linewidth=2.5,
        )
        legend_entries.append(f"All Cold mu={cold_mean:.1f}, sigma={cold_std:.1f}")

    if not np.isnan(warm_mean):
        plt.axvline(
            warm_mean,
            color="orange",
            linestyle="dashed",
            linewidth=2.5,
        )
        legend_entries.append(f"All Warm mu={warm_mean:.1f}, sigma={warm_std:.1f}")

    for msg in skipped_files:
        plt.plot([], [], " ", label=f"Skipped: {msg}")
        legend_entries.append(f"Skipped: {msg}")

    plt.xlabel("Input Noise [ENC]")
    plt.ylabel("Counts")
    plt.grid(True)
    plt.xlim(600, 1200)

    title_str = f"Module: {module_name} | Parent: {parent_name}\nOverlaid {stream} Histograms"

    if first_timestamp:
        title_str += f"\nTimestamp: {first_timestamp}"

    plt.title(title_str)

    if legend_entries:
        legend = plt.legend(
            legend_entries,
            fontsize="x-small",
            loc="center left",
            bbox_to_anchor=(-0.02, 0.5),
        )

        for txt in legend.get_texts():
            if txt.get_text().startswith("Skipped:"):
                txt.set_color("red")

    plt.tight_layout()

    save_dir = os.path.join(output_base_dir, module_name, "histograms_combined")
    mkdir(save_dir)

    save_path = os.path.join(save_dir, f"{module_name}_combined-{stream}")

    plt.savefig(f"{save_path}.pdf")
    plt.savefig(f"{save_path}.png", dpi=300)
    plt.close()

    print(f"✅ Saved: {save_path}.pdf and {save_path}.png")

    return True


def write_error_summary_txt(output_base_dir):
    mkdir(output_base_dir)

    summary_path = os.path.join(
        output_base_dir,
        "histograms_combined_error_summary.txt",
    )

    categories = {
        "B": "CATEGORY B — high input noise values greater than 1100",
        "C": "CATEGORY C — low input noise values less than 600",
        "D": "CATEGORY D — files skipped, empty, missing, unreadable, or skipped by mean/std cuts",
        "E": "CATEGORY E — script did not run for entire module / no valid histogram plotted",
    }

    with open(summary_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("INPUT NOISE HISTOGRAM ERROR SUMMARY\n")
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


def print_final_module_summary():
    categories = {
        "B": "CATEGORY B — high input noise values greater than 1100",
        "C": "CATEGORY C — low input noise values less than 600",
        "D": "CATEGORY D — skipped / bad files",
        "E": "CATEGORY E — no valid histogram plotted",
    }

    category_modules = {}

    for key in categories:
        modules = sorted(set(
            entry["module"]
            for entry in error_summary[key]
            if entry["module"] != "Unknown"
        ))

        category_modules[key] = modules

    all_failed_modules = sorted(set(
        module
        for modules in category_modules.values()
        for module in modules
    ))

    passed_modules = sorted(set(module_plot_status.keys()) - set(all_failed_modules))

    print("\n" + "=" * 100)
    print("FINAL MODULE SUMMARY")
    print("=" * 100)

    print(f"TOTAL MODULES PROCESSED: {len(module_plot_status)}")
    print(f"TOTAL PASSED MODULES:    {len(passed_modules)}")
    print(f"TOTAL FAILED MODULES:    {len(all_failed_modules)}")

    for key, title in categories.items():
        modules = category_modules[key]

        print("\n" + "-" * 100)
        print(title)
        print("-" * 100)
        print(f"FAILED MODULE COUNT: {len(modules)}")

        if not modules:
            print("None")
            continue

        for idx, module in enumerate(modules, start=1):
            print(f"{idx:03d}. {module}")

    print("\n" + "=" * 100)
    print("OVERALL FAILED MODULES")
    print("=" * 100)

    if not all_failed_modules:
        print("None")
    else:
        for idx, module in enumerate(all_failed_modules, start=1):
            failed_categories = []

            for cat in categories:
                if module in category_modules[cat]:
                    failed_categories.append(f"Category {cat}")

            print(f"{idx:03d}. {module} — {', '.join(failed_categories)}")

    print("\n" + "=" * 100)
    print("PASSED MODULES")
    print("=" * 100)

    if not passed_modules:
        print("None")
    else:
        for idx, module in enumerate(passed_modules, start=1):
            print(f"{idx:03d}. {module}")

    print("\n" + "=" * 100)
    print("DETAILED ERROR MESSAGES")
    print("=" * 100)

    for key, title in categories.items():
        entries = error_summary[key]

        print("\n" + "-" * 100)
        print(title)
        print("-" * 100)
        print(f"TOTAL ENTRIES: {len(entries)}")

        if key in ["B", "C"]:
            total_values = sum(entry.get("count") or 0 for entry in entries)
            print(f"TOTAL VALUES: {total_values}")

        if not entries:
            print("None")
            continue

        grouped = defaultdict(list)

        for entry in entries:
            grouped[entry["module"]].append(entry)

        for module, module_entries in grouped.items():
            print(f"\nModule: {module}")

            if key in ["B", "C"]:
                module_total = sum(entry.get("count") or 0 for entry in module_entries)
                print(f"Module total values: {module_total}")

            for entry in module_entries:
                if key == "B":
                    print(
                        f"⚠️ CATEGORY B: {entry['file']} — "
                        f"stream={entry.get('stream', 'N/A')}, "
                        f"high_count={entry.get('count', 0)}, "
                        f"high_values={entry.get('values', [])}"
                    )

                elif key == "C":
                    print(
                        f"⚠️ CATEGORY C: {entry['file']} — "
                        f"stream={entry.get('stream', 'N/A')}, "
                        f"low_count={entry.get('count', 0)}, "
                        f"low_values={entry.get('values', [])}"
                    )

                elif key == "D":
                    print(f"❌ CATEGORY D: {entry['file']} — {entry['message']}")

                elif key == "E":
                    print(f"❌ CATEGORY E: {entry['file']} — {entry['message']}")

    print("\n" + "=" * 100)
    print("END FINAL MODULE SUMMARY")
    print("=" * 100)


def main():
    parser = argparse.ArgumentParser(
        description="Plot combined input noise histograms"
    )

    parser.add_argument(
        "--serial_number",
        help="Serial number, e.g. 20USBHX2002657",
    )

    parser.add_argument(
        "-i",
        "--input",
        help=(
            "Glob pattern, e.g. "
            "'LBNL/HX/SN20USBHX2002099/SN20USBHX2002099_*.json' "
            "or 'LBNL/HX/SN*/*.json'"
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        default="LBNL/HX3",
        help="Output base directory. Default: LBNL/HX3",
    )

    args = parser.parse_args()

    if args.input:
        input_files = sorted(glob.glob(args.input))

    elif args.serial_number:
        serial = clean_serial(args.serial_number)

        input_files = sorted(
            glob.glob(f"LBNL/HX/SN{serial}/SN{serial}_*.json")
        )

        if not input_files:
            input_files = sorted(
                glob.glob(f"SN{serial}/SN{serial}_*.json")
            )

    else:
        parser.error("Please provide either --serial_number or -i/--input")

    output_base_dir = args.output

    print(f"\nFound {len(input_files)} input files")
    print(f"Output base directory: {output_base_dir}")

    if len(input_files) == 0:
        print("❌ CATEGORY E: No JSON files found.")
        add_error(
            "E",
            "Unknown",
            None,
            "No JSON files found. Script did not run.",
        )
        write_error_summary_txt(output_base_dir)
        print_final_module_summary()
        return

    filtered_files = filter_input_files(input_files)
    grouped_files = group_files_by_module(filtered_files)

    print("\nModules:")
    for module_name, files in grouped_files.items():
        print(f"  {module_name}: {len(files)} files")

    if not grouped_files:
        print("❌ CATEGORY E: No modules found after filtering.")
        add_error(
            "E",
            "Unknown",
            None,
            "No modules found after filtering.",
        )
        write_error_summary_txt(output_base_dir)
        print_final_module_summary()
        return

    for module_name, files in grouped_files.items():
        under_ok = plot_combined_stream(
            files,
            "under",
            output_base_dir,
            module_name,
        )

        away_ok = plot_combined_stream(
            files,
            "away",
            output_base_dir,
            module_name,
        )

        module_plot_status[module_name] = under_ok or away_ok

    for module_name, ok in module_plot_status.items():
        if not ok:
            add_error(
                "E",
                module_name,
                None,
                "Script did not successfully make any histogram plot for this module.",
            )

    write_error_summary_txt(output_base_dir)
    print_final_module_summary()


if __name__ == "__main__":
    main()