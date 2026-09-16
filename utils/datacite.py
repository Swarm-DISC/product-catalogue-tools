"""Convert catalogue records into DataCite JSON (REST API ``attributes``).

This is the primary channel for correcting the registered Swarm L2 DOIs (see
``schema_org_handoff.md`` §7): unlike landing-page harvesting it can carry a
ROR ``nameIdentifier`` on each creator. The output is the ``attributes`` object
of a DataCite REST ``PUT /dois/{doi}`` body. Nothing here sends it anywhere.

The field set reproduces what ESA registered (e.g. ``10.57780/esa-a3497d1``),
with the fixes from ``datacite_metadata_issues.md`` applied:

- §1: every creator is ``nameType: Organizational``;
- §2: creators carry their ROR as a ``nameIdentifier`` when the catalogue has one;
- §3: ``SeriesInformation`` is the catalogue ``definition``, stripped only of
  leading/trailing whitespace so punctuation is reproduced exactly;
- §4: creator names are stripped.

Two fields are deliberate *additions* beyond the registered records:
``descriptions[Abstract]`` (from ``description``) and ``subjects`` (from
``thematic_areas``).

``sizes``, ``formats``, ``geoLocations``, ``dates``, ``rightsList`` and
``relatedIdentifiers`` are deliberately *not* emitted: the catalogue has no
trustworthy source for them, and an empty array in a full-record PUT deletes
whatever is registered.

``publisher`` uses the object form, which needs DataCite kernel-4.5. Against a
4.3-only consumer, fall back to the plain string ``"European Space Agency"``.
"""

import json
import os

from .catalog_utils import load_catalog
from .schema_org import LANDING_PAGE_BASE, PUBLISHER, _strip_html

ROR_SCHEME_URI = "https://ror.org/"
ESA_ROR = PUBLISHER["@id"]
CONTRIBUTORS = [{"name": "D/EOP", "contributorType": "Other"}]
VERSION = "0"
LANGUAGE = "en"


def doi_identifier(product):
    """Return the identifier dict holding the product's DOI, or None.

    "Has a DOI" means some identifier has ``identifierType == "DOI"``; whether
    anything is marked ``primary`` is irrelevant (SW_EFIx_LP_1B and
    SW_FAC_SVD_2F differ on that but neither has a DOI).
    """
    dois = [
        i for i in product.identifiers or []
        if i.get("identifierType") == "DOI" and (i.get("identifier") or "").strip()
    ]
    if not dois:
        return None
    cited = product._citation_identifier()
    if cited and cited.get("identifierType") == "DOI":
        return cited
    return dois[0]


def _ror_identifier(ror):
    return {
        "nameIdentifier": ror,
        "nameIdentifierScheme": "ROR",
        "schemeUri": ROR_SCHEME_URI,
    }


def _creators(product):
    creators = []
    for author in product.authors or []:
        name = (author.get("name") or "").strip()
        if not name:
            continue
        creator = {"name": name, "nameType": "Organizational"}
        ror = (author.get("ror") or "").strip()
        if ror:
            creator["nameIdentifiers"] = [_ror_identifier(ror)]
        creators.append(creator)
    return creators


def _descriptions(product):
    descriptions = []
    definition = (product.definition or "").strip()
    if definition:
        descriptions.append(
            {"description": definition, "descriptionType": "SeriesInformation"}
        )
    abstract = _strip_html(product.description)
    if abstract:
        descriptions.append({"description": abstract, "descriptionType": "Abstract"})
    return descriptions


def product_to_datacite(product):
    """Build the DataCite ``attributes`` for a product, or None if it has no DOI."""
    identifier = doi_identifier(product)
    if identifier is None:
        return None
    attributes = {
        "doi": identifier["identifier"].strip(),
        "url": f"{LANDING_PAGE_BASE}/{product.product_id}",
        "titles": [{"title": product.product_id}],
        "creators": _creators(product),
        "publisher": {
            "name": PUBLISHER["name"],
            "publisherIdentifier": ESA_ROR,
            "publisherIdentifierScheme": "ROR",
            "schemeUri": ROR_SCHEME_URI,
        },
        "publicationYear": product.creation_year,
        "types": {"resourceTypeGeneral": "Dataset"},
        "contributors": CONTRIBUTORS,
        "language": LANGUAGE,
        "version": VERSION,
        "descriptions": _descriptions(product),
        "subjects": [{"subject": area} for area in product.thematic_areas or []],
        "schemaVersion": "http://datacite.org/schema/kernel-4",
    }
    return {k: v for k, v in attributes.items() if v not in (None, "", [])}


def dump_datacite_output(directory):
    catalog = load_catalog()
    os.makedirs(directory, exist_ok=True)
    for product_id in sorted(catalog.product_ids):
        attributes = product_to_datacite(catalog.get_product(product_id))
        if attributes is None:
            continue
        path = os.path.join(directory, f"{product_id}.json")
        with open(path, "w") as f:
            json.dump(attributes, f, indent=2, ensure_ascii=False)
            f.write("\n")
