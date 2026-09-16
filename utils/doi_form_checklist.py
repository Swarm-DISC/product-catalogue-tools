"""Per-record checklist for ESA's "Request the update of DOI data (Datacite)" form.

Writes ``<html_directory>/doi-checklist/``: an ``index.html`` plus one page per
catalogue record, listing the form's fields in form order with values taken
from the catalogue, so they are copied rather than retyped. Each record page
also embeds the DataCite JSON from ``utils.datacite``.

Values come from the catalogue only; there are no live DataCite calls, so the
build stays offline. The pages are complete HTML documents with inline CSS/JS
and no CDN dependencies.

Run from the repository root with::

    uv run python -m utils.doi_form_checklist [html_directory]
"""

from datetime import datetime, timezone
from html import escape, unescape
from io import StringIO
import json
import os
import re
import subprocess

from markdown import markdown
import pandas as pd

from .catalog_utils import _get_catalogue_repo_path, load_catalog
from .datacite import CONTRIBUTORS, ESA_ROR, VERSION, doi_identifier, product_to_datacite
from .schema_org import LANDING_PAGE_BASE, PUBLISHER

REPO_ROOT = os.path.join(os.path.dirname(__file__), "..")
DATA_POLICY_URL = "https://earth.esa.int/eogateway/documents/20142/1564626/Terms-and-Conditions-for-the-use-of-ESA-Data.pdf"
SOURCE_DOCUMENTS = ["datacite_metadata_issues.md", "schema_org_handoff.md"]
LEAVE_BLANK = "leave blank"
MAX_PREFILL_FORMAT_LENGTH = 40

# Values that are identical on every record's form.
CONSTANT_FIELDS = [
    ("Version / Baseline", VERSION),
    ("Contributors", CONTRIBUTORS[0]["name"]),
    ("Creators", PUBLISHER["name"]),
    ("Publisher", PUBLISHER["name"]),
]

