#!/usr/bin/env bash

# ============================================================
# 01_run_data_download.sh
#
# Downloads/refreshes all source data before any plotting.
# Run first:
#   bash 01_run_data_download.sh
# ============================================================

set -euo pipefail

PYTHON_BIN="${PYTHON_BIN:-python3}"

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

print_header "Stage 1 of 3: Downloading and refreshing ITk data"

if [[ -z "${ITK_DB_AUTH:-}" ]]; then
    echo "ERROR: ITK_DB_AUTH is not set."
    echo ""
    echo "Run this first:"
    echo "  export ITK_DB_AUTH=YOUR_TOKEN"
    exit 1
fi

echo "ITK_DB_AUTH is set."

print_header "Getting latest module serial numbers and timestamps"

run_python "get_module_serial_numbers.py"
run_python "get_test_timestamp_full_list_BNL.py"
run_python "get_test_timestamp_full_list_LBNL.py"
run_python "get_test_timestamp_full_list_UCSC.py"

print_header "Downloading ML IV JSON files"

run_python "get_all_tests_categoryE_i_bnl.py"
run_python "get_all_tests_categoryE_i_lbnl.py"
run_python "get_all_tests_categoryE_i_ucsc.py"

print_header "Downloading HX input-noise JSON files"

run_python "get_all_tests_categoryDandE_ii_bnl.py" \
    --test_name "Response Curve TC" \
    --max_workers 6

run_python "get_all_tests_categoryDandE_ii_lbnl.py" \
    --test_name "Response Curve TC" \
    --max_workers 6

run_python "get_all_tests_categoryDandE_ii_ucsc.py" \
    --test_name "Response Curve TC" \
    --max_workers 6

print_header "Data download complete"

echo "Next run:"
echo "  bash 02_run_problem_modules_and_website.sh"
