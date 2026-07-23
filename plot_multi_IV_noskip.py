#!/usr/bin/env python3
'''
Plot IV curves of ITk barrel modules after module thermocycling
Written by Jesse Liu 2023–24

Usage:
    python plot_multi_IV_noskip.py -i 'SN20USBML1235761/*.json'
'''
#!/usr/bin/env python3
'''
Plot IV curves of ITk barrel modules after module thermocycling

Saves output to:
  SN<serial_number>/IV/SN<serial_number>.pdf and .png

Usage:
  python plot_multi_IVcopy.py -i 'SN*/SN*_*.json'

  python plot_multi_IVcopy.py -i 'SN*/SN*_*.json'

  python plot_multi_IV.py -i 'SN20USBML1236150/*.json'  

  
  python plot_multi_IV_noskip.py -i 'SN20USBML1235885/*.json'


python plot_multi_IV.py -i 'SN20USBML1235852/*.json'
python plot_multi_IV.py -i 'SN20USBML1235853/*.json'
python plot_multi_IV.py -i 'SN20USBML1235873/*.json'
python plot_multi_IV.py -i 'SN20USBML1235874/*.json'
python plot_multi_IV.py -i 'SN20USBML1235875/*.json'
python plot_multi_IV.py -i 'SN20USBML1235876/*.json'
python plot_multi_IV.py -i 'SN20USBML1235877/*.json'
python plot_multi_IV.py -i 'SN20USBML1235878/*.json'
python plot_multi_IV.py -i 'SN20USBML1235879/*.json'
python plot_multi_IV.py -i 'SN20USBML1235880/*.json'
python plot_multi_IV.py -i 'SN20USBML1235881/*.json'
python plot_multi_IV.py -i 'SN20USBML1235882/*.json'
python plot_multi_IV.py -i 'SN20USBML1235883/*.json'
python plot_multi_IV.py -i 'SN20USBML1235884/*.json'
python plot_multi_IV.py -i 'SN20USBML1235885/*.json'
python plot_multi_IV.py -i 'SN20USBML1235886/*.json'
python plot_multi_IV.py -i 'SN20USBML1235887/*.json'
python plot_multi_IV.py -i 'SN20USBML1235888/*.json'
python plot_multi_IV.py -i 'SN20USBML1235889/*.json'
python plot_multi_IV.py -i 'SN20USBML1235907/*.json'
python plot_multi_IV.py -i 'SN20USBML1235908/*.json'
python plot_multi_IV.py -i 'SN20USBML1235909/*.json'
python plot_multi_IV.py -i 'SN20USBML1235919/*.json'
python plot_multi_IV.py -i 'SN20USBML1235920/*.json'
python plot_multi_IV.py -i 'SN20USBML1235921/*.json'
python plot_multi_IV.py -i 'SN20USBML1235922/*.json'
python plot_multi_IV.py -i 'SN20USBML1235923/*.json'
python plot_multi_IV.py -i 'SN20USBML1235924/*.json'
python plot_multi_IV.py -i 'SN20USBML1235925/*.json'
python plot_multi_IV.py -i 'SN20USBML1235926/*.json'
python plot_multi_IV.py -i 'SN20USBML1235927/*.json'
python plot_multi_IV.py -i 'SN20USBML1235928/*.json'
python plot_multi_IV.py -i 'SN20USBML1235929/*.json'
python plot_multi_IV.py -i 'SN20USBML1236083/*.json'
python plot_multi_IV.py -i 'SN20USBML1236084/*.json'
python plot_multi_IV.py -i 'SN20USBML1236085/*.json'
python plot_multi_IV.py -i 'SN20USBML1236086/*.json'
python plot_multi_IV.py -i 'SN20USBML1236087/*.json'
python plot_multi_IV.py -i 'SN20USBML1236088/*.json'
python plot_multi_IV.py -i 'SN20USBML1236090/*.json'
python plot_multi_IV.py -i 'SN20USBML1236091/*.json'
python plot_multi_IV.py -i 'SN20USBML1236092/*.json'
python plot_multi_IV.py -i 'SN20USBML1236093/*.json'
python plot_multi_IV.py -i 'SN20USBML1236094/*.json'
python plot_multi_IV.py -i 'SN20USBML1236095/*.json'
python plot_multi_IV.py -i 'SN20USBML1236096/*.json'
python plot_multi_IV.py -i 'SN20USBML1236097/*.json'
python plot_multi_IV.py -i 'SN20USBML1236098/*.json'
python plot_multi_IV.py -i 'SN20USBML1236100/*.json'
python plot_multi_IV.py -i 'SN20USBML1236101/*.json'
python plot_multi_IV.py -i 'SN20USBML1236102/*.json'
python plot_multi_IV.py -i 'SN20USBML1236103/*.json'
python plot_multi_IV.py -i 'SN20USBML1236104/*.json'
python plot_multi_IV.py -i 'SN20USBML1236105/*.json'
python plot_multi_IV.py -i 'SN20USBML1236106/*.json'
python plot_multi_IV.py -i 'SN20USBML1236107/*.json'
python plot_multi_IV.py -i 'SN20USBML1236108/*.json'
python plot_multi_IV.py -i 'SN20USBML1236109/*.json'
python plot_multi_IV.py -i 'SN20USBML1236110/*.json'
python plot_multi_IV.py -i 'SN20USBML1236111/*.json'
python plot_multi_IV.py -i 'SN20USBML1236112/*.json'
python plot_multi_IV.py -i 'SN20USBML1236113/*.json'
python plot_multi_IV.py -i 'SN20USBML1236148/*.json'
python plot_multi_IV.py -i 'SN20USBML1236149/*.json'
python plot_multi_IV.py -i 'SN20USBML1236150/*.json'
python plot_multi_IV.py -i 'SN20USBML1236151/*.json'
python plot_multi_IV.py -i 'SN20USBML1236152/*.json'
python plot_multi_IV.py -i 'SN20USBML1236153/*.json'
'''

