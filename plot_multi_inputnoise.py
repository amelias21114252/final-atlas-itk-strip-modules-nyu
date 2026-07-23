#!/usr/bin/env python3
'''
Plot input noise after thermal cycling ATLAS ITk strips barrel modules
Updated by Amelia Stevens, Aug 2025

Usage:
python plot_multi_inputnoise.py --serial_number 20USBHX2002592
python plot_multi_inputnoise.py --serial_number 20USBHX2002657

python plot_multi_inputnoise.py --serial_number 20USBHX2002683

python plot_multi_inputnoise.py --serial_number 20USBHX2002657
python plot_multi_inputnoise.py --serial_number 20USBHX2002683
python plot_multi_inputnoise.py --serial_number 20USBHX2002629
python plot_multi_inputnoise.py --serial_number 20USBHX2002630
python plot_multi_inputnoise.py --serial_number 20USBHX2002603
python plot_multi_inputnoise.py --serial_number 20USBHX2002631
python plot_multi_inputnoise.py --serial_number 20USBHX2002652
python plot_multi_inputnoise.py --serial_number 20USBHX2002653
⚠️ Skipping dead sensor entry: Sensor Dead
python plot_multi_inputnoise.py --serial_number 20USBHX2002654
python plot_multi_inputnoise.py --serial_number 20USBHX2002656
python plot_multi_inputnoise.py --serial_number 20USBHX2002684
python plot_multi_inputnoise.py --serial_number 20USBHX2002685
python plot_multi_inputnoise.py --serial_number 20USBHX2002686
python plot_multi_inputnoise.py --serial_number 20USBHX2002687
python plot_multi_inputnoise.py --serial_number 20USBHX2002688
python plot_multi_inputnoise.py --serial_number 20USBHX2002709
python plot_multi_inputnoise.py --serial_number 20USBHX2002710
python plot_multi_inputnoise.py --serial_number 20USBHX2002711
python plot_multi_inputnoise.py --serial_number 20USBHX2002712
python plot_multi_inputnoise.py --serial_number 20USBHX2002713
python plot_multi_inputnoise.py --serial_number 20USBHX2002677
python plot_multi_inputnoise.py --serial_number 20USBHX2002678
python plot_multi_inputnoise.py --serial_number 20USBHX2002679
python plot_multi_inputnoise.py --serial_number 20USBHX2002680
python plot_multi_inputnoise.py --serial_number 20USBHX2002655
python plot_multi_inputnoise.py --serial_number 20USBHX2002691
python plot_multi_inputnoise.py --serial_number 20USBHX2002692
python plot_multi_inputnoise.py --serial_number 20USBHX2002693
python plot_multi_inputnoise.py --serial_number 20USBHX2002689
python plot_multi_inputnoise.py --serial_number 20USBHX2002681
python plot_multi_inputnoise.py --serial_number 20USBHX2002682
python plot_multi_inputnoise.py --serial_number 20USBHX2002690
python plot_multi_inputnoise.py --serial_number 20USBHX2002694
python plot_multi_inputnoise.py --serial_number 20USBHX2002695
python plot_multi_inputnoise.py --serial_number 20USBHX2002783
python plot_multi_inputnoise.py --serial_number 20USBHX2002697
python plot_multi_inputnoise.py --serial_number 20USBHX2002698
python plot_multi_inputnoise.py --serial_number 20USBHX2002784
python plot_multi_inputnoise.py --serial_number 20USBHX2002785
python plot_multi_inputnoise.py --serial_number 20USBHX2002786
python plot_multi_inputnoise.py --serial_number 20USBHX2002940
python plot_multi_inputnoise.py --serial_number 20USBHX2002942
python plot_multi_inputnoise.py --serial_number 20USBHX2002943
python plot_multi_inputnoise.py --serial_number 20USBHX2002938
python plot_multi_inputnoise.py --serial_number 20USBHX2002939
python plot_multi_inputnoise.py --serial_number 20USBHX2002944
python plot_multi_inputnoise.py --serial_number 20USBHX2002953
python plot_multi_inputnoise.py --serial_number 20USBHX2002954
python plot_multi_inputnoise.py --serial_number 20USBHX2002956
python plot_multi_inputnoise.py --serial_number 20USBHX2002957
python plot_multi_inputnoise.py --serial_number 20USBHX2002971
python plot_multi_inputnoise.py --serial_number 20USBHX2002964
python plot_multi_inputnoise.py --serial_number 20USBHX2002965
python plot_multi_inputnoise.py --serial_number 20USBHX2002966
python plot_multi_inputnoise.py --serial_number 20USBHX2002967
python plot_multi_inputnoise.py --serial_number 20USBHX2002983
python plot_multi_inputnoise.py --serial_number 20USBHX2002960
python plot_multi_inputnoise.py --serial_number 20USBHX2002961
python plot_multi_inputnoise.py --serial_number 20USBHX2002787
python plot_multi_inputnoise.py --serial_number 20USBHX2002959
python plot_multi_inputnoise.py --serial_number 20USBHX2002958
python plot_multi_inputnoise.py --serial_number 20USBHX2002980
python plot_multi_inputnoise.py --serial_number 20USBHX2002981
python plot_multi_inputnoise.py --serial_number 20USBHX2002982
python plot_multi_inputnoise.py --serial_number 20USBHX2002968
python plot_multi_inputnoise.py --serial_number 20USBHX2002969
python plot_multi_inputnoise.py --serial_number 20USBHX2002970
'''

