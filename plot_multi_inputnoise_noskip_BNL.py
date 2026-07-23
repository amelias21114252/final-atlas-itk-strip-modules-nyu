#!/usr/bin/env python3
'''
Plot input noise after thermal cycling ATLAS ITk strips barrel modules

Usage:
python plot_multi_inputnoise_noskip_BNL.py -i 'BNL/HX/SN20USBHX2002099/SN20USBHX2002099_*.json'
python plot_multi_inputnoise_noskip_BNL.py -i 'BNL/HX/SN*/*.json'

Output:
BNL/HX3/SN20USBHX2002301/inputnoise_noskip/SN20USBHX2002301-away.png
BNL/HX3/SN20USBHX2002301/inputnoise_noskip/SN20USBHX2002301-under.png
'''

import os
import json
import argparse
from glob import glob
from pprint import pprint
from collections import defaultdict

import numpy as np

import matplotlib as mplt
mplt.use("Agg")
import matplotlib.pyplot as plt


X_AXIS_MIN = 0
Y_AXIS_MIN = 0
Y_AXIS_MAX = 2000
DEFAULT_CHANNEL_COUNT = 1280
CHANNEL_TICK_STEP = 128


error_summary = {
    "B": [],
    "C": [],
    "D": [],
    "E": [],
}


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
    if serial.startswith("SN"):
        return serial
    return f"SN{serial}"


def safe_get_module_name(file_path):
    try:
        data = json_to_dict(file_path)
        return data["properties"]["det_info"]["name"]
    except Exception:
        return None


def get_module_from_path(file_path):
    parts = file_path.split(os.sep)

    for part in parts:
        if part.startswith("SN20USB"):
            return part

    basename = os.path.basename(file_path)
    return basename.split("_")[0]


def get_file_number(file_path):
    basename = os.path.basename(file_path)
    name = os.path.splitext(basename)[0]

    if "_" in name:
        return name.split("_")[-1]

    return name[-2:]


def add_error(category, module_name, file_path, message):
    error_summary[category].append({
        "module": module_name or "Unknown",
        "file": os.path.basename(file_path) if file_path else "N/A",
        "message": message,
    })


def filter_input_files(infiles, keep_fit_code=4):
    print(f"\nFiltering to keep fit_type_code = {keep_fit_code}")

    kept = []

    for f in infiles:
        try:
            data = json_to_dict(f)
            module_name = data.get("properties", {}).get("det_info", {}).get("name", None)
            module_name = module_name or get_module_from_path(f)

            fit_code = data.get("properties", {}).get("fit_type_code")

            if fit_code == keep_fit_code:
                kept.append(f)
            else:
                msg = f"fit_type_code = {fit_code}"
                print(f"❌ CATEGORY D: {os.path.basename(f)} — {msg}")
                add_error("D", module_name, f, f"File skipped: {msg}")

        except Exception as e:
            module_name = get_module_from_path(f)
            print(f"❌ CATEGORY D: {os.path.basename(f)} — {e}")
            add_error("D", module_name, f, f"File skipped or unreadable: {e}")

    print(f"Kept {len(kept)} files")
    print(f"Skipped {len(infiles) - len(kept)} files")

    return kept


def get_module_names(files):
    modules = set()

    for f in files:
        module_name = safe_get_module_name(f)

        if not module_name:
            module_name = get_module_from_path(f)

        if module_name:
            modules.add(module_name)

    return sorted(modules)


