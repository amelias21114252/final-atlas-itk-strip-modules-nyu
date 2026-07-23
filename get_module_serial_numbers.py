#!/usr/bin/env python

# python get_module_serial_numbers.py --max_workers 6

#export ITK_DB_AUTH=YOUR_TOKEN


"""
Script to retrieve serial numbers of production ITk modules from different
assembly institutes and automatically save ML and HX serial-number lists.

This faster version uses ThreadPoolExecutor to fetch hybrid serial numbers
in parallel.

Authentication:
    export ITK_DB_AUTH=TOKEN
"""

import os
import argparse
from pathlib import Path
from pprint import pprint
from concurrent.futures import ThreadPoolExecutor, as_completed

import itkdb
import pandas as pd


# ============================================================
# Output folder
# ============================================================

OUTPUT_DIR = Path("serial_lists")
OUTPUT_DIR.mkdir(exist_ok=True)


# ============================================================
# Helper functions
# ============================================================

def normalize_serial(serial):
    if serial is None:
        return ""

    return str(serial).strip()


def strip_sn(serial):
    serial = normalize_serial(serial)

    if serial.startswith("SN"):
        return serial[2:]

    return serial


def make_client(token):
    """
    Make a new ITkDB client.

    Important: each thread should use its own client.
    """
    if token:
        user = itkdb.core.UserBearer(bearer=token)
        return itkdb.Client(user=user)

    return itkdb.Client()


def fetch_serials_from_batch(batch_names, institute, component_type, client):
    """
    Fetch module serial numbers from ITk database for one institute.
    """

    print("=" * 80)
    print("Fetching serial numbers")
    print(f"Institute: {institute}")
    print(f"Component type: {component_type}")
    print(f"Batch names: {batch_names}")
    print("=" * 80)

    data = {
        "filterMap": {
            "componentType": component_type,
            "institute": institute,
        }
    }

    component_jsons = client.get("listComponents", json=data)

    components = pd.json_normalize(
        data=component_jsons,
        record_path=["batches"],
        meta=["serialNumber", "state", "trashed"],
        record_prefix="_",
    )

    list_of_components_in_batch = components.loc[
        (components["_number"].isin(batch_names))
        & (components["_state"] == "ready")
        & (components["state"] == "ready")
    ]

    serial_numbers = (
        list_of_components_in_batch["serialNumber"]
        .dropna()
        .astype(str)
        .str.strip()
        .tolist()
    )

    print()
    print(
        f"Fetched {len(serial_numbers)} serial numbers "
        f"for {component_type} at {institute}"
    )

    return serial_numbers


def get_hybrid_serial_from_module(module_serial, token):
    """
    Given one ML module serial number, get its connected HX hybrid serial number.

    This function creates its own ITkDB client so it is safe to use in threads.
    """

    module_serial = normalize_serial(module_serial)

    try:
        client = make_client(token)

        component = client.get(
            "getComponent",
            json={"component": module_serial},
        )

    except Exception as error:
        return module_serial, "", f"ERROR getting component for {module_serial}: {error}"

    hybrid_serial = ""

    for item in component.get("children", []):
        component_type = item.get("componentType", {}).get("code", "")

        if "HYBRID" in component_type:
            try:
                hybrid_serial = item["component"]["serialNumber"]
            except Exception:
                hybrid_serial = ""

    hybrid_serial = normalize_serial(hybrid_serial)

    return module_serial, hybrid_serial, ""


def hybrid_serial_dictionary_from_module_list(module_serial_numbers, token, max_workers=6):
    """
    Create dictionary:

        ML serial number -> HX serial number

    This faster version runs the getComponent calls in parallel.
    """

    d_hybrid_serials = {}

    print()
    print("Fetching hybrid serial numbers in parallel")
    print(f"Number of modules: {len(module_serial_numbers)}")
    print(f"Parallel workers: {max_workers}")
    print("-" * 80)

    with ThreadPoolExecutor(max_workers=max_workers) as executor:

        future_to_module = {
            executor.submit(
                get_hybrid_serial_from_module,
                module_serial,
                token,
            ): module_serial
            for module_serial in module_serial_numbers
        }

        for i, future in enumerate(as_completed(future_to_module), start=1):
            module_serial = future_to_module[future]

            try:
                module_serial, hybrid_serial, error = future.result()

                d_hybrid_serials[module_serial] = hybrid_serial

                if error:
                    print(f"[{i}/{len(module_serial_numbers)}] {error}")
                else:
                    print(
                        f"[{i}/{len(module_serial_numbers)}] "
                        f"{module_serial}, {hybrid_serial}"
                    )

            except Exception as error:
                d_hybrid_serials[module_serial] = ""
                print(
                    f"[{i}/{len(module_serial_numbers)}] "
                    f"ERROR for {module_serial}: {error}"
                )

    # Keep same order as input list
    ordered_dictionary = {
        module_serial: d_hybrid_serials.get(module_serial, "")
        for module_serial in module_serial_numbers
    }

    return ordered_dictionary


def save_serial_list(serials, output_file, remove_sn=True):
    """
    Save one serial number per line.
    """

    cleaned_serials = []

    for serial in serials:
        serial = normalize_serial(serial)

        if not serial:
            continue

        if remove_sn:
            serial = strip_sn(serial)

        cleaned_serials.append(serial)

    output_file = Path(output_file)

    with output_file.open("w") as f:
        for serial in cleaned_serials:
            f.write(serial + "\n")

    print(f"Saved {len(cleaned_serials)} serials to {output_file}")


