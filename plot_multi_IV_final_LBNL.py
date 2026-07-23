#!/usr/bin/env python3

# ============================================================
# plot_multi_IV_final_LBNL.py
#
# Fast IV plotting + Category A / D(i) summary generator
# Keeps original plotting style.
#
# Run:
#   python plot_multi_IV_final_LBNL.py -i "LBNL/ML/*/*.json" -o "LBNL/ML3" --workers 6
#
# Optional faster test without PNG:
#   python plot_multi_IV_final_LBNL.py -i "LBNL/ML/*/*.json" -o "LBNL/ML3" --workers 6 --no_png
#
# Saves plots:
#   LBNL/ML3/SN20USBML.../IV/SN20USBML....pdf
#   LBNL/ML3/SN20USBML.../IV/SN20USBML....png
#
# Saves summaries:
#   LBNL/ML3/iv_error_summary.txt
#   LBNL/ML3/iv_category_summary_lbnl.txt
#
# Logic:
#   > 300 nA and <= 600 nA  -> yellow warning / additional comment
#   > 600 nA                -> Category A
#   empty/missing IV files  -> Category D(i)
# ============================================================

import os
import re
import json
import argparse
import datetime
import collections
from glob import glob
from pathlib import Path
from collections import OrderedDict
from concurrent.futures import ProcessPoolExecutor, as_completed

import numpy as np

import matplotlib as mplt
mplt.use("Agg")
import matplotlib.pyplot as plt


# ============================================================
# Original plotting style
# ============================================================

mplt.rc("text", usetex=True)
mplt.rc(
    "font",
    **{
        "family": "sans-serif",
        "sans-serif": ["Helvetica"],
    },
)


# ============================================================
# Settings
# ============================================================

SITE = "LBNL"
DEFAULT_OUTPUT_DIR = "LBNL/ML3"

WARNING_CURRENT_THRESHOLD_NA = 300.0
CATEGORY_A_CURRENT_THRESHOLD_NA = 600.0
EXPECTED_IV_TESTS = 24


# ============================================================
# Serial helpers
# ============================================================

def strip_sn(serial):
    if serial is None:
        return ""

    serial = str(serial).strip()

    if serial.startswith("SN"):
        return serial[2:]

    return serial


def with_sn(serial):
    if serial is None:
        return ""

    serial = str(serial).strip()

    if not serial:
        return ""

    if serial.startswith("SN"):
        return serial

    return f"SN{serial}"


def clean_sn(serial):
    return strip_sn(serial)


def mkdir(path):
    if not path:
        return

    os.makedirs(path, exist_ok=True)


# ============================================================
# Run / temperature helpers
# ============================================================

def get_run_number_from_filename(file_path):
    """
    Example:
      SN20USBML1236980_03.json -> 3
    """
    base = os.path.basename(file_path)

    match = re.search(r"_(\d+)\.json$", base)

    if not match:
        return None

    return int(match.group(1))


def get_temperature_label_from_run(run_number):
    """
    IV temperature map:
      JSON 01 = warm
      JSON 02 = cold
      alternating warm/cold
      JSON 23 and JSON 24 = warm
    """

    if run_number is None:
        return "unknown"

    if run_number in [23, 24]:
        return "warm"

    if run_number % 2 == 1:
        return "warm"

    return "cold"


def summarize_temperature_modes(temp_labels):
    temp_labels = [t for t in temp_labels if t in ["warm", "cold"]]

    if not temp_labels:
        return "Temperature unknown"

    unique = set(temp_labels)

    if unique == {"warm"}:
        return "Warm-only"

    if unique == {"cold"}:
        return "Cold-only"

    return "Warm/cold mixed"


def format_run_list(run_numbers):
    if not run_numbers:
        return "unknown"

    return ", ".join(f"{run:02}" for run in sorted(run_numbers))


