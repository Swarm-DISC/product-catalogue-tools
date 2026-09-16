# Handoff — schema.org JSON-LD for DataCite landing-page harvesting

**Repo:** `Swarm-DISC/product-catalogue-tools` (branch `main`, work uncommitted)
**Date:** 2026-09-16
**Related:** `datacite_metadata_issues.md` (the 74-DOI batch registered 2026-09-15)

---

## 1. The question that started this

DataCite Fabrica can populate a DOI record by harvesting schema.org metadata from
the landing page: you paste the landing page URL into the metadata field instead of
uploading a file. We wanted to know whether our catalogue JSON is in the right shape
for that, and what would have to change.

**Answer: no, not as-is — and the catalogue JSON is the smaller of the two problems.
The blocker is the handbook landing page.**

---

## 2. How the harvester actually works (verified from source, not docs)

Read these if you need to re-check any mapping claim below:

- `datacite/bolognese` → `lib/bolognese/readers/schema_org_reader.rb` and `lib/bolognese/utils.rb`
- `front-matter/commonmeta-py` → `commonmeta/readers/schema_org_reader.py` and `commonmeta/utils.py`

Key behaviours:

| Behaviour | Evidence |
|---|---|
| Reads **one** ld+json block. bolognese takes literally the first (`doc.at('script[type="application/ld+json"]')`); commonmeta takes the first with a recognised `@type` (`pick_json_ld`). | `schema_org_reader.rb` `get_schema_org`; `so_reader.py:281` |
| Title comes from `name` only — **not** `headline`. | `titles` in `read_schema_org` |
| `@type: Dataset` → `resourceTypeGeneral: Dataset`; `@type: Article` → `Text`. | `SO_TO_DC_TRANSLATIONS`, `utils.rb:274` |
| `creator["@type"]: "Organization"` → `nameType="Organizational"` (literally `@type.titleize + "al"`). | `from_schema_org_creators`, `utils.rb:997` |
| A creator's `@id` becomes a `nameIdentifier` **only if it is an ORCID**. ROR is recognised on `affiliation` and `publisher`, never on the creator itself. | `utils.rb:995`; `cm_utils.py:1541` |
| `publisher["@id"]` → `publisherIdentifier`. | `read_schema_org`, publisher block |
| `datePublished` → `publicationYear` (EDTF, so a bare `"2018"` is fine). | `read_schema_org`, dates block |
| `sameAs` → `IsIdenticalTo`; `citation` → `References`; `isPartOf`/`hasPart` → as named. | `SO_TO_DC_RELATION_TYPES` |
| `keywords` → subjects (array or comma-separated string). | `subjects` block |

---

## 3. State of the landing pages (blockers)

Checked `https://swarmhandbook.earth.esa.int/catalogue/SW_DNSxACC_2_` on 2026-09-16.
It is a Next.js SSR page, so JSON-LD **is** present in the raw HTML — good, a
non-JS harvester can see it. But:

1. **Four ld+json blocks, in this order: `Organization`, `WebSite`, `BreadcrumbList`,
   `Article`.** bolognese would harvest the `Organization` block — the site-wide logo
   stub. Result is junk.
2. **The `Article` block is wrong even if it were picked.** `@type: Article` →
   `Text`, not `Dataset`. It uses `headline`, which the harvester does not read, so
   the **title would come out empty**. Its `author` is hardcoded to ESA, losing every
   real institutional creator.
3. **No DOI on the page.** `__NEXT_DATA__.props.pageProps.doi` is `""` for
   `SW_DNSxACC_2_`. `SW_MAGx_LR_1B` *does* have one
   (`https://doi.org/10.57780/esa-091794d`), so the CMS supports the field — the new
   74-DOI batch simply has not been ingested yet.
4. **The page carries no authors and no creation year at all.** Page props are:
   `seo, title, productFullName, doi, doiLink, description, *DataAccessLink,
   fastProcessingDescription, previewImage, details, relatedResources, changeLog,
   outputVariablesTable*, missions, subsets, products, url, navigationMenu,
   isArchived, schema`. No harvester tweak fixes this; the handbook ingest must carry
   the fields.

**Separate bug to report to the handbook team:** `ARTICLE_URL` and the breadcrumb
items are built as `https://swarmhandbook.earth.esa.intcatalogue/SW_DNSxACC_2_` —
missing slash between host and path.

---

## 4. What was built

**`utils/schema_org.py`** (new, untracked) — converts catalogue records to
schema.org `Dataset` JSON-LD.

```
uv run python -m utils.schema_org SW_DNSxACC_2_   # print one record
uv run python -m utils.schema_org                 # dump all 91 to schema_org/
```

Public API: `product_to_schema_org(product)` and `dump_schema_org_output(directory)`.
Not wired into the `Makefile` — see open question 3.

Mapping implemented:

| Catalogue field | schema.org |
|---|---|
| primary DOI | `@id`, `identifier[]` |
| `product_id` | `name` (matches the titles already registered at DataCite) |
| `definition` | `alternateName` |
| `description` | `description`, HTML stripped |
| `authors[]` | `creator[] {@type: Organization, @id: <ror>}` |
| `creation_year` | `datePublished` |
| `thematic_areas` + `applicable_missions` + `applicable_spacecraft` | `keywords` |
| `link_files_http` / `link_files_ftp` / `link_hapi` | `distribution[] DataDownload` |
| `variables_table` | `variableMeasured[] PropertyValue` (name/unitText/description) |
| `identifiers[].role: external` | `sameAs` |
| `identifiers[].role: related` | `citation` |
| — (hardcoded) | `publisher` + `provider` = ESA with ROR `https://ror.org/03wd9za21` |
| — (hardcoded) | `includedInDataCatalog` = Swarm Product Data Handbook |

---

## 5. Catalogue audit (91 records, run 2026-09-16)

- 89/91 have a concept DOI marked `primary`. The two without are `SW_EFIx_LP_1B` and
  `SW_FAC_SVD_2F`; for these the generator falls back to the landing page URL as
  `@id`, which is correct behaviour.
- All 91 have `authors`, `creation_year`, `description`, `definition`,
  `thematic_areas`.
- 23 have an empty `variables_table` → no `variableMeasured`. Not an error.
- 5 have HTML markup inside `description` → stripped by `_strip_html`.

**Fields we cannot supply because the catalogue schema has no home for them:**
`license`, `temporalCoverage`, `spatialCoverage`, `version`, and real
`encodingFormat` values (the generator currently assumes `application/x-cdf` for file
links). Adding these needs `product-catalogue/schema.json` changes plus per-record
data entry.

---

## 6. Impact on `datacite_metadata_issues.md`

- **Issue 1 (organisations registered as `nameType="Personal"`, 74/74): fixed** by this
  route — `"@type": "Organization"` maps straight to `Organizational`.
- **Issue 2 (no ROR on any creator, 74/74): NOT fixed.** Neither converter promotes a
  creator's ROR `@id` to a `nameIdentifier`. The generator emits it anyway because it
  is correct schema.org and Google reads it, but DataCite will drop it. This still
  needs either the `Creator ROR` spreadsheet column or a direct API upload.
- **Issues 3 and 4 (transcription drift, stray whitespace):** structurally fixed by any
  machine-generated route, since text stops being retyped. Note `SW_EEFxTMS_2F` has a
  leading space in a creator name and `SW_EFIx_TCT02` a leading space in `definition`
  — both are ours to fix in the catalogue. `_creators` strips whitespace; the
  `definition` one is not stripped.

---

## 7. Recommendation carried forward

Landing-page harvesting is the wrong *primary* channel: it is lossy (no creator ROR,
no relatedIdentifier precision) and it puts our metadata behind a CMS we do not
control. Preferred shape:

- **Primary:** generate DataCite JSON from the catalogue and push via the DataCite
  API. Full control including ROR `nameIdentifier`s.
- **Complementary:** hand the JSON-LD to the handbook team to embed as the **first**
  ld+json block on each catalogue page. Buys Google Dataset Search indexing and a
  correct harvest as fallback.

---

## 8. Open questions / next steps

1. **Write the DataCite JSON generator?** Offered to the user, not yet answered. This
   is the higher-value piece per section 7.
2. **Who owns the handbook page template?** The JSON-LD is useless until someone on
   the handbook/CMS side embeds it, ingests `authors` + `creation_year` + `doi`, and
   reorders the ld+json blocks. Need a contact and a channel for handing over 91
   JSON-LD documents.
3. **Wire `utils/schema_org.py` into `make html`?** Deliberately not done — the HTML
   target builds *previews* for us, whereas the JSON-LD needs to reach the handbook
   CMS. Decide the delivery mechanism first (committed artefacts in
   `product-catalogue`? published alongside the GitHub Pages previews? API push?).
4. **Extend `product-catalogue/schema.json`** with `license`, `version`,
   `temporalCoverage`, `spatialCoverage`, `encodingFormat`? Worth doing for the
   DataCite JSON route too, not just JSON-LD.
5. **Validate a sample** against Google's Rich Results Test and, if a test prefix is
   available, a DataCite *sandbox* harvest before touching production DOIs.

---

## 9. Files

| Path | Status |
|---|---|
| `utils/schema_org.py` | new, untracked — the converter |
| `schema_org_handoff.md` | this file |
| `datacite_metadata_issues.md` | pre-existing, untracked — the four registration issues |
| `utils/catalog_utils.py` | unchanged — `Product`, `load_catalog`, `dump_html_output` |
| `product-catalogue/schema.json` | unchanged — submodule, catalogue schema |

Nothing has been committed. The working tree also holds unrelated untracked work
(`add_registered_dois.py`, `update_from_csv.py`, spreadsheets, `input.csv`).