def save_module_hybrid_pairs_csv(all_pairs, output_file):
    """
    Save all institute ML-HX pairs into one CSV file.
    """

    rows = []

    for institute, pair_dict in all_pairs.items():
        for ml_serial, hx_serial in pair_dict.items():
            rows.append(
                {
                    "institute": institute,
                    "ml_serial_with_sn": normalize_serial(ml_serial),
                    "hx_serial_with_sn": normalize_serial(hx_serial),
                    "ml_serial": strip_sn(ml_serial),
                    "hx_serial": strip_sn(hx_serial),
                }
            )

    df = pd.DataFrame(rows)
    df.to_csv(output_file, index=False)

    print(f"Saved module-hybrid pair CSV to {output_file}")


def save_institute_outputs(institute_name, pair_dict):
    """
    Save ML and HX serial lists for one institute.
    """

    short_name = institute_name.lower()

    ml_serials = list(pair_dict.keys())
    hx_serials = list(pair_dict.values())

    ml_output = OUTPUT_DIR / f"{short_name}_ml_serials.txt"
    hx_output = OUTPUT_DIR / f"{short_name}_hx_serials.txt"

    save_serial_list(ml_serials, ml_output, remove_sn=True)
    save_serial_list(hx_serials, hx_output, remove_sn=True)


# ============================================================
# Main
# ============================================================

if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Fetch ITk module and hybrid serial numbers."
    )

    parser.add_argument(
        "--max_workers",
        type=int,
        default=6,
        help="Number of parallel workers for hybrid lookups. Try 4, 6, or 8.",
    )

    args = parser.parse_args()

    token = os.getenv("ITK_DB_AUTH")

    if not token:
        print("=" * 80)
        print("WARNING: ITK_DB_AUTH is not set.")
        print("You should run:")
        print("export ITK_DB_AUTH=YOUR_TOKEN")
        print("=" * 80)
    else:
        print("ITK_DB_AUTH token found.")

    main_client = make_client(token)

    # ========================================================
    # Lawrence Berkeley National Laboratory
    # ========================================================

    print()
    print("Fetching LBNL module/hybrid serial numbers")

    serials_LBNL = fetch_serials_from_batch(
        batch_names=["PRODUCTION_LBNL"],
        institute="LBNL_STRIP_MODULES",
        component_type="MODULE",
        client=main_client,
    )

    d_hybrids_LBNL = hybrid_serial_dictionary_from_module_list(
        serials_LBNL,
        token,
        max_workers=args.max_workers,
    )

    # ========================================================
    # Brookhaven National Laboratory
    # ========================================================

    print()
    print("Fetching BNL module/hybrid serial numbers")

    serials_BNL = fetch_serials_from_batch(
        batch_names=["PRODUCTION_BNL"],
        institute="BNL",
        component_type="MODULE",
        client=main_client,
    )

    d_hybrids_BNL = hybrid_serial_dictionary_from_module_list(
        serials_BNL,
        token,
        max_workers=args.max_workers,
    )

    # ========================================================
    # University of California Santa Cruz
    # ========================================================

    print()
    print("Fetching UCSC module/hybrid serial numbers")

    serials_UCSC = fetch_serials_from_batch(
        batch_names=["PRODUCTION_UCSC"],
        institute="UCSC",
        component_type="MODULE",
        client=main_client,
    )

    d_hybrids_UCSC = hybrid_serial_dictionary_from_module_list(
        serials_UCSC,
        token,
        max_workers=args.max_workers,
    )

    # ========================================================
    # Print dictionaries
    # ========================================================

    print()
    print("Serial numbers for Brookhaven BNL ITk production modules and hybrids:")
    pprint(d_hybrids_BNL)

    print()
    print("Serial numbers for Berkeley LBNL ITk production modules and hybrids:")
    pprint(d_hybrids_LBNL)

    print()
    print("Serial numbers for Santa Cruz UCSC ITk production modules and hybrids:")
    pprint(d_hybrids_UCSC)

    # ========================================================
    # Save automatic output files
    # ========================================================

    print()
    print("=" * 80)
    print("Saving automatic serial-number output files")
    print("=" * 80)

    all_pairs = {
        "BNL": d_hybrids_BNL,
        "LBNL": d_hybrids_LBNL,
        "UCSC": d_hybrids_UCSC,
    }

    save_institute_outputs("BNL", d_hybrids_BNL)
    save_institute_outputs("LBNL", d_hybrids_LBNL)
    save_institute_outputs("UCSC", d_hybrids_UCSC)

    save_module_hybrid_pairs_csv(
        all_pairs,
        OUTPUT_DIR / "all_module_hybrid_pairs.csv",
    )

    print()
    print("=" * 80)
    print("Finished.")
    print("Created these files:")
    print(f"{OUTPUT_DIR}/bnl_ml_serials.txt")
    print(f"{OUTPUT_DIR}/bnl_hx_serials.txt")
    print(f"{OUTPUT_DIR}/lbnl_ml_serials.txt")
    print(f"{OUTPUT_DIR}/lbnl_hx_serials.txt")
    print(f"{OUTPUT_DIR}/ucsc_ml_serials.txt")
    print(f"{OUTPUT_DIR}/ucsc_hx_serials.txt")
    print(f"{OUTPUT_DIR}/all_module_hybrid_pairs.csv")
    print("=" * 80)