def format_timestamp(raw_timestamp):
    if not raw_timestamp:
        return "Invalid Time"

    timestamp_stripped = (
        str(raw_timestamp)
        .replace("T", " ")
        .split(".")[0]
        .replace("Z", "")
        .strip()
    )

    try:
        dt = datetime.datetime.strptime(
            timestamp_stripped,
            "%Y-%m-%d %H:%M:%S",
        )
        return dt.strftime("%Y-%m-%d %H:%M")

    except ValueError:
        return timestamp_stripped


# ============================================================
# JSON helpers
# ============================================================

def json_to_dict(file_name):
    with open(file_name, "r") as infile:
        return json.load(infile)


def get_module_name_from_json(file_path):
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

        return with_sn(module_name) if module_name else ""

    except Exception:
        return ""


def build_module_file_map(input_files):
    """
    Groups files by module once.
    This is faster than scanning all JSON files again for every module.
    """
    module_files = collections.defaultdict(list)
    unreadable_files = []

    for file_path in input_files:
        module_name = get_module_name_from_json(file_path)

        if module_name:
            module_files[module_name].append(file_path)
        else:
            unreadable_files.append(file_path)

    ordered = OrderedDict()

    for module in sorted(module_files.keys()):
        ordered[module] = sorted(
            module_files[module],
            key=lambda f: (
                get_run_number_from_filename(f) or 999,
                os.path.basename(f),
            ),
        )

    return ordered, unreadable_files


# ============================================================
# IV reader
# ============================================================

def read_AMAC_IV(file_name, do_amac_offset=True):
    with open(file_name, "r") as infile:
        input_dict = json.load(infile)

    results = input_dict.get("results", {})

    current_raw = (
        results.get("CURRENT")
        or results.get("current")
        or results.get("Current")
    )

    voltage_raw = (
        results.get("VOLTAGE")
        or results.get("voltage")
        or results.get("Voltage")
    )

    if current_raw is None or voltage_raw is None:
        raise ValueError("empty or missing IV data")

    if len(current_raw) == 0 or len(voltage_raw) == 0:
        raise ValueError("empty or missing IV data")

    current_zero_offset = float(current_raw[0]) if do_amac_offset else 0.0

    voltages = [abs(float(x)) for x in voltage_raw]
    currents = [float(x) - current_zero_offset for x in current_raw]

    if len(voltages) == 0 or len(currents) == 0:
        raise ValueError("empty or missing IV data")

    temperatures = input_dict.get("temperatures", {})
    properties = input_dict.get("properties", {})
    dcs = properties.get("DCS", {})

    if temperatures:
        ntcpb_temp = temperatures.get("AMAC_NTCpb", [0.0])
        ntcx_temp = temperatures.get("AMAC_NTCx", [0.0])

        if isinstance(ntcpb_temp, list):
            ntcpb_temp = ntcpb_temp[0] if ntcpb_temp else 0.0

        if isinstance(ntcx_temp, list):
            ntcx_temp = ntcx_temp[0] if ntcx_temp else 0.0

    elif dcs:
        ntcpb_temp = dcs.get("AMAC_NTCpb", 0.0)
        ntcx_temp = dcs.get("AMAC_NTCx", 0.0)

    else:
        ntcpb_temp = 0.0
        ntcx_temp = 0.0

    raw_timestamp = input_dict.get(
        "timestamp",
        input_dict.get("date", ""),
    )

    timestamp = format_timestamp(raw_timestamp)

    return voltages, currents, timestamp, float(ntcpb_temp), float(ntcx_temp)


# ============================================================
# Comment builders
# ============================================================

