# CERN–ATLAS ITk QC Plotting and Website Pipeline

This repository processes ITk module QC data for **BNL**, **LBNL**, and **UCSC**. It downloads IV and input-noise JSON data, generates problem and regular plots, builds category summaries, and creates the final website.

The recommended workflow uses one master shell script:

```bash
bash run_all_itk_pipeline.sh
```

The master script runs three stages in order:

1. Download and refresh source data.
2. Generate problem-module plots, category summaries, and an intermediate website.
3. Generate regular plots and rebuild the final website.

---

## 1. Pipeline files

| File | Purpose |
|---|---|
| `run_all_itk_pipeline.sh` | Runs the complete workflow in the correct order. |
| `01_run_data_download.sh` | Downloads serial information, timestamps, IV JSON files, and input-noise JSON files. |
| `02_run_problem_modules_and_website.sh` | Generates problem-only outputs in `ML2` and `HX2`, creates category summaries, and builds the website. |
| `03_run_regular_modules_and_website.sh` | Generates regular outputs in `ML3` and `HX3`, then performs the final website rebuild. |

Run the shell scripts from a project directory containing all required Python scripts and the `BNL`, `LBNL`, and `UCSC` data folders.

---

## 2. Requirements

Required software:

- Bash
- Python 3
- Python packages used by the database and plotting scripts
- A valid `ITK_DB_AUTH` token when downloading new data

The pipeline uses strict shell error handling. It stops when:

- a command fails;
- a required Python script is missing;
- a required category summary is missing or empty.

Use a virtual environment when needed:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

A `requirements.txt` file is only required when one is included in the project.

---

## 3. Database authentication

Stage 1 requires an ITk Production Database token:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
```

Confirm it is set:

```bash
[[ -n "${ITK_DB_AUTH:-}" ]] && echo "ITK_DB_AUTH is set"
```

Tokens can expire. Refresh the token if database scripts begin failing or modules unexpectedly appear as unavailable.

Do not save the token directly inside a shell or Python script.

---

## 4. Recommended complete run

Place the four shell scripts together. From the ITk project directory, run:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash /path/to/pipeline/run_all_itk_pipeline.sh
```

The current working directory is treated as the project directory.

To make the scripts executable:

```bash
chmod +x run_all_itk_pipeline.sh \
  01_run_data_download.sh \
  02_run_problem_modules_and_website.sh \
  03_run_regular_modules_and_website.sh
```

Then run:

```bash
./run_all_itk_pipeline.sh
```

---

## 5. Run against a different project directory

Use `--project-dir` when the shell scripts are not stored in the project directory:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash /path/to/pipeline/run_all_itk_pipeline.sh \
  --project-dir /path/to/itk-project
```

The selected project directory must contain the Python programs referenced by the three stage scripts.

---

## 6. Select the Python executable

Use a specific virtual-environment interpreter:

```bash
bash run_all_itk_pipeline.sh \
  --python /path/to/itk-project/.venv/bin/python
```

Alternatively, set `PYTHON_BIN`:

```bash
export PYTHON_BIN=/path/to/itk-project/.venv/bin/python
bash run_all_itk_pipeline.sh
```

The default is `python3`.

---

## 7. Skip the download stage

To reuse existing JSON files and regenerate only the plots, summaries, and website:

```bash
bash run_all_itk_pipeline.sh --skip-download
```

This runs Stages 2 and 3. Before using it, confirm these source directories contain current JSON data:

```text
BNL/ML/      BNL/HX/
LBNL/ML/     LBNL/HX/
UCSC/ML/     UCSC/HX/
```

---

## 8. Restart at a specific stage

Use `--start-at`:

```bash
bash run_all_itk_pipeline.sh --start-at 2
```

| Value | Starting point |
|---:|---|
| `1` | Download and refresh source data |
| `2` | Generate problem outputs and then regular outputs |
| `3` | Generate only regular outputs and the final website |

Examples:

```bash
# Rebuild problem and regular outputs without downloading again
bash run_all_itk_pipeline.sh --start-at 2

