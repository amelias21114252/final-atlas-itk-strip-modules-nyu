#!/usr/bin/env python3
"""
Script: plot_combined_inputnoise.py

Description:
    Loads JSON files (input noise data) and creates one overlaid histogram plot per stream:
      - Categorized by cold (≤0°C) and warm (>0°C)
      - Includes mean/std markers
      - Shows skipped files in the legend (in red)
      - Prints single global timestamp and parent module in title and legend

Usage:
    python plot_combined_inputnoise.py --serial_number 20USBHX2002657
    python plot_combined_inputnoise.py --serial_number 20USBHX2002592

    python plot_combined_inputnoise.py --serial_number 20USBHX2002683


python plot_combined_inputnoise.py --serial_number 20USBHX2002657
python plot_combined_inputnoise.py --serial_number 20USBHX2002683
python plot_combined_inputnoise.py --serial_number 20USBHX2002629
python plot_combined_inputnoise.py --serial_number 20USBHX2002630
python plot_combined_inputnoise.py --serial_number 20USBHX2002603
python plot_combined_inputnoise.py --serial_number 20USBHX2002631
python plot_combined_inputnoise.py --serial_number 20USBHX2002652
python plot_combined_inputnoise.py --serial_number 20USBHX2002653
⚠️ Skipping dead sensor entry: Sensor Dead
python plot_combined_inputnoise.py --serial_number 20USBHX2002654
python plot_combined_inputnoise.py --serial_number 20USBHX2002656
python plot_combined_inputnoise.py --serial_number 20USBHX2002684
python plot_combined_inputnoise.py --serial_number 20USBHX2002685
python plot_combined_inputnoise.py --serial_number 20USBHX2002686
python plot_combined_inputnoise.py --serial_number 20USBHX2002687
python plot_combined_inputnoise.py --serial_number 20USBHX2002688
python plot_combined_inputnoise.py --serial_number 20USBHX2002709
python plot_combined_inputnoise.py --serial_number 20USBHX2002710
python plot_combined_inputnoise.py --serial_number 20USBHX2002711
python plot_combined_inputnoise.py --serial_number 20USBHX2002712
python plot_combined_inputnoise.py --serial_number 20USBHX2002713
python plot_combined_inputnoise.py --serial_number 20USBHX2002677
python plot_combined_inputnoise.py --serial_number 20USBHX2002678
python plot_combined_inputnoise.py --serial_number 20USBHX2002679
python plot_combined_inputnoise.py --serial_number 20USBHX2002680
python plot_combined_inputnoise.py --serial_number 20USBHX2002655
python plot_combined_inputnoise.py --serial_number 20USBHX2002691
python plot_combined_inputnoise.py --serial_number 20USBHX2002692
python plot_combined_inputnoise.py --serial_number 20USBHX2002693
python plot_combined_inputnoise.py --serial_number 20USBHX2002689
python plot_combined_inputnoise.py --serial_number 20USBHX2002681
python plot_combined_inputnoise.py --serial_number 20USBHX2002682
python plot_combined_inputnoise.py --serial_number 20USBHX2002690 ///
python plot_combined_inputnoise.py --serial_number 20USBHX2002694
python plot_combined_inputnoise.py --serial_number 20USBHX2002695
python plot_combined_inputnoise.py --serial_number 20USBHX2002783
python plot_combined_inputnoise.py --serial_number 20USBHX2002697
python plot_combined_inputnoise.py --serial_number 20USBHX2002698
python plot_combined_inputnoise.py --serial_number 20USBHX2002940
python plot_combined_inputnoise.py --serial_number 20USBHX2002942
python plot_combined_inputnoise.py --serial_number 20USBHX2002943
python plot_combined_inputnoise.py --serial_number 20USBHX2002938
python plot_combined_inputnoise.py --serial_number 20USBHX2002939
python plot_combined_inputnoise.py --serial_number 20USBHX2002944
python plot_combined_inputnoise.py --serial_number 20USBHX2002953
python plot_combined_inputnoise.py --serial_number 20USBHX2002954
python plot_combined_inputnoise.py --serial_number 20USBHX2002956
python plot_combined_inputnoise.py --serial_number 20USBHX2002957
python plot_combined_inputnoise.py --serial_number 20USBHX2002971
python plot_combined_inputnoise.py --serial_number 20USBHX2002964
python plot_combined_inputnoise.py --serial_number 20USBHX2002965
python plot_combined_inputnoise.py --serial_number 20USBHX2002966
python plot_combined_inputnoise.py --serial_number 20USBHX2002967
python plot_combined_inputnoise.py --serial_number 20USBHX2002983
python plot_combined_inputnoise.py --serial_number 20USBHX2002960
python plot_combined_inputnoise.py --serial_number 20USBHX2002961
python plot_combined_inputnoise.py --serial_number 20USBHX2002787
python plot_combined_inputnoise.py --serial_number 20USBHX2002959
python plot_combined_inputnoise.py --serial_number 20USBHX2002958
python plot_combined_inputnoise.py --serial_number 20USBHX2002980
python plot_combined_inputnoise.py --serial_number 20USBHX2002981
python plot_combined_inputnoise.py --serial_number 20USBHX2002982
python plot_combined_inputnoise.py --serial_number 20USBHX2002968
python plot_combined_inputnoise.py --serial_number 20USBHX2002969
python plot_combined_inputnoise.py --serial_number 20USBHX2002970
"""

