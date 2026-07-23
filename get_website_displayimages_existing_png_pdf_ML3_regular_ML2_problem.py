#python get_website_displayimages_existing_png_pdf_ML3_regular_ML2_problem.py

#!/usr/bin/env python3

import json
import csv
import re
from pathlib import Path
import shutil


BASE_URL = "https://ameliame.web.cern.ch"


# ============================================================
# Output folder
# ============================================================

OUTPUT_DIR = Path("categories_website")
OUTPUT_DIR.mkdir(exist_ok=True)

institutes = {
    "BNL": [],
    "LBNL": [],
    "UCSC": [],
}

page_names = {
    "BNL": "bnl.html",
    "LBNL": "lbnl.html",
    "UCSC": "ucsc.html",
}

TIMESTAMP_FILES = {
    "BNL": "formatted_timestamps_bnl.txt",
    "LBNL": "formatted_timestamps_lbnl.txt",
    "UCSC": "formatted_timestamps_ucsc.txt",
}


def parse_formatted_timestamp_file(file_path):
    text = Path(file_path).read_text(encoding="utf-8")
    rows = []
    pat = re.compile(
        r'^\s*\(\s*"([^"]*)"\s*,\s*"([^"]*)"\s*,\s*"([^"]*)"\s*\)\s*,?(?:\s*#.*)?$',
        re.M,
    )

    for match in pat.finditer(text):
        hx, ml, timestamp = [value.strip() for value in match.groups()]

        if (
            "..." in hx
            or "..." in ml
            or timestamp.upper().startswith("YYYY-")
            or "yyyy-mm-dd" in timestamp.lower()
        ):
            continue

        if hx or ml:
            rows.append((hx, ml, timestamp))

    if not rows:
        raise ValueError(f"No timestamp tuples found in {file_path}")

    return rows

def load_external_timestamp_lists():
    from pathlib import Path
    loaded={}
    for site,fname in TIMESTAMP_FILES.items():
        candidates=[Path(fname),Path(__file__).resolve().parent/fname]
        fp=None
        for c in candidates:
            if c.exists():
                fp=c;break
        if fp is None:
            raise FileNotFoundError(f"Missing required timestamp file: {fname}")
        loaded[site]=parse_formatted_timestamp_file(fp)
        print(f"Loaded {site}: {len(loaded[site])} timestamps")
    institutes.clear()
    institutes.update(loaded)

load_external_timestamp_lists()


# ============================================================
# Category definitions
# One place for category lists + default messages + optional comments
#
# Format:
# "serial_without_SN": None
#     -> uses the default message
#
# "serial_without_SN": "custom comment"
#     -> uses this detailed comment
# ============================================================

CATEGORY_DEFINITIONS = {
    "Category A": {
        "serial_type": "ML",
        "css_class": "category-a",
        "default": "IV current above 600 nA threshold.",
        "modules": {},
    },
    "Category B(i)": {
        "serial_type": "HX",
        "css_class": "category-b",
        "default": "Away-stream input noise greater than 1100 ENC for 10 or more channels.",
        "modules": {},
    },
    "Category B(ii)": {
        "serial_type": "HX",
        "css_class": "category-b",
        "default": "Under-stream input noise greater than 1100 ENC for 10 or more channels.",
        "modules": {},
    },
    "Category C(i)": {
        "serial_type": "HX",
        "css_class": "category-c",
        "default": "Away-stream input noise less than 600 ENC for 10 or more channels.",
        "modules": {},
    },
    "Category C(ii)": {
        "serial_type": "HX",
        "css_class": "category-c",
        "default": "Under-stream input noise less than 600 ENC for 10 or more channels.",
        "modules": {},
    },
    "Category D(i)": {
        "serial_type": "ML",
        "css_class": "category-d",
        "default": "Incomplete IV dataset.",
        "modules": {},
    },
    "Category D(ii)": {
        "serial_type": "HX",
        "css_class": "category-d",
        "default": "Incomplete input-noise dataset.",
        "modules": {},
    },
    "Category E(i)": {
        "serial_type": "ML",
        "css_class": "category-e",
        "default": "IV data unavailable or could not be processed.",
        "modules": {},
    },
    "Category E(ii)": {
        "serial_type": "HX",
        "css_class": "category-e",
        "default": "Input-noise data unavailable or could not be processed.",
        "modules": {},
    },
}


# ============================================================
# Additional comments / warnings
# These can apply to any category: A, B, C, D, E, or modules
# that are below an error threshold.
# These do not create categories by themselves.
# ============================================================

ADDITIONAL_COMMENTS = {}

# Named warnings used by the problem pages. Input-noise warning maps contain
# modules with at least one channel outside the accepted 600–1100 ENC window,
# even when fewer than 10 channels are affected.
PROBLEM_WARNING_INFO = {}


# ============================================================
# General module comments
# Not category-specific
# ============================================================

module_comments = {}
# Required imports
# ============================================================

import json
import csv
import shutil
from pathlib import Path


# ============================================================
# Logo files for homepage
# Put these files in the same folder as this script,
# or directly inside categories_website/
# ============================================================

logo_files = {
    "BNL": "bnl.png",
    "LBNL": "lbnl.png",
    "UCSC": "scipp.png",
}


# ============================================================
# Normal page names
# ============================================================

page_names = {
    "BNL": "bnl.html",
    "LBNL": "lbnl.html",
    "UCSC": "ucsc.html",
}


# ============================================================
# Separate problematic/display page names
# ============================================================

problem_page_names = {
    "BNL": "bnlproblem.html",
    "LBNL": "lbnlproblem.html",
    "UCSC": "ucscproblem.html",
}



# ============================================================
# Dynamic category loaders for BNL, LBNL, and UCSC
#
# Timestamp behavior is intentionally unchanged. The website continues to
# read formatted_timestamps_bnl.txt, formatted_timestamps_lbnl.txt, and
# formatted_timestamps_ucsc.txt and displays each timestamp string exactly as
# stored in those tuple files.
# ============================================================

import ast


def dynamic_normalize_serial(module):
    if not module:
        return ""
    module = str(module).strip()
    return module if module.startswith("SN") else f"SN{module}"


SITE_DYNAMIC_FILES = {
    "BNL": {
        "ml_summary": [
            "BNL/ML2/summary_page_bnl_ml.txt",
            "BNL/ML/summary_page_bnl_ml.txt",
        ],
        "iv_categories": [
            "BNL/ML2/iv_category_summary_bnl.txt",
            "BNL/ML/iv_category_summary_bnl.txt",
        ],
        "inputnoise_categories": [
            "BNL/HX2/inputnoise_category_summary_bnl.txt",
            "BNL/HX2/inputnoise_category_summary_bnl.txt",
        ],
        "hx_summary": [
            "BNL/HX2/summary_page_bnl_HX.txt",
            "BNL/HX2/summary_page_bnl_hx.txt",
            "BNL/HX/summary_page_bnl_HX.txt",
            "BNL/HX/summary_page_bnl_hx.txt",
        ],
    },
    "LBNL": {
        "ml_summary": [
            "LBNL/ML2/summary_page_lbnl_ml.txt",
            "LBNL/ML/summary_page_lbnl_ml.txt",
        ],
        "iv_categories": [
            "LBNL/ML2/iv_category_summary_lbnl.txt",
            "LBNL/ML/iv_category_summary_lbnl.txt",
        ],
        "inputnoise_categories": [
            "LBNL/HX2/inputnoise_category_summary_lbnl.txt",
            "LBNL/HX2/inputnoise_category_summary_lbnl.txt",
        ],
        "hx_summary": [
            "LBNL/HX2/summary_page_lbnl_HX.txt",
            "LBNL/HX2/summary_page_lbnl_hx.txt",
            "LBNL/HX/summary_page_lbnl_HX.txt",
            "LBNL/HX/summary_page_lbnl_hx.txt",
        ],
    },
    "UCSC": {
        "ml_summary": [
            "UCSC/ML2/summary_page_ucsc_ml.txt",
            "UCSC/ML/summary_page_ucsc_ml.txt",
        ],
        "iv_categories": [
            "UCSC/ML2/iv_category_summary_ucsc.txt",
            "UCSC/ML/iv_category_summary_ucsc.txt",
        ],
        "inputnoise_categories": [
            "UCSC/HX2/inputnoise_category_summary_ucsc.txt",
            "UCSC/HX2/inputnoise_category_summary_ucsc.txt",
        ],
        "hx_summary": [
            "UCSC/HX2/summary_page_ucsc_HX.txt",
            "UCSC/HX2/summary_page_ucsc_hx.txt",
            "UCSC/HX/summary_page_ucsc_HX.txt",
            "UCSC/HX/summary_page_ucsc_hx.txt",
        ],
    },
}