import matplotlib as mplt
mplt.use('Agg')
from glob import glob
import numpy as np
import os, json, collections, argparse, datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from pprint import pprint

mplt.rc("text", usetex=True)
mplt.rc('font', **{'family': 'sans-serif', 'sans-serif': ['Helvetica']})

def main():
    parser = argparse.ArgumentParser(description='Plot IV curves after thermal cycling')
    parser.add_argument('-i', '--input', help='Path to IV JSON files', default="")
    parser.add_argument('--do_amac_offset', dest='do_amac_offset', action='store_true')
    parser.add_argument('--do_logY', dest='do_logY', action='store_true')
    args = parser.parse_args()

    if not args.input:
        print("Please provide input path with -i")
        exit()

    l_input_files = glob(args.input)
    do_amac_offset = args.do_amac_offset
    do_logY = args.do_logY

    l_module_names = get_module_names(l_input_files)
    print('\nJSON output data files to consider:')
    pprint(l_input_files)
    print('\nModule names parsed to make plots:')
    pprint(l_module_names)

    for module_name in l_module_names:
        mk_single_plot(module_name, l_input_files, do_amac_offset, do_logY)

def mk_single_plot(in_name, l_input_files, do_amac_offset, do_logY):
    fig, ax = plt.subplots()
    fig.set_size_inches(12, 8)
    print(f'Making plot for {in_name}')

    l_input_files_amac = []
    for f in l_input_files:
        try:
            with open(f, 'r') as jf:
                data = json.load(jf)
                if data.get("component", data.get("serial_number")) == in_name:
                    l_input_files_amac.append(f)
        except Exception as e:
            print(f"⚠️ Failed to parse {f}: {e}")

    d_unsorted = {}
    for input_file in l_input_files_amac:
        input = json_to_dict(input_file)
        timestamp = input.get('timestamp', input.get('date', '1970-01-01T00:00:00Z'))
        sort_key = f"{timestamp}_{os.path.basename(input_file)}"
        d_unsorted[sort_key] = input_file

    od = collections.OrderedDict(sorted(d_unsorted.items()))
    l_input_files_sorted = list(od.values())

    print('AMAC sorted dictionary values:')
    pprint(l_input_files_sorted)

    blues = mplt.cm.Blues(np.linspace(0.4, 0.9, len(l_input_files_sorted)))
    oranges = mplt.cm.Oranges(np.linspace(0.4, 0.9, len(l_input_files_sorted)))

    for count, input_file in enumerate(l_input_files_sorted):
        if '.json' in input_file:
            voltages, currents, timestamp, ntcpb_temp, ntcx_temp = read_AMAC_IV(input_file, do_amac_offset)

            if len(voltages) == 0 or len(currents) == 0:
                print(f"⚠️ Skipping plot for {input_file} due to empty or missing data.")
                continue

            print(f"Plotting {len(voltages)} points for file: {input_file}")

            lcolour = blues[count] if ntcpb_temp < 0 else oranges[count]
            ntcx_txt = '{0:.3g}'.format(ntcx_temp).replace('-', '$-$')
            plt.plot(voltages, currents, lw=2, ls='-', c=lcolour, label='{0}, {1}C'.format(timestamp, ntcx_txt))

    text_size = 28
    if do_logY:
        ax.set_yscale('log')
        ax.set_ylim(1, 10000)
    else:
        ax.set_ylim(-20, 550)

    ax.set_xlim(-10, 750)  # Adjust if zoom needed

    plt.xlabel(r'Voltage [V]', labelpad=15, size=38)
    plt.ylabel(r'Current [nA]', labelpad=15, size=38)
    ax.tick_params('x', length=12, width=1, which='major', labelsize=28, pad=10, direction="in")
    ax.tick_params('x', length=6, width=1, which='minor', direction="in")
    ax.tick_params('y', length=12, width=1, which='major', labelsize=28, pad=10, direction="in", right=True)
    ax.tick_params('y', length=6, width=1, which='minor', direction="in", right=True)

    plt.legend(loc='upper left', prop={'size':14}, frameon=False, handlelength=2.1, handletextpad=0.5, borderpad=0.6, ncol=3, columnspacing=0.6)
    fig.text(0.20, 0.56, in_name, color='k', size=text_size)
    fig.text(0.20, 0.51, 'Temperatures = AMAC NTCx', color='gray', size=text_size * 0.5)

    plt.tight_layout(pad=0.3)
    plt.subplots_adjust(top=0.97, left=0.16, right=0.99)

    # Save plot to SN<serial>/IV/SN<serial>.pdf
    plot_dir = os.path.join(f"SN{in_name}", "IV")
    mkdir(plot_dir)
    save_name = os.path.join(plot_dir, f"SN{in_name}")
    print(f"Saving plot as {save_name}.pdf")
    plt.savefig(f"{save_name}.pdf", format='pdf')
    plt.savefig(f"{save_name}.png", format='png', dpi=300)