def make_iv_current_comment(current_values, affected_runs, affected_temperatures, threshold):
    current_count = len(current_values)
    affected_test_count = len(affected_runs)

    error_rate = (
        100.0 * affected_test_count / EXPECTED_IV_TESTS
        if EXPECTED_IV_TESTS
        else 0.0
    )

    temp_summary = summarize_temperature_modes(affected_temperatures)
    run_text = format_run_list(affected_runs)
    max_current = max(current_values) if current_values else 0.0

    if current_count == 1:
        value_text = f"1 IV current value above {threshold:.0f} nA"
    else:
        value_text = f"{current_count} IV current values above {threshold:.0f} nA"

    return (
        f"IV current above {threshold:.0f} nA. "
        f"{value_text} in {affected_test_count}/{EXPECTED_IV_TESTS} tests. "
        f"Maximum current: {max_current:.2f} nA. "
        f"Error rate: {error_rate:.2f}%. "
        f"{temp_summary}. "
        f"Affected runs: {run_text}."
    )


def make_category_d_i_comment(missing_runs):
    missing_count = len(missing_runs)
    successful_count = EXPECTED_IV_TESTS - missing_count

    if missing_count == 1:
        file_phrase = "1 IV test file is empty or missing"
    else:
        file_phrase = f"{missing_count} IV test files are empty or missing"

    run_text = format_run_list(missing_runs)

    return (
        f"Incomplete IV dataset. "
        f"{successful_count}/{EXPECTED_IV_TESTS} tests ran successfully; "
        f"{file_phrase}. "
        f"Skipped runs: {run_text}."
    )


# ============================================================
# Worker: plot one module
# ============================================================

