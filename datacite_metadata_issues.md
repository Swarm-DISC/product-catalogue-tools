# DataCite metadata issues — Swarm L2 DOI batch (74 DOIs, registered 2026-09-15)

Prefix `10.57780`, all records `findable`. DOIs resolve to the correct Swarm Handbook
pages and titles, publishers, and publication years all match our catalogue. Four
metadata issues remain, in rough order of impact.

## 1. Organisations are registered as people (74/74 records)

Every non-ESA creator — 75 entries across the batch — carries
`nameType="Personal"`. ESA itself is correctly `Organizational`.

| | |
|---|---|
| Registered | `<creatorName nameType="Personal">GFZ Helmholtz Centre for Geosciences</creatorName>` |
| Should be | `<creatorName nameType="Organizational">GFZ Helmholtz Centre for Geosciences</creatorName>` |

Affects 19 institutions (GFZ ×19, TU Delft ×13, DTU ×8, U Calgary ×7, IPGP ×6, …).
Consumers that parse `nameType` will try to split these into given/family names, so
institutional authorship is misrepresented in every downstream citation.

## 2. No ROR identifiers on any creator (74/74 records)

No creator in the batch has a `nameIdentifier`, although ESA's ROR *is* correctly set
on the `publisher` element (`https://ror.org/03wd9za21`) on all 74 records. We hold a
ROR for every authoring institution in our catalogue and can supply them — our
handover spreadsheet currently has an `Authors` column with names only. **Suggested
fix on our side: add a `Creator ROR` column to the spreadsheet** so the identifiers
travel with the names.

Target form:

```xml
<creator>
  <creatorName nameType="Organizational">GFZ Helmholtz Centre for Geosciences</creatorName>
  <nameIdentifier nameIdentifierScheme="ROR" schemeURI="https://ror.org/">https://ror.org/04z8jg394</nameIdentifier>
</creator>
```

## 3. Descriptions altered during transcription (9 records)

Eight are dropped commas, which change the technical reading. One is truncated:

| Product | DOI | Issue |
|---|---|---|
| `SW_MLI_SHA_2E` | `10.57780/esa-5e497d1` | **Truncated**: ends `"…Dedicated Lithospheric Inversion express"`; should end `"…Inversion, expressed in terms of high degree Spherical Harmonics"` |
| `SW_FAC_LLS_2F` | `10.57780/esa-2879355` | `"dual-satellite A-C local least-squares"` → should be `"A-C, local least-squares"` |
| `SW_MCO_SHA_2F` | `10.57780/esa-2a69b15` | comma dropped before `"from the fast-track inversion"` |
| `SW_MCO_SHA_2Y` | `10.57780/esa-10597d1` | comma dropped before `"related to SW_CFW_SHA_2Y"` |
| `SW_MIO_SHA_2C` | `10.57780/esa-c4597d1` | comma dropped before `"derived in comprehensive chain (CI)"` |
| `SW_MIO_SHA_2D` | `10.57780/esa-6079355` | comma dropped before `"derived from dedicated chain (DIFI)"` |
| `SW_VOBS_1M_2_` | `10.57780/esa-33497d1` | comma dropped before `"on a uniform grid"` |
| `SW_VOBS_4M_2_` | `10.57780/esa-9879355` | comma dropped before `"on a uniform grid"` |
| `SW_EFIx_TCT02` | `10.57780/esa-4079355` | DataCite is correct here; *our* definition has a stray leading space — to fix on our side |

The same text appears in both `descriptions[SeriesInformation]` and `container.title`,
so both need correcting.

## 4. Stray whitespace in a creator name (1 record)

`SW_EEFxTMS_2F` (`10.57780/esa-7d59fd1`) has `" Technical University of Denmark"` with a
leading space. It shows up in DataCite's rendered BibTeX as
`{ Technical University of Denmark}`.

---

**Process note.** Issues 1 and 2 are systematic — they apply to every record in the
batch, so they are almost certainly a default in the registration step rather than
per-record slips. Issue 3 is transcription drift from copy-and-paste. Both classes
would be avoided if the handover carried `nameType` and ROR columns explicitly and the
description text were ingested from the spreadsheet rather than retyped.