def resolve_data_file(relative_paths, site, data_name):
    """Resolve one required summary file from accepted path variants."""
    if isinstance(relative_paths, (str, Path)):
        relative_paths = [relative_paths]

    script_dir = Path(__file__).resolve().parent
    checked = []

    for relative_path in relative_paths:
        relative_path = Path(relative_path)
        candidates = [relative_path, script_dir / relative_path]

        # Uploaded copies can have suffixes such as "(1)" or "_2".
        for parent in (relative_path.parent, script_dir / relative_path.parent):
            if parent.exists():
                candidates.extend(sorted(parent.glob(f"{relative_path.stem}*{relative_path.suffix}")))

        for candidate in candidates:
            checked.append(str(candidate))
            if candidate.exists() and candidate.is_file():
                return candidate

    raise FileNotFoundError(
        f"Missing required {site} {data_name} file.\n"
        f"Accepted production paths: {', '.join(map(str, relative_paths))}\n"
        f"Checked working-directory and script-directory locations."
    )


def extract_python_assignment(text, variable_name, expected_type=dict):
    """Safely extract a literal Python assignment from a text summary."""
    pattern = re.compile(rf"(?m)^\s*{re.escape(variable_name)}\s*=\s*")
    match = pattern.search(text)
    if not match:
        return expected_type()

    start = match.end()
    opener = text[start:start + 1]
    matching = {"{": "}", "[": "]", "(": ")"}
    if opener not in matching:
        return expected_type()

    closer = matching[opener]
    depth = 0
    quote = None
    escaped = False

    for index in range(start, len(text)):
        char = text[index]
        if quote:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == quote:
                quote = None
            continue
        if char in ('"', "'"):
            quote = char
            continue
        if char == opener:
            depth += 1
        elif char == closer:
            depth -= 1
            if depth == 0:
                value = ast.literal_eval(text[start:index + 1])
                if not isinstance(value, expected_type):
                    raise TypeError(
                        f"{variable_name} is {type(value).__name__}; "
                        f"expected {expected_type.__name__}."
                    )
                return value

    raise ValueError(f"Unterminated assignment for {variable_name}")


def normalized_comment_map(raw_map):
    normalized = {}
    for serial, comment in raw_map.items():
        serial_sn = dynamic_normalize_serial(serial)
        if serial_sn:
            normalized[serial_sn] = str(comment).strip() if comment else ""
    return normalized


def extract_serial_universe(text, serial_type):
    pattern = rf'["\'](SN)?(20USB{serial_type}\d+)["\']'
    return {
        dynamic_normalize_serial(match.group(2))
        for match in re.finditer(pattern, text)
    }


def remove_serials_from_map(mapping, serials):
    for serial in list(mapping):
        if dynamic_normalize_serial(serial) in serials:
            del mapping[serial]


def merge_additional_comment(serial, comment):
    serial = dynamic_normalize_serial(serial)
    if not serial or not comment:
        return

    current = ADDITIONAL_COMMENTS.get(serial)
    if not current:
        comments = []
    elif isinstance(current, list):
        comments = list(current)
    else:
        comments = [current]

    if comment not in comments:
        comments.append(comment)
    ADDITIONAL_COMMENTS[serial] = comments

def merge_problem_warning(serial, warning_label, comment):
    """Store a named problem warning for one module."""
    serial = dynamic_normalize_serial(serial)
    if not serial or not warning_label:
        return

    entries = PROBLEM_WARNING_INFO.setdefault(serial, [])
    entry = {
        "label": str(warning_label).strip(),
        "comment": str(comment).strip() if comment else "",
    }
    if entry not in entries:
        entries.append(entry)


REQUESTED_CATEGORY_DEFAULTS = {
    "Category A": "IV current above 600 nA threshold.",
    "Category B(i)": "Away-stream input noise greater than 1100 ENC for 10 or more channels.",
    "Category B(ii)": "Under-stream input noise greater than 1100 ENC for 10 or more channels.",
    "Category C(i)": "Away-stream input noise less than 600 ENC for 10 or more channels.",
    "Category C(ii)": "Under-stream input noise less than 600 ENC for 10 or more channels.",
    "Category D(i)": "Incomplete IV dataset.",
    "Category D(ii)": "Incomplete input-noise dataset.",
    "Category E(i)": "IV data unavailable or could not be processed.",
    "Category E(ii)": "Input-noise data unavailable or could not be processed.",
}


def apply_dynamic_site_categories(site):
    file_config = SITE_DYNAMIC_FILES[site]
    paths = {
        name: resolve_data_file(candidates, site, name)
        for name, candidates in file_config.items()
    }
    texts = {
        name: path.read_text(encoding="utf-8")
        for name, path in paths.items()
    }

    site_ml_serials = extract_serial_universe(texts["ml_summary"], "ML")
    site_hx_serials = extract_serial_universe(texts["hx_summary"], "HX")

    # Include every serial from the already-loaded timestamp tuples. This
    # guarantees that warning-only modules are recognized as belonging to the
    # correct institute even when a final summary page omits their serial.
    timestamp_hx_serials = {
        dynamic_normalize_serial(hx)
        for hx, _ml, _timestamp in institutes.get(site, [])
        if hx
    }
    timestamp_ml_serials = {
        dynamic_normalize_serial(ml)
        for _hx, ml, _timestamp in institutes.get(site, [])
        if ml
    }
    site_ml_serials |= timestamp_ml_serials
    site_hx_serials |= timestamp_hx_serials
    site_serials = site_ml_serials | site_hx_serials

    # Remove stale embedded entries belonging to this institute only. Entries
    # belonging to the other institutes remain until their own dynamic pass.
    for category_data in CATEGORY_DEFINITIONS.values():
        remove_serials_from_map(category_data["modules"], site_serials)
    remove_serials_from_map(ADDITIONAL_COMMENTS, site_serials)
    remove_serials_from_map(PROBLEM_WARNING_INFO, site_serials)

    iv_text = texts["iv_categories"]
    noise_text = texts["inputnoise_categories"]

    category_sources = {
        "Category A": normalized_comment_map(
            extract_python_assignment(iv_text, "category_a_comments")
        ),
        "Category B(i)": normalized_comment_map(
            extract_python_assignment(noise_text, "category_b_i_comments")
        ),
        "Category B(ii)": normalized_comment_map(
            extract_python_assignment(noise_text, "category_b_ii_comments")
        ),
        "Category C(i)": normalized_comment_map(
            extract_python_assignment(noise_text, "category_c_i_comments")
        ),
        "Category C(ii)": normalized_comment_map(
            extract_python_assignment(noise_text, "category_c_ii_comments")
        ),
        "Category D(i)": normalized_comment_map(
            extract_python_assignment(iv_text, "category_d_i_comments")
        ),
        "Category D(ii)": normalized_comment_map(
            extract_python_assignment(noise_text, "category_d_ii_comments")
        ),
        "Category E(i)": normalized_comment_map(
            extract_python_assignment(iv_text, "category_e_i_comments")
        ),
        "Category E(ii)": normalized_comment_map(
            extract_python_assignment(noise_text, "category_e_ii_comments")
        ),
    }

    # Final ML/HX pages are authoritative for full E populations and may also
    # contain the complete D(ii) mapping.
    category_sources["Category E(i)"].update(normalized_comment_map(
        extract_python_assignment(texts["ml_summary"], "category_e_i_comments")
    ))
    category_sources["Category E(ii)"].update(normalized_comment_map(
        extract_python_assignment(texts["hx_summary"], "category_e_ii_comments")
    ))
    category_sources["Category D(ii)"].update(normalized_comment_map(
        extract_python_assignment(texts["hx_summary"], "category_d_ii_comments")
    ))

    for category_name, modules in category_sources.items():
        CATEGORY_DEFINITIONS[category_name]["default"] = REQUESTED_CATEGORY_DEFAULTS[category_name]
        CATEGORY_DEFINITIONS[category_name]["modules"].update(modules)

    # Warnings are displayed and exported but do not replace official category
    # status. This includes IV yellow warnings and input-noise warning maps.
    warning_definitions = {
        "yellow_warning_comments": (
            "IV Warning",
            "IV warning below the Category A threshold.",
        ),
        "warning_b_i_comments": (
            "Category B(i) Warning",
            "Away-stream input noise above 1100 ENC in at least one channel.",
        ),
        "warning_b_ii_comments": (
            "Category B(ii) Warning",
            "Under-stream input noise above 1100 ENC in at least one channel.",
        ),
        "warning_c_i_comments": (
            "Category C(i) Warning",
            "Away-stream input noise below 600 ENC in at least one channel.",
        ),
        "warning_c_ii_comments": (
            "Category C(ii) Warning",
            "Under-stream input noise below 600 ENC in at least one channel.",
        ),
    }

    for variable_name, (warning_label, fallback_comment) in warning_definitions.items():
        source_text = iv_text if variable_name == "yellow_warning_comments" else noise_text
        warning_map = normalized_comment_map(
            extract_python_assignment(source_text, variable_name)
        )
        for serial, comment in warning_map.items():
            final_comment = comment or fallback_comment
            merge_problem_warning(serial, warning_label, final_comment)
            merge_additional_comment(serial, final_comment)

    counts = {
        category: len(modules)
        for category, modules in category_sources.items()
    }
    warning_count = sum(
        1 for serial in ADDITIONAL_COMMENTS
        if dynamic_normalize_serial(serial) in site_serials
    )

    print(f"Loaded dynamic {site} classifications:")
    print(f"  ML serial population: {len(site_ml_serials)}")
    print(f"  HX serial population: {len(site_hx_serials)}")
    for category_name in REQUESTED_CATEGORY_DEFAULTS:
        print(f"  {category_name}: {counts[category_name]}")
    print(f"  Modules with additional warnings: {warning_count}")
    for name, path in paths.items():
        print(f"  {name}: {path}")