import os, json, argparse
import numpy as np
from glob import glob
from pprint import pprint
import matplotlib as mplt
mplt.use('Agg')  # Allows headless plotting
import matplotlib.pyplot as plt

def flatten(input):
    if isinstance(input, list) and all(isinstance(x, (int, float)) for x in input):
        return input
    elif isinstance(input, list) and all(isinstance(x, list) for x in input):
        return [item for sublist in input for item in sublist]
    else:
        raise TypeError(f"Expected list of floats or list of lists, got: {type(input)}")

def main():
    parser = argparse.ArgumentParser(description='Plot input noise after thermal cycling ATLAS ITk strips barrel modules')
    parser.add_argument('--serial_number', required=True, help='e.g. 20USBHX2002592')
    args = parser.parse_args()

    serial_number = args.serial_number
    pattern = f"SN{serial_number}/SN{serial_number}_*.json"
    input_files = glob(pattern)

    print(f"Found {len(input_files)} files for serial: {serial_number}")
    pprint(input_files)

    filtered_files = filter_input_files(input_files)
    module_names = get_module_names(filtered_files)

    print("\nFiltered files:")
    pprint(filtered_files)
    print("\nModules:")
    pprint(module_names)

    for module_name in module_names:
        mk_inoise_plot(module_name, filtered_files, 'under')
        mk_inoise_plot(module_name, filtered_files, 'away')