def plot_one_module_worker(args_tuple):
    """
    Runs inside worker process.
    Keeps original plotting style.
    """

    (
        module_name,
        input_files,
        output_base_dir,
        do_amac_offset,
        do_logY,
        save_png,
    ) = args_tuple

    module_sn = with_sn(module_name)

    result = {
        "module": module_sn,
        "checked": True,
        "valid_plot_count": 0,
        "warning_records": [],
        "category_a_records": [],
        "category_d_records": [],
        "category_e_records": [],
        "present_runs": set(),
        "missing_runs": set(),
        "plot_pdf": "",
        "plot_png": "",
    }

    fig, ax = plt.subplots()
    fig.set_size_inches(12, 8)

    print(f"Making plot for {module_sn}")

    sorted_files = sorted(
        input_files,
        key=lambda f: (
            get_run_number_from_filename(f) or 999,
            os.path.basename(f),
        ),
    )

    blues = mplt.cm.Blues(np.linspace(0.4, 0.9, max(len(sorted_files), 1)))
    oranges = mplt.cm.Oranges(np.linspace(0.4, 0.9, max(len(sorted_files), 1)))

    handles = []
    labels = []
    skipped_msgs = []
    first_valid_timestamp = None

    for count, input_file in enumerate(sorted_files):
        basename = os.path.basename(input_file)
        run_number = get_run_number_from_filename(input_file)

        if run_number is not None:
            result["present_runs"].add(run_number)

        try:
            voltages, currents, timestamp, ntcpb_temp, ntcx_temp = read_AMAC_IV(
                input_file,
                do_amac_offset=do_amac_offset,
            )

            if first_valid_timestamp is None and timestamp != "Invalid Time":
                first_valid_timestamp = timestamp

            if len(voltages) == 0 or len(currents) == 0:
                raise ValueError("empty or missing IV data")

            result["valid_plot_count"] += 1

            max_current = max(currents)
            temp_label = get_temperature_label_from_run(run_number)

            # Yellow warning: > 300 nA
            if max_current > WARNING_CURRENT_THRESHOLD_NA:
                warning_message = (
                    f"{basename} — HIGH CURRENT WARNING: "
                    f"maximum current = {max_current:.2f} nA "
                    f"(> {WARNING_CURRENT_THRESHOLD_NA:.0f} nA)"
                )

                result["warning_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "temperature": temp_label,
                    "current": max_current,
                    "message": warning_message,
                })

            # Real Category A: > 600 nA
            if max_current > CATEGORY_A_CURRENT_THRESHOLD_NA:
                category_a_message = (
                    f"{basename} — HIGH CURRENT CATEGORY A: "
                    f"maximum current = {max_current:.2f} nA "
                    f"(> {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA)"
                )

                result["category_a_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "temperature": temp_label,
                    "current": max_current,
                    "message": category_a_message,
                })

            # Keep original color rule/style.
            lcolour = blues[count] if ntcpb_temp < 0 else oranges[count]
            ntcx_txt = "{0:.3g}".format(ntcx_temp).replace("-", "$-$")

            line = ax.plot(
                voltages,
                currents,
                lw=2,
                ls="-",
                c=lcolour,
                label="{0}, {1}C".format(timestamp, ntcx_txt),
            )

            handles.append(line[0])
            labels.append("{0}, {1}C".format(timestamp, ntcx_txt))

        except Exception as e:
            err_text = str(e).strip()

            if "empty or missing IV data" in err_text:
                msg = f"{basename} — empty"
                result["category_d_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "message": msg,
                })
            else:
                msg = f"{basename} — {err_text}"
                result["category_e_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "message": msg,
                })

            skipped_msgs.append(msg)

    # Detect missing run files 01–24.
    expected_runs = set(range(1, EXPECTED_IV_TESTS + 1))
    missing_runs = sorted(expected_runs - result["present_runs"])

    if missing_runs:
        result["missing_runs"] = set(missing_runs)

        for run in missing_runs:
            msg = f"{module_sn}_{run:02}.json — missing"
            result["category_d_records"].append({
                "module": module_sn,
                "file": f"{module_sn}_{run:02}.json",
                "run": run,
                "message": msg,
            })
            skipped_msgs.append(msg)

    if result["valid_plot_count"] == 0:
        result["category_d_records"].append({
            "module": module_sn,
            "file": "N/A",
            "run": None,
            "message": "No valid IV curves were plotted for this module.",
        })

    # Keep original red skipped-message legend style.
    for msg in skipped_msgs:
        dummy_handle = plt.Line2D(
            [],
            [],
            color="red",
            marker="x",
            linestyle="None",
            markersize=8,
            markeredgewidth=1.5,
        )
        handles.append(dummy_handle)
        labels.append(msg)

    if handles:
        legend = ax.legend(
            handles,
            labels,
            loc="upper left",
            prop={"size": 14},
            frameon=False,
            handlelength=1.8,
            handletextpad=0.5,
            borderpad=0.6,
            ncol=3,
            columnspacing=0.6,
        )

        for text, label in zip(legend.get_texts(), labels):
            if label in skipped_msgs:
                text.set_color("red")

    text_size = 28

    if do_logY:
        ax.set_yscale("log")
        ax.set_ylim(1, 10000)
    else:
        ax.set_ylim(-20, 550)

    ax.set_xlim(-10, 750)

    plt.xlabel(r"Voltage [V]", labelpad=15, size=38)
    plt.ylabel(r"Current [nA]", labelpad=15, size=38)

    ax.tick_params(
        "x",
        length=12,
        width=1,
        which="major",
        labelsize=28,
        pad=10,
        direction="in",
    )
    ax.tick_params(
        "x",
        length=6,
        width=1,
        which="minor",
        direction="in",
    )
    ax.tick_params(
        "y",
        length=12,
        width=1,
        which="major",
        labelsize=28,
        pad=10,
        direction="in",
        right=True,
    )
    ax.tick_params(
        "y",
        length=6,
        width=1,
        which="minor",
        direction="in",
        right=True,
    )

    fig.text(0.20, 0.56, module_sn, color="k", size=text_size)

    if first_valid_timestamp:
        fig.text(
            0.20,
            0.51,
            f"Timestamp: {first_valid_timestamp}",
            color="k",
            size=text_size * 0.6,
        )
    else:
        fig.text(
            0.20,
            0.51,
            "Timestamp: Unknown",
            color="gray",
            size=text_size * 0.6,
        )

    fig.text(
        0.20,
        0.47,
        "Temperatures = AMAC NTCx",
        color="gray",
        size=text_size * 0.5,
    )

    plt.tight_layout(pad=0.3)
    plt.subplots_adjust(top=0.97, left=0.16, right=0.99)

    plot_dir = Path(output_base_dir) / module_sn / "IV"
    plot_dir.mkdir(parents=True, exist_ok=True)

    save_base = plot_dir / module_sn
    save_pdf = f"{save_base}.pdf"
    save_png_path = f"{save_base}.png"

    print(f"Saving plot as {save_pdf}")
    plt.savefig(save_pdf, format="pdf")

    if save_png:
        print(f"Saving plot as {save_png_path}")
        plt.savefig(save_png_path, format="png", dpi=300)

    plt.close(fig)

    result["plot_pdf"] = save_pdf
    result["plot_png"] = save_png_path if save_png else ""

    return result