def apply_dynamic_all_sites():
    for site in ("BNL", "LBNL", "UCSC"):
        apply_dynamic_site_categories(site)

apply_dynamic_all_sites()

# ============================================================
# Build status_info automatically from CATEGORY_DEFINITIONS
# ============================================================

status_info = {}


def normalize_serial(module):
    """
    Convert both serial formats to SN format.

    20USBHX2002099    -> SN20USBHX2002099
    SN20USBHX2002099 -> SN20USBHX2002099
    """
    if not module:
        return ""

    module = str(module).strip()

    if module.startswith("SN"):
        return module

    return "SN" + module


def strip_sn(module):
    """
    Convert SN format to no-SN format.

    SN20USBHX2002099 -> 20USBHX2002099
    """
    if not module:
        return ""

    module = str(module).strip()

    if module.startswith("SN"):
        return module[2:]

    return module


def get_module_message(modules, serial, default_message):
    """
    Looks up category messages using either SN or no-SN keys.
    This fixes Category C and mixed-key dictionaries.
    """
    serial_sn = normalize_serial(serial)
    serial_no_sn = strip_sn(serial)

    if serial_sn in modules:
        message = modules[serial_sn]
    elif serial_no_sn in modules:
        message = modules[serial_no_sn]
    else:
        message = default_message

    if message is None:
        message = default_message

    return message


def normalize_comments(value):
    """
    Prevents strings from being split character-by-character.

    Works for:
        "single comment"
        ["comment 1", "comment 2"]
    """
    if not value:
        return []

    if isinstance(value, list):
        return value

    return [value]


def build_status_info():
    for category_name, category_data in CATEGORY_DEFINITIONS.items():
        for module in category_data["modules"].keys():
            serial = normalize_serial(module)

            if serial:
                status_info.setdefault(serial, []).append(category_name)


build_status_info()


# ============================================================
# URL helpers
# ============================================================

def hx_url(site, hx):
    """
    Normal HX URL.
    Used for:
      - normal institute pages
      - combined histograms on problem pages
    """
    hx = normalize_serial(hx) if hx else ""
    return f"{BASE_URL}/{site}/HX/{hx}" if hx else ""


def hx2_url(site, hx):
    """
    HX2 URL.
    Used for skipped Input Noise PNG plots on problem pages.
    """
    hx = normalize_serial(hx) if hx else ""
    return f"{BASE_URL}/{site}/HX2/{hx}" if hx else ""


def hx3_url(site, hx):
    """
    HX3 URL.
    Used for no-skip Input Noise PNG plots on problem pages.
    """
    hx = normalize_serial(hx) if hx else ""
    return f"{BASE_URL}/{site}/HX3/{hx}" if hx else ""


def ml_url(site, ml):
    ml = normalize_serial(ml) if ml else ""
    return f"{BASE_URL}/{site}/ML/{ml}" if ml else ""



def ml3_url(site, ml):
    """ML3 URL used by regular institute pages."""
    ml = normalize_serial(ml) if ml else ""
    return f"{BASE_URL}/{site}/ML3/{ml}" if ml else ""


def ml2_url(site, ml):
    """ML2 URL used for Category A/D(i)/yellow-warning problem plots."""
    ml = normalize_serial(ml) if ml else ""
    return f"{BASE_URL}/{site}/ML2/{ml}" if ml else ""


# ============================================================
# Status helpers
# ============================================================

def get_status(hx, ml):
    notes = []

    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    if hx in status_info:
        notes.extend(status_info[hx])

    if ml in status_info:
        notes.extend(status_info[ml])

    if notes:
        return "❌", "<br>".join(notes)

    return "✅", "OK"


def format_status_notes(hx, ml):
    """
    Status notes for normal institute pages.
    Shows all categories, including Category E.
    """
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    icon, note = get_status(hx, ml)

    if icon == "✅":
        return "✅", '<div class="status-pass-box">✅ OK</div>'

    html_lines = []

    for category_name, category_data in CATEGORY_DEFINITIONS.items():
        serial_type = category_data["serial_type"]
        css_class = category_data["css_class"]
        default_message = category_data["default"]
        modules = category_data["modules"]

        serial = ml if serial_type == "ML" else hx

        if not serial:
            continue

        serial_sn = normalize_serial(serial)

        if serial_sn not in status_info:
            continue

        if category_name not in status_info[serial_sn]:
            continue

        message = get_module_message(modules, serial_sn, default_message)

        html_lines.append(
            f'<div class="status-error {css_class}">'
            f'❌ <strong>{category_name}:</strong> {message}'
            f'</div>'
        )

    if html_lines:
        return "❌", "\n".join(html_lines)

    return "❌", f'<div class="status-error">❌ {note}</div>'


def format_problem_status_notes(hx, ml):
    """
    Display official Category A–D classifications on problem pages.

    Category E is intentionally hidden from problem pages. Warning-only
    modules remain visible through the Additional Comments section.
    """
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    html_lines = []

    for category_name, category_data in CATEGORY_DEFINITIONS.items():
        if category_name.lower().startswith("category e"):
            continue

        serial = ml if category_data["serial_type"] == "ML" else hx
        if not serial:
            continue

        if category_name not in status_info.get(serial, []):
            continue

        message = get_module_message(
            category_data["modules"],
            serial,
            category_data["default"],
        )

        html_lines.append(
            f'<div class="status-error {category_data["css_class"]}">'
            f'❌ <strong>{category_name}:</strong> {message}'
            f'</div>'
        )

    if html_lines:
        return "❌", "\n".join(html_lines)

    return "⚠️", ""

def format_additional_comments(hx, ml):
    comments = []

    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    if hx in ADDITIONAL_COMMENTS:
        comments.extend(normalize_comments(ADDITIONAL_COMMENTS[hx]))

    if ml in ADDITIONAL_COMMENTS:
        comments.extend(normalize_comments(ADDITIONAL_COMMENTS[ml]))

    if not comments:
        return ""

    comment_lines = []

    for comment in comments:
        comment_lines.append(
            f'<div class="status-warning">⚠️ {comment}</div>'
        )

    return f"""
<div class="additional-comments-box">
  <div class="additional-comments-title">Additional comments</div>
  {''.join(comment_lines)}
</div>
"""



# ============================================================
# Problem-page local file checks
# ============================================================

def web_url_to_local_path(url):
    """
    Convert one website URL into the corresponding local repository path.
    """
    if not url:
        return None

    prefix = BASE_URL.rstrip("/") + "/"
    relative = url[len(prefix):] if url.startswith(prefix) else url.lstrip("/")
    return Path(relative)


def problem_file_exists(url):
    """
    Return True only when the problem-page file exists locally.

    This is intentionally used only for problem pages. Regular HX3 pages keep
    their existing behavior unchanged.
    """
    local_path = web_url_to_local_path(url)
    return bool(local_path and local_path.is_file())


def problem_plot_img(src, label):
    """Display a problem-page PNG only when the local file exists."""
    if not problem_file_exists(src):
        return ""
    return plot_img(src, label)


def problem_pdf_link(url, label):
    """Return a problem-page PDF link only when the local file exists."""
    if not problem_file_exists(url):
        return ""
    return f'<a href="{url}" target="_blank">{label}</a>'



def problem_file_link(url, label):
    """Return a problem-page link only when the local file exists."""
    if not problem_file_exists(url):
        return ""
    return f'<a href="{url}" target="_blank">{label}</a>'


def join_problem_sections(sections):
    """Join non-empty problem-page sections or return an em dash."""
    visible_sections = [section for section in sections if section and section.strip()]
    return "\n<br>\n".join(visible_sections) if visible_sections else ""


# ============================================================
# PNG image helper for separate problem/display pages
# ============================================================

def plot_img(src, label):
    """
    Display PNG image directly on webpage.
    No clickable link.
    """
    return f"""
<div class="plot-preview">
  <img src="{src}" alt="{label}">
</div>
"""



