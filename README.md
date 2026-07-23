# `00_run_all_itk_pipeline.sh`

## Complete ATLAS ITk Strip-Module QC Pipeline

This repository downloads and processes ATLAS ITk strip-module quality-control data for **BNL**, **LBNL**, and **UCSC**. It generates IV and input-noise plots, identifies problem categories, creates regular and problem-only output folders, and builds the final website.

The normal workflow is automated. After obtaining a database token, run one command:

```bash
bash 00_run_all_itk_pipeline.sh
```

---

## 1. Files used by the pipeline

| File | Purpose |
|---|---|
| `00_run_all_itk_pipeline.sh` | Runs all three stages in the correct order. |
| `01_run_data_download.sh` | Downloads or refreshes serial information, timestamps, ML IV JSON files, and HX input-noise JSON files. |
| `02_run_problem_modules_and_website.sh` | Creates problem-only plots in `ML2` and `HX2`, generates category summaries, and builds the website. |
| `03_run_regular_modules_and_website.sh` | Creates regular plots in `ML3` and `HX3`, then rebuilds the final website. |

Keep these four shell scripts in the same directory. Run them from the main project directory containing the Python scripts and the `BNL`, `LBNL`, and `UCSC` folders.

---

## 2. Requirements

You need:

- Bash
- Python 3
- The Python packages required by the plotting and database scripts
- Access to the ITk Production Database
- A current `ITK_DB_AUTH` token

The shell scripts stop immediately when a required command fails or a required file is missing.

A virtual environment can be used:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Set a different Python executable with:

```bash
export PYTHON_BIN=/path/to/.venv/bin/python
```

The default is `python3`.

---

## 3. Get an ITk database token

Open this token page:

<https://uuidentity.plus4u.net/uu-identitymanagement-maing01/a9b105aff2744771be4daa8361954677/showToken>

Copy the token and export it in the terminal:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
```

Check that it is set:

```bash
[[ -n "${ITK_DB_AUTH:-}" ]] && echo "ITK_DB_AUTH is set"
```

The token may expire after roughly 15 minutes. If database downloads begin failing, obtain a new token and export it again.

Do not commit the token to GitHub and do not save it inside a shell or Python script.

---

## 4. Run the complete pipeline

Make the shell scripts executable once:

```bash
chmod +x 00_run_all_itk_pipeline.sh \
  01_run_data_download.sh \
  02_run_problem_modules_and_website.sh \
  03_run_regular_modules_and_website.sh
```

Then run:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash 00_run_all_itk_pipeline.sh
```

The master script runs:

1. `01_run_data_download.sh`
2. `02_run_problem_modules_and_website.sh`
3. `03_run_regular_modules_and_website.sh`

If any stage fails, the pipeline stops so that later stages are not built from incomplete data.

---

# Stage 1 — Download and refresh data