# ============================================================
# Build comments from worker results
# ============================================================

def build_comments_from_results(results):
    category_a_comments = OrderedDict()
    yellow_warning_comments = OrderedDict()
    category_d_i_comments = OrderedDict()
    category_e_i_comments = OrderedDict()

    for result in sorted(results, key=lambda x: x["module"]):
        module = result["module"]

        category_a_records = result["category_a_records"]
        warning_records = result["warning_records"]
        d_records = result["category_d_records"]
        e_records = result["category_e_records"]

        # Category A comments: real category above 600 nA.
        if category_a_records:
            current_values = [r["current"] for r in category_a_records]

            affected_runs = {
                r["run"]
                for r in category_a_records
                if r["run"] is not None
            }

            affected_temperatures = [
                r["temperature"]
                for r in category_a_records
            ]

            category_a_comments[module] = make_iv_current_comment(
                current_values=current_values,
                affected_runs=affected_runs,
                affected_temperatures=affected_temperatures,
                threshold=CATEGORY_A_CURRENT_THRESHOLD_NA,
            )

        # Yellow warnings: above 300 nA but no Category A.
        elif warning_records:
            current_values = [r["current"] for r in warning_records]

            affected_runs = {
                r["run"]
                for r in warning_records
                if r["run"] is not None
            }

            affected_temperatures = [
                r["temperature"]
                for r in warning_records
            ]

            yellow_warning_comments[module] = make_iv_current_comment(
                current_values=current_values,
                affected_runs=affected_runs,
                affected_temperatures=affected_temperatures,
                threshold=WARNING_CURRENT_THRESHOLD_NA,
            )

        # Category D(i): empty or missing IV files.
        d_runs = {
            r["run"]
            for r in d_records
            if r["run"] is not None
        }

        if d_runs:
            category_d_i_comments[module] = make_category_d_i_comment(d_runs)

        elif d_records:
            category_d_i_comments[module] = (
                "Incomplete IV dataset. "
                "No valid IV curves were plotted for this module."
            )

        # Category E(i)
        if e_records:
            first_message = e_records[0]["message"]
            category_e_i_comments[module] = (
                f"IV data unavailable or could not be processed. {first_message}"
            )

    return (
        category_a_comments,
        yellow_warning_comments,
        category_d_i_comments,
        category_e_i_comments,
    )


# ============================================================
# Output writers
# ============================================================

def write_comment_dict(f, title, comments):
    f.write(f"{title} = {{\n")

    for serial, comment in comments.items():
        f.write(f'    "{serial}": "{comment}",\n')

    f.write("}\n\n")


def write_modules_format(f, comments):
    f.write('"modules": {\n')

    for serial, comment in comments.items():
        serial_no_sn = strip_sn(serial)
        f.write(f'    "{serial_no_sn}": "{comment}",\n')

    f.write("}\n\n")


