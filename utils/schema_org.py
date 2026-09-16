"""Convert catalogue records into schema.org Dataset JSON-LD.

The JSON-LD is what DataCite Fabrica harvests when you give it a landing page
URL instead of a metadata file, and what Google Dataset Search indexes. It is
embedded in the handbook page as::

    <script type="application/ld+json">...</script>

DataCite's converter reads the *first* ld+json block on the page, so the
Dataset block must come before any Organization/WebSite/BreadcrumbList blocks.
"""

from html import unescape
from io import StringIO
import json
import os
import re

import pandas as pd

from .catalog_utils import load_catalog

LANDING_PAGE_BASE = "https://swarmhandbook.earth.esa.int/catalogue"
PUBLISHER = {
    "@type": "Organization",
    "@id": "https://ror.org/03wd9za21",
    "name": "European Space Agency",
}
DATA_CATALOG = {
    "@type": "DataCatalog",
    "name": "Swarm Product Data Handbook",
    "url": LANDING_PAGE_BASE,
}


def _strip_html(text):
    """schema.org descriptions are plain text; a few records hold markup."""
    text = re.sub(r"<[^>]+>", " ", text or "")
    return re.sub(r"\s+", " ", unescape(text)).strip()


def _doi_url(identifier):
    value = (identifier.get("identifier") or "").strip()
    if not value:
        return ""
    if identifier.get("identifierType") == "DOI":
        return value if value.startswith("http") else f"https://doi.org/{value}"
    return value


def _creators(product):
    creators = []
    for author in product.authors or []:
        name = (author.get("name") or "").strip()
        if not name:
            continue
        creator = {"@type": "Organization", "name": name}
        if author.get("ror"):
            # Carried for completeness. DataCite's harvester only maps ORCID
            # from @id, so this does not become a creator nameIdentifier.
            creator["@id"] = author["ror"]
        creators.append(creator)
    return creators


def _distributions(product):
    distributions = []
    for url, fmt in (
        (product.link_files_http, "application/x-cdf"),
        (product.link_files_ftp, "application/x-cdf"),
        (product.link_hapi, "application/json"),
    ):
        if url:
            distributions.append(
                {"@type": "DataDownload", "contentUrl": url, "encodingFormat": fmt}
            )
    return distributions


def _variables(product):
    if not product.variables_table:
        return []
    try:
        df = pd.read_csv(StringIO(product.variables_table))
    except Exception:
        return []
    variables = []
    for _, row in df.iterrows():
        variable = {"@type": "PropertyValue", "name": str(row.get("Variable", "")).strip()}
        if not variable["name"]:
            continue
        units = str(row.get("Units", "")).strip()
        description = str(row.get("Description", "")).strip()
        if units and units != "-":
            variable["unitText"] = units
        if description:
            variable["description"] = description
        variables.append(variable)
    return variables


def product_to_schema_org(product):
    """Build the schema.org Dataset JSON-LD for a single product."""
    identifiers = product.identifiers or []
    primary = next((i for i in identifiers if i.get("primary")), None)
    landing_page = f"{LANDING_PAGE_BASE}/{product.product_id}"

    identifier_urls = []
    same_as = []
    citation = []
    for identifier in identifiers:
        url = _doi_url(identifier)
        if not url:
            continue
        role = identifier.get("role")
        if identifier is primary or role in (None, "concept", "version"):
            identifier_urls.append(url)
        elif role == "external":
            same_as.append(url)
        elif role == "related":
            citation.append(url)
    identifier_urls = list(dict.fromkeys(identifier_urls + [landing_page]))

    keywords = list(
        dict.fromkeys(
            (product.thematic_areas or [])
            + (product.applicable_missions or [])
            + (product.applicable_spacecraft or [])
        )
    )

    dataset = {
        "@context": "https://schema.org",
        "@type": "Dataset",
        "@id": _doi_url(primary) if primary else landing_page,
        "url": landing_page,
        "name": product.product_id,
        "alternateName": (product.definition or "").strip() or None,
        "description": _strip_html(product.description),
        "identifier": identifier_urls,
        "creator": _creators(product),
        "publisher": PUBLISHER,
        "provider": PUBLISHER,
        "datePublished": str(product.creation_year) if product.creation_year else None,
        "keywords": keywords or None,
        "includedInDataCatalog": DATA_CATALOG,
        "distribution": _distributions(product) or None,
        "variableMeasured": _variables(product) or None,
        "sameAs": same_as or None,
        "citation": citation or None,
    }
    return {k: v for k, v in dataset.items() if v}


def dump_schema_org_output(directory):
    catalog = load_catalog()
    os.makedirs(directory, exist_ok=True)
    for product_id in sorted(catalog.product_ids):
        dataset = product_to_schema_org(catalog.get_product(product_id))
        path = os.path.join(directory, f"{product_id}.jsonld")
        with open(path, "w") as f:
            json.dump(dataset, f, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    import sys

    catalog = load_catalog()
    if len(sys.argv) > 1:
        product = catalog.get_product(sys.argv[1])
        print(json.dumps(product_to_schema_org(product), indent=2, ensure_ascii=False))
    else:
        dump_schema_org_output("schema_org")