def read_AMAC_IV(file_name, do_AMAC_offset=True):
    print(f'Opening file: {file_name}')
    with open(file_name, 'r') as infile:
        input = json.load(infile)

    results = input.get('results', {})
    current_raw = results.get('CURRENT') or results.get('current')
    voltage_raw = results.get('VOLTAGE') or results.get('voltage')

    if current_raw is None or voltage_raw is None:
        print(f"⚠️ Skipping {file_name} — missing current or voltage data.")
        return [], [], "INVALID", 0.0, 0.0

    current_zero_offset = current_raw[0] if do_AMAC_offset else 0.0
    print(f'Using AMAC current zero offset: {current_zero_offset}')

    voltages = [abs(float(x)) for x in voltage_raw]
    currents = [float(x) - current_zero_offset for x in current_raw]

    if all(i == 0 for i in currents) or all(v == 0 for v in voltages):
        print(f"⚠️ Warning: Empty or zero IV data in {file_name}")

    if "temperatures" in input:
        ntcpb_temp = input["temperatures"]["AMAC_NTCpb"][0]
        ntcx_temp = input["temperatures"]["AMAC_NTCx"][0]
    elif "properties" in input and "DCS" in input["properties"]:
        ntcpb_temp = input["properties"]["DCS"]["AMAC_NTCpb"]
        ntcx_temp = input["properties"]["DCS"]["AMAC_NTCx"]
    else:
        ntcpb_temp = 0.0
        ntcx_temp = 0.0

    timestamp = input.get('timestamp', input.get('date', '1970-01-01T00:00:00Z'))
    timestamp_stripped = timestamp.replace('T', ' ').split('.')[0]
    try:
        pydate_datetime_stamp = datetime.datetime.strptime(timestamp_stripped, '%Y-%m-%d %H:%M:%S')
        out_datetime = pydate_datetime_stamp.strftime('%Y-%m-%d %H:%M')
    except ValueError:
        out_datetime = "Invalid Time"

    return voltages, currents, out_datetime, ntcpb_temp, ntcx_temp

def json_to_dict(file_name):
    with open(file_name, 'r') as infile:
        return json.load(infile)

def get_module_names(l_filtered_input_files):
    l_module_names = []
    for input_file in l_filtered_input_files:
        if '.json' in input_file:
            input = json_to_dict(input_file)
            module_name = input.get('component', input.get('serial_number', 'UNKNOWN'))
            if module_name not in l_module_names:
                l_module_names.append(module_name)
    l_module_names.sort()
    return l_module_names

def mkdir(dirPath):
    try:
        os.makedirs(dirPath, exist_ok=True)
        print('Successfully made directory:', dirPath)
    except OSError:
        pass

if __name__ == "__main__":
    main()