Run separately with:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash 01_run_data_download.sh
```

## What Stage 1 runs

### Module and timestamp scripts

```text
get_module_serial_numbers.py
get_test_timestamp_full_list_BNL.py
get_test_timestamp_full_list_LBNL.py
get_test_timestamp_full_list_UCSC.py
```

- `get_module_serial_numbers.py` obtains the HX-to-ML module relationships.
- The timestamp scripts create the site timestamp files used by the website.

Expected timestamp files:

```text
formatted_timestamps_bnl.txt
formatted_timestamps_lbnl.txt
formatted_timestamps_ucsc.txt
```

### ML IV download scripts

```text
get_all_tests_categoryE_i_bnl.py
get_all_tests_categoryE_i_lbnl.py
get_all_tests_categoryE_i_ucsc.py
```

These scripts download ML data for:

```text
Module AMAC IV TC
```

A complete ML module normally has **24 IV JSON files**.

They also help identify:

- Category D(i): incomplete IV dataset
- Category E(i): IV data unavailable or could not be processed

### HX input-noise download scripts

```text
get_all_tests_categoryDandE_ii_bnl.py
get_all_tests_categoryDandE_ii_lbnl.py
get_all_tests_categoryDandE_ii_ucsc.py
```

The pipeline runs these with:

```bash
--test_name "Response Curve TC" --max_workers 6
```

A complete HX module normally has **25 input-noise JSON files**.

Use `Response Curve TC` for HX input-noise data. Do not use `Module AMAC IV TC` for these HX scripts.

They also help identify:

- Category D(ii): incomplete input-noise dataset
- Category E(ii): input-noise data unavailable or could not be processed

## Expected source folders

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

---

# Stage 2 — Problem modules and category summaries

Run separately with:

```bash
bash 02_run_problem_modules_and_website.sh
```

Stage 2 reads source JSON files from `ML` and `HX` and saves problem-focused output in `ML2` and `HX2`.

## Problem IV scripts

```text
plot_multi_IV_final_BNL_Category_A_Di_warning.py
plot_multi_IV_final_LBNL_Category_A_Di_warning.py
plot_multi_IV_final_UCSC_Category_A_Di_warning.py
```

These scripts:

- generate problem IV plots;
- save PDF and PNG output under `ML2`;
- identify Category A and D(i);
- record E(i) when IV data cannot be processed;
- create warnings for IV current above 300 nA but not above 600 nA.

Problem IV folders:

```text
BNL/ML2/
LBNL/ML2/
UCSC/ML2/
```

## Problem input-noise scripts

For each site, Stage 2 runs:

- standard problem input-noise plotting;
- no-skip problem input-noise plotting;
- combined problem histograms;
- combined no-skip problem histograms;
- detailed per-file histograms.

BNL examples:

```text
plot_multi_inputnoise_BNL_one_channel_subcategories.py
plot_multi_inputnoise_noskip_BNL_one_channel_subcategories.py
plot_combined_inputnoise_BNL_one_channel_subcategories.py
plot_combined_inputnoise_noskip_BNL_one_channel_subcategories.py
plot_detailed_inputnoise_histograms_per_file_BNL.py
```

Equivalent LBNL and UCSC scripts are also run.

Problem HX folders:

```text
BNL/HX2/
LBNL/HX2/
UCSC/HX2/
```

## Category B/C summary scripts

```text
generate_categoryBandC_BNL_from_inputnoise_summary.py
generate_categoryBandC_LBNL_from_inputnoise_summary.py
generate_categoryBandC_UCSC_from_inputnoise_summary.py
```

Expected summary files include:

```text
BNL/ML2/iv_category_summary_bnl.txt
LBNL/ML2/iv_category_summary_lbnl.txt
UCSC/ML2/iv_category_summary_ucsc.txt

BNL/HX2/inputnoise_category_summary_bnl.txt
LBNL/HX2/inputnoise_category_summary_lbnl.txt
UCSC/HX2/inputnoise_category_summary_ucsc.txt
```

Stage 2 verifies that these files exist and are not empty before continuing.

## Website script

Stage 2 runs:

```text
get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py
```

The website is written to:

```text
categories_website/
```

---

# Stage 3 — Regular plots and final website

Run separately with:

```bash
bash 03_run_regular_modules_and_website.sh
```

Stage 3 generates regular plots for all available modules.

## Regular IV scripts

```text
plot_multi_IV_final_BNL.py
plot_multi_IV_final_LBNL.py
plot_multi_IV_final_UCSC.py
```

Regular IV output is saved under:

```text
BNL/ML3/
LBNL/ML3/
UCSC/ML3/
```

## Regular input-noise scripts

For each site, Stage 3 runs:

- standard input-noise plots;
- no-skip input-noise plots;
- combined histograms;
- combined no-skip histograms.

BNL examples:

```text
plot_multi_inputnoise_BNL.py
plot_multi_inputnoise_noskip_BNL.py
plot_combined_inputnoise_BNL.py
plot_combined_inputnoise_noskip_BNL.py
```

Equivalent LBNL and UCSC scripts are also run.

Regular HX output is saved under:

```text
BNL/HX3/
LBNL/HX3/
UCSC/HX3/
```

Stage 3 then runs the website generator again so that the final pages include the completed regular plots and problem-module data.

---

## 5. Category definitions

| Category | Definition |
|---|---|
| **A** | IV current above **600 nA**. |
| **B(i)** | Away-stream input noise greater than **1100 ENC** for 10 or more channels. |
| **B(ii)** | Under-stream input noise greater than **1100 ENC** for 10 or more channels. |
| **C(i)** | Away-stream input noise less than **600 ENC** for 10 or more channels. |
| **C(ii)** | Under-stream input noise less than **600 ENC** for 10 or more channels. |
| **D(i)** | Incomplete IV dataset. |
| **D(ii)** | Incomplete input-noise dataset. |
| **E(i)** | IV data unavailable or could not be processed. |
| **E(ii)** | Input-noise data unavailable or could not be processed. |

An IV value above **300 nA** but not above **600 nA** is displayed as an additional warning and does not create a separate category.

---

## 6. Important output locations

| Output | Location |
|---|---|
| Downloaded ML IV JSON | `SITE/ML/SN20USBML.../` |
| Downloaded HX input-noise JSON | `SITE/HX/SN20USBHX.../` |
| Problem IV plots and summaries | `SITE/ML2/` |
| Problem input-noise plots and summaries | `SITE/HX2/` |
| Regular IV plots | `SITE/ML3/` |
| Regular input-noise plots | `SITE/HX3/` |
| Final website | `categories_website/` |

`SITE` is `BNL`, `LBNL`, or `UCSC`.

Combined no-skip histogram folders may also contain low/high JSON files, for example:

```text
BNL/HX2/SN20USBHX.../histograms_combined_noskip/
```

---

## 7. Run only one stage

Download data only:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
bash 01_run_data_download.sh
```

