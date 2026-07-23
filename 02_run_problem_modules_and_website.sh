#!/usr/bin/env bash

# ============================================================
# 02_run_problem_modules_and_website.sh
#
# Generates problem-only plots in HX2/ML2, including detailed
# input-noise histograms, summaries, and then builds the website.
# Run second:
#   bash 02_run_problem_modules_and_website.sh
# ============================================================

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

BNL_IV_SCRIPT="plot_multi_IV_final_BNL_Category_A_Di_warning.py"
LBNL_IV_SCRIPT="plot_multi_IV_final_LBNL_Category_A_Di_warning.py"
UCSC_IV_SCRIPT="plot_multi_IV_final_UCSC_Category_A_Di_warning.py"

BNL_PROBLEM_INPUTNOISE_SCRIPT="plot_multi_inputnoise_BNL_one_channel_subcategories.py"
BNL_PROBLEM_INPUTNOISE_NOSKIP_SCRIPT="plot_multi_inputnoise_noskip_BNL_one_channel_subcategories.py"
BNL_PROBLEM_COMBINED_SCRIPT="plot_combined_inputnoise_BNL_one_channel_subcategories.py"
BNL_PROBLEM_COMBINED_NOSKIP_SCRIPT="plot_combined_inputnoise_noskip_BNL_one_channel_subcategories.py"
BNL_PROBLEM_DETAILED_SCRIPT="plot_detailed_inputnoise_histograms_per_file_BNL.py"

LBNL_PROBLEM_INPUTNOISE_SCRIPT="plot_multi_inputnoise_LBNL_one_channel_subcategories.py"
LBNL_PROBLEM_INPUTNOISE_NOSKIP_SCRIPT="plot_multi_inputnoise_noskip_LBNL_one_channel_subcategories.py"
LBNL_PROBLEM_COMBINED_SCRIPT="plot_combined_inputnoise_LBNL_one_channel_subcategories.py"
LBNL_PROBLEM_COMBINED_NOSKIP_SCRIPT="plot_combined_inputnoise_noskip_LBNL_one_channel_subcategories.py"
LBNL_PROBLEM_DETAILED_SCRIPT="plot_detailed_inputnoise_histograms_per_file_LBNL.py"

UCSC_PROBLEM_INPUTNOISE_SCRIPT="plot_multi_inputnoise_UCSC_one_channel_subcategories.py"
UCSC_PROBLEM_INPUTNOISE_NOSKIP_SCRIPT="plot_multi_inputnoise_noskip_UCSC_one_channel_subcategories.py"
UCSC_PROBLEM_COMBINED_SCRIPT="plot_combined_inputnoise_UCSC_one_channel_subcategories.py"
UCSC_PROBLEM_COMBINED_NOSKIP_SCRIPT="plot_combined_inputnoise_noskip_UCSC_one_channel_subcategories.py"
UCSC_PROBLEM_DETAILED_SCRIPT="plot_detailed_inputnoise_histograms_per_file_UCSC.py"

BNL_BC_SUMMARY_SCRIPT="generate_categoryBandC_BNL_from_inputnoise_summary.py"
LBNL_BC_SUMMARY_SCRIPT="generate_categoryBandC_LBNL_from_inputnoise_summary.py"
UCSC_BC_SUMMARY_SCRIPT="generate_categoryBandC_UCSC_from_inputnoise_summary.py"

WEBSITE_SCRIPT="get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py"

print_header() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

run_python() {
    local script="$1"
    shift

    if [[ ! -f "$script" ]]; then
        echo "ERROR: Required script not found: $script" >&2
        exit 1
    fi

    echo "+ $PYTHON_BIN $script $*"
    "$PYTHON_BIN" "$script" "$@"
}

verify_nonempty_file() {
    local file_path="$1"

    if [[ ! -s "$file_path" ]]; then
        echo "ERROR: Required file is missing or empty: $file_path" >&2
        exit 1
    fi

    echo "Verified: $file_path"
}

print_header "Stage 2 of 3: Generating problem-module plots"