# Rebuild only ML3/HX3 and the final website
bash run_all_itk_pipeline.sh --start-at 3
```

`--skip-download` and `--start-at 2` both avoid Stage 1.

---

# Stage 1 — Download and refresh data

Run Stage 1 separately with:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash 01_run_data_download.sh
```

## Stage 1 commands

The stage runs:

```text
get_module_serial_numbers.py
get_test_timestamp_full_list_BNL.py
get_test_timestamp_full_list_LBNL.py
get_test_timestamp_full_list_UCSC.py

get_all_tests_categoryE_i_bnl.py
get_all_tests_categoryE_i_lbnl.py
get_all_tests_categoryE_i_ucsc.py

get_all_tests_categoryDandE_ii_bnl.py
get_all_tests_categoryDandE_ii_lbnl.py
get_all_tests_categoryDandE_ii_ucsc.py
```

The HX scripts are called with:

```bash
--test_name "Response Curve TC" --max_workers 6
```

Do not use `Module AMAC IV TC` for the HX input-noise download scripts. That test name belongs to ML IV data.

## Expected source data

A complete module normally has:

- **24 IV JSON files** for an ML serial number;
- **25 input-noise JSON files** for an HX serial number.

Expected source structure:

```text
BNL/
├── ML/
│   └── SN20USBML.../
│       └── *.json
└── HX/
    └── SN20USBHX.../
        └── *.json

LBNL/
├── ML/
└── HX/

UCSC/
├── ML/
└── HX/
```

Timestamp outputs:

```text
formatted_timestamps_bnl.txt
formatted_timestamps_lbnl.txt
formatted_timestamps_ucsc.txt
```

The current website workflow reads the generated files dynamically. Manual copying of timestamp tuples or category dictionaries into the website script is no longer part of the normal workflow.

---

# Stage 2 — Problem modules and category summaries

Run Stage 2 separately with:

```bash
bash 02_run_problem_modules_and_website.sh
```

This stage reads source JSON files from `ML` and `HX`, then writes problem-focused outputs to `ML2` and `HX2`.

## Problem IV outputs

The following scripts process ML IV JSON data:

```text
plot_multi_IV_final_BNL_Category_A_Di_warning.py
plot_multi_IV_final_LBNL_Category_A_Di_warning.py
plot_multi_IV_final_UCSC_Category_A_Di_warning.py
```

Input and output pattern:

```bash
python3 SCRIPT.py -i "SITE/ML/*/*.json" -o "SITE/ML2"
```

Examples:

```bash
python3 plot_multi_IV_final_BNL_Category_A_Di_warning.py \
  -i "BNL/ML/*/*.json" -o "BNL/ML2"
```

Required IV category summaries:

```text
BNL/ML2/iv_category_summary_bnl.txt
LBNL/ML2/iv_category_summary_lbnl.txt
UCSC/ML2/iv_category_summary_ucsc.txt
```

## Problem input-noise outputs

For each institute, Stage 2 generates:

- standard problem input-noise plots;
- no-skip problem input-noise plots;
- combined problem histograms;
- combined no-skip problem histograms;
- detailed per-file histograms;
- low/high JSON outputs where produced by the plotting scripts.

BNL scripts:

```text
plot_multi_inputnoise_BNL_one_channel_subcategories.py
plot_multi_inputnoise_noskip_BNL_one_channel_subcategories.py
plot_combined_inputnoise_BNL_one_channel_subcategories.py
plot_combined_inputnoise_noskip_BNL_one_channel_subcategories.py
plot_detailed_inputnoise_histograms_per_file_BNL.py
```

Equivalent LBNL and UCSC scripts are used for their site folders.

Input and output pattern:

```bash
python3 SCRIPT.py -i "SITE/HX/SN*/*.json" -o "SITE/HX2"
```

## Category B/C summaries

Stage 2 converts each site's input-noise error summary into a category summary:

```text
generate_categoryBandC_BNL_from_inputnoise_summary.py
generate_categoryBandC_LBNL_from_inputnoise_summary.py
generate_categoryBandC_UCSC_from_inputnoise_summary.py
```

Required outputs:

```text
BNL/HX2/inputnoise_category_summary_bnl.txt
LBNL/HX2/inputnoise_category_summary_lbnl.txt
UCSC/HX2/inputnoise_category_summary_ucsc.txt
```

The stage verifies that all six ML2/HX2 category summary files exist and are nonempty before continuing.

## Intermediate website

After problem outputs are generated, Stage 2 runs:

```text
get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py
```

The website is written to:

```text
categories_website/
```

Stage 3 runs the website generator again after regular plots are available. The Stage 3 build is the final build.

---

# Stage 3 — Regular plots and final website

Run Stage 3 separately with:

```bash
bash 03_run_regular_modules_and_website.sh
```

## Regular IV plots

Regular IV scripts write to `ML3`:

```text
plot_multi_IV_final_BNL.py
plot_multi_IV_final_LBNL.py
plot_multi_IV_final_UCSC.py
```

Output directories:

```text
BNL/ML3/
LBNL/ML3/
UCSC/ML3/
```

## Regular input-noise plots

Stage 3 runs standard, no-skip, combined, and combined no-skip scripts for each institute.

Examples for BNL:

```text
plot_multi_inputnoise_BNL.py
plot_multi_inputnoise_noskip_BNL.py
plot_combined_inputnoise_BNL.py
plot_combined_inputnoise_noskip_BNL.py
```

Equivalent scripts are used for LBNL and UCSC.

Output directories:

```text
BNL/HX3/
LBNL/HX3/
UCSC/HX3/
```

## Final website build

Stage 3 reruns:

```text
get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py
```

Final website location:

```text
categories_website/
```

The website displays regular plots from `ML3` and `HX3`, problem information from `ML2` and `HX2`, and low/high JSON links from the paths expected by the website generator.

---

# Category definitions

Current category definitions used by the website are:

| Category | Definition |
|---|---|
| **A** | IV current above **600 nA**. |
| **B(i)** | Away-stream input noise greater than **1100 ENC** for **10 or more channels**. |
| **B(ii)** | Under-stream input noise greater than **1100 ENC** for **10 or more channels**. |
| **C(i)** | Away-stream input noise less than **600 ENC** for **10 or more channels**. |
| **C(ii)** | Under-stream input noise less than **600 ENC** for **10 or more channels**. |
| **D(i)** | Incomplete IV dataset. |
| **D(ii)** | Incomplete input-noise dataset. |
| **E(i)** | IV data unavailable or could not be processed. |
| **E(ii)** | Input-noise data unavailable or could not be processed. |

An IV value above **300 nA but not above 600 nA** is a warning/additional comment, not Category A.

Additional yellow comments provide useful diagnostic information without creating a separate category.

---

# Main output directories

| Directory | Contents |
|---|---|
| `SITE/ML/` | Source ML IV JSON files |
| `SITE/HX/` | Source HX input-noise JSON files |
| `SITE/ML2/` | Problem IV plots and IV category summaries |
| `SITE/HX2/` | Problem input-noise plots, detailed plots, JSON outputs, and B/C summaries |
| `SITE/ML3/` | Regular IV plots |
| `SITE/HX3/` | Regular input-noise plots |
| `categories_website/` | Generated regular and problem website pages |

`SITE` represents `BNL`, `LBNL`, or `UCSC`.

Example problem JSON output:

```text
BNL/HX2/SN20USBHX.../histograms_combined_noskip/
  SN20USBHX..._away_low_high_values.json
  SN20USBHX..._under_low_high_values.json
```

Exact subdirectory names depend on the corresponding plotting script.

---

# Run and debug one module

These commands are optional and are not required by the three-stage pipeline.

## Download one HX module

```bash
python3 get_test_run.py \
  --serial_number 20USBHX2004501 \
  --test_name "Response Curve TC"
```

When supported by the local project:

```bash
python3 get_test_run2.py \
  --serial_number 20USBHX2004501 \
  --test_name "Response Curve TC"
```

## Download one ML module

```bash
python3 get_test_run.py \
  --serial_number 20USBML1235274 \
  --test_name "Module AMAC IV TC"
```

When supported by the local project:

```bash
python3 get_test_run3.py \
  --serial_number 20USBML1235274 \
  --test_name "Module AMAC IV TC"
```

## Plot one module

The exact interface depends on the version of the individual plotting script. Common patterns are:

```bash
python3 plot_multi_IV.py -i "SN20USBML1235852/*.json"
```

or:

```bash
python3 plot_multi_inputnoise.py --serial_number 20USBHX2002657
```

Use `python3 SCRIPT.py --help` before running an individual script to confirm its current options.

---

# Logging

Save the complete pipeline output:

```bash
set -o pipefail
bash run_all_itk_pipeline.sh 2>&1 | tee itk_pipeline.log
```

Include timestamps in the log when the `ts` command is installed:

```bash
set -o pipefail
bash run_all_itk_pipeline.sh 2>&1 | ts | tee itk_pipeline.log
```

Run with shell tracing:

```bash
bash -x run_all_itk_pipeline.sh --start-at 2
```

---

# Troubleshooting

## `ITK_DB_AUTH is not set`

Set the token before Stage 1:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
```

Use existing JSON data instead:

```bash
bash run_all_itk_pipeline.sh --skip-download
```

## Authentication expired

Symptoms may include failed database calls, empty downloads, or new E(i)/E(ii) entries. Refresh `ITK_DB_AUTH`, rerun Stage 1, and then rerun Stages 2 and 3.

## `Required script not found`

The selected project directory does not contain a Python file referenced by a stage script.

Run from the correct directory:

```bash
cd /path/to/itk-project
bash /path/to/pipeline/run_all_itk_pipeline.sh
```

Or pass it explicitly:

```bash
bash /path/to/pipeline/run_all_itk_pipeline.sh \
  --project-dir /path/to/itk-project
```

## `Required file is missing or empty`

Stage 2 expects these files:

```text
BNL/ML2/iv_category_summary_bnl.txt
LBNL/ML2/iv_category_summary_lbnl.txt
UCSC/ML2/iv_category_summary_ucsc.txt
BNL/HX2/inputnoise_category_summary_bnl.txt
LBNL/HX2/inputnoise_category_summary_lbnl.txt
UCSC/HX2/inputnoise_category_summary_ucsc.txt
```

Review the preceding Python error and confirm that source JSON files exist.

## Website links are missing

The website intentionally omits files that do not exist. Confirm that Stage 2 and Stage 3 completed and that the expected ML2/HX2/ML3/HX3 PDF, PNG, and JSON files were generated.

## A module is unexpectedly in Category E

Check:

1. whether the source JSON directory exists;
2. whether the expected 24 IV or 25 input-noise runs were downloaded;
3. whether the token expired during Stage 1;
4. whether the relevant Python script printed a parsing exception;
5. whether the serial number belongs to the correct ML or HX workflow.

## Rerun only the website generator

After plot and summary files already exist:

```bash
python3 get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py
```

---

# CERN website deployment

The pipeline creates local website files in:

```text
categories_website/
```

Deploy the generated HTML/assets according to the current CERN web-area or CERNBox procedure used by the project. Also deploy the BNL/LBNL/UCSC output folders referenced by the HTML pages. Plot and JSON links will not work when only the HTML files are uploaded.

Before deployment, open the generated pages locally and verify:

- BNL, LBNL, and UCSC regular pages;
- BNL, LBNL, and UCSC problem pages;
- IV PDF/PNG links;
- input-noise PDF/PNG links;
- combined histogram links;
- low/high JSON links;
- category filters and search.

---

# Quick command reference

Complete refresh:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash run_all_itk_pipeline.sh
```

Plots and website only:

```bash
bash run_all_itk_pipeline.sh --skip-download
```

Problem and regular outputs only:

```bash
bash run_all_itk_pipeline.sh --start-at 2
```

Regular outputs and final website only:

```bash
bash run_all_itk_pipeline.sh --start-at 3
```

Use a selected project directory and Python interpreter:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash /path/to/pipeline/run_all_itk_pipeline.sh \
  --project-dir /path/to/itk-project \
  --python /path/to/itk-project/.venv/bin/python
```