def local_web_file_path(url):
    """Resolve a website URL against the working directory or script folder."""
    if not url:
        return None

    prefix = BASE_URL.rstrip("/") + "/"
    relative = url[len(prefix):] if url.startswith(prefix) else url.lstrip("/")

    candidates = [
        Path(relative),
        Path(__file__).resolve().parent / relative,
    ]

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    return None


def local_web_file_exists(url):
    """Return True when a website asset exists in the local repository."""
    return local_web_file_path(url) is not None


def existing_plot_and_pdf(png_url, pdf_url, label):
    """Render an existing PNG and/or existing PDF link."""
    parts = []

    if local_web_file_exists(png_url):
        parts.append(plot_img(png_url, label))

    if local_web_file_exists(pdf_url):
        parts.append(
            f'<div class="plot-pdf-link">'
            f'<a href="{pdf_url}" target="_blank">Open {label} PDF</a>'
            f'</div>'
        )

    return "\n".join(parts)


def existing_pdf_only(pdf_url, label):
    """Render only an existing PDF link, with no PNG preview."""
    if not local_web_file_exists(pdf_url):
        return ""
    return (
        f'<div class="plot-pdf-link">'
        f'<a href="{pdf_url}" target="_blank">Open {label} PDF</a>'
        f'</div>'
    )


def existing_plot_sections(sections):
    """Join only non-empty plot sections."""
    return "\n<br>\n".join(
        section for section in sections
        if section and section.strip()
    )


# ============================================================
# Navigation and summary
# ============================================================

def nav():
    return """
<p>
  <a href="index.html">Home</a> |
  <a href="bnl.html">BNL</a> |
  <a href="lbnl.html">LBNL</a> |
  <a href="ucsc.html">UCSC</a> |
  <a href="bnlproblem.html">BNL Problems</a> |
  <a href="lbnlproblem.html">LBNL Problems</a> |
  <a href="ucscproblem.html">UCSC Problems</a>
</p>
"""


def category_summary():
    return """
<h2>Category Summary</h2>

<ul>
  <li><strong>Category A:</strong> IV current above 600 nA.</li>
  <li><strong>Category B(i):</strong> Away-stream input noise greater than 1100 ENC for 10 or more channels.</li>
  <li><strong>Category B(ii):</strong> Under-stream input noise greater than 1100 ENC for 10 or more channels.</li>
  <li><strong>Category C(i):</strong> Away-stream input noise less than 600 ENC for 10 or more channels.</li>
  <li><strong>Category C(ii):</strong> Under-stream input noise less than 600 ENC for 10 or more channels.</li>
  <li><strong>Category D(i):</strong> Incomplete IV dataset.</li>
  <li><strong>Category D(ii):</strong> Incomplete input-noise dataset.</li>
  <li><strong>Category E(i):</strong> IV data unavailable or could not be processed.</li>
  <li><strong>Category E(ii):</strong> Input-noise data unavailable or could not be processed.</li>
</ul>

<div class="additional-comments-legend">
  <strong>Yellow note:</strong> Additional module comments are shown when a module has useful notes that do not define a separate category.
</div>
"""


def search_controls(site, total):
    return f"""
<div class="controls">
  <input
    id="moduleSearch"
    type="text"
    onkeyup="filterRows()"
    placeholder="Search {site} serial, parent, status, category, timestamp, comment..."
  >

  <select id="statusFilter" onchange="filterRows()">
    <option value="all">All statuses</option>
    <option value="pass">Pass only</option>
    <option value="category a">Category A</option>
    <option value="category b(i)">Category B(i) — Away high input noise</option>
    <option value="category b(ii)">Category B(ii) — Under high input noise</option>
    <option value="category c(i)">Category C(i) — Away low input noise</option>
    <option value="category c(ii)">Category C(ii) — Under low input noise</option>
    <option value="category d(i)">Category D(i) — Incomplete IV dataset</option>
    <option value="category d(ii)">Category D(ii) — Incomplete input-noise dataset</option>
    <option value="category e(i)">Category E(i) — IV data unavailable</option>
    <option value="category e(ii)">Category E(ii) — Input-noise data unavailable</option>
    <option value="additional comments">Additional comments</option>
    <option value="comment">Has general comment</option>
    <option value="other">Other issues</option>
  </select>

  <div class="count-box">
    Showing <span id="visibleCount">{total}</span> of {total}
  </div>
</div>
"""


# ============================================================
# HTML shell
# ============================================================

def shell(title, body):
    return f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="UTF-8">
  <title>{title}</title>

  <style>
    body {{
      font-family: Arial, sans-serif;
      margin: 2rem;
      background: #fafafa;
      color: #212529;
    }}

    h1, h2 {{
      color: purple;
    }}

    table {{
      border-collapse: collapse;
      width: 100%;
      background: white;
    }}

    th, td {{
      border: 1px solid #ccc;
      padding: 8px;
      vertical-align: top;
    }}

    th {{
      background: #eee;
      position: sticky;
      top: 0;
      z-index: 1;
      text-align: center;
    }}

    a {{
      color: #0056b3;
    }}

    details > summary {{
      cursor: pointer;
      font-weight: bold;
      color: purple;
    }}

    ul {{
      margin-top: 0.25rem;
      padding-left: 1.25rem;
    }}

    .front-hero {{
      background: linear-gradient(135deg, #f4eaff, #ffffff);
      border: 1px solid #d7b7ff;
      border-radius: 22px;
      padding: 28px;
      margin-bottom: 28px;
      box-shadow: 0 3px 12px rgba(0, 0, 0, 0.06);
    }}

    .front-logo-grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 24px;
      margin: 28px 0;
    }}

    .front-logo-card {{
      background: white;
      border: 1px solid #d7b7ff;
      border-radius: 18px;
      padding: 24px;
      text-align: center;
      box-shadow: 0 3px 10px rgba(0, 0, 0, 0.08);
      transition: transform 0.15s ease, box-shadow 0.15s ease;
    }}

    .front-logo-card:hover {{
      transform: translateY(-3px);
      box-shadow: 0 6px 16px rgba(0, 0, 0, 0.12);
    }}

    .front-logo-card img {{
      max-width: 190px;
      max-height: 115px;
      object-fit: contain;
      margin-bottom: 16px;
    }}

    .front-button {{
      display: inline-block;
      background: purple;
      color: white;
      padding: 10px 18px;
      border-radius: 12px;
      text-decoration: none;
      font-weight: bold;
      border: 1px solid purple;
    }}

    .front-button:hover {{
      background: #5f0080;
      color: white;
      text-decoration: none;
    }}

    .controls {{
      display: flex;
      gap: 12px;
      align-items: center;
      margin: 20px 0;
      flex-wrap: wrap;
      background: #f4eaff;
      padding: 16px;
      border-radius: 16px;
      border: 1px solid #d7b7ff;
    }}

    .controls input,
    .controls select {{
      font-size: 16px;
      padding: 10px 14px;
      border-radius: 12px;
      border: 1px solid #ccc;
    }}

    .controls input {{
      min-width: 360px;
      flex: 1;
    }}

    .count-box {{
      font-weight: bold;
      color: purple;
      background: white;
      padding: 10px 14px;
      border-radius: 12px;
      border: 1px solid #d7b7ff;
    }}

    .status-pass {{
      color: green;
      font-weight: bold;
    }}

    .status-fail {{
      color: #b00020;
      font-weight: bold;
    }}

    .status-cell {{
      white-space: normal;
      min-width: 300px;
      max-width: 430px;
    }}

    .status-scroll {{
      max-height: 190px;
      overflow-y: auto;
      padding-right: 4px;
    }}

    .status-pass-box {{
      color: #1f7a3a;
      font-weight: bold;
      background: #eaf8ee;
      border: 1px solid #9bd3a8;
      border-radius: 8px;
      padding: 6px 8px;
    }}

    .status-error {{
      color: #8a0000;
      background: #ffecec;
      border: 1px solid #f3b3b3;
      border-radius: 8px;
      padding: 6px 8px;
      margin-bottom: 6px;
      font-weight: 600;
      line-height: 1.35;
    }}

    .category-a,
    .category-b,
    .category-c {{
      background: #ffecec;
      border-color: #f3b3b3;
      color: #8a0000;
    }}

    .category-d,
    .category-e {{
      background: #f3eaff;
      border-color: #c9a7ff;
      color: #4b0082;
    }}

    .additional-comments-box {{
      margin-top: 8px;
      background: #fff7d6;
      border: 1px solid #ffd966;
      border-radius: 8px;
      padding: 8px;
      color: #6b4e00;
      font-weight: 600;
    }}

    .additional-comments-title {{
      font-weight: bold;
      margin-bottom: 4px;
      color: #5c4500;
    }}

    .status-warning {{
      background: #fff9e6;
      border: 1px solid #ffe08a;
      border-radius: 6px;
      padding: 5px 7px;
      margin-top: 4px;
      line-height: 1.35;
    }}

    .additional-comments-legend {{
      background: #fff7d6;
      border: 1px solid #ffd966;
      border-radius: 10px;
      padding: 10px 12px;
      margin: 12px 0 20px 0;
      color: #6b4e00;
    }}

    .comment-box {{
      margin-top: 8px;
      background: #f8f9fa;
      border: 1px solid #ddd;
      border-radius: 8px;
      padding: 8px;
      color: #333;
      font-weight: normal;
    }}

    .details-cell {{
      min-width: 280px;
    }}

    .plot-preview {{
      margin-bottom: 14px;
      text-align: center;
    }}

    .plot-label {{
      font-weight: bold;
      margin-bottom: 5px;
      color: #333;
    }}

    .plot-preview img {{
      width: 360px;
      max-width: 100%;
      border: 1px solid #ccc;
      background: white;
    }}
  </style>

  <script>
    function normalizeText(text) {{
      return text.toLowerCase().replace(/\\s+/g, " ").trim();
    }}

    function filterRows() {{
      const searchInput = normalizeText(document.getElementById("moduleSearch").value);
      const filterValue = document.getElementById("statusFilter").value;
      const rows = document.querySelectorAll("tbody tr.module-row");

      let visibleCount = 0;

      rows.forEach(row => {{
        const rowText = normalizeText(row.innerText);
        const categoryText = row.getAttribute("data-category") || "";
        const statusText = row.getAttribute("data-status") || "";
        const hasComment = row.getAttribute("data-comment") === "yes";
        const hasAdditionalComments = row.getAttribute("data-additional-comments") === "yes";

        const matchesSearch = searchInput === "" || rowText.includes(searchInput);

        let matchesFilter = true;

        if (filterValue === "pass") {{
          matchesFilter = statusText === "pass";
        }} else if (filterValue === "comment") {{
          matchesFilter = hasComment;
        }} else if (filterValue === "additional comments") {{
          matchesFilter = hasAdditionalComments;
        }} else if (filterValue === "other") {{
          matchesFilter =
            statusText === "fail" &&
            !categoryText.includes("category a") &&
            !categoryText.includes("category b(i)") &&
            !categoryText.includes("category b(ii)") &&
            !categoryText.includes("category c(i)") &&
            !categoryText.includes("category c(ii)") &&
            !categoryText.includes("category d(i)") &&
            !categoryText.includes("category d(ii)") &&
            !categoryText.includes("category e(i)") &&
            !categoryText.includes("category e(ii)");
        }} else if (filterValue !== "all") {{
          matchesFilter = categoryText.includes(filterValue);
        }}

        if (matchesSearch && matchesFilter) {{
          row.style.display = "";
          visibleCount += 1;
        }} else {{
          row.style.display = "none";
        }}
      }});

      document.getElementById("visibleCount").innerText = visibleCount;
    }}

    window.addEventListener("DOMContentLoaded", filterRows);
  </script>
