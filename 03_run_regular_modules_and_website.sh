#!/usr/bin/env bash

# ============================================================
# 03_run_regular_modules_and_website.sh
#
# Generates regular plots in HX3 and performs the final website
# rebuild. Run third:
#   bash 03_run_regular_modules_and_website.sh
# ============================================================

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

BNL_REGULAR_INPUTNOISE_SCRIPT="plot_multi_inputnoise_BNL.py"
BNL_REGULAR_INPUTNOISE_NOSKIP_SCRIPT="plot_multi_inputnoise_noskip_BNL.py"
BNL_REGULAR_COMBINED_SCRIPT="plot_combined_inputnoise_BNL.py"
BNL_REGULAR_COMBINED_NOSKIP_SCRIPT="plot_combined_inputnoise_noskip_BNL.py"

LBNL_REGULAR_INPUTNOISE_SCRIPT="plot_multi_inputnoise_LBNL.py"
LBNL_REGULAR_INPUTNOISE_NOSKIP_SCRIPT="plot_multi_inputnoise_noskip_LBNL.py"
LBNL_REGULAR_COMBINED_SCRIPT="plot_combined_inputnoise_LBNL.py"
LBNL_REGULAR_COMBINED_NOSKIP_SCRIPT="plot_combined_inputnoise_noskip_LBNL.py"

UCSC_REGULAR_INPUTNOISE_SCRIPT="plot_multi_inputnoise_UCSC.py"
UCSC_REGULAR_INPUTNOISE_NOSKIP_SCRIPT="plot_multi_inputnoise_noskip_UCSC.py"
UCSC_REGULAR_COMBINED_SCRIPT="plot_combined_inputnoise_UCSC.py"
UCSC_REGULAR_COMBINED_NOSKIP_SCRIPT="plot_combined_inputnoise_noskip_UCSC.py"

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

print_header "Stage 3 of 3: Generating regular-module plots"

print_header "Generating BNL regular HX plots in BNL/HX3"

python plot_multi_IV_final_BNL.py -i "BNL/ML/*/*.json" -o "BNL/ML3"

python plot_multi_IV_final_LBNL.py -i "LBNL/ML/*/*.json" -o "LBNL/ML3"

python plot_multi_IV_final_UCSC.py -i "UCSC/ML/*/*.json" -o "UCSC/ML3"

run_python "$BNL_REGULAR_INPUTNOISE_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX3"
run_python "$BNL_REGULAR_INPUTNOISE_NOSKIP_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX3"
run_python "$BNL_REGULAR_COMBINED_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX3"
run_python "$BNL_REGULAR_COMBINED_NOSKIP_SCRIPT" \
    -i "BNL/HX/SN*/*.json" -o "BNL/HX3"

print_header "Generating LBNL regular HX plots in LBNL/HX3"

run_python "$LBNL_REGULAR_INPUTNOISE_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX3"
run_python "$LBNL_REGULAR_INPUTNOISE_NOSKIP_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX3"
run_python "$LBNL_REGULAR_COMBINED_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX3"
run_python "$LBNL_REGULAR_COMBINED_NOSKIP_SCRIPT" \
    -i "LBNL/HX/SN*/*.json" -o "LBNL/HX3"

print_header "Generating UCSC regular HX plots in UCSC/HX3"

run_python "$UCSC_REGULAR_INPUTNOISE_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX3"
run_python "$UCSC_REGULAR_INPUTNOISE_NOSKIP_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX3"
run_python "$UCSC_REGULAR_COMBINED_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX3"
run_python "$UCSC_REGULAR_COMBINED_NOSKIP_SCRIPT" \
    -i "UCSC/HX/SN*/*.json" -o "UCSC/HX3"

print_header "Performing final website rebuild"
run_python "$WEBSITE_SCRIPT"

print_header "Regular-module stage and website update complete"

echo "Regular plot folders:"
echo "  BNL/HX3/"
echo "  LBNL/HX3/"
echo "  UCSC/HX3/"
echo ""
echo "Final website folder:"
echo "  categories_website/"
echo ""
echo "Done."
