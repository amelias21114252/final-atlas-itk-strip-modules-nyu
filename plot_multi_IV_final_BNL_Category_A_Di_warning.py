#!/usr/bin/env python3

# ============================================================
# plot_multi_IV_final_BNL_Category_A_Di_warning.py
#
# Fast IV analysis + Category A / D(i) / yellow-warning summary generator.
#
# Saves plots for:
#   > 600 nA                -> Category A
#   > 300 nA and <= 600 nA  -> Yellow warning
#   empty/missing IV files  -> Category D(i)
#
# Category E(i)-only modules are analyzed and included in summaries,
# but no plot is saved unless the module also has Category A,
# Category D(i), or a yellow warning.
#
# Run:
#   python plot_multi_IV_final_BNL_Category_A_Di_warning.py -i "BNL/ML/*/*.json" -o "BNL/ML2" --workers 6
#
# Optional faster test without PNG:
#   python plot_multi_IV_final_BNL_Category_A_Di_warning.py \
#       -i "BNL/ML/*/*.json" -o "BNL/ML" --workers 6 --no_png
#
# Selected plots:
#   BNL/ML/SN20USBML.../IV/SN20USBML....pdf
#   BNL/ML/SN20USBML.../IV/SN20USBML....png
#
# Shared PDF folders:
#   BNL/ML/category_A_Di_IV_plots_pdf/
#   BNL/ML/yellow_warning_IV_plots_pdf/
#
# Summaries:
#   BNL/ML/iv_error_summary.txt
#   BNL/ML/iv_category_summary_bnl.txt
# ============================================================

import os
import re
import json
import argparse
import datetime
import collections
import shutil
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

SITE = "BNL"
DEFAULT_OUTPUT_DIR = "BNL/ML2"

WARNING_CURRENT_THRESHOLD_NA = 300.0
CATEGORY_A_CURRENT_THRESHOLD_NA = 600.0
EXPECTED_IV_TESTS = 24

SELECTED_IV_PDF_FOLDER = "category_A_Di_IV_plots_pdf"
YELLOW_WARNING_IV_PDF_FOLDER = "yellow_warning_IV_plots_pdf"
IV_ABOVE_300_JSON_FOLDER = "iv_above_300_json"


# ============================================================
# Serial helpers
# ============================================================

def strip_sn(serial):
    if serial is None:
        return ""

    serial = str(serial).strip()
    return serial[2:] if serial.startswith("SN") else serial


def with_sn(serial):
    if serial is None:
        return ""

    serial = str(serial).strip()

    if not serial:
        return ""

    return serial if serial.startswith("SN") else f"SN{serial}"


def clean_sn(serial):
    return strip_sn(serial)


def mkdir(path):
    if path:
        os.makedirs(path, exist_ok=True)


# ============================================================
# Run / temperature helpers
# ============================================================

def get_run_number_from_filename(file_path):
    """Example: SN20USBML1235761_03.json -> 3"""
    match = re.search(r"_(\d+)\.json$", os.path.basename(file_path))
    return int(match.group(1)) if match else None


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

    if run_number in (23, 24):
        return "warm"

    return "warm" if run_number % 2 == 1 else "cold"


def summarize_temperature_modes(temp_labels):
    temp_labels = [t for t in temp_labels if t in ("warm", "cold")]

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
    """Group files by module once."""
    module_files = collections.defaultdict(list)
    unreadable_files = []

    for file_path in input_files:
        module_name = get_module_name_from_json(file_path)

        if module_name:
            module_files[module_name].append(file_path)
        else:
            unreadable_files.append(file_path)

    ordered = OrderedDict()

    for module in sorted(module_files):
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

    if not voltages or not currents:
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

    return (
        voltages,
        currents,
        timestamp,
        float(ntcpb_temp),
        float(ntcx_temp),
    )


# ============================================================
# Comment builders
# ============================================================