def mk_inoise_plot(module_name, input_files, stream="under", output_base_dir="BNL/HX3"):
    fig, ax = plt.subplots(figsize=(16, 9))

    print(f"\nPlotting input noise for {module_name}, stream: {stream}")

    files = sorted([
        f for f in input_files
        if module_name in f or get_module_from_path(f) == module_name
    ])

    if not files:
        msg = f"No files found for module {module_name}, stream {stream}"
        print(f"❌ CATEGORY E: {msg}")
        add_error("E", module_name, None, msg)
        plt.close()
        return False

    n_files = len(files)
    blues = mplt.cm.Blues(np.linspace(0.4, 0.9, max(n_files, 1)))
    oranges = mplt.cm.Oranges(np.linspace(0.4, 0.9, max(n_files, 1)))

    skipped_msgs = []
    timestamp_str = "Unknown"
    parent_name = module_name
    max_len = 0

    result_key = "innse_under" if stream == "under" else "innse_away"

    for f in files:
        try:
            data = json_to_dict(f)

            raw_ts = data.get("timestamp", data.get("date", None))
            parent_name = data.get("parent_name", module_name)

            if raw_ts:
                timestamp_str = (
                    str(raw_ts)
                    .replace("T", " ")
                    .split(".")[0]
                    .replace("Z", "")
                    .strip()
                )

            break

        except Exception:
            continue

    parent_name = ensure_sn(str(parent_name).replace("SN", "")) if parent_name != "Unknown" else module_name

    plotted_count = 0

    for idx, f in enumerate(files):
        try:
            data = json_to_dict(f)

            results = data.get("results", {})
            properties = data.get("properties", {})

            if result_key not in results:
                raise KeyError(f"Missing results['{result_key}']")

            noise_raw = results[result_key]

            if noise_raw is None:
                raise ValueError("noise data is None")

            noise = flatten(noise_raw)
            noise = np.array(noise, dtype=float)

            if len(noise) == 0:
                raise ValueError("noise array is empty")

            mean_val = float(np.mean(noise))
            max_len = max(max_len, len(noise))

            basename = os.path.basename(f)

            if mean_val > 1100:
                msg = f"{basename} — mean input noise = {mean_val:.1f} > 1100"
                print(f"⚠️ CATEGORY B: {msg}")
                add_error("B", module_name, f, msg)

            if mean_val < 600:
                msg = f"{basename} — mean input noise = {mean_val:.1f} < 600"
                print(f"⚠️ CATEGORY C: {msg}")
                add_error("C", module_name, f, msg)

            dcs = properties.get("DCS", {})
            temp = float(dcs.get("AMAC_NTCpb", 999))

            temp_label = "+20C" if temp > 10 else "-35C"
            color = oranges[idx] if temp > 10 else blues[idx]

            file_number = get_file_number(f)

            ax.plot(
                range(len(noise)),
                noise,
                lw=1,
                ls="-",
                c=color,
                label=f"{temp_label} file {file_number} [μ: {mean_val:.1f}]",
            )

            plotted_count += 1

        except Exception as e:
            basename = os.path.basename(f)
            msg = f"{basename} — {e}"
            print(f"❌ CATEGORY D: {msg}")
            skipped_msgs.append(msg)
            add_error("D", module_name, f, msg)

    if plotted_count == 0:
        msg = f"No valid curves plotted for {module_name}, stream {stream}"
        print(f"❌ CATEGORY E: {msg}")
        add_error("E", module_name, None, msg)
        plt.close()
        return False

    x_axis_max = max_len if max_len > 0 else DEFAULT_CHANNEL_COUNT
    ax.set_xlim(X_AXIS_MIN, x_axis_max)
    ax.set_ylim(Y_AXIS_MIN, Y_AXIS_MAX)

    ax.set_xlabel("Channel number", labelpad=15, fontsize=38)
    ax.set_ylabel("Input noise [ENC]", labelpad=15, fontsize=38)

    ax.tick_params(axis="both", labelsize=28)
    ax.set_xticks(list(range(X_AXIS_MIN, x_axis_max + 1, CHANNEL_TICK_STEP)))

    handles, labels = ax.get_legend_handles_labels()

    seen = set()
    unique = []

    for h, l in zip(handles, labels):
        if l not in seen:
            unique.append((h, l))
            seen.add(l)

    if unique:
        ax.legend(
            *zip(*unique),
            loc="upper center",
            bbox_to_anchor=(0.5, 0.995),
            ncol=4,
            prop={"size": 15},
            frameon=False,
        )

    fig.text(0.15, 0.31, r"3 point gain response curve, $-$350V, times UTC", color="k", size=22)
    fig.text(0.15, 0.27, f"{module_name}, Stream: {stream}", color="k", size=28)
    fig.text(0.15, 0.23, f"Parent Module: {parent_name}", color="k", size=22)
    fig.text(0.15, 0.19, f"Timestamp: {timestamp_str}", color="k", size=22)

    for i, msg in enumerate(skipped_msgs):
        ypos = 0.14 - i * 0.035

        if ypos < 0.02:
            break

        fig.text(0.15, ypos, msg, color="red", size=16)

    plt.tight_layout(pad=0.3)
    plt.subplots_adjust(top=0.88, bottom=0.12, left=0.11, right=0.97)

    # IMPORTANT:
    # This saves into BNL/HX3/SERIAL/inputnoise_noskip/
    save_dir = os.path.join(output_base_dir, module_name, "inputnoise_noskip")
    mkdir(save_dir)

    save_path_pdf = os.path.join(save_dir, f"{module_name}-{stream}.pdf")
    save_path_png = os.path.join(save_dir, f"{module_name}-{stream}.png")

    print(f"Saving PDF: {save_path_pdf}")
    print(f"Saving PNG: {save_path_png}")

    plt.savefig(save_path_pdf)
    plt.savefig(save_path_png, dpi=200)

    plt.close()

    return True


