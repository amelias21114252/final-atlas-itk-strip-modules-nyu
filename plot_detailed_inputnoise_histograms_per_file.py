#!/usr/bin/env python3
"""
Script: plot_detailed_inputnoise_histograms_per_file.py

Description:
    For each JSON file matching a pattern, this script:
    - Plots per-channel histograms for 'innse_under' and 'innse_away'
    - Plots one combined histogram for each of them
    - Displays mean/std lines
    - Prints and displays number of <600 and >1000 values

    python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002592
    python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002657

    python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002683

python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002657
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002683
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002629
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002630
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002603
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002631
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002652
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002653
⚠️ Skipping dead sensor entry: Sensor Dead
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002654
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002656
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002684
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002685
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002686

python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002688
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002709
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002710
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002711
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002712
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002713
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002677 ///

python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002678
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002679
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002680
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002655
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002692
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002691
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002693
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002689
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002681
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002682
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002690
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002694
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002695
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002783
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002697
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002698
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002784
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002785
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002786
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002940
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002942
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002943
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002938
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002939
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002944
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002953
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002954
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002956
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002957
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002971
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002964
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002965
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002966
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002967
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002983
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002960
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002961
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002787
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002959
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002958
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002980
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002981
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002982
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002968
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002969
python plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002970
"""

import json
import matplotlib.pyplot as plt
import os
import glob
import numpy as np
import argparse

def flatten(input_list):
    return [item for sublist in input_list for item in sublist]