Rebuild problem outputs only:

```bash
bash 02_run_problem_modules_and_website.sh
```

Rebuild regular outputs and the final website only:

```bash
bash 03_run_regular_modules_and_website.sh
```

Stages 2 and 3 do not require a fresh database token when valid JSON data already exists locally.

---

## 8. Debug one module

### Download one HX input-noise module

```bash
python3 get_test_run.py \
  --serial_number 20USBHX2004501 \
  --test_name "Response Curve TC"
```

Or use the script that separates the results into 25 files:

```bash
python3 get_test_run2.py \
  --serial_number 20USBHX2004826 \
  --test_name "Response Curve TC"
```

### Download one ML IV module

```bash
python3 get_test_run.py \
  --serial_number 20USBML1235274 \
  --test_name "Module AMAC IV TC"
```

Or use the script that separates the results into 24 files:

```bash
python3 get_test_run3.py \
  --serial_number 20USBML1235274 \
  --test_name "Module AMAC IV TC"
```

### Plot one ML module

```bash
python3 plot_multi_IV.py -i "SN20USBML1235852/*.json"
```

### Plot one HX module

```bash
python3 plot_multi_inputnoise.py --serial_number 20USBHX2002657
python3 plot_multi_inputnoise_noskip.py --serial_number 20USBHX2002657
python3 plot_combined_inputnoise.py --serial_number 20USBHX2002657
python3 plot_combined_inputnoise_noskip.py --serial_number 20USBHX2002657
python3 plot_detailed_inputnoise_histograms_per_file.py --serial_number 20USBHX2002657
```

---

## 9. Troubleshooting

### `ITK_DB_AUTH is not set`

Get a token from the link in Section 3 and run:

```bash
export ITK_DB_AUTH=YOUR_TOKEN
```

### Token expired

Obtain a new token and export it again. An expired token can cause download failures and may incorrectly make modules appear as Category E.

### Required Python script not found

Run the shell scripts from the main project directory and confirm that all Python script names match those listed in the stage scripts.

### Required category summary is missing or empty

Review the earlier plotting output for errors. Confirm that the source JSON folders contain data and that the problem plotting scripts completed successfully.

### A module has fewer than 24 IV files

It may be Category D(i), or some files may have failed to download.

### A module has fewer than 25 input-noise files

It may be Category D(ii), or some files may have failed to download.

### Plots or links are missing from the website

Confirm that the expected PDF/PNG files exist under `ML2`, `ML3`, `HX2`, or `HX3`, then rerun:

```bash
python3 get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py
```

---

## 10. Upload to CERNBox/CERN web space

After the final website is generated, upload or synchronize:

```text
categories_website/
BNL/
LBNL/
UCSC/
```

The website generator currently uses the base URL:

```text
https://ameliame.web.cern.ch
```

Confirm that the remote directory structure matches the local paths used by the generated HTML pages. Missing or differently named folders will produce broken image and PDF links.

---

## 11. GitHub safety

Do not commit:

- `ITK_DB_AUTH` tokens;
- private credentials;
- temporary authentication files;
- large generated data or plots unless they are intentionally versioned.

A useful `.gitignore` may include:

```gitignore
.venv/
__pycache__/
*.pyc
.DS_Store

# Local secrets
.env

# Optional generated outputs
categories_website/
BNL/HX2/
BNL/HX3/
BNL/ML2/
BNL/ML3/
LBNL/HX2/
LBNL/HX3/
LBNL/ML2/
LBNL/ML3/
UCSC/HX2/
UCSC/HX3/
UCSC/ML2/
UCSC/ML3/
```

Only ignore generated folders when they should not be stored in the repository.