</head>

<body>
{nav()}
{body}
</body>
</html>
"""


# ============================================================
# Normal table blocks
# Normal pages keep PDF links and Detailed Histograms.
# ============================================================

def detailed_histograms_block(hx_base, hx, check_exists=False):
    """
    Build detailed-histogram PNG previews, PDF links, and per-run JSON links.

    The regular pages pass an HX3 module URL, so every existing detailed PNG
    is displayed directly and every matching PDF is linked. Problem pages can
    still request existence checking for their selected HX directory.
    """
    hx = normalize_serial(hx) if hx else ""

    if not hx:
        return ""

    run_sections = []

    def render_plot(stem_url, label):
        png_url = f"{stem_url}.png"
        pdf_url = f"{stem_url}.pdf"

        if check_exists:
            return existing_plot_and_pdf(png_url, pdf_url, label)

        return (
            plot_img(png_url, label)
            + f'<div class="plot-pdf-link"><a href="{pdf_url}" '
              f'target="_blank">Open {label} PDF</a></div>'
        )

    for run in range(1, 26):
        run_str = f"{run:02}"
        run_items = []

        away_stem = (
            f"{hx_base}/detailedhistograms/"
            f"{hx}_{run_str}_combined_innse_away"
        )
        under_stem = (
            f"{hx_base}/detailedhistograms/"
            f"{hx}_{run_str}_combined_innse_under"
        )
        json_url = (
            f"{hx_base}/detailedhistograms/"
            f"{hx}_{run_str}_low_high_values.json"
        )

        combined_sections = existing_plot_sections([
            render_plot(away_stem, f"Run {run_str} Away combined"),
            render_plot(under_stem, f"Run {run_str} Under combined"),
        ])
        if combined_sections:
            run_items.append(combined_sections)

        if check_exists:
            json_link = problem_file_link(json_url, "Low/High JSON")
        else:
            json_link = f'<a href="{json_url}" target="_blank">Low/High JSON</a>'

        if json_link:
            run_items.append(
                f'<div class="plot-pdf-link">{json_link}</div>'
            )

        channel_sections = []
        for channel in range(10):
            away_channel_stem = (
                f"{hx_base}/detailedhistograms/"
                f"{hx}_{run_str}_innse_away_{channel}"
            )
            under_channel_stem = (
                f"{hx_base}/detailedhistograms/"
                f"{hx}_{run_str}_innse_under_{channel}"
            )

            channel_html = existing_plot_sections([
                render_plot(
                    away_channel_stem,
                    f"Run {run_str} Away channel {channel}",
                ),
                render_plot(
                    under_channel_stem,
                    f"Run {run_str} Under channel {channel}",
                ),
            ])

            if channel_html:
                channel_sections.append(
                    f'<details class="channel-details">'
                    f'<summary>Channel {channel}</summary>{channel_html}</details>'
                )

        if channel_sections:
            run_items.append("".join(channel_sections))

        if run_items:
            run_sections.append(
                f'<details class="run-details">'
                f'<summary>Test Run {run_str}</summary>'
                + "".join(run_items)
                + '</details>'
            )

    if not run_sections:
        return ""

    return (
        '<details><summary>View All 25 Detailed Histogram Runs</summary>'
        + "".join(run_sections)
        + '</details>'
    )


def module_row(i, site, hx, ml, timestamp):
    """
    Regular institute-page row.

    Uses HX3 and ML3 for all regular-page plots. Every existing PNG is
    displayed directly and every matching PDF is linked. HX2 remains only as
    a fallback source for older combined low/high JSON files.
    """
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    hx_base = hx3_url(site, hx)
    hx2_base = hx2_url(site, hx)
    ml_base = ml3_url(site, ml)
    timestamp = timestamp or ""

    icon, note = get_status(hx, ml)
    status_class = "status-pass" if icon == "✅" else "status-fail"
    data_status = "pass" if icon == "✅" else "fail"

    _status_icon, status_html = format_status_notes(hx, ml)
    additional_comments_html = format_additional_comments(hx, ml)
    has_additional_comments = "yes" if additional_comments_html else "no"

    data_category = note.replace("<br>", " ").lower()
    if additional_comments_html:
        data_category += " additional comments"

    comment = (
        module_comments.get(hx)
        or module_comments.get(strip_sn(hx))
        or module_comments.get(ml)
        or module_comments.get(strip_sn(ml))
    )
    comment_html = f'<div class="comment-box">{comment}</div>' if comment else ""
    data_comment = "yes" if comment else "no"

    input_noise_html = ""
    combined_html = ""
    iv_html = ""

    if hx:
        away_input = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/inputnoise/{hx}-away.png",
                f"{hx_base}/inputnoise/{hx}-away.pdf",
                "Away",
            ),
            existing_pdf_only(
                f"{hx_base}/inputnoise_noskip/{hx}-away.pdf",
                "No Skip Away",
            ),
        ])

        under_input = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/inputnoise/{hx}-under.png",
                f"{hx_base}/inputnoise/{hx}-under.pdf",
                "Under",
            ),
            existing_pdf_only(
                f"{hx_base}/inputnoise_noskip/{hx}-under.pdf",
                "No Skip Under",
            ),
        ])

        sections = []
        if away_input:
            sections.append(away_input)
        if under_input:
            sections.append(under_input)
        input_noise_html = existing_plot_sections(sections)

        away_combined = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/histograms_combined/{hx}_combined-away.png",
                f"{hx_base}/histograms_combined/{hx}_combined-away.pdf",
                "Away",
            ),
            existing_pdf_only(
                f"{hx_base}/histograms_combined_noskip/{hx}_combined-away.pdf",
                "No Skip Away",
            ),
        ])

        under_combined = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/histograms_combined/{hx}_combined-under.png",
                f"{hx_base}/histograms_combined/{hx}_combined-under.pdf",
                "Under",
            ),
            existing_pdf_only(
                f"{hx_base}/histograms_combined_noskip/{hx}_combined-under.pdf",
                "No Skip Under",
            ),
        ])

        # Prefer regular-page HX3 JSON files.
        away_json = problem_file_link(
            (
                f"{hx_base}/histograms_combined_noskip/"
                f"{hx}_away_low_below600_high_above1100.json"
            ),
            "Away Low/High JSON",
        )
        under_json = problem_file_link(
            (
                f"{hx_base}/histograms_combined_noskip/"
                f"{hx}_under_low_below600_high_above1100.json"
            ),
            "Under Low/High JSON",
        )

        # Support older JSON filenames as a fallback.
        if not away_json:
            away_json = problem_file_link(
                (
                    f"{hx2_base}/histograms_combined_noskip/"
                    f"{hx}_away_low_high_values.json"
                ),
                "Away Low/High JSON",
            )

        if not under_json:
            under_json = problem_file_link(
                (
                    f"{hx2_base}/histograms_combined_noskip/"
                    f"{hx}_under_low_high_values.json"
                ),
                "Under Low/High JSON",
            )

        if away_json:
            away_combined = existing_plot_sections([
                away_combined,
                f'<div class="plot-pdf-link">{away_json}</div>',
            ])

        if under_json:
            under_combined = existing_plot_sections([
                under_combined,
                f'<div class="plot-pdf-link">{under_json}</div>',
            ])

        sections = []
        if away_combined:
            sections.append(away_combined)
        if under_combined:
            sections.append(under_combined)
        combined_html = existing_plot_sections(sections)

    if ml:
        iv_html = existing_plot_and_pdf(
            f"{ml_base}/IV/{ml}.png",
            f"{ml_base}/IV/{ml}.pdf",
            "IV",
        )

    return f"""