def main():
    parser = argparse.ArgumentParser(description="Plot histograms for input noise JSON files")
    parser.add_argument("--serial_number", required=True, help="e.g. 20USBHX2002592")
    args = parser.parse_args()

    serial_number = args.serial_number
    input_dir = f"SN{serial_number}"
    file_pattern = f"SN{serial_number}_*.json"
    file_paths = sorted(glob.glob(os.path.join(input_dir, file_pattern)))

    print(f"Found {len(file_paths)} files in {input_dir}")
    if not file_paths:
        print("❌ No matching JSON files found.")
        return

    output_dir = os.path.join(input_dir, "detailedhistograms")
    os.makedirs(output_dir, exist_ok=True)

    for file_path in file_paths:
        with open(file_path, 'r') as f:
            data = json.load(f)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        timestamp_raw = data.get("timestamp", data.get("date", "Unknown Time"))
        timestamp_str = timestamp_raw.replace("T", " ").split(".")[0].replace("Z", "").strip()
        parent_name = data.get("parent_name", None)

        ntcpb_temp = data["properties"]["DCS"]["AMAC_NTCpb"]
        ntcx_temp = data["properties"]["DCS"]["AMAC_NTCx"]
        is_warm = (ntcpb_temp > 0) and (ntcx_temp > 0)
        bar_color = '#ff7f0e' if is_warm else '#1f77b4'

        innse_under_list = data["results"].get("innse_under", [])
        innse_away_list = data["results"].get("innse_away", [])
        mean_under_list = data["results"].get("innse_mean_under", [])
        mean_away_list = data["results"].get("innse_mean_away", [])

        title_prefix = f"{base_name}"
        if parent_name:
            title_prefix += f" (SN{parent_name})"

        # Plot per-channel innse_under
        for idx, arr in enumerate(innse_under_list):
            mean_val = mean_under_list[idx] if idx < len(mean_under_list) else np.mean(arr)
            std_val = np.std(arr)
            low_vals = [v for v in arr if v < 600]
            high_vals = [v for v in arr if v > 1000]
            print(f"🔍 {base_name}_innse_under[{idx}]: <600: {len(low_vals)}, >1000: {len(high_vals)}")

            plt.figure(figsize=(8, 5))
            plt.hist(arr, bins=20, edgecolor='black', alpha=0.75, color=bar_color)
            plt.axvline(mean_val, color='red', linestyle='--')
            plt.text(0.98, 0.95, f"(<600: {len(low_vals)}, >1000: {len(high_vals)})",
                     transform=plt.gca().transAxes, ha='right', va='top', color='red', fontsize='small')
            plt.title(f"{title_prefix}\ninnse_under[{idx}] (NTCpb={ntcpb_temp:.1f}°C, NTCx={ntcx_temp:.1f}°C)\n{timestamp_str}")
            plt.xlabel("Input Noise (ENC)")
            plt.ylabel("Frequency")
            plt.legend([f"Mean = {mean_val:.2f}", f"Std Dev = {std_val:.2f}"])
            plt.tight_layout()
            plt.savefig(f"{output_dir}/{base_name}_innse_under_{idx}.pdf")
            plt.close()

        # Plot per-channel innse_away
        for idx, arr in enumerate(innse_away_list):
            mean_val = mean_away_list[idx] if idx < len(mean_away_list) else np.mean(arr)
            std_val = np.std(arr)
            low_vals = [v for v in arr if v < 600]
            high_vals = [v for v in arr if v > 1000]
            print(f"🔍 {base_name}_innse_away[{idx}]: <600: {len(low_vals)}, >1000: {len(high_vals)}")

            plt.figure(figsize=(8, 5))
            plt.hist(arr, bins=20, edgecolor='black', alpha=0.75, color=bar_color)
            plt.axvline(mean_val, color='red', linestyle='--')
            plt.text(0.98, 0.95, f"(<600: {len(low_vals)}, >1000: {len(high_vals)})",
                     transform=plt.gca().transAxes, ha='right', va='top', color='red', fontsize='small')
            plt.title(f"{title_prefix}\ninnse_away[{idx}] (NTCpb={ntcpb_temp:.1f}°C, NTCx={ntcx_temp:.1f}°C)\n{timestamp_str}")
            plt.xlabel("Input Noise (ENC)")
            plt.ylabel("Frequency")
            plt.legend([f"Mean = {mean_val:.2f}", f"Std Dev = {std_val:.2f}"])
            plt.tight_layout()
            plt.savefig(f"{output_dir}/{base_name}_innse_away_{idx}.pdf")
            plt.close()

        # Combined innse_under
        if innse_under_list:
            all_under = flatten(innse_under_list)
            mean_val = np.mean(all_under)
            std_val = np.std(all_under)
            low_vals = [v for v in all_under if v < 600]
            high_vals = [v for v in all_under if v > 1000]
            print(f"📊 {base_name}_combined_innse_under: <600: {len(low_vals)}, >1000: {len(high_vals)}")

            plt.figure(figsize=(8, 5))
            plt.hist(all_under, bins=30, edgecolor='black', alpha=0.75, color=bar_color)
            plt.axvline(mean_val, color='red', linestyle='--')
            plt.text(0.98, 0.95, f"(<600: {len(low_vals)}, >1000: {len(high_vals)})",
                     transform=plt.gca().transAxes, ha='right', va='top', color='red', fontsize='small')
            plt.title(f"{title_prefix}\nCombined innse_under (NTCpb={ntcpb_temp:.1f}°C, NTCx={ntcx_temp:.1f}°C)\n{timestamp_str}")
            plt.xlabel("Input Noise (ENC)")
            plt.ylabel("Frequency")
            plt.legend([f"Mean = {mean_val:.2f}", f"Std Dev = {std_val:.2f}"])
            plt.tight_layout()
            plt.savefig(f"{output_dir}/{base_name}_combined_innse_under.pdf")
            plt.close()

        # Combined innse_away
        if innse_away_list:
            all_away = flatten(innse_away_list)
            mean_val = np.mean(all_away)
            std_val = np.std(all_away)
            low_vals = [v for v in all_away if v < 600]
            high_vals = [v for v in all_away if v > 1000]
            print(f"📊 {base_name}_combined_innse_away: <600: {len(low_vals)}, >1000: {len(high_vals)}")

            plt.figure(figsize=(8, 5))
            plt.hist(all_away, bins=30, edgecolor='black', alpha=0.75, color=bar_color)
            plt.axvline(mean_val, color='red', linestyle='--')
            plt.text(0.98, 0.95, f"(<600: {len(low_vals)}, >1000: {len(high_vals)})",
                     transform=plt.gca().transAxes, ha='right', va='top', color='red', fontsize='small')
            plt.title(f"{title_prefix}\nCombined innse_away (NTCpb={ntcpb_temp:.1f}°C, NTCx={ntcx_temp:.1f}°C)\n{timestamp_str}")
            plt.xlabel("Input Noise (ENC)")
            plt.ylabel("Frequency")
            plt.legend([f"Mean = {mean_val:.2f}", f"Std Dev = {std_val:.2f}"])
            plt.tight_layout()
            plt.savefig(f"{output_dir}/{base_name}_combined_innse_away.pdf")
            plt.close()

if __name__ == "__main__":
    main()