def write_serial_list(f, title, comments):
    f.write("=" * 80 + "\n")
    f.write(title + "\n")
    f.write("=" * 80 + "\n\n")

    for serial in comments:
        serial_no_sn = strip_sn(serial)
        f.write(f'    "{serial_no_sn}",\n')

    f.write("\n")


def write_category_section(f, category_name, description, records):
    f.write("\n")
    f.write("=" * 80 + "\n")
    f.write(f"{category_name}\n")
    f.write(description + "\n")
    f.write("=" * 80 + "\n")

    if not records:
        f.write("None found.\n")
        return

    grouped = collections.defaultdict(list)

    for record in records:
        grouped[record["module"]].append(record["message"])

    for module in sorted(grouped.keys()):
        f.write(f"\n{module}\n")
        f.write("-" * len(module) + "\n")

        for i, message in enumerate(grouped[module], start=1):
            f.write(f"{i}. {message}\n")


def write_error_summary(results, output_file):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    total_modules_checked = len(results)
    modules_not_working = set()

    category_A_records = []
    category_D_records = []
    category_E_records = []

    for result in results:
        module = result["module"]

        if (
            result["category_a_records"]
            or result["category_d_records"]
            or result["category_e_records"]
        ):
            modules_not_working.add(module)

        category_A_records.extend(result["category_a_records"])
        category_D_records.extend(result["category_d_records"])
        category_E_records.extend(result["category_e_records"])

    working_count = total_modules_checked - len(modules_not_working)

    total_entries = (
        len(category_A_records)
        + len(category_D_records)
        + len(category_E_records)
    )

    with output_file.open("w") as f:
        f.write("IV Plot Error Summary\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Generated: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"Yellow warning threshold: > {WARNING_CURRENT_THRESHOLD_NA:.0f} nA\n")
        f.write(f"Category A threshold: > {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA\n")
        f.write(f"Expected IV tests: {EXPECTED_IV_TESTS}\n\n")

        f.write("FINAL SUMMARY\n")
        f.write("-" * 80 + "\n")
        f.write(f"TOTAL MODULES CHECKED: {total_modules_checked}\n")
        f.write(f"WORKING MODULES: {working_count}\n")
        f.write(f"NOT WORKING MODULES: {len(modules_not_working)}\n")
        f.write(f"TOTAL FLAGGED FILES / WARNINGS: {total_entries}\n\n")

        f.write("CATEGORY COUNTS\n")
        f.write("-" * 80 + "\n")
        f.write(
            f"Category A — IV current values above "
            f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA: {len(category_A_records)}\n"
        )
        f.write(f"Category D — Incomplete dataset or missing generated files: {len(category_D_records)}\n")
        f.write(f"Category E — Script did not run or data are unavailable: {len(category_E_records)}\n\n")

        write_category_section(
            f,
            "Category A",
            f"IV current values above {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA.",
            category_A_records,
        )

        write_category_section(
            f,
            "Category D",
            "Incomplete dataset or missing generated files.",
            category_D_records,
        )

        write_category_section(
            f,
            "Category E",
            "Script did not run or data are unavailable.",
            category_E_records,
        )

    print(f"Saved IV error summary to: {output_file}")


def write_category_summary(
    output_file,
    site_label,
    category_a_comments,
    yellow_warning_comments,
    category_d_i_comments,
    category_e_i_comments,
):
    output_file = Path(output_file)
    output_file.parent.mkdir(parents=True, exist_ok=True)

    combined_category_comments = OrderedDict()
    combined_category_comments.update(category_a_comments)
    combined_category_comments.update(category_d_i_comments)

    with output_file.open("w") as f:
        f.write("=" * 80 + "\n")
        f.write(f"{site_label} IV CATEGORY SUMMARY\n")
        f.write("=" * 80 + "\n\n")

        f.write(f"Category A threshold: > {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA\n")
        f.write(
            f"Yellow warning threshold: > {WARNING_CURRENT_THRESHOLD_NA:.0f} nA "
            f"and <= {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA\n"
        )
        f.write(f"Expected IV tests: {EXPECTED_IV_TESTS}\n\n")

        f.write("FINAL COUNTS\n")
        f.write("-" * 80 + "\n")
        f.write(f"Category A modules: {len(category_a_comments)}\n")
        f.write(f"Yellow warning modules: {len(yellow_warning_comments)}\n")
        f.write(f"Category D(i) modules: {len(category_d_i_comments)}\n")
        f.write(f"Category E(i) modules: {len(category_e_i_comments)}\n\n")

        write_serial_list(
            f,
            f"CATEGORY A MODULE SERIALS ABOVE {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA",
            category_a_comments,
        )

        write_serial_list(
            f,
            (
                f"YELLOW WARNING MODULE SERIALS ABOVE {WARNING_CURRENT_THRESHOLD_NA:.0f} nA "
                f"BUT NOT ABOVE {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA"
            ),
            yellow_warning_comments,
        )

        write_serial_list(
            f,
            "CATEGORY D(i) MODULE SERIALS WITH INCOMPLETE IV DATASET",
            category_d_i_comments,
        )

        write_serial_list(
            f,
            "CATEGORY E(i) MODULE SERIALS WITH IV DATA UNAVAILABLE",
            category_e_i_comments,
        )

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY A COMMENTS\n")
        f.write("=" * 80 + "\n\n")
        write_comment_dict(f, "category_a_comments", category_a_comments)

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE YELLOW WARNING COMMENTS\n")
        f.write("=" * 80 + "\n\n")
        write_comment_dict(f, "yellow_warning_comments", yellow_warning_comments)

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY D(i) COMMENTS\n")
        f.write("=" * 80 + "\n\n")
        write_comment_dict(f, "category_d_i_comments", category_d_i_comments)

        f.write("=" * 80 + "\n")
        f.write("READY-TO-PASTE CATEGORY E(i) COMMENTS\n")
        f.write("=" * 80 + "\n\n")
        write_comment_dict(f, "category_e_i_comments", category_e_i_comments)

        f.write("=" * 80 + "\n")
        f.write("CATEGORY A CATEGORY_DEFINITIONS FORMAT\n")
        f.write("=" * 80 + "\n\n")
        write_modules_format(f, category_a_comments)

        f.write("=" * 80 + "\n")
        f.write("YELLOW WARNING / ADDITIONAL_COMMENTS FORMAT\n")
        f.write("=" * 80 + "\n\n")
        write_modules_format(f, yellow_warning_comments)

        f.write("=" * 80 + "\n")
        f.write("CATEGORY D(i) CATEGORY_DEFINITIONS FORMAT\n")
        f.write("=" * 80 + "\n\n")
        write_modules_format(f, category_d_i_comments)

        f.write("=" * 80 + "\n")
        f.write("CATEGORY E(i) CATEGORY_DEFINITIONS FORMAT\n")
        f.write("=" * 80 + "\n\n")
        write_modules_format(f, category_e_i_comments)

        f.write("=" * 80 + "\n")
        f.write("COMBINED CATEGORY A + CATEGORY D(i) CATEGORY_DEFINITIONS FORMAT\n")
        f.write("=" * 80 + "\n\n")
        write_modules_format(f, combined_category_comments)

    print(f"Saved IV category summary to: {output_file}")


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description="Fast LBNL IV plotter plus Category A / D(i) summary generator."
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help='Input glob, for example "LBNL/ML/*/*.json"',
    )

    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output base folder. Default: {DEFAULT_OUTPUT_DIR}",
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help="Number of parallel workers. Default: 6",
    )

    parser.add_argument(
        "--do_amac_offset",
        action="store_true",
        help="Subtract first current value as AMAC offset.",
    )

    parser.add_argument(
        "--do_logY",
        action="store_true",
        help="Use log scale for current axis.",
    )

    parser.add_argument(
        "--no_png",
        action="store_true",
        help="Save only PDF, not PNG, for faster testing.",
    )

    args = parser.parse_args()

    output_base_dir = Path(args.output)
    output_base_dir.mkdir(parents=True, exist_ok=True)

    input_files = sorted(glob(args.input))

    print("\n" + "=" * 80)
    print("FAST LBNL IV PLOTTING + CATEGORY SUMMARY")
    print("=" * 80)
    print(f"Input glob: {args.input}")
    print(f"Output folder: {output_base_dir}")
    print(f"Workers: {args.workers}")
    print(f"Save PNG: {not args.no_png}")
    print(f"Found JSON files: {len(input_files)}")
    print("=" * 80 + "\n")

    if not input_files:
        raise FileNotFoundError(
            f"No JSON files found for input pattern:\n{args.input}"
        )

    module_file_map, unreadable_files = build_module_file_map(input_files)

    print(f"Modules found: {len(module_file_map)}")

    if unreadable_files:
        print(f"Unreadable / unassigned files: {len(unreadable_files)}")

    if not module_file_map:
        raise RuntimeError("No valid module names could be parsed from JSON files.")

    tasks = []

    for module_name, files in module_file_map.items():
        tasks.append((
            module_name,
            files,
            str(output_base_dir),
            args.do_amac_offset,
            args.do_logY,
            not args.no_png,
        ))

    results = []

    if args.workers <= 1:
        for task in tasks:
            results.append(plot_one_module_worker(task))
    else:
        with ProcessPoolExecutor(max_workers=args.workers) as executor:
            future_to_module = {
                executor.submit(plot_one_module_worker, task): task[0]
                for task in tasks
            }

            completed = 0

            for future in as_completed(future_to_module):
                module_name = future_to_module[future]
                completed += 1

                try:
                    result = future.result()
                    results.append(result)

                    print(
                        f"[{completed}/{len(tasks)}] Finished {module_name} "
                        f"valid plots={result['valid_plot_count']}"
                    )

                except Exception as e:
                    module_sn = with_sn(module_name)

                    print(f"❌ Worker failed for {module_sn}: {e}")

                    results.append({
                        "module": module_sn,
                        "checked": True,
                        "valid_plot_count": 0,
                        "warning_records": [],
                        "category_a_records": [],
                        "category_d_records": [],
                        "category_e_records": [{
                            "module": module_sn,
                            "file": "N/A",
                            "run": None,
                            "message": f"Worker failed: {e}",
                        }],
                        "present_runs": set(),
                        "missing_runs": set(),
                        "plot_pdf": "",
                        "plot_png": "",
                    })

    results = sorted(results, key=lambda x: x["module"])

    (
        category_a_comments,
        yellow_warning_comments,
        category_d_i_comments,
        category_e_i_comments,
    ) = build_comments_from_results(results)

    iv_error_summary_file = output_base_dir / "iv_error_summary.txt"
    iv_category_summary_file = output_base_dir / "iv_category_summary_lbnl.txt"

    write_error_summary(
        results=results,
        output_file=iv_error_summary_file,
    )

    write_category_summary(
        output_file=iv_category_summary_file,
        site_label=SITE,
        category_a_comments=category_a_comments,
        yellow_warning_comments=yellow_warning_comments,
        category_d_i_comments=category_d_i_comments,
        category_e_i_comments=category_e_i_comments,
    )

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
    print(f"Plots saved under: {output_base_dir}/SN20USBML.../IV/")
    print(f"Saved: {iv_error_summary_file}")
    print(f"Saved: {iv_category_summary_file}")
    print("")
    print("Important:")
    print("  Category A = IV current > 600 nA")
    print("  Yellow warning = IV current > 300 nA and <= 600 nA")
    print("  Category D(i) = incomplete IV dataset")
    print("=" * 80)


if __name__ == "__main__":
    main()