<tr class="module-row"
    data-status="{data_status}"
    data-category="{data_category}"
    data-comment="{data_comment}"
    data-additional-comments="{has_additional_comments}">
  <td>{i}</td>
  <td>{hx}</td>
  <td>{ml}</td>
  <td>{timestamp}</td>
  <td>{input_noise_html}</td>
  <td>{iv_html}</td>
  <td>{combined_html}</td>
  <td class="{status_class} status-cell">
    <div class="status-scroll">
      {status_html}
      {additional_comments_html}
      {comment_html}
    </div>
  </td>
</tr>
"""

def is_category_abcd(category_name):
    category_name = category_name.lower()

    return (
        category_name.startswith("category a")
        or category_name.startswith("category b")
        or category_name.startswith("category c")
        or category_name.startswith("category d")
    )


def has_problem_or_additional_comment(hx, ml):
    """
    Include a module on a problem page when it has:

      - an official Category A, B, C, D, or E classification;
      - an IV or input-noise warning;
      - or an additional/general problem comment.
    """
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    official_categories = categories_for_pair(hx, ml)

    return bool(
        official_categories
        or PROBLEM_WARNING_INFO.get(hx)
        or PROBLEM_WARNING_INFO.get(ml)
        or ADDITIONAL_COMMENTS.get(hx)
        or ADDITIONAL_COMMENTS.get(ml)
        or module_comments.get(hx)
        or module_comments.get(strip_sn(hx))
        or module_comments.get(ml)
        or module_comments.get(strip_sn(ml))
    )


def get_problem_data_category(hx, ml, has_additional_comments):
    """
    Build filter metadata for Category A–E and warning-only modules.
    """
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    categories = []

    for serial in (hx, ml):
        categories.extend(
            category.lower()
            for category in status_info.get(serial, [])
        )

        for warning in PROBLEM_WARNING_INFO.get(serial, []):
            label = warning.get("label", "")
            if not label:
                continue

            categories.append("additional comments")

            base_match = re.match(
                r"(Category [BC]\([iv]+\))",
                label,
                re.IGNORECASE,
            )
            if base_match:
                categories.append(base_match.group(1).lower())

            if label.lower().startswith("iv warning"):
                categories.append("category a")

    if has_additional_comments:
        categories.append("additional comments")

    return " ".join(dict.fromkeys(categories))


def problem_module_row(i, site, hx, ml, timestamp):
    """
    Problem-page row.

    Uses HX2 and ML2. Only existing PNG images and PDF links are displayed.
    """
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    hx_base = hx2_url(site, hx)
    ml_base = ml2_url(site, ml)
    timestamp = timestamp or ""

    status_class = "status-fail"
    data_status = "fail"

    _status_icon, status_html = format_problem_status_notes(hx, ml)
    additional_comments_html = format_additional_comments(hx, ml)
    has_additional_comments = "yes" if additional_comments_html else "no"

    data_category = get_problem_data_category(
        hx,
        ml,
        additional_comments_html != "",
    )

    comment = (
        module_comments.get(hx)
        or module_comments.get(strip_sn(hx))
        or module_comments.get(ml)
        or module_comments.get(strip_sn(ml))
    )
    comment_html = f'<div class="comment-box">{comment}</div>' if comment else ""
    data_comment = "yes" if comment else "no"

    input_noise_html = ""
    combined_html = ""
    detailed_html = ""
    iv_html = ""

    if hx:
        away_input = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/inputnoise/{hx}-away.png",
                f"{hx_base}/inputnoise/{hx}-away.pdf",
                "Away",
            ),
            existing_pdf_only(
                f"{hx_base}/inputnoise_noskip/{hx}-away.pdf",
                "No Skip Away",
            ),
        ])

        under_input = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/inputnoise/{hx}-under.png",
                f"{hx_base}/inputnoise/{hx}-under.pdf",
                "Under",
            ),
            existing_pdf_only(
                f"{hx_base}/inputnoise_noskip/{hx}-under.pdf",
                "No Skip Under",
            ),
        ])

        sections = []
        if away_input:
            sections.append(away_input)
        if under_input:
            sections.append(under_input)
        input_noise_html = existing_plot_sections(sections)

        away_combined = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/histograms_combined/{hx}_combined-away.png",
                f"{hx_base}/histograms_combined/{hx}_combined-away.pdf",
                "Away",
            ),
            existing_pdf_only(
                f"{hx_base}/histograms_combined_noskip/{hx}_combined-away.pdf",
                "No Skip Away",
            ),
        ])

        under_combined = existing_plot_sections([
            existing_plot_and_pdf(
                f"{hx_base}/histograms_combined/{hx}_combined-under.png",
                f"{hx_base}/histograms_combined/{hx}_combined-under.pdf",
                "Under",
            ),
            existing_pdf_only(
                f"{hx_base}/histograms_combined_noskip/{hx}_combined-under.pdf",
                "No Skip Under",
            ),
        ])

        away_json = problem_file_link(
            (
                f"{hx_base}/histograms_combined_noskip/"
                f"{hx}_away_low_below600_high_above1100.json"
            ),
            "Away Low/High JSON",
        )
        under_json = problem_file_link(
            (
                f"{hx_base}/histograms_combined_noskip/"
                f"{hx}_under_low_below600_high_above1100.json"
            ),
            "Under Low/High JSON",
        )

        if not away_json:
            away_json = problem_file_link(
                (
                    f"{hx_base}/histograms_combined_noskip/"
                    f"{hx}_away_low_high_values.json"
                ),
                "Away Low/High JSON",
            )

        if not under_json:
            under_json = problem_file_link(
                (
                    f"{hx_base}/histograms_combined_noskip/"
                    f"{hx}_under_low_high_values.json"
                ),
                "Under Low/High JSON",
            )

        if away_json:
            away_combined = existing_plot_sections([
                away_combined,
                f'<div class="plot-pdf-link">{away_json}</div>',
            ])

        if under_json:
            under_combined = existing_plot_sections([
                under_combined,
                f'<div class="plot-pdf-link">{under_json}</div>',
            ])

        sections = []
        if away_combined:
            sections.append(away_combined)
        if under_combined:
            sections.append(under_combined)
        combined_html = existing_plot_sections(sections)

        detailed_html = detailed_histograms_block(
            hx_base,
            hx,
            check_exists=True,
        )

    if ml:
        iv_html = existing_plot_and_pdf(
            f"{ml_base}/IV/{ml}.png",
            f"{ml_base}/IV/{ml}.pdf",
            "IV",
        )

    return f"""
<tr class="module-row"
    data-status="{data_status}"
    data-category="{data_category}"
    data-comment="{data_comment}"
    data-additional-comments="{has_additional_comments}">
  <td>{i}</td>
  <td>{hx}</td>
  <td>{ml}</td>
  <td>{timestamp}</td>
  <td>{input_noise_html}</td>
  <td>{iv_html}</td>
  <td>{combined_html}</td>
  <td class="details-cell">{detailed_html}</td>
  <td class="{status_class} status-cell">
    <div class="status-scroll">
      {status_html}
      {additional_comments_html}
      {comment_html}
    </div>
  </td>