def make_iv_current_comment(
    current_values,
    affected_runs,
    affected_temperatures,
    threshold,
):
    current_count = len(current_values)
    affected_test_count = len(affected_runs)

    error_rate = (
        100.0 * affected_test_count / EXPECTED_IV_TESTS
        if EXPECTED_IV_TESTS
        else 0.0
    )

    temp_summary = summarize_temperature_modes(
        affected_temperatures
    )
    run_text = format_run_list(affected_runs)
    max_current = max(current_values) if current_values else 0.0

    if current_count == 1:
        value_text = (
            f"1 IV current value above {threshold:.0f} nA"
        )
    else:
        value_text = (
            f"{current_count} IV current values above "
            f"{threshold:.0f} nA"
        )

    return (
        f"IV current above {threshold:.0f} nA. "
        f"{value_text} in "
        f"{affected_test_count}/{EXPECTED_IV_TESTS} tests. "
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
        file_phrase = (
            f"{missing_count} IV test files are empty or missing"
        )

    return (
        "Incomplete IV dataset. "
        f"{successful_count}/{EXPECTED_IV_TESTS} tests ran successfully; "
        f"{file_phrase}. "
        f"Skipped runs: {format_run_list(missing_runs)}."
    )


# ============================================================
# Worker: analyze one module and save selected plots
# ============================================================

def plot_one_module_worker(args_tuple):
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
        "is_selected_plot_module": False,
        "is_yellow_warning_plot_module": False,
        "plot_category": "",
        "plot_skipped_not_selected": False,
        "valid_plot_count": 0,
        "warning_records": [],
        "category_a_records": [],
        "category_d_records": [],
        "category_e_records": [],
        "present_runs": set(),
        "missing_runs": set(),
        "plot_pdf": "",
        "plot_png": "",
        "selected_pdf_copy": "",
        "warning_pdf_copy": "",
        "above_300_json": "",
    }

    print(f"Analyzing {module_sn}")

    sorted_files = sorted(
        input_files,
        key=lambda f: (
            get_run_number_from_filename(f) or 999,
            os.path.basename(f),
        ),
    )

    valid_curves = []
    first_valid_timestamp = None

    for input_file in sorted_files:
        basename = os.path.basename(input_file)
        run_number = get_run_number_from_filename(input_file)

        if run_number is not None:
            result["present_runs"].add(run_number)

        try:
            (
                voltages,
                currents,
                timestamp,
                ntcpb_temp,
                ntcx_temp,
            ) = read_AMAC_IV(
                input_file,
                do_amac_offset=do_amac_offset,
            )

            if (
                first_valid_timestamp is None
                and timestamp != "Invalid Time"
            ):
                first_valid_timestamp = timestamp

            result["valid_plot_count"] += 1

            max_current = max(currents)
            temp_label = get_temperature_label_from_run(
                run_number
            )

            if max_current > WARNING_CURRENT_THRESHOLD_NA:
                result["warning_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "temperature": temp_label,
                    "current": max_current,
                    "message": (
                        f"{basename} — HIGH CURRENT WARNING: "
                        f"maximum current = {max_current:.2f} nA "
                        f"(> {WARNING_CURRENT_THRESHOLD_NA:.0f} nA)"
                    ),
                })

            if max_current > CATEGORY_A_CURRENT_THRESHOLD_NA:
                result["category_a_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "temperature": temp_label,
                    "current": max_current,
                    "message": (
                        f"{basename} — HIGH CURRENT CATEGORY A: "
                        f"maximum current = {max_current:.2f} nA "
                        f"(> {CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA)"
                    ),
                })

            valid_curves.append({
                "voltages": voltages,
                "currents": currents,
                "timestamp": timestamp,
                "ntcpb_temp": ntcpb_temp,
                "ntcx_temp": ntcx_temp,
            })

        except Exception as exc:
            err_text = str(exc).strip()

            if "empty or missing IV data" in err_text:
                result["category_d_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "message": f"{basename} — empty",
                })

            else:
                result["category_e_records"].append({
                    "module": module_sn,
                    "file": basename,
                    "run": run_number,
                    "message": f"{basename} — {err_text}",
                })

    expected_runs = set(
        range(1, EXPECTED_IV_TESTS + 1)
    )
    missing_runs = sorted(
        expected_runs - result["present_runs"]
    )

    if missing_runs:
        result["missing_runs"] = set(missing_runs)

        for run in missing_runs:
            result["category_d_records"].append({
                "module": module_sn,
                "file": f"{module_sn}_{run:02}.json",
                "run": run,
                "message": (
                    f"{module_sn}_{run:02}.json — missing"
                ),
            })

    if result["valid_plot_count"] == 0:
        result["category_d_records"].append({
            "module": module_sn,
            "file": "N/A",
            "run": None,
            "message": (
                "No valid IV curves were plotted for this module."
            ),
        })

    # Save one JSON summary for every module with at least one IV test
    # whose maximum current is above 300 nA. This includes both yellow
    # warnings (>300 and <=600 nA) and Category A (>600 nA).
    if result["warning_records"]:
        json_dir = (
            Path(output_base_dir)
            / IV_ABOVE_300_JSON_FOLDER
        )
        json_dir.mkdir(parents=True, exist_ok=True)

        json_path = json_dir / f"{module_sn}_iv_above_300.json"

        affected_records = []
        for record in sorted(
            result["warning_records"],
            key=lambda item: (
                item["run"] if item["run"] is not None else 999,
                item["file"],
            ),
        ):
            current = float(record["current"])
            affected_records.append({
                "file": record["file"],
                "run": record["run"],
                "temperature": record["temperature"],
                "maximum_current_nA": current,
                "above_300_nA": current > WARNING_CURRENT_THRESHOLD_NA,
                "above_600_nA_category_A": current > CATEGORY_A_CURRENT_THRESHOLD_NA,
                "classification": (
                    "Category A"
                    if current > CATEGORY_A_CURRENT_THRESHOLD_NA
                    else "Yellow warning"
                ),
            })

        json_payload = {
            "site": SITE,
            "module": module_sn,
            "warning_threshold_nA": WARNING_CURRENT_THRESHOLD_NA,
            "category_A_threshold_nA": CATEGORY_A_CURRENT_THRESHOLD_NA,
            "expected_IV_tests": EXPECTED_IV_TESTS,
            "affected_test_count": len({
                record["run"]
                for record in result["warning_records"]
                if record["run"] is not None
            }),
            "affected_value_count": len(result["warning_records"]),
            "maximum_current_nA": max(
                float(record["current"])
                for record in result["warning_records"]
            ),
            "has_category_A": bool(result["category_a_records"]),
            "records": affected_records,
        }

        with json_path.open("w", encoding="utf-8") as json_file:
            json.dump(json_payload, json_file, indent=2)
            json_file.write("\n")

        result["above_300_json"] = str(json_path)
        print(f"Saved >300 nA JSON summary to {json_path}")

    result["is_selected_plot_module"] = bool(
        result["category_a_records"]
        or result["category_d_records"]
    )

    result["is_yellow_warning_plot_module"] = bool(
        result["warning_records"]
        and not result["category_a_records"]
    )

    if result["is_selected_plot_module"]:
        result["plot_category"] = "Category A / D(i)"

    elif result["is_yellow_warning_plot_module"]:
        result["plot_category"] = "Yellow warning"

    else:
        result["plot_skipped_not_selected"] = True
        print(
            f"Skipping plot: {module_sn} has no Category A, "
            "Category D(i), or yellow warning."
        )
        return result

    if not valid_curves:
        print(
            f"Cannot create plot for {module_sn}: "
            "no valid IV curves are available."
        )
        return result

    print(
        f"Making {result['plot_category']} plot for {module_sn}"
    )

    fig, ax = plt.subplots()
    fig.set_size_inches(12, 8)

    blues = mplt.cm.Blues(
        np.linspace(0.4, 0.9, max(len(valid_curves), 1))
    )
    oranges = mplt.cm.Oranges(
        np.linspace(0.4, 0.9, max(len(valid_curves), 1))
    )

    handles = []
    labels = []

    for count, curve in enumerate(valid_curves):
        lcolour = (
            blues[count]
            if curve["ntcpb_temp"] < 0
            else oranges[count]
        )

        ntcx_txt = (
            "{0:.3g}"
            .format(curve["ntcx_temp"])
            .replace("-", "$-$")
        )

        label = (
            f"{curve['timestamp']}, {ntcx_txt}C"
        )

        line = ax.plot(
            curve["voltages"],
            curve["currents"],
            lw=2,
            ls="-",
            c=lcolour,
            label=label,
        )

        handles.append(line[0])
        labels.append(label)

    if handles:
        ax.legend(
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

    text_size = 28

    if do_logY:
        ax.set_yscale("log")
        ax.set_ylim(1, 10000)
    else:
        ax.set_ylim(-20, 550)

    ax.set_xlim(-10, 750)

    plt.xlabel(
        r"Voltage [V]",
        labelpad=15,
        size=38,
    )
    plt.ylabel(
        r"Current [nA]",
        labelpad=15,
        size=38,
    )

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

    fig.text(
        0.20,
        0.56,
        module_sn,
        color="k",
        size=text_size,
    )

    fig.text(
        0.20,
        0.51,
        (
            f"Timestamp: {first_valid_timestamp}"
            if first_valid_timestamp
            else "Timestamp: Unknown"
        ),
        color="k" if first_valid_timestamp else "gray",
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
    plt.subplots_adjust(
        top=0.97,
        left=0.16,
        right=0.99,
    )

    plot_dir = (
        Path(output_base_dir)
        / module_sn
        / "IV"
    )
    plot_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    save_base = plot_dir / module_sn
    save_pdf = f"{save_base}.pdf"
    save_png_path = f"{save_base}.png"

    print(
        f"Saving {result['plot_category']} plot as "
        f"{save_pdf}"
    )
    plt.savefig(
        save_pdf,
        format="pdf",
    )

    if save_png:
        print(
            f"Saving {result['plot_category']} plot as "
            f"{save_png_path}"
        )
        plt.savefig(
            save_png_path,
            format="png",
            dpi=300,
        )

    plt.close(fig)

    result["plot_pdf"] = save_pdf
    result["plot_png"] = (
        save_png_path
        if save_png
        else ""
    )

    if result["is_selected_plot_module"]:
        selected_pdf_dir = (
            Path(output_base_dir)
            / SELECTED_IV_PDF_FOLDER
        )
        selected_pdf_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        selected_pdf_copy = (
            selected_pdf_dir
            / f"{module_sn}.pdf"
        )

        shutil.copy2(
            save_pdf,
            selected_pdf_copy,
        )

        print(
            "Copied Category A / D(i) PDF to "
            f"{selected_pdf_copy}"
        )

        result["selected_pdf_copy"] = str(
            selected_pdf_copy
        )

    elif result["is_yellow_warning_plot_module"]:
        warning_pdf_dir = (
            Path(output_base_dir)
            / YELLOW_WARNING_IV_PDF_FOLDER
        )
        warning_pdf_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        warning_pdf_copy = (
            warning_pdf_dir
            / f"{module_sn}.pdf"
        )

        shutil.copy2(
            save_pdf,
            warning_pdf_copy,
        )

        print(
            "Copied yellow-warning PDF to "
            f"{warning_pdf_copy}"
        )

        result["warning_pdf_copy"] = str(
            warning_pdf_copy
        )

    return result


# ============================================================
# Build comments from worker results
# ============================================================

def build_comments_from_results(results):
    category_a_comments = OrderedDict()
    yellow_warning_comments = OrderedDict()
    category_d_i_comments = OrderedDict()
    category_e_i_comments = OrderedDict()

    for result in sorted(
        results,
        key=lambda x: x["module"],
    ):
        module = result["module"]

        category_a_records = (
            result["category_a_records"]
        )
        warning_records = (
            result["warning_records"]
        )
        d_records = result["category_d_records"]
        e_records = result["category_e_records"]

        if category_a_records:
            category_a_comments[module] = (
                make_iv_current_comment(
                    [
                        record["current"]
                        for record in category_a_records
                    ],
                    {
                        record["run"]
                        for record in category_a_records
                        if record["run"] is not None
                    },
                    [
                        record["temperature"]
                        for record in category_a_records
                    ],
                    CATEGORY_A_CURRENT_THRESHOLD_NA,
                )
            )

        elif warning_records:
            yellow_warning_comments[module] = (
                make_iv_current_comment(
                    [
                        record["current"]
                        for record in warning_records
                    ],
                    {
                        record["run"]
                        for record in warning_records
                        if record["run"] is not None
                    },
                    [
                        record["temperature"]
                        for record in warning_records
                    ],
                    WARNING_CURRENT_THRESHOLD_NA,
                )
            )

        d_runs = {
            record["run"]
            for record in d_records
            if record["run"] is not None
        }

        if d_runs:
            category_d_i_comments[module] = (
                make_category_d_i_comment(
                    d_runs
                )
            )

        elif d_records:
            category_d_i_comments[module] = (
                "Incomplete IV dataset. "
                "No valid IV curves were plotted for this module."
            )

        if e_records:
            category_e_i_comments[module] = (
                "IV data unavailable or could not be processed. "
                + e_records[0]["message"]
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
        f.write(
            f'    "{serial}": "{comment}",\n'
        )

    f.write("}\n\n")


def write_modules_format(f, comments):
    f.write('"modules": {\n')

    for serial, comment in comments.items():
        f.write(
            f'    "{strip_sn(serial)}": "{comment}",\n'
        )

    f.write("}\n\n")


def write_serial_list(f, title, comments):
    f.write("=" * 80 + "\n")
    f.write(title + "\n")
    f.write("=" * 80 + "\n\n")

    for serial in comments:
        f.write(
            f'    "{strip_sn(serial)}",\n'
        )

    f.write("\n")


def write_category_section(
    f,
    category_name,
    description,
    records,
):
    f.write("\n" + "=" * 80 + "\n")
    f.write(f"{category_name}\n")
    f.write(f"{description}\n")
    f.write("=" * 80 + "\n")

    if not records:
        f.write("None found.\n")
        return

    grouped = collections.defaultdict(list)

    for record in records:
        grouped[record["module"]].append(
            record["message"]
        )

    for module in sorted(grouped):
        f.write(
            f"\n{module}\n"
            + "-" * len(module)
            + "\n"
        )

        for index, message in enumerate(
            grouped[module],
            start=1,
        ):
            f.write(
                f"{index}. {message}\n"
            )


def write_error_summary(results, output_file):
    output_file = Path(output_file)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    total_modules_checked = len(results)

    selected_modules_plotted = sum(
        bool(result.get("plot_pdf"))
        for result in results
    )

    category_a_di_plots = sum(
        bool(result.get("selected_pdf_copy"))
        for result in results
    )

    warning_plots = sum(
        bool(result.get("warning_pdf_copy"))
        for result in results
    )

    not_selected_modules_skipped = sum(
        bool(result.get("plot_skipped_not_selected"))
        for result in results
    )

    modules_not_working = set()
    category_a_records = []
    category_d_records = []
    category_e_records = []

    for result in results:
        module = result["module"]

        if (
            result["category_a_records"]
            or result["category_d_records"]
            or result["category_e_records"]
        ):
            modules_not_working.add(module)

        category_a_records.extend(
            result["category_a_records"]
        )
        category_d_records.extend(
            result["category_d_records"]
        )
        category_e_records.extend(
            result["category_e_records"]
        )

    working_count = (
        total_modules_checked
        - len(modules_not_working)
    )

    total_entries = (
        len(category_a_records)
        + len(category_d_records)
        + len(category_e_records)
    )

    with output_file.open("w") as f:
        f.write(
            "IV Plot Error Summary\n"
            + "=" * 80
            + "\n\n"
        )

        f.write(
            "Generated: "
            f"{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        )
        f.write(
            f"Yellow warning threshold: > "
            f"{WARNING_CURRENT_THRESHOLD_NA:.0f} nA\n"
        )
        f.write(
            f"Category A threshold: > "
            f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA\n"
        )
        f.write(
            f"Expected IV tests: {EXPECTED_IV_TESTS}\n"
        )
        f.write(
            "Plot mode: Category A, Category D(i), "
            "and yellow-warning modules\n\n"
        )

        f.write(
            "FINAL SUMMARY\n"
            + "-" * 80
            + "\n"
        )
        f.write(
            f"TOTAL MODULES CHECKED: "
            f"{total_modules_checked}\n"
        )
        f.write(
            f"WORKING MODULES: "
            f"{working_count}\n"
        )
        f.write(
            f"NOT WORKING MODULES: "
            f"{len(modules_not_working)}\n"
        )
        f.write(
            f"TOTAL IV PLOTS SAVED: "
            f"{selected_modules_plotted}\n"
        )
        f.write(
            f"CATEGORY A / D(i) PLOTS SAVED: "
            f"{category_a_di_plots}\n"
        )
        f.write(
            f"YELLOW-WARNING PLOTS SAVED: "
            f"{warning_plots}\n"
        )
        f.write(
            f"NON-SELECTED MODULE PLOTS SKIPPED: "
            f"{not_selected_modules_skipped}\n"
        )
        f.write(
            f"TOTAL FLAGGED FILES / WARNINGS: "
            f"{total_entries}\n\n"
        )

        f.write(
            "CATEGORY COUNTS\n"
            + "-" * 80
            + "\n"
        )
        f.write(
            "Category A — IV current values above "
            f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA: "
            f"{len(category_a_records)}\n"
        )
        f.write(
            "Category D — Incomplete dataset or missing "
            f"generated files: {len(category_d_records)}\n"
        )
        f.write(
            "Category E — Script did not run or data are "
            f"unavailable: {len(category_e_records)}\n\n"
        )

        write_category_section(
            f,
            "Category A",
            (
                "IV current values above "
                f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA."
            ),
            category_a_records,
        )

        write_category_section(
            f,
            "Category D",
            (
                "Incomplete dataset or missing generated "
                "files."
            ),
            category_d_records,
        )

        write_category_section(
            f,
            "Category E",
            (
                "Script did not run or data are unavailable."
            ),
            category_e_records,
        )

    print(
        f"Saved IV error summary to: {output_file}"
    )


def write_category_summary(
    output_file,
    site_label,
    category_a_comments,
    yellow_warning_comments,
    category_d_i_comments,
    category_e_i_comments,
):
    output_file = Path(output_file)
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    combined_category_comments = OrderedDict()
    combined_category_comments.update(
        category_a_comments
    )
    combined_category_comments.update(
        category_d_i_comments
    )

    with output_file.open("w") as f:
        f.write("=" * 80 + "\n")
        f.write(
            f"{site_label} IV CATEGORY SUMMARY\n"
        )
        f.write("=" * 80 + "\n\n")

        f.write(
            f"Category A threshold: > "
            f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA\n"
        )

        f.write(
            f"Yellow warning threshold: > "
            f"{WARNING_CURRENT_THRESHOLD_NA:.0f} nA "
            f"and <= "
            f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA\n"
        )

        f.write(
            f"Expected IV tests: {EXPECTED_IV_TESTS}\n"
        )
        f.write(
            "Plot mode: Category A, Category D(i), "
            "and yellow-warning modules\n\n"
        )

        f.write(
            "FINAL COUNTS\n"
            + "-" * 80
            + "\n"
        )
        f.write(
            f"Category A modules: "
            f"{len(category_a_comments)}\n"
        )
        f.write(
            f"Yellow warning modules: "
            f"{len(yellow_warning_comments)}\n"
        )
        f.write(
            f"Category D(i) modules: "
            f"{len(category_d_i_comments)}\n"
        )
        f.write(
            f"Category E(i) modules: "
            f"{len(category_e_i_comments)}\n\n"
        )

        write_serial_list(
            f,
            (
                "CATEGORY A MODULE SERIALS ABOVE "
                f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA"
            ),
            category_a_comments,
        )

        write_serial_list(
            f,
            (
                "YELLOW WARNING MODULE SERIALS ABOVE "
                f"{WARNING_CURRENT_THRESHOLD_NA:.0f} nA "
                "BUT NOT ABOVE "
                f"{CATEGORY_A_CURRENT_THRESHOLD_NA:.0f} nA"
            ),
            yellow_warning_comments,
        )

        write_serial_list(
            f,
            (
                "CATEGORY D(i) MODULE SERIALS WITH "
                "INCOMPLETE IV DATASET"
            ),
            category_d_i_comments,
        )

        write_serial_list(
            f,
            (
                "CATEGORY E(i) MODULE SERIALS WITH "
                "IV DATA UNAVAILABLE"
            ),
            category_e_i_comments,
        )

        f.write(
            "=" * 80
            + "\nREADY-TO-PASTE CATEGORY A COMMENTS\n"
            + "=" * 80
            + "\n\n"
        )
        write_comment_dict(
            f,
            "category_a_comments",
            category_a_comments,
        )

        f.write(
            "=" * 80
            + "\nREADY-TO-PASTE YELLOW WARNING COMMENTS\n"
            + "=" * 80
            + "\n\n"
        )
        write_comment_dict(
            f,
            "yellow_warning_comments",
            yellow_warning_comments,
        )

        f.write(
            "=" * 80
            + "\nREADY-TO-PASTE CATEGORY D(i) COMMENTS\n"
            + "=" * 80
            + "\n\n"
        )
        write_comment_dict(
            f,
            "category_d_i_comments",
            category_d_i_comments,
        )

        f.write(
            "=" * 80
            + "\nREADY-TO-PASTE CATEGORY E(i) COMMENTS\n"
            + "=" * 80
            + "\n\n"
        )
        write_comment_dict(
            f,
            "category_e_i_comments",
            category_e_i_comments,
        )

        f.write(
            "=" * 80
            + "\nCATEGORY A CATEGORY_DEFINITIONS FORMAT\n"
            + "=" * 80
            + "\n\n"
        )
        write_modules_format(
            f,
            category_a_comments,
        )

        f.write(
            "=" * 80
            + "\nYELLOW WARNING / ADDITIONAL_COMMENTS FORMAT\n"
            + "=" * 80
            + "\n\n"
        )
        write_modules_format(
            f,
            yellow_warning_comments,
        )

        f.write(
            "=" * 80
            + "\nCATEGORY D(i) CATEGORY_DEFINITIONS FORMAT\n"
            + "=" * 80
            + "\n\n"
        )
        write_modules_format(
            f,
            category_d_i_comments,
        )

        f.write(
            "=" * 80
            + "\nCATEGORY E(i) CATEGORY_DEFINITIONS FORMAT\n"
            + "=" * 80
            + "\n\n"
        )
        write_modules_format(
            f,
            category_e_i_comments,
        )

        f.write(
            "=" * 80
            + "\nCOMBINED CATEGORY A + CATEGORY D(i) "
            "CATEGORY_DEFINITIONS FORMAT\n"
            + "=" * 80
            + "\n\n"
        )
        write_modules_format(
            f,
            combined_category_comments,
        )

    print(
        f"Saved IV category summary to: {output_file}"
    )


# ============================================================
# Main
# ============================================================

def main():
    parser = argparse.ArgumentParser(
        description=(
            "Fast BNL IV analyzer and Category A / D(i) / "
            "yellow-warning summary generator."
        )
    )

    parser.add_argument(
        "-i",
        "--input",
        required=True,
        help=(
            'Input glob, for example '
            '"BNL/ML/*/*.json"'
        ),
    )

    parser.add_argument(
        "-o",
        "--output",
        default=DEFAULT_OUTPUT_DIR,
        help=(
            f"Output base folder. "
            f"Default: {DEFAULT_OUTPUT_DIR}"
        ),
    )

    parser.add_argument(
        "--workers",
        type=int,
        default=6,
        help=(
            "Number of parallel workers. "
            "Default: 6"
        ),
    )

    parser.add_argument(
        "--do_amac_offset",
        action="store_true",
        help=(
            "Subtract first current value as AMAC offset."
        ),
    )

    parser.add_argument(
        "--do_logY",
        action="store_true",
        help=(
            "Use log scale for current axis."
        ),
    )

    parser.add_argument(
        "--no_png",
        action="store_true",
        help=(
            "Save only PDF, not PNG, for faster testing."
        ),
    )

    args = parser.parse_args()

    output_base_dir = Path(args.output)
    output_base_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    input_files = sorted(
        glob(args.input)
    )

    print("\n" + "=" * 80)
    print(
        "FAST BNL IV ANALYSIS — "
        "PLOT CATEGORY A, D(i), AND WARNINGS"
    )
    print("=" * 80)
    print(f"Input glob: {args.input}")
    print(
        f"Output folder: {output_base_dir}"
    )
    print(f"Workers: {args.workers}")
    print(
        f"Save PNG: {not args.no_png}"
    )
    print(
        f"Found JSON files: {len(input_files)}"
    )
    print("=" * 80 + "\n")

    if not input_files:
        raise FileNotFoundError(
            "No JSON files found for input pattern:\n"
            f"{args.input}"
        )

    module_file_map, unreadable_files = (
        build_module_file_map(
            input_files
        )
    )

    print(
        f"Modules found: {len(module_file_map)}"
    )

    if unreadable_files:
        print(
            "Unreadable / unassigned files: "
            f"{len(unreadable_files)}"
        )

    if not module_file_map:
        raise RuntimeError(
            "No valid module names could be parsed "
            "from JSON files."
        )

    tasks = [
        (
            module_name,
            files,
            str(output_base_dir),
            args.do_amac_offset,
            args.do_logY,
            not args.no_png,
        )
        for module_name, files
        in module_file_map.items()
    ]

    results = []

    if args.workers <= 1:
        for index, task in enumerate(
            tasks,
            start=1,
        ):
            result = (
                plot_one_module_worker(task)
            )
            results.append(result)

            if result["plot_pdf"]:
                status = (
                    f"PLOTTED "
                    f"{result['plot_category']}"
                )
            else:
                status = (
                    "NO A/D(i)/WARNING—SKIPPED"
                )

            print(
                f"[{index}/{len(tasks)}] "
                f"Finished {result['module']} — "
                f"{status}"
            )

    else:
        with ProcessPoolExecutor(
            max_workers=args.workers
        ) as executor:
            future_to_module = {
                executor.submit(
                    plot_one_module_worker,
                    task,
                ): task[0]
                for task in tasks
            }

            for completed, future in enumerate(
                as_completed(
                    future_to_module
                ),
                start=1,
            ):
                module_name = (
                    future_to_module[future]
                )

                try:
                    result = future.result()
                    results.append(result)

                    if result["plot_pdf"]:
                        status = (
                            f"PLOTTED "
                            f"{result['plot_category']}"
                        )
                    else:
                        status = (
                            "NO A/D(i)/WARNING—SKIPPED"
                        )

                    print(
                        f"[{completed}/{len(tasks)}] "
                        f"Finished {module_name} "
                        f"valid curves="
                        f"{result['valid_plot_count']} "
                        f"— {status}"
                    )

                except Exception as exc:
                    module_sn = with_sn(
                        module_name
                    )

                    print(
                        f"❌ Worker failed for "
                        f"{module_sn}: {exc}"
                    )

                    results.append({
                        "module": module_sn,
                        "checked": True,
                        "is_selected_plot_module": False,
                        "is_yellow_warning_plot_module": False,
                        "plot_category": "",
                        "plot_skipped_not_selected": True,
                        "valid_plot_count": 0,
                        "warning_records": [],
                        "category_a_records": [],
                        "category_d_records": [],
                        "category_e_records": [{
                            "module": module_sn,
                            "file": "N/A",
                            "run": None,
                            "message": (
                                f"Worker failed: {exc}"
                            ),
                        }],
                        "present_runs": set(),
                        "missing_runs": set(),
                        "plot_pdf": "",
                        "plot_png": "",
                        "selected_pdf_copy": "",
                        "warning_pdf_copy": "",
        "above_300_json": "",
                    })

    results = sorted(
        results,
        key=lambda x: x["module"],
    )

    (
        category_a_comments,
        yellow_warning_comments,
        category_d_i_comments,
        category_e_i_comments,
    ) = build_comments_from_results(
        results
    )

    iv_error_summary_file = (
        output_base_dir
        / "iv_error_summary.txt"
    )

    iv_category_summary_file = (
        output_base_dir
        / "iv_category_summary_bnl.txt"
    )

    write_error_summary(
        results,
        iv_error_summary_file,
    )

    write_category_summary(
        iv_category_summary_file,
        SITE,
        category_a_comments,
        yellow_warning_comments,
        category_d_i_comments,
        category_e_i_comments,
    )

    total_plots = sum(
        bool(result.get("plot_pdf"))
        for result in results
    )

    selected_plots = sum(
        bool(result.get("selected_pdf_copy"))
        for result in results
    )

    warning_plots = sum(
        bool(result.get("warning_pdf_copy"))
        for result in results
    )

    above_300_json_files = sum(
        bool(result.get("above_300_json"))
        for result in results
    )

    not_selected_skipped = sum(
        bool(
            result.get(
                "plot_skipped_not_selected"
            )
        )
        for result in results
    )

    print("\n" + "=" * 80)
    print("DONE")
    print("=" * 80)
    print(
        f"Modules analyzed: {len(results)}"
    )
    print(
        f"Total IV plots saved: {total_plots}"
    )
    print(
        "Category A / D(i) plots saved: "
        f"{selected_plots}"
    )
    print(
        "Yellow-warning plots saved: "
        f"{warning_plots}"
    )
    print(
        "IV >300 nA JSON files saved: "
        f"{above_300_json_files}"
    )
    print(
        "Non-selected module plots skipped: "
        f"{not_selected_skipped}"
    )

    print(
        "Module plot folders: "
        f"{output_base_dir}/"
        "SN20USBML.../IV/"
    )

    print(
        "Category A / D(i) PDF folder: "
        f"{output_base_dir}/"
        f"{SELECTED_IV_PDF_FOLDER}/"
    )

    print(
        "Yellow-warning PDF folder: "
        f"{output_base_dir}/"
        f"{YELLOW_WARNING_IV_PDF_FOLDER}/"
    )

    print(
        "IV >300 nA JSON folder: "
        f"{output_base_dir}/"
        f"{IV_ABOVE_300_JSON_FOLDER}/"
    )

    print(
        f"Saved: {iv_error_summary_file}"
    )
    print(
        f"Saved: {iv_category_summary_file}"
    )
    print("")
    print("Important:")
    print(
        "  Plot saved = Category A, "
        "Category D(i), or yellow warning"
    )
    print(
        "  Category A = IV current > 600 nA"
    )
    print(
        "  Yellow warning = IV current > 300 nA "
        "and <= 600 nA"
    )
    print(
        "  Category D(i) = incomplete IV dataset"
    )
    print(
        "  Category E(i) = unreadable or "
        "unavailable IV data"
    )
    print("=" * 80)


if __name__ == "__main__":
    main()