print_header "Generating problem-only IV plots in ML2"

run_python "$BNL_IV_SCRIPT" -i "BNL/ML/*/*.json" -o "BNL/ML2"
run_python "$LBNL_IV_SCRIPT" -i "LBNL/ML/*/*.json" -o "LBNL/ML2"
run_python "$UCSC_IV_SCRIPT" -i "UCSC/ML/*/*.json" -o "UCSC/ML2"

print_header "Generating BNL problem-only HX plots in BNL/HX2"

run_python "$BNL_PROBLEM_INPUTNOISE_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX2"
run_python "$BNL_PROBLEM_INPUTNOISE_NOSKIP_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX2"
run_python "$BNL_PROBLEM_COMBINED_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX2"
run_python "$BNL_PROBLEM_COMBINED_NOSKIP_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX2"
run_python "$BNL_PROBLEM_DETAILED_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX2"

print_header "Generating LBNL problem-only HX plots in LBNL/HX2"

run_python "$LBNL_PROBLEM_INPUTNOISE_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX2"
run_python "$LBNL_PROBLEM_INPUTNOISE_NOSKIP_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX2"
run_python "$LBNL_PROBLEM_COMBINED_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX2"
run_python "$LBNL_PROBLEM_COMBINED_NOSKIP_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX2"
run_python "$LBNL_PROBLEM_DETAILED_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX2"

print_header "Generating UCSC problem-only HX plots in UCSC/HX2"

run_python "$UCSC_PROBLEM_INPUTNOISE_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX2"
run_python "$UCSC_PROBLEM_INPUTNOISE_NOSKIP_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX2"
run_python "$UCSC_PROBLEM_COMBINED_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX2"
run_python "$UCSC_PROBLEM_COMBINED_NOSKIP_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX2"
run_python "$UCSC_PROBLEM_DETAILED_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX2"

print_header "Generating Category B/C summaries from HX2"

run_python "$BNL_BC_SUMMARY_SCRIPT" \
    --input_file "BNL/HX2/inputnoise_error_summary_bnl.txt" \
    --output_file "BNL/HX2/inputnoise_category_summary_bnl.txt"

run_python "$LBNL_BC_SUMMARY_SCRIPT" \
    --input_file "LBNL/HX2/inputnoise_error_summary_lbnl.txt" \
    --output_file "LBNL/HX2/inputnoise_category_summary_lbnl.txt"

run_python "$UCSC_BC_SUMMARY_SCRIPT" \
    --input_file "UCSC/HX2/inputnoise_error_summary_ucsc.txt" \
    --output_file "UCSC/HX2/inputnoise_category_summary_ucsc.txt"

print_header "Verifying problem-category summaries"

required_summary_files=(
    "BNL/ML2/iv_category_summary_bnl.txt"
    "LBNL/ML2/iv_category_summary_lbnl.txt"
    "UCSC/ML2/iv_category_summary_ucsc.txt"
    "BNL/HX2/inputnoise_category_summary_bnl.txt"
    "LBNL/HX2/inputnoise_category_summary_lbnl.txt"
    "UCSC/HX2/inputnoise_category_summary_ucsc.txt"
)

for summary_file in "${required_summary_files[@]}"; do
    verify_nonempty_file "$summary_file"
done

print_header "Building website after problem-module plots"
run_python "$WEBSITE_SCRIPT"

print_header "Problem-module stage complete"

echo "Generated problem plot folders:"
echo "  BNL/HX2 and BNL/ML2"
echo "  LBNL/HX2 and LBNL/ML2"
echo "  UCSC/HX2 and UCSC/ML2"
echo ""
echo "Detailed problem histograms were generated with:"
echo "  $BNL_PROBLEM_DETAILED_SCRIPT"
echo "  $LBNL_PROBLEM_DETAILED_SCRIPT"
echo "  $UCSC_PROBLEM_DETAILED_SCRIPT"
echo ""
echo "Website rebuilt in categories_website/."
echo "Next run:"
echo "  bash 03_run_regular_modules_and_website.sh"