</tr>
"""


def categories_for_pair(hx, ml):
    """Return normalized category labels attached to either HX or ML serial."""
    hx = normalize_serial(hx) if hx else ""
    ml = normalize_serial(ml) if ml else ""

    categories = []

    for serial in (hx, ml):
        categories.extend(
            str(category).strip()
            for category in status_info.get(serial, [])
            if str(category).strip()
        )

    return categories


def pair_has_category_e(hx, ml):
    """Return True when either serial has Category E(i) or Category E(ii)."""
    return any(
        category.lower().startswith("category e")
        for category in categories_for_pair(hx, ml)
    )


def serial_numeric_key(serial):
    """
    Sort SN20USBHX/SN20USBML serials by their numeric suffix.

    This keeps serials such as SN20USBHX2003653 immediately before
    SN20USBHX2003654.
    """
    serial = normalize_serial(serial) if serial else ""
    match = re.search(r"(\d+)$", serial)

    if match:
        return (0, int(match.group(1)), serial)

    return (1, float("inf"), serial)


def module_pair_sort_key(pair):
    """
    Shared ordering for regular and problem pages:

      1. non-Category-E rows first;
      2. Category E rows at the bottom;
      3. HX serials in ascending numeric order;
      4. ML-only rows in ascending numeric order.
    """
    hx, ml, timestamp = pair
    category_e_rank = 1 if pair_has_category_e(hx, ml) else 0

    if hx:
        serial_group = 0
        serial_key = serial_numeric_key(hx)
    else:
        serial_group = 1
        serial_key = serial_numeric_key(ml)

    return (
        category_e_rank,
        serial_group,
        serial_key,
        normalize_serial(ml) if ml else "",
        str(timestamp or ""),
    )


def valid_module_pair(hx, ml, timestamp):
    """Reject documentation/example rows from generated HTML."""
    hx_text = str(hx or "").strip()
    ml_text = str(ml or "").strip()
    timestamp_text = str(timestamp or "").strip()

    return not (
        "..." in hx_text
        or "..." in ml_text
        or timestamp_text.upper().startswith("YYYY-")
        or (not hx_text and not ml_text)
    )




def discover_ml3_iv_modules(site):
    """
    Discover every ML module with an IV PNG or PDF saved under SITE/ML3.

    Expected layouts:
      SITE/ML3/SN20USBML.../IV/SN20USBML....png
      SITE/ML3/SN20USBML.../IV/SN20USBML....pdf
    """
    ml3_root = Path(site) / "ML3"
    discovered = set()

    if not ml3_root.is_dir():
        return discovered

    for module_dir in ml3_root.glob("SN20USBML*"):
        if not module_dir.is_dir():
            continue

        serial = normalize_serial(module_dir.name)
        iv_dir = module_dir / "IV"

        if (
            (iv_dir / f"{serial}.png").is_file()
            or (iv_dir / f"{serial}.pdf").is_file()
        ):
            discovered.add(serial)

    return discovered


def augment_regular_pairs_with_ml3(site, pairs):
    """
    Add every ML3 IV module to the regular-page pair list.

    Existing HX/ML/timestamp pairs are preserved. An ML3 module that is not in
    the timestamp list is added as an ML-only row with a blank HX and timestamp.
    """
    visible_pairs = [
        (hx, ml, timestamp)
        for hx, ml, timestamp in pairs
        if valid_module_pair(hx, ml, timestamp)
    ]

    known_ml = {
        normalize_serial(ml)
        for _hx, ml, _timestamp in visible_pairs
        if ml
    }

    missing_ml3_modules = sorted(
        discover_ml3_iv_modules(site) - known_ml
    )

    visible_pairs.extend(
        ("", ml, "")
        for ml in missing_ml3_modules
    )

    return visible_pairs


def build_site_page(site, pairs):
    # Include every existing ML3 IV plot, even when its serial is absent from
    # the formatted timestamp list.
    visible_pairs = augment_regular_pairs_with_ml3(site, pairs)
    visible_pairs = sorted(
        visible_pairs,
        key=module_pair_sort_key,
    )

    rows = "\n".join(
        module_row(i, site, hx, ml, timestamp)
        for i, (hx, ml, timestamp) in enumerate(visible_pairs, start=1)
    )

    body = f"""
<h1>{site} Modules</h1>

{category_summary()}

<p>
  Regular plots are displayed from HX3 and ML3. Combined-histogram low/high
  JSON links are displayed from HX2. Missing files are omitted.
</p>

<p>Total module pairs / ML3 IV modules: <strong>{len(visible_pairs)}</strong></p>

{search_controls(site, len(visible_pairs))}

<table>
  <thead>
    <tr>
      <th>#</th>
      <th>HX Serial</th>
      <th>ML Parent</th>
      <th>Timestamp</th>
      <th>Input Noise</th>
      <th>IV Plot</th>
      <th>Combined Histograms</th>
      <th>Status / Notes</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
"""

    return shell(f"{site} Modules", body)

def build_problem_site_page(site, pairs):
    problem_pairs = [
        (hx, ml, timestamp)
        for hx, ml, timestamp in pairs
        if valid_module_pair(hx, ml, timestamp)
        and has_problem_or_additional_comment(hx, ml)
    ]
    problem_pairs = sorted(
        problem_pairs,
        key=module_pair_sort_key,
    )

    rows = "\n".join(
        problem_module_row(i, site, hx, ml, timestamp)
        for i, (hx, ml, timestamp) in enumerate(problem_pairs, start=1)
    )

    body = f"""
<h1>{site} Problematic Modules</h1>

{category_summary()}

<p>
  Existing PNG, PDF, JSON, and CSV files are displayed from HX2 and ML2.
  Missing files are omitted.
</p>

<p>Problematic / commented module pairs: <strong>{len(problem_pairs)}</strong></p>

{search_controls(site, len(problem_pairs))}

<table>
  <thead>
    <tr>
      <th>#</th>
      <th>HX Serial</th>
      <th>ML Parent</th>
      <th>Timestamp</th>
      <th>Input Noise</th>
      <th>IV Plot</th>
      <th>Combined Histograms</th>
      <th>Detailed Histograms / JSON</th>
      <th>Status / Notes</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>
"""

    return shell(f"{site} Problematic Modules", body)

def build_home_page():
    total = sum(len(pairs) for pairs in institutes.values())

    logo_cards = "\n".join(
        f"""
        <div class="front-logo-card">
          <a href="{page_names[site]}">
            <img src="{logo_files.get(site, '')}" alt="{site} logo">
          </a>

          <h2>{site}</h2>

          <p>{len(pairs)} module pairs</p>

          <a class="front-button" href="{page_names[site]}">
            Open {site} Page
          </a>

          <br><br>

          <a class="front-button" href="{problem_page_names[site]}">
            Open {site} Problems
          </a>
        </div>
        """
        for site, pairs in institutes.items()
    )

    body = f"""
<div class="front-hero">
  <h1>ATLAS ITk Strip Modules – NYU Contributions</h1>
  <p><strong>Maintained by:</strong> Amelia Stevens, CERN username: ameliame</p>
  <p>This webpage displays IV and input-noise results for silicon strip detector modules.</p>
  <p>Total module pairs: <strong>{total}</strong></p>
</div>

<h2>Institute Pages</h2>

<div class="front-logo-grid">
{logo_cards}
</div>