def write_error_summary_txt(output_base_dir):
    mkdir(output_base_dir)

    summary_path = os.path.join(output_base_dir, "inputnoise_noskip_error_summary.txt")

    categories = {
        "B": "CATEGORY B — input noise mean greater than 1100",
        "C": "CATEGORY C — input noise mean less than 600",
        "D": "CATEGORY D — files skipped, empty, missing, or unreadable",
        "E": "CATEGORY E — script did not run for entire module / no valid curves plotted",
    }

    with open(summary_path, "w") as f:
        f.write("=" * 80 + "\n")
        f.write("INPUT NOISE NOSKIP ERROR SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        total_errors = sum(len(error_summary[key]) for key in error_summary)
        f.write(f"Total issues found: {total_errors}\n\n")

        for category, title in categories.items():
            entries = error_summary[category]

            f.write("\n" + "=" * 80 + "\n")
            f.write(title + "\n")
            f.write("=" * 80 + "\n")
            f.write(f"Total: {len(entries)}\n\n")

            if not entries:
                f.write("None\n")
                continue

            grouped = defaultdict(list)

            for entry in entries:
                grouped[entry["module"]].append(entry)

            for module, module_entries in grouped.items():
                f.write(f"\nModule: {module}\n")
                f.write("-" * 80 + "\n")

                for entry in module_entries:
                    f.write(f"File: {entry['file']}\n")
                    f.write(f"Reason: {entry['message']}\n\n")

    print("\n" + "=" * 80)
    print("Saved error summary TXT file:")
    print(summary_path)
    print("=" * 80)


def main():
    parser = argparse.ArgumentParser(
        description="Plot input noise after thermal cycling ATLAS ITk strips barrel modules"
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
        default="BNL/HX3",
        help="Output base directory. Default: BNL/HX3",
    )

    args = parser.parse_args()

    if args.input:
        input_files = sorted(glob(args.input))

    elif args.serial_number:
        serial_number = clean_serial(args.serial_number)

        input_files = sorted(glob(f"BNL/HX/SN{serial_number}/SN{serial_number}_*.json"))

        if not input_files:
            input_files = sorted(glob(f"SN{serial_number}/SN{serial_number}_*.json"))

    else:
        parser.error("Please provide either --serial_number or -i/--input")

    # IMPORTANT:
    # Do not infer BNL/HX from the input path.
    # Always use args.output, which defaults to BNL/HX3.
    output_base_dir = args.output

    print(f"\nFound {len(input_files)} input files")
    print(f"Output base directory: {output_base_dir}")
    pprint(input_files)

    if len(input_files) == 0:
        print("❌ CATEGORY E: No JSON files found.")
        add_error("E", "Unknown", None, "No JSON files found. Script did not run.")
        write_error_summary_txt(output_base_dir)
        return

    filtered_files = filter_input_files(input_files)
    module_names = get_module_names(filtered_files)

    print("\nFiltered files:")
    pprint(filtered_files)

    print("\nModules:")
    pprint(module_names)

    if not module_names:
        print("❌ CATEGORY E: No module names found after filtering.")
        add_error("E", "Unknown", None, "No module names found after filtering.")
        write_error_summary_txt(output_base_dir)
        return

    module_plot_status = {}

    for module_name in module_names:
        under_ok = mk_inoise_plot(
            module_name,
            filtered_files,
            stream="under",
            output_base_dir=output_base_dir,
        )

        away_ok = mk_inoise_plot(
            module_name,
            filtered_files,
            stream="away",
            output_base_dir=output_base_dir,
        )

        module_plot_status[module_name] = under_ok or away_ok

    for module_name, ok in module_plot_status.items():
        if not ok:
            add_error(
                "E",
                module_name,
                None,
                "Script did not successfully make any input noise plot for this module.",
            )

    write_error_summary_txt(output_base_dir)


if __name__ == "__main__":
    main()