import os
import json
import numpy as np
import matplotlib.pyplot as plt
import glob
import argparse
from datetime import datetime
from matplotlib import cm

def flatten(input):
    if isinstance(input, list) and all(isinstance(x, (int, float)) for x in input):
        return input
    elif isinstance(input, list) and all(isinstance(x, list) for x in input):
        return [item for sublist in input for item in sublist]
    else:
        raise TypeError(f"Expected list of floats or list of lists, got: {type(input)}")

def parse_timestamp(ts_str):
    try:
        return datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
    except Exception:
        return datetime.min

def plot_combined_stream(json_paths, stream='under', save_dir='plots_combined', serial_number="UNKNOWN"):
    file_data = []
    warm_noise_values = []
    cold_noise_values = []
    skipped_files = []
    parent_name = "Unknown Parent"

    # Load first valid JSON to get parent name
    for path in json_paths:
        try:
            with open(path, 'r') as f:
                first_data = json.load(f)
            if "parent_name" in first_data:
                parent_name = first_data["parent_name"]
            break
        except:
            continue

    for path in json_paths:
        with open(path, 'r') as f:
            data = json.load(f)

        try:
            noise_raw = data["results"]["innse_under" if stream == 'under' else "innse_away"]
            noise = flatten(noise_raw)
        except Exception as e:
            msg = f"{os.path.basename(path)} — invalid noise structure ({e})"
            print(f"❌ Skipping {msg}")
            skipped_files.append(msg)
            continue

        try:
            temp = data["properties"]["DCS"]["AMAC_NTCpb"]
            mean_val = np.mean(noise)
            std_val = np.std(noise)

            if mean_val > 1000 or mean_val < 0 or std_val > 300:
                msg = f"{os.path.basename(path)} — mean={mean_val:.1f}, std={std_val:.1f}"
                print(f"⚠ Skipping {msg}")
                skipped_files.append(msg)
                continue

            timestamp_raw = data.get("timestamp", data.get("date", "Unknown Time"))
            timestamp_clean = timestamp_raw.replace("T", " ").split(".")[0].replace("Z", "").strip()

            file_data.append({
                'file': os.path.basename(path),
                'temp': temp,
                'noise': noise,
                'timestamp': timestamp_clean
            })

            if temp > 0:
                warm_noise_values.extend(noise)
            else:
                cold_noise_values.extend(noise)

        except Exception as e:
            msg = f"{os.path.basename(path)} — parsing error ({e})"
            print(f"❌ Skipping {msg}")
            skipped_files.append(msg)
            continue

    cold_data = sorted([d for d in file_data if d['temp'] <= 0], key=lambda x: parse_timestamp(x['timestamp']))
    warm_data = sorted([d for d in file_data if d['temp'] > 0], key=lambda x: parse_timestamp(x['timestamp']))

    cold_cmap = cm.get_cmap('Blues', max(len(cold_data), 1))
    warm_cmap = cm.get_cmap('Oranges', max(len(warm_data), 1))

    cold_mean = np.mean(cold_noise_values) if cold_noise_values else np.nan
    warm_mean = np.mean(warm_noise_values) if warm_noise_values else np.nan
    cold_std = np.std(cold_noise_values) if cold_noise_values else np.nan
    warm_std = np.std(warm_noise_values) if warm_noise_values else np.nan

    plt.figure(figsize=(14, 6))
    legend_entries = []

    # Global timestamp
    first_timestamp = None
    for entry in file_data:
        if entry['timestamp'] != "Unknown Time":
            first_timestamp = entry['timestamp']
            break
    if first_timestamp:
        legend_entries.append(f"Timestamp: {first_timestamp}")

    for i, entry in enumerate(cold_data):
        color = cold_cmap(i)
        mean_val = np.mean(entry['noise'])
        std_val = np.std(entry['noise'])
        label = f"cold_{i+1:02d} T={entry['temp']:.1f}°C | μ={mean_val:.1f}, σ={std_val:.1f}"
        plt.hist(entry['noise'], bins=40, alpha=0.5, color=color, edgecolor='black', linewidth=0.3)
        plt.axvline(mean_val, color=color, linestyle='dashed', linewidth=1)
        legend_entries.append(label)

    for i, entry in enumerate(warm_data):
        color = warm_cmap(i)
        mean_val = np.mean(entry['noise'])
        std_val = np.std(entry['noise'])
        label = f"warm_{i+1:02d} T={entry['temp']:.1f}°C | μ={mean_val:.1f}, σ={std_val:.1f}"
        plt.hist(entry['noise'], bins=40, alpha=0.5, color=color, edgecolor='black', linewidth=0.3)
        plt.axvline(mean_val, color=color, linestyle='dashed', linewidth=1)
        legend_entries.append(label)

    if not np.isnan(cold_mean):
        plt.axvline(cold_mean, color='blue', linestyle='dashed', linewidth=2.5)
        legend_entries.append(f"All Cold μ={cold_mean:.1f}, σ={cold_std:.1f}")
    if not np.isnan(warm_mean):
        plt.axvline(warm_mean, color='orange', linestyle='dashed', linewidth=2.5)
        legend_entries.append(f"All Warm μ={warm_mean:.1f}, σ={warm_std:.1f}")

    for msg in skipped_files:
        plt.plot([], [], ' ', label=f"⛔ {msg}")
        legend_entries.append(f"⛔ {msg}")

    plt.xlabel('Input Noise [ENC]')
    plt.ylabel('Counts')

    # Updated title to include parent name and timestamp
    title_str = f"Module SN: SN{serial_number} | Parent: SN{parent_name}\nOverlaid {stream} Histograms"
    if first_timestamp:
        title_str += f"\nTimestamp: {first_timestamp}"
    plt.title(title_str)

    plt.grid(True)
    legend = plt.legend(legend_entries, fontsize='x-small', loc='center left', bbox_to_anchor=(-0.02, 0.5))
    for txt in legend.get_texts():
        if txt.get_text().startswith("⛔"):
            txt.set_color('red')

    plt.xlim(700, 1000)
    plt.tight_layout()

    os.makedirs(save_dir, exist_ok=True)
    save_path = os.path.join(save_dir, f"SN{serial_number}_combined-{stream}")
    plt.savefig(f"{save_path}.pdf")
    plt.savefig(f"{save_path}.png", dpi=300)
    plt.close()

    print(f"✅ Saved: {save_path}.pdf and .png")

    if skipped_files:
        print("\n🚫 Skipped files due to data issues:")
        for f in skipped_files:
            print(f" - {f}")

def main():
    parser = argparse.ArgumentParser(description="Plot combined input noise histograms")
    parser.add_argument("--serial_number", required=True, help="e.g. 20USBHX2002657")
    args = parser.parse_args()

    serial = args.serial_number
    input_dir = f"SN{serial}"
    file_pattern = f"SN{serial}_*.json"
    file_paths = sorted(glob.glob(os.path.join(input_dir, file_pattern)))
    output_dir = os.path.join(input_dir, "histograms_combined")

    if not file_paths:
        print("⚠️ No matching JSON files found.")
        return

    plot_combined_stream(file_paths, stream='under', save_dir=output_dir, serial_number=serial)
    plot_combined_stream(file_paths, stream='away', save_dir=output_dir, serial_number=serial)

if __name__ == "__main__":
    main()