# Issues in the *registered* DataCite records. They cannot be derived from the
# catalogue; transcribed from datacite_metadata_issues.md §3 and §4.
_DESCRIPTION_BOTH_PLACES = (
    " The same text is registered in both descriptions[SeriesInformation] and"
    " container.title."
)
KNOWN_ISSUES = {
    "SW_MLI_SHA_2E": [
        "§3 Description truncated: registered text ends \"…Dedicated Lithospheric"
        " Inversion express\"; it should end \"…Inversion, expressed in terms of high"
        " degree Spherical Harmonics\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_FAC_LLS_2F": [
        "§3 Comma dropped: registered \"dual-satellite A-C local least-squares\";"
        " should be \"A-C, local least-squares\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_MCO_SHA_2F": [
        "§3 Comma dropped before \"from the fast-track inversion\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_MCO_SHA_2Y": [
        "§3 Comma dropped before \"related to SW_CFW_SHA_2Y\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_MIO_SHA_2C": [
        "§3 Comma dropped before \"derived in comprehensive chain (CI)\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_MIO_SHA_2D": [
        "§3 Comma dropped before \"derived from dedicated chain (DIFI)\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_VOBS_1M_2_": [
        "§3 Comma dropped before \"on a uniform grid\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_VOBS_4M_2_": [
        "§3 Comma dropped before \"on a uniform grid\"." + _DESCRIPTION_BOTH_PLACES,
    ],
    "SW_EFIx_TCT02": [
        "§3 The registered description is correct; it is the catalogue definition"
        " that has a stray leading space (fix in product-catalogue). The value below"
        " is already stripped.",
    ],
    "SW_EEFxTMS_2F": [
        "§4 Registered creator name \" Technical University of Denmark\" has a leading"
        " space (renders as \"{ Technical University of Denmark}\" in DataCite BibTeX).",
    ],
}

# Issues shared by every registered record (datacite_metadata_issues.md §1, §2).
BATCH_ISSUES = [
    "§1 Every non-ESA creator is registered with nameType=\"Personal\"; it should be"
    " \"Organizational\".",
    "§2 No creator carries its ROR nameIdentifier (only the publisher has ESA's ROR).",
]
FORM_LIMITATION = (
    "The form has no nameType or ROR input, so issues §1 and §2 cannot be fixed"
    " through this form — and per schema_org_handoff.md §6, landing-page harvesting"
    " cannot carry creator ROR either. The routes that work are the \"Creator ROR\""
    " spreadsheet column proposed in datacite_metadata_issues.md §2, or a DataCite"
    " API push of the DataCite JSON below."
)

CSS = """
body { font-family: system-ui, sans-serif; max-width: 72em; margin: 1em auto; padding: 0 1em; line-height: 1.4; color: #1a1a1a; }
table { border-collapse: collapse; width: 100%; margin: 0.5em 0 1em; }
th, td { border: 1px solid #ccc; padding: 0.3em 0.5em; vertical-align: top; text-align: left; }
th { background: #f0f0f0; }
.value { white-space: pre-wrap; font-family: ui-monospace, monospace; }
.blank { color: #666; font-style: italic; }
.note { color: #555; font-size: 0.9em; margin-top: 0.3em; }
.callout { border-left: 4px solid; padding: 0.4em 0.8em; margin: 0.6em 0; }
.callout.issue { border-color: #c0392b; background: #fdf0ee; }
.callout.warning { border-color: #d68910; background: #fef5e7; }
.callout.info { border-color: #2e86c1; background: #eef6fc; }
.callout ul { margin: 0.2em 0; padding-left: 1.2em; }
.flag { display: inline-block; font-size: 0.8em; padding: 0 0.4em; margin: 0 0.2em 0.2em 0; border-radius: 3px; background: #fef5e7; border: 1px solid #d68910; }
.flag.issue { background: #fdf0ee; border-color: #c0392b; }
tr.readonly td { color: #555; }
tr.done td { background: #eafaf1; }
pre { background: #f6f6f6; padding: 0.6em; overflow-x: auto; }
button { cursor: pointer; }
footer { margin-top: 2em; color: #666; font-size: 0.85em; border-top: 1px solid #ccc; padding-top: 0.5em; }
"""

JS = """
const PREFIX = "doi-checklist:";
function store(key, on) {
  try { on ? localStorage.setItem(PREFIX + key, "1") : localStorage.removeItem(PREFIX + key); } catch (e) {}
}
function stored(key) {
  try { return localStorage.getItem(PREFIX + key) === "1"; } catch (e) { return false; }
}
function countStored(prefix) {
  let n = 0;
  try {
    for (let i = 0; i < localStorage.length; i++) {
      const k = localStorage.key(i);
      if (k.startsWith(PREFIX + prefix) && !k.endsWith(":done") && localStorage.getItem(k) === "1") n++;
    }
  } catch (e) {}
  return n;
}
function refresh() {
  document.querySelectorAll("input[data-key]").forEach(cb => {
    const row = cb.closest("tr");
    if (row) row.classList.toggle("done", cb.checked);
  });
  const progress = document.getElementById("progress");
  if (progress) {
    const boxes = document.querySelectorAll("input[data-key]");
    const done = [...boxes].filter(cb => cb.checked).length;
    progress.textContent = done + " of " + boxes.length + " done";
  }
  document.querySelectorAll("[data-fields-prefix]").forEach(el => {
    const n = countStored(el.dataset.fieldsPrefix);
    el.textContent = n ? n + "/" + el.dataset.fieldsTotal + " fields ticked" : "";
  });
}
function selectContents(el) {
  const range = document.createRange();
  range.selectNodeContents(el);
  const sel = window.getSelection();
  sel.removeAllRanges();
  sel.addRange(range);
}
function copyValue(btn) {
  const el = document.getElementById(btn.dataset.target);
  const text = el.textContent;
  const label = btn.textContent;
  const flash = msg => { btn.textContent = msg; setTimeout(() => { btn.textContent = label; }, 2000); };
  const fallback = () => {
    // navigator.clipboard is unavailable on plain http other than localhost,
    // e.g. `make serve` shared over a LAN address.
    selectContents(el);
    let ok = false;
    try { ok = document.execCommand("copy"); } catch (e) {}
    flash(ok ? "Copied" : "Selected — press Ctrl+C");
  };
  if (navigator.clipboard && window.isSecureContext) {
    navigator.clipboard.writeText(text).then(() => flash("Copied"), fallback);
  } else {
    fallback();
  }
}
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("input[data-key]").forEach(cb => {
    cb.checked = stored(cb.dataset.key);
    cb.addEventListener("change", () => { store(cb.dataset.key, cb.checked); refresh(); });
  });
  document.querySelectorAll("button[data-target]").forEach(btn => {
    btn.addEventListener("click", () => copyValue(btn));
  });
  refresh();
});
"""

SCRATCHPAD_NOTE = (
    "Tick-boxes are a personal scratchpad: they are stored in this browser only"
    " (localStorage) and do not travel with the shared URL."
)


def _details_value(details, label):
    """Extract a plain-text cell from the ``details`` HTML table by row label."""
    m = re.search(
        r"<tr[^>]*>\s*<t[dh][^>]*>\s*" + re.escape(label)
        + r"\s*</t[dh]>\s*<t[dh][^>]*>(.*?)</t[dh]>",
        details or "", re.S | re.I)
    if not m:
        return ""
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", m.group(1)))).strip()


def _non_esa_authors(product):
    authors = []
    for author in product.authors or []:
        name = (author.get("name") or "").strip()
        ror = (author.get("ror") or "").strip()
        if name.lower() == PUBLISHER["name"].lower() or ror.lower() == ESA_ROR:
            continue
        authors.append((name, ror))
    return authors


def _variables_rows(product):
    if not product.variables_table:
        return None
    try:
        df = pd.read_csv(StringIO(product.variables_table))
    except Exception:
        return None
    return df.fillna("")


def _related_identifiers(product):
    return [
        i for i in product.identifiers or []
        if i.get("role") in ("external", "related") and (i.get("identifier") or "").strip()
    ]


def _authors_table(authors):
    if not authors:
        return ""
    rows = "".join(
        f"<tr><td>{escape(name)}</td><td>{escape(ror) if ror else '<span class=blank>no ROR in catalogue</span>'}</td></tr>"
        for name, ror in authors
    )
    return f"<table><tr><th>Author</th><th>ROR</th></tr>{rows}</table>"


def _variables_block(df):
    header = "".join(f"<th>{escape(str(c))}</th>" for c in df.columns)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(v))}</td>" for v in row) + "</tr>"
        for row in df.itertuples(index=False)
    )
    return (
        f"<details><summary>{len(df)} variables (optional)</summary>"
        f"<table><tr>{header}</tr>{body}</table></details>"
    )


def form_rows(product):
    """The form's fields, in form order, with values from the catalogue.

    Each row has ``label``, ``value`` (plain text; empty means nothing to enter),
    ``editable`` and ``note``. Optional keys: ``key`` (localStorage slug),
    ``constant`` (identical on every record), ``blank`` (text shown instead of
    "leave blank"), ``extra`` (pre-rendered HTML shown under the value).
    """
    product_id = product.product_id
    year = str(product.creation_year or "")

    data_format = _details_value(product.details, "Data format")
    if data_format and len(data_format) <= MAX_PREFILL_FORMAT_LENGTH:
        format_row = {"value": data_format, "note": "From the “Data format” row of the product details."}
    elif data_format:
        format_row = {
            "value": "",
            "blank": "see product details",
            "note": "The “Data format” entry is too long to pre-fill.",
            "extra": f"<details><summary>Data format text</summary><p>{escape(data_format)}</p></details>",
        }
    else:
        format_row = {"value": "", "note": "No “Data format” in the product details."}

    data_volume = _details_value(product.details, "Data volume")
    sizes_extra = (
        f"<div class=note>Context only — per-file volume from the product details,"
        f" not a collection size: <code>{escape(data_volume)}</code></div>"
        if data_volume else ""
    )

    authors = _non_esa_authors(product)
    variables = _variables_rows(product)
    related = _related_identifiers(product)

    rows = [
        {"label": "Product types", "value": ", ".join(product.product_types or []), "editable": False, "note": ""},
        {"label": "EO Dataset / Collection Name", "value": product_id, "editable": False, "note": ""},
        {"label": "Version / Baseline", "value": VERSION, "editable": False, "constant": True,
         "note": "Matches the registered DataCite version."},
        {"label": "Contributors", "value": CONTRIBUTORS[0]["name"], "editable": False, "constant": True,
         "note": "Registered as a DataCite contributor with contributorType=Other."},
        {"label": "Collection Description", "value": (product.definition or "").strip(), "editable": True,
         "note": "The catalogue definition; registered as descriptions[SeriesInformation]."},
        {"label": "Landing Page URL", "value": f"{LANDING_PAGE_BASE}/{product_id}", "editable": True, "note": ""},
        {"label": "Collection File Format", "editable": True, **format_row},
        {"label": "Collection Creation Year", "value": year, "editable": True, "note": ""},
        {"label": "Collection Publication Year", "value": year, "editable": True,
         "note": "Same as the creation year, by convention."},
        {"label": "Sizes", "value": "", "editable": True,
         "note": "The form means the size of the whole collection, which the catalogue does not hold.",
         "extra": sizes_extra},
        {"label": "Creators", "value": PUBLISHER["name"], "editable": False, "constant": True, "note": ""},
        {"label": "Publisher", "value": PUBLISHER["name"], "editable": False, "constant": True, "note": ""},
        {"label": "Subjects", "value": ", ".join(product.thematic_areas or []), "editable": True,
         "note": "The catalogue thematic areas."},
        {"label": "Authors", "value": ", ".join(name for name, _ in authors), "editable": True,
         "note": "Non-ESA authors (ESA is excluded by name and by ROR). The form has no ROR input; RORs shown for reference.",
         "extra": _authors_table(authors)},
        {"label": "Projects", "value": "", "editable": True, "blank": "leave as-is",
         "note": "No DataCite or catalogue equivalent."},
        {"label": "Data Policy URL", "value": DATA_POLICY_URL, "editable": True, "note": ""},
        {"label": "Geolocations", "value": "", "editable": True,
         "blank": "Leave empty — global/orbital coverage, no bounding box in the catalogue", "note": ""},
        {"label": "Temporal Coverage Attributes", "value": "", "editable": True,
         "blank": "Leave empty — not held in the catalogue", "note": ""},
        {"label": "Event Attributes", "value": "", "editable": True,
         "blank": "Leave empty — not applicable", "note": ""},
        {"label": "Parameters Attributes", "value": "", "editable": True,
         "blank": "optional — see variables below" if variables is not None else LEAVE_BLANK,
         "note": "" if variables is not None else "No variables table in the catalogue.",
         "extra": _variables_block(variables) if variables is not None else ""},
        {"label": "Related Identifiers",
         "value": "\n".join(i["identifier"].strip() for i in related), "editable": True,
         "note": (
             "Identifiers with role “external” or “related”. None exist in the catalogue today."
             " Role-less URL identifiers are excluded because they are the handbook landing"
             " page, already entered as Landing Page URL."
         )},
    ]
    for row in rows:
        row["key"] = re.sub(r"[^a-z0-9]+", "-", row["label"].lower()).strip("-")
    return rows


def catalogue_warnings(product):
    """Warnings derived from the catalogue data, as (short flag, message) pairs."""
    warnings = []
    definition = product.definition or ""
    if definition != definition.strip():
        warnings.append((
            "definition whitespace",
            "The catalogue definition has leading/trailing whitespace (fix in"
            " product-catalogue). The Collection Description below is stripped.",
        ))
    for author in product.authors or []:
        name = author.get("name") or ""
        if name != name.strip():
            warnings.append(("author whitespace", f"Author name {name!r} has leading/trailing whitespace."))
        if not (author.get("ror") or "").strip():
            warnings.append(("author has no ROR", f"Author {name.strip()!r} has no ROR in the catalogue."))
    if doi_identifier(product) is None:
        warnings.append(("no DOI", "No DOI registered for this record."))
    return warnings


def _build_info():
    try:
        commit = subprocess.run(
            ["git", "-C", _get_catalogue_repo_path(), "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, check=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        commit = "unknown"
    built = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    return f"Built {built} from product-catalogue {commit}."


def _page(title, body, footer):
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(title)}</title>
<style>{CSS}</style>
<script>{JS}</script>
</head>
<body>
{body}
<footer>{escape(footer)} {escape(SCRATCHPAD_NOTE)}</footer>
</body>
</html>
"""


def _callout(kind, title, items):
    if not items:
        return ""
    lis = "".join(f"<li>{escape(i)}</li>" for i in items)
    return f"<div class='callout {kind}'><strong>{escape(title)}</strong><ul>{lis}</ul></div>"


def _value_cell(row, element_id):
    if row["value"]:
        cell = f"<span class=value id='{element_id}'>{escape(row['value'])}</span>"
    else:
        cell = f"<span class=blank>{escape(row.get('blank', LEAVE_BLANK))}</span>"
    if row.get("note"):
        cell += f"<div class=note>{escape(row['note'])}</div>"
    return cell + row.get("extra", "")


def _record_page(product, footer):
    product_id = product.product_id
    identifier = doi_identifier(product)
    datacite = product_to_datacite(product)
    rows = form_rows(product)

    if identifier:
        doi = identifier["identifier"].strip()
        doi_html = f"<a href='https://doi.org/{escape(doi)}'>{escape(doi)}</a>"
    else:
        doi_html = "<em>no DOI registered</em>"

    landing = f"{LANDING_PAGE_BASE}/{product_id}"
    links = [
        f"<a href='{escape(landing)}'>handbook landing page</a>",
        f"<a href='../{escape(product_id)}.html'>catalogue preview</a>",
        f"<a href='../schema_org/{escape(product_id)}.jsonld'>JSON-LD</a>",
    ]
    if datacite:
        links.append(f"<a href='../datacite/{escape(product_id)}.json'>DataCite JSON</a>")

    callouts = _callout("issue", "Known issues in the registered DataCite record", KNOWN_ISSUES.get(product_id, []))
    if identifier:
        callouts += _callout("issue", "Batch-wide issues (all registered records)", BATCH_ISSUES + [FORM_LIMITATION])
    callouts += _callout("warning", "Catalogue warnings", [msg for _, msg in catalogue_warnings(product)])

    table_rows = []
    for n, row in enumerate(rows, start=1):
        if row.get("constant"):
            continue
        element_id = f"v-{row['key']}"
        if row["editable"]:
            tick = f"<input type=checkbox data-key='{escape(product_id)}:{row['key']}' aria-label='done'>"
            copy = f"<button data-target='{element_id}'>Copy</button>" if row["value"] else ""
            cls = ""
        else:
            tick = copy = ""
            cls = " class=readonly"
        table_rows.append(
            f"<tr{cls}><td>{tick}</td><td>{n}</td><td>{escape(row['label'])}"
            f"{' <em>(read-only)</em>' if not row['editable'] else ''}</td>"
            f"<td>{_value_cell(row, element_id)}</td><td>{copy}</td></tr>"
        )

    constants = "".join(
        f"<tr><td>{n}</td><td>{escape(row['label'])}</td><td>{_value_cell(row, '')}</td></tr>"
        for n, row in enumerate(rows, start=1) if row.get("constant")
    )

    if datacite:
        datacite_block = (
            "<h2>DataCite JSON</h2>"
            "<p>The <code>attributes</code> of a DataCite REST update for this DOI, generated"
            " from the catalogue with the fixes above applied. Not sent anywhere.</p>"
            "<details><summary>Show DataCite JSON</summary>"
            "<p><button data-target='datacite-json'>Copy JSON</button></p>"
            f"<pre id='datacite-json'>{escape(json.dumps(datacite, indent=2, ensure_ascii=False))}</pre>"
            "</details>"
        )
    else:
        datacite_block = "<h2>DataCite JSON</h2><p>None generated: this record has no DOI.</p>"

    body = f"""
<p><a href="index.html">&larr; all records</a> · <a href="../index.html">product catalogue</a></p>
<h1>{escape(product_id)}</h1>
<p>DOI: {doi_html}<br>{' · '.join(links)}</p>
{callouts}
<h2>Form fields <small id="progress"></small></h2>
<table>
<tr><th></th><th>#</th><th>Form field</th><th>Value</th><th></th></tr>
{''.join(table_rows)}
</table>
<details><summary>Constant fields (same on every record)</summary>
<table><tr><th>#</th><th>Form field</th><th>Value</th></tr>{constants}</table>
</details>
{datacite_block}
"""
    return _page(f"DOI checklist — {product_id}", body, footer)


def _index_page(products, docs, footer):
    constants = "".join(
        f"<tr><td>{escape(label)}</td><td><span class=value>{escape(value)}</span></td></tr>"
        for label, value in CONSTANT_FIELDS
    )
    doc_links = "".join(
        f"<li><a href='docs/{escape(name)}.html'>{escape(name)}</a></li>" for name in docs
    )
    rows = []
    for product in products:
        product_id = product.product_id
        identifier = doi_identifier(product)
        doi = identifier["identifier"].strip() if identifier else ""
        doi_html = f"<a href='https://doi.org/{escape(doi)}'>{escape(doi)}</a>" if doi else "<em>none</em>"
        flags = "".join(
            f"<span class='flag issue'>known issue {escape(issue.split(' ', 1)[0])}</span>"
            for issue in KNOWN_ISSUES.get(product_id, [])
        )
        flags += "".join(
            f"<span class=flag>{escape(flag)}</span>"
            for flag in dict.fromkeys(flag for flag, _ in catalogue_warnings(product))
        )
        artefacts = f"<a href='../schema_org/{escape(product_id)}.jsonld'>jsonld</a>"
        if identifier:
            artefacts += f" · <a href='../datacite/{escape(product_id)}.json'>json</a>"
        editable = sum(1 for row in form_rows(product) if row["editable"])
        rows.append(
            f"<tr><td><input type=checkbox data-key='{escape(product_id)}:done' aria-label='done'></td>"
            f"<td><a href='{escape(product_id)}.html'>{escape(product_id)}</a>"
            f"<div class=note data-fields-prefix='{escape(product_id)}:' data-fields-total='{editable}'></div></td>"
            f"<td>{doi_html}</td><td>{flags}</td><td>{artefacts}</td></tr>"
        )

    body = f"""
<p><a href="../index.html">&larr; product catalogue</a></p>
<h1>DOI update form checklist</h1>
<p>One page per catalogue record for ESA's “Request the update of DOI data (Datacite)”
form. Values come from the product catalogue: copy them, don't retype them.</p>
{_callout("issue", "Batch-wide issues in the registered DOIs (datacite_metadata_issues.md)", [
    *BATCH_ISSUES,
    "§3 Nine descriptions were altered during transcription — see the flagged records below.",
    "§4 One creator name has a stray leading space (SW_EEFxTMS_2F).",
    FORM_LIMITATION.replace("the DataCite JSON below", "the generated DataCite JSON"),
])}
<h2>Constant form fields</h2>
<p>Identical on every record; record pages list them in a collapsed block.</p>
<table><tr><th>Form field</th><th>Value</th></tr>{constants}</table>
<h2>Generated artefacts and sources</h2>
<ul>
<li>schema.org JSON-LD, one per record: <code>schema_org/&lt;product_id&gt;.jsonld</code></li>
<li>DataCite JSON (REST <code>attributes</code>), one per record with a DOI: <code>datacite/&lt;product_id&gt;.json</code></li>
{doc_links}
</ul>
<h2>Records <small id="progress"></small></h2>
<p class=note>{escape(SCRATCHPAD_NOTE)}</p>
<table>
<tr><th>Done</th><th>Product ID</th><th>DOI</th><th>Flags</th><th>Artefacts</th></tr>
{''.join(rows)}
</table>
"""
    return _page("DOI update form checklist", body, footer)


def _write_source_docs(docs_directory, footer):
    """Render the review documents to HTML; returns the names written."""
    written = []
    for name in SOURCE_DOCUMENTS:
        path = os.path.join(REPO_ROOT, name)
        if not os.path.exists(path):
            continue
        with open(path) as f:
            content = markdown(f.read(), extensions=["markdown.extensions.tables", "markdown.extensions.fenced_code"])
        os.makedirs(docs_directory, exist_ok=True)
        with open(os.path.join(docs_directory, f"{name}.html"), "w") as f:
            f.write(_page(name, f"<p><a href='../index.html'>&larr; checklist</a></p>{content}", footer))
        written.append(name)
    return written


def dump_doi_checklist_output(html_directory):
    catalog = load_catalog()
    products = [catalog.get_product(i) for i in sorted(catalog.product_ids)]
    directory = os.path.join(html_directory, "doi-checklist")
    # Unlike dump_html_output (which relies on the Makefile's `mkdir -p`), this
    # creates its own subdirectory. Deliberate: don't "align" the two.
    os.makedirs(directory, exist_ok=True)
    footer = _build_info()
    docs = _write_source_docs(os.path.join(directory, "docs"), footer)
    for product in products:
        with open(os.path.join(directory, f"{product.product_id}.html"), "w") as f:
            f.write(_record_page(product, footer))
    with open(os.path.join(directory, "index.html"), "w") as f:
        f.write(_index_page(products, docs, footer))


if __name__ == "__main__":
    import sys

    dump_doi_checklist_output(sys.argv[1] if len(sys.argv) > 1 else "html")