def mk_inoise_plot(module_name, input_files, stream='under'):
    fig, ax = plt.subplots(figsize=(16, 9))
    print(f'\nPlotting input noise for {module_name}, stream: {stream}')

    files = sorted([f for f in input_files if module_name in f])
    n_files = len(files)
    blues = mplt.cm.Blues(np.linspace(0.4, 0.9, n_files))
    oranges = mplt.cm.Oranges(np.linspace(0.4, 0.9, n_files))

    skipped_msgs = []
    timestamp_str = "Unknown"
    parent_name = "Unknown"

    # Get timestamp and parent name from first valid file
    for f in files:
        try:
            data = json_to_dict(f)
            raw_ts = data.get("timestamp", data.get("date", None))
            parent_name = data.get("parent_name", "Unknown")
            if raw_ts:
                timestamp_str = raw_ts.replace("T", " ").split(".")[0].replace("Z", "").strip()
                break
        except:
            continue

    for idx, f in enumerate(files):
        try:
            data = json_to_dict(f)
            noise = flatten(data['results']['innse_under' if stream == 'under' else 'innse_away'])
            mean_val = np.mean(noise)
            if mean_val > 1000:
                basename = os.path.basename(f)
                trimmed_name = basename[basename.find("SN"):]  # Keep only SN*.json
                msg = f"{trimmed_name} — mean = {mean_val:.1f} > 1000"
                print(f"⚠️ Skipping {msg}")
                skipped_msgs.append(msg)
                continue

            temp = float(data['properties']['DCS']['AMAC_NTCpb'])
            temp_label = '+20C' if temp > 10 else '-35C'
            color = oranges[idx] if temp > 10 else blues[idx]

            basename = os.path.basename(f)
            file_number = ''.join(filter(str.isdigit, basename.split('SN')[-1]))[-2:]

            ax.plot(range(len(noise)), noise, lw=1, ls='-', c=color, label=f"{temp_label} (file {file_number}) [μ: {mean_val:.1f}]")

        except Exception as e:
            basename = os.path.basename(f)
            trimmed_name = basename[basename.find("SN"):]
            msg = f"{trimmed_name} — {e}"
            print(f"❌ Skipping {msg}")
            skipped_msgs.append(msg)

    ax.set_xlim(0, 1280)

    all_means = []
    for f in files:
        try:
            data = json_to_dict(f)
            noise = flatten(data['results']['innse_under' if stream == 'under' else 'innse_away'])
            mean_val = np.mean(noise)
            if mean_val < 1000:
                all_means.append(np.max(noise))
        except:
            continue

    max_y = max(all_means + [1000]) * 1.2
    ax.set_ylim(0, 2000)
    ax.set_xlabel("Channel number", labelpad=15, fontsize=38)
    ax.set_ylabel("Input noise [ENC]", labelpad=15, fontsize=38)
    ax.tick_params(axis='both', labelsize=28)
    ax.set_xticks(list(range(0, 1281, 128)))

    handles, labels = ax.get_legend_handles_labels()
    seen = set()
    unique = [(h, l) for h, l in zip(handles, labels) if not (l in seen or seen.add(l))]

    ax.legend(
        *zip(*unique),
        loc='upper center',
        bbox_to_anchor=(0.5, 0.995),
        ncol=4,
        prop={'size': 15},
        frameon=False
    )

    # Text annotations with parent name
    fig.text(0.15, 0.31, r'3 point gain response curve, $-$350V, times UTC', color='k', size=22)
    fig.text(0.15, 0.27, f"{module_name}, Stream: {stream}", color='k', size=28)
    fig.text(0.15, 0.23, f"Parent Module: SN{parent_name}", color='k', size=22)
    fig.text(0.15, 0.19, f"Timestamp: {timestamp_str}", color='k', size=22)

    # Skipped file messages
    for i, msg in enumerate(skipped_msgs):
        ypos = 0.14 - i * 0.035
        if ypos < 0.02:
            break
        fig.text(0.15, ypos, msg, color='red', size=16)

    plt.tight_layout(pad=0.3)
    plt.subplots_adjust(top=0.88, bottom=0.12, left=0.11, right=0.97)

    save_dir = os.path.join(module_name, "inputnoise")
    mkdir(save_dir)
    save_path = os.path.join(save_dir, f"{module_name}-{stream}.pdf")
    print(f"Saving: {save_path}")
    plt.savefig(save_path)
    plt.close()

def filter_input_files(infiles, keep_fit_code=4):
    print(f'Filtering to keep fit_type_code = {keep_fit_code}')
    return [f for f in infiles if json_to_dict(f)['properties'].get('fit_type_code') == keep_fit_code]

def get_module_names(files):
    modules = set()
    for f in files:
        try:
            modules.add(json_to_dict(f)['properties']['det_info']['name'])
        except:
            continue
    return sorted(modules)

def json_to_dict(file_path):
    with open(file_path, 'r') as f:
        return json.load(f)

def mkdir(path):
    try:
        os.makedirs(path)
        print(f'Made directory: {path}')
    except OSError:
        pass

if __name__ == "__main__":
    main()