{category_summary()}
"""

    return shell("ATLAS ITk Strip Modules", body)


# ============================================================
# Copy homepage logo files
# ============================================================

def copy_logo_files(out_dir):
    """
    Copies bnl.png, lbnl.png, scipp.png into categories_website/
    if they exist in the current script directory.

    If they are already inside categories_website/, no action is needed.
    """
    for site, filename in logo_files.items():
        src = Path(filename)
        dst = out_dir / filename

        if dst.exists():
            print(f"✅ Found logo already in output folder: {dst}")
            continue

        if src.exists():
            shutil.copy(src, dst)
            print(f"✅ Copied logo: {src} -> {dst}")
        else:
            print(f"⚠️ Missing logo for {site}: expected {filename}")
            print(f"   Put it here: {dst}")


# ============================================================
# Main
# ============================================================

def main():
    out_dir = Path("categories_website")
    out_dir.mkdir(exist_ok=True)

    copy_logo_files(out_dir)

    all_rows = []

    for site, pairs in institutes.items():
        for hx, ml, timestamp in pairs:
            hx = normalize_serial(hx) if hx else ""
            ml = normalize_serial(ml) if ml else ""

            icon, note = get_status(hx, ml)

            comment = (
                module_comments.get(hx)
                or module_comments.get(strip_sn(hx))
                or module_comments.get(ml)
                or module_comments.get(strip_sn(ml))
                or ""
            )

            additional_comments = []

            if hx in ADDITIONAL_COMMENTS:
                additional_comments.extend(normalize_comments(ADDITIONAL_COMMENTS[hx]))

            if ml in ADDITIONAL_COMMENTS:
                additional_comments.extend(normalize_comments(ADDITIONAL_COMMENTS[ml]))

            additional_comment = "; ".join(additional_comments)

            all_rows.append({
                "institute": site,
                "serial": hx,
                "parent": ml,
                "timestamp": timestamp,
                "status": note.replace("<br>", "; "),
                "status_icon": icon,
                "comment": comment,
                "additional_comment": additional_comment,

                # Regular-page PDF paths use HX3
                "input_noise_away_pdf": f"{hx3_url(site, hx)}/inputnoise/{hx}-away.pdf" if hx else "",
                "input_noise_under_pdf": f"{hx3_url(site, hx)}/inputnoise/{hx}-under.pdf" if hx else "",
                "input_noise_noskip_away_pdf": f"{hx3_url(site, hx)}/inputnoise_noskip/{hx}-away.pdf" if hx else "",
                "input_noise_noskip_under_pdf": f"{hx3_url(site, hx)}/inputnoise_noskip/{hx}-under.pdf" if hx else "",
                "iv_pdf": f"{ml3_url(site, ml)}/IV/{ml}.pdf" if ml else "",
                "combined_away_pdf": f"{hx3_url(site, hx)}/histograms_combined/{hx}_combined-away.pdf" if hx else "",
                "combined_under_pdf": f"{hx3_url(site, hx)}/histograms_combined/{hx}_combined-under.pdf" if hx else "",
                "combined_noskip_away_pdf": f"{hx3_url(site, hx)}/histograms_combined_noskip/{hx}_combined-away.pdf" if hx else "",
                "combined_noskip_under_pdf": f"{hx3_url(site, hx)}/histograms_combined_noskip/{hx}_combined-under.pdf" if hx else "",

                # Problem/display PNG paths
                # Problem input-noise PNG paths use HX2
                "input_noise_away_png": f"{hx2_url(site, hx)}/inputnoise/{hx}-away.png" if hx else "",
                "input_noise_under_png": f"{hx2_url(site, hx)}/inputnoise/{hx}-under.png" if hx else "",
                "input_noise_noskip_away_png": f"{hx2_url(site, hx)}/inputnoise_noskip/{hx}-away.png" if hx else "",
                "input_noise_noskip_under_png": f"{hx2_url(site, hx)}/inputnoise_noskip/{hx}-under.png" if hx else "",

                # Problem combined-histogram PNG paths use HX2
                "combined_away_png": f"{hx2_url(site, hx)}/histograms_combined/{hx}_combined-away.png" if hx else "",
                "combined_under_png": f"{hx2_url(site, hx)}/histograms_combined/{hx}_combined-under.png" if hx else "",
                "combined_noskip_away_png": f"{hx2_url(site, hx)}/histograms_combined_noskip/{hx}_combined-away.png" if hx else "",
                "combined_noskip_under_png": f"{hx2_url(site, hx)}/histograms_combined_noskip/{hx}_combined-under.png" if hx else "",

                "iv_png": f"{ml2_url(site, ml)}/IV/{ml}.png" if ml else "",

                "json_away_skipped": f"{hx3_url(site, hx)}/histograms_combined_noskip/{hx}_away_low_high_values.json" if hx else "",
                "json_under_skipped": f"{hx3_url(site, hx)}/histograms_combined_noskip/{hx}_under_low_high_values.json" if hx else "",
                "detailed_histograms_base": f"{hx3_url(site, hx)}/detailedhistograms" if hx else "",
            })

    with open(out_dir / "serial_parent_map.json", "w", encoding="utf-8") as f:
        json.dump(all_rows, f, indent=2)

    with open(out_dir / "serial_parent_map.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)

        writer.writerow([
            "institute",
            "serial",
            "parent",
            "timestamp",
            "status",
            "status_icon",
            "comment",
            "additional_comment",

            "input_noise_away_pdf",
            "input_noise_under_pdf",
            "input_noise_noskip_away_pdf",
            "input_noise_noskip_under_pdf",
            "iv_pdf",
            "combined_away_pdf",
            "combined_under_pdf",
            "combined_noskip_away_pdf",
            "combined_noskip_under_pdf",

            "input_noise_away_png",
            "input_noise_under_png",
            "input_noise_noskip_away_png",
            "input_noise_noskip_under_png",
            "combined_away_png",
            "combined_under_png",
            "combined_noskip_away_png",
            "combined_noskip_under_png",
            "iv_png",

            "json_away_skipped",
            "json_under_skipped",
            "detailed_histograms_base",
        ])

        for row in all_rows:
            writer.writerow([
                row["institute"],
                row["serial"],
                row["parent"],
                row["timestamp"],
                row["status"],
                row["status_icon"],
                row["comment"],
                row["additional_comment"],

                row["input_noise_away_pdf"],
                row["input_noise_under_pdf"],
                row["input_noise_noskip_away_pdf"],
                row["input_noise_noskip_under_pdf"],
                row["iv_pdf"],
                row["combined_away_pdf"],
                row["combined_under_pdf"],
                row["combined_noskip_away_pdf"],
                row["combined_noskip_under_pdf"],

                row["input_noise_away_png"],
                row["input_noise_under_png"],
                row["input_noise_noskip_away_png"],
                row["input_noise_noskip_under_png"],
                row["combined_away_png"],
                row["combined_under_png"],
                row["combined_noskip_away_png"],
                row["combined_noskip_under_png"],
                row["iv_png"],

                row["json_away_skipped"],
                row["json_under_skipped"],
                row["detailed_histograms_base"],
            ])

    home_html = build_home_page()
    (out_dir / "index.html").write_text(home_html, encoding="utf-8")

    # Write original normal institute pages
    for site, pairs in institutes.items():
        html = build_site_page(site, pairs)
        (out_dir / page_names[site]).write_text(html, encoding="utf-8")

    # Write separate problem/display pages
    for site, pairs in institutes.items():
        problem_html = build_problem_site_page(site, pairs)
        (out_dir / problem_page_names[site]).write_text(problem_html, encoding="utf-8")

    with open(out_dir / "index.html.json", "w", encoding="utf-8") as f:
        json.dump({"html": home_html}, f, indent=2)

    print(f"✅ Wrote files to: {out_dir}/")
    print("✅ Wrote serial_parent_map.json")
    print("✅ Wrote serial_parent_map.csv")
    print("✅ Wrote index.html")
    print("✅ Wrote bnl.html")
    print("✅ Wrote lbnl.html")
    print("✅ Wrote ucsc.html")
    print("✅ Wrote bnlproblem.html")
    print("✅ Wrote lbnlproblem.html")
    print("✅ Wrote ucscproblem.html")
    print("✅ Wrote index.html.json")
    print("")
    print("✅ Original pages were kept.")
    print("✅ Separate problem/display pages were created.")
    print("✅ Problem pages include Category A–D modules and warning comments; Category E-only modules are excluded.")
    print("✅ Warning modules with even one channel outside 600–1100 ENC are included once under Additional Comments.")
    print("✅ Problem pages display PNG images directly.")
    print("")
    print("✅ Problem page HX2 PNG paths:")
    print("   BNL/HX2/SN.../inputnoise/*.png")
    print("   BNL/HX2/SN.../inputnoise_noskip/*.png")
    print("   LBNL/HX2/SN.../inputnoise/*.png")
    print("   LBNL/HX2/SN.../inputnoise_noskip/*.png")
    print("   UCSC/HX2/SN.../inputnoise/*.png")
    print("   UCSC/HX2/SN.../inputnoise_noskip/*.png")
    print("")
    print("✅ Problem page Combined Histogram PNG paths:")
    print("   BNL/HX2/SN.../histograms_combined/*.png")
    print("   BNL/HX2/SN.../histograms_combined_noskip/*.png")
    print("   LBNL/HX2/SN.../histograms_combined/*.png")
    print("   LBNL/HX2/SN.../histograms_combined_noskip/*.png")
    print("   UCSC/HX2/SN.../histograms_combined/*.png")
    print("   UCSC/HX2/SN.../histograms_combined_noskip/*.png")
    print("")
    print("✅ Problem page IV PNG paths:")
    print("   BNL/ML2/SN.../IV/*.png")
    print("   LBNL/ML2/SN.../IV/*.png")
    print("   UCSC/ML2/SN.../IV/*.png")
    print("")
    print("✅ Problem pages do not include the Detailed Histograms column.")
    print("")
    print("Logo image files expected:")
    print(f"   {out_dir}/bnl.png")
    print(f"   {out_dir}/lbnl.png")
    print(f"   {out_dir}/scipp.png")


if __name__ == "__main__":
    main()