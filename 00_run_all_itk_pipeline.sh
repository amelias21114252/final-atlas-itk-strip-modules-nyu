#!/usr/bin/env bash

# ============================================================
# 00_run_all_itk_pipeline.sh
#
# Runs the complete ITk QC workflow in order:
#   1. Download/refresh source data
#   2. Generate problem-module plots and summaries
#   3. Generate regular-module plots and rebuild the website
#
# Usage:
#   bash 00_run_all_itk_pipeline.sh
#   bash 00_run_all_itk_pipeline.sh --skip-download
#   bash 00_run_all_itk_pipeline.sh --start-at 2
# ============================================================

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="${PROJECT_DIR:-$PWD}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
START_STAGE=1
SKIP_DOWNLOAD=0

usage() {
    cat <<'USAGE'
Usage: bash 00_run_all_itk_pipeline.sh [options]

Options:
  --project-dir PATH   Directory containing the Python scripts and BNL/LBNL/UCSC folders.
                       Default: current working directory.
  --python PATH        Python executable to use. Default: python3.
  --skip-download      Skip Stage 1 and use existing downloaded JSON data.
  --start-at N         Start at stage 1, 2, or 3.
  -h, --help           Show this help message.

Environment variables:
  ITK_DB_AUTH          Required when Stage 1 is run.
  PROJECT_DIR          Alternative way to set the project directory.
  PYTHON_BIN           Alternative way to choose the Python executable.

Examples:
  export ITK_DB_AUTH=YOUR_TOKEN
  bash 00_run_all_itk_pipeline.sh

  bash 00_run_all_itk_pipeline.sh --skip-download
  bash 00_run_all_itk_pipeline.sh --start-at 2
  bash 00_run_all_itk_pipeline.sh --project-dir /path/to/project
USAGE
}

print_header() {
    echo ""
    echo "============================================================"
    echo "$1"
    echo "============================================================"
}

require_file() {
    local file_path="$1"
    if [[ ! -f "$file_path" ]]; then
        echo "ERROR: Required pipeline script not found: $file_path" >&2
        exit 1
    fi
}

run_stage() {
    local stage_number="$1"
    local stage_name="$2"
    local stage_script="$3"

    print_header "Running Stage ${stage_number}: ${stage_name}"
    echo "+ bash $stage_script"
    bash "$stage_script"
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --project-dir)
            [[ $# -ge 2 ]] || { echo "ERROR: --project-dir requires a path." >&2; exit 2; }
            PROJECT_DIR="$2"
            shift 2
            ;;
        --python)
            [[ $# -ge 2 ]] || { echo "ERROR: --python requires a path or command." >&2; exit 2; }
            PYTHON_BIN="$2"
            shift 2
            ;;
        --skip-download)
            SKIP_DOWNLOAD=1
            shift
            ;;
        --start-at)
            [[ $# -ge 2 ]] || { echo "ERROR: --start-at requires 1, 2, or 3." >&2; exit 2; }
            START_STAGE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "ERROR: Unknown option: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ ! "$START_STAGE" =~ ^[123]$ ]]; then
    echo "ERROR: --start-at must be 1, 2, or 3." >&2
    exit 2
fi

PROJECT_DIR="$(cd -- "$PROJECT_DIR" && pwd)"
export PYTHON_BIN

STAGE1="$SCRIPT_DIR/01_run_data_download.sh"
STAGE2="$SCRIPT_DIR/02_run_problem_modules_and_website.sh"
STAGE3="$SCRIPT_DIR/03_run_regular_modules_and_website.sh"

require_file "$STAGE1"
require_file "$STAGE2"
require_file "$STAGE3"

print_header "Complete ITk QC plotting and website pipeline"
echo "Pipeline scripts: $SCRIPT_DIR"
echo "Project directory: $PROJECT_DIR"
echo "Python executable: $PYTHON_BIN"
echo "Starting stage: $START_STAGE"

cd "$PROJECT_DIR"

if (( START_STAGE <= 1 )) && (( SKIP_DOWNLOAD == 0 )); then
    run_stage 1 "Download and refresh source data" "$STAGE1"
elif (( START_STAGE <= 1 )); then
    print_header "Skipping Stage 1: Download and refresh source data"
fi

if (( START_STAGE <= 2 )); then
    run_stage 2 "Problem-module plots, summaries, and website" "$STAGE2"
fi

if (( START_STAGE <= 3 )); then
    run_stage 3 "Regular-module plots and final website rebuild" "$STAGE3"
fi

print_header "All requested ITk pipeline stages completed successfully"
echo "Problem outputs: BNL/LBNL/UCSC HX2 and ML2"
echo "Regular outputs: BNL/LBNL/UCSC HX3 and ML3"
echo "Website output: categories_website/"
