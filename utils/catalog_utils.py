from dataclasses import dataclass, field
from html import escape
from io import StringIO, BytesIO
import json
import os
import sys
from tempfile import NamedTemporaryFile
from textwrap import dedent

from markdown import markdown
import pandas as pd
from tabulate import tabulate

from .definitions import SPACECRAFT, SC2MISSIONS, THEMATIC_AREAS


def _get_catalogue_repo_path():
    return os.path.join(
        os.path.dirname(__file__),
        "../product-catalogue",
    )


def _get_catalog_dir():
    return os.path.join(
        _get_catalogue_repo_path(),
        "catalogue"
    )


def _get_schema_path():
    return os.path.join(
        _get_catalogue_repo_path(),
        "schema.json"
    )


def load_schema():
    with open(_get_schema_path(), "r") as schema_file:
        schema = json.load(schema_file)
    return schema


def load_catalog(directory=_get_catalog_dir()):
    paths = os.listdir(directory)
    paths = [os.path.join(directory, p) for p in paths if ".json" in p]
    products = []
    for path in paths:
        products.append(Product.from_json_file(path))
    products = {p.product_id: p for p in products}
    return Catalog(products=products)


@dataclass
class Product:
    product_id: str = ""
    definition: str = ""
    applicable_missions: "list[str]|None" = field(default_factory=lambda: [])
    applicable_spacecraft: "list[str]|None" = field(default_factory=lambda: [])
    thematic_areas: "list[str]|None" = field(default_factory=lambda: [])
    authors: "list[dict]|None" = field(default_factory=lambda: [])
    creation_year: "int|None" = None
    product_types: "list[str]|None" = field(default_factory=lambda: [])
    identifiers: "list[dict]|None" = field(default_factory=lambda: [])
    description: str = ""
    link_files_http: str = ""
    link_files_ftp: str = ""
    link_vires_gui: str = ""
    link_notebook: str = ""
    link_hapi: str = ""
    variables_table: str = ""
    related_resources: str = ""
    details: str = ""
    changelog: str = ""
    fast_processing: bool = False
    
    @staticmethod
    def allowed_thematic_areas():
        return THEMATIC_AREAS
    
    @staticmethod
    def allowed_spacecraft():
        return list(SC2MISSIONS.keys())
    
    def __str__(self):
        items = self.as_dict()
        items = [f"{k}:\n{v}" for k, v in items.items()]
        return "\n\n".join(items)

    def as_dict(self):
        items = {}
        for field in self.__dataclass_fields__:
            value = getattr(self, field)
            items[field] = value
        return items
    
    def as_json(self):
        return json.dumps(self.as_dict(), indent=4)

    def get_json_file(self):
        tempfile = NamedTemporaryFile()
        tempfile.write(bytes(self.as_json(), "utf-8"))
        tempfile.seek(0)
        return tempfile

    @property
    def tabulate_variables(self):
        if self.variables_table == "":
            return ""
        try:
            df = pd.read_csv(StringIO(self.variables_table))
            return tabulate(df.values, df.columns, tablefmt="pipe")
        except Exception:
            return "INVALID TABLE"

    @property
    def markdown_links(self):
        s = ""
        if any((self.link_files_http, self.link_files_ftp)):
            s += "- Files:\n"
            if self.link_files_http:
                s += f"\t- <{self.link_files_http}>\n"
            if self.link_files_ftp:
                s += f"\t- {self.link_files_ftp}\n"
        if any((self.link_vires_gui, self.link_notebook, self.link_hapi)):
            s += "- Web services:\n"
            if self.link_vires_gui:
                s += f"\t- [VirES GUI]({self.link_vires_gui})\n"
            if self.link_notebook:
                s += f"\t- [Notebook]({self.link_notebook})\n"
            if self.link_hapi:
                s += f"\t- [HAPI]({self.link_hapi})\n"
        s = s.rstrip()
        return s
    
    @property
    def markdown_preview(self):
        # Format authors information
        authors_info = "N/A"
        if self.authors:
            authors_list = []
            for author in self.authors:
                if "ror" in author:
                    authors_list.append(f"{author['name']} - {author['ror']}")
                else:
                    authors_list.append(author['name'])
            authors_info = ", ".join(authors_list)
        
        # Format creation year
        creation_year_info = "N/A"
        if self.creation_year:
            creation_year_info = str(self.creation_year)  # Simply convert integer year to string
        
        # Format product types
        product_types_info = ", ".join(self.product_types) if self.product_types else "N/A"
        
        has_primary = any((i or {}).get("primary") for i in (self.identifiers or []))
        cite_as = self.preview_citation_text if has_primary else "N/A"
        cite_bibtex = self.preview_citation_bibtex_block if has_primary else ""
        items = [
            f"# {self.product_id}\n\n{self.definition}",
            f"**Cite as:** {cite_as}",
            cite_bibtex,
            self.additional_references_block,
            f"**Product types:** {product_types_info}",
            f"**Authored by:** {authors_info}",
            f"**Creation year:** {creation_year_info}",
            f"**Thematic areas:** {', '.join(self.thematic_areas)}",
            f"**Applicable missions:** {', '.join(self.applicable_missions)}",
            f"**Applicable spacecraft:** {', '.join(self.applicable_spacecraft)}",
            f"## Description\n\n{self.description}",
            f"## Data access\n\n{self.markdown_links}",
            f"## FAST processing\n\n{"This product is also available via the FAST processing chain." if self.fast_processing else ""}",
            f"## Preview image\n\n(delivered separately)",
            f"## File contents\n\n{self.tabulate_variables if self.tabulate_variables else 'N/A'}",
            f"## More details\n\n{self.details if self.details else 'N/A'}",
            f"## Related resources\n\n{self.related_resources if self.related_resources else 'N/A'}",
            f"## Changelog\n\n{self.changelog if self.changelog else 'N/A'}",
        ]
        return "\n\n".join(items)

    def _citation_identifier(self):
        if not self.identifiers:
            return None
        for identifier in self.identifiers:
            if identifier.get("primary") and identifier.get("identifier"):
                return identifier
        for identifier in self.identifiers:
            if (
                identifier.get("identifierType") == "DOI"
                and identifier.get("role") == "concept"
                and identifier.get("identifier")
            ):
                return identifier
        for identifier in self.identifiers:
            if (
                identifier.get("identifierType") == "DOI"
                and identifier.get("role") == "version"
                and identifier.get("identifier")
            ):
                return identifier
        for identifier in self.identifiers:
            if identifier.get("identifierType") == "URL" and identifier.get("identifier"):
                return identifier
        return None

    @staticmethod
    def _format_identifier_for_markdown(identifier):
        if not identifier:
            return ""
        identifier_value = identifier.get("identifier", "")
        identifier_type = identifier.get("identifierType", "")
        if identifier_type == "DOI" and identifier_value:
            return f"https://doi.org/{identifier_value}"
        return identifier_value

    def _generated_citation_text(self):
        author_names = [author.get("name", "").strip() for author in self.authors or []]
        author_names = [name for name in author_names if name]
        authors_info = ", ".join(author_names) if author_names else "N/A"
        creation_year_info = str(self.creation_year) if self.creation_year else "N/A"
        identifier_md = self._format_identifier_for_markdown(self._citation_identifier())
        return ", ".join([
            authors_info,
            creation_year_info,
            f'"{self.product_id}"',
            "European Space Agency",
            identifier_md,
        ]).rstrip(", ")

    def _generated_citation_bibtex(self):
        author_names = [author.get("name", "").strip() for author in self.authors or []]
        authors_info = " and ".join([f"{{{name}}}" for name in author_names if name]) or "Unknown"
        year_info = str(self.creation_year) if self.creation_year else "n.d."
        identifier = self._citation_identifier() or {}
        identifier_value = identifier.get("identifier", "")
        identifier_type = identifier.get("identifierType", "")

        key = self.product_id.replace(" ", "_") if self.product_id else "dataset"
        lines = [
            f"@misc{{{key},",
            f"  author = {{{authors_info}}},",
            f"  title = {{{self.product_id}}},",
            f"  year = {{{year_info}}},",
            "  publisher = {European Space Agency},",
        ]
        if identifier_value and identifier_type == "DOI":
            lines.append(f"  doi = {{{identifier_value}}},")
            lines.append(f"  url = {{https://doi.org/{identifier_value}}},")
        elif identifier_value:
            lines.append(f"  url = {{{identifier_value}}},")
        lines.append("}")
        return "\n".join(lines)

    def ensure_primary_citation(self):
        if not self.identifiers:
            return
        primary = next(
            (i for i in self.identifiers if (i or {}).get("primary")),
            None,
        )
        if primary is None:
            return
        citation = primary.get("citation") or {}
        citation["text"] = self._generated_citation_text()
        citation["bibtex"] = self._generated_citation_bibtex()
        primary["citation"] = citation

    @property
    def preview_citation_text(self):
        primary = self._citation_identifier()
        if primary:
            citation = primary.get("citation") or {}
            text = (citation.get("text") or "").strip()
            if text:
                return text
        return self._generated_citation_text()

    @property
    def preview_citation_bibtex(self):
        primary = self._citation_identifier()
        if primary:
            citation = primary.get("citation") or {}
            bibtex = (citation.get("bibtex") or "").strip()
            if bibtex:
                return bibtex
        return self._generated_citation_bibtex()

    @property
    def preview_citation_bibtex_block(self):
        return self._bibtex_details_block(self.preview_citation_bibtex)

    @staticmethod
    def _bibtex_details_block(bibtex_raw):
        bibtex_text = escape((bibtex_raw or "").replace("\\n", "\n"))
        return "\n".join([
            "<div style='margin-left: 2em;'>",
            "<details>",
            "<summary>BibTeX</summary>",
            "<textarea readonly rows=10 style='width: 100%; font-family: monospace;'>",
            bibtex_text,
            "</textarea>",
            "</details>",
            "</div>",
        ])

    @property
    def additional_references_block(self):
        parts = []
        for identifier in self.identifiers or []:
            if (identifier or {}).get("primary"):
                continue
            if not identifier.get("identifier"):
                continue
            citation = identifier.get("citation") or {}
            text = (citation.get("text") or "").strip()
            bibtex = (citation.get("bibtex") or "").strip()
            if text:
                display = self._linkify_urls(escape(text))
            else:
                display = self._identifier_as_link(identifier)
            item = [f"<li>{display}"]
            if bibtex:
                item.append(self._bibtex_details_block(bibtex))
            item.append("</li>")
            parts.append("\n".join(item))
        if not parts:
            return "**Additional references:** N/A"
        return "**Additional references:**\n\n<ul>\n" + "\n".join(parts) + "\n</ul>"

    @staticmethod
    def _linkify_urls(escaped_text):
        import re
        return re.sub(
            r"(https?://[^\s<]+?)(?=[.,;:)\]]*(?:\s|$))",
            lambda m: f"<a href='{m.group(1)}'>{m.group(1)}</a>",
            escaped_text,
        )

    @staticmethod
    def _identifier_as_link(identifier):
        value = (identifier.get("identifier") or "").strip()
        if not value:
            return ""
        if identifier.get("identifierType") == "DOI":
            href = f"https://doi.org/{value}"
            label = value
        else:
            href = value
            label = value
        return f"<a href='{escape(href)}'>{escape(label)}</a>"

    @property
    def citation_text(self):
        return self.preview_citation_text
    
    @property
    def html_preview(self):
        return markdown(self.markdown_preview, extensions=['markdown.extensions.tables'])
    
    @classmethod
    def from_json(cls, bytestring):
        product_json = json.loads(bytestring)
        difference = set(product_json.keys()) - set(cls.__dataclass_fields__)
        if difference:
            raise TypeError(f"Mismatching product fields in supplied .json:\n{difference}")
        return cls(**product_json)
    
    @classmethod
    def from_json_file(cls, path):
        with open(path, "r") as f:
            product_json = json.load(f)
        difference = set(product_json.keys()) - set(cls.__dataclass_fields__)
        if difference:
            raise TypeError(f"Mismatching product fields in supplied .json:\n{difference}")
        return cls(**product_json)


@dataclass
class Catalog:
    products: "dict[Product]"
    
    @property
    def product_ids(self):
        return list(self.products.keys())
    
    def get_product(self, product_id):
        return self.products.get(product_id)


def dump_html_output(html_directory):
    catalog = load_catalog()
    index_items = []
    product_ids = catalog.product_ids
    product_ids.sort()
    for id in product_ids:
        index_items.append(f"<a href='{id}.html'>{id}</a><br>")
        html = catalog.get_product(id).html_preview
        with open(os.path.join(html_directory, f"{id}.html"), "w") as f:
            f.write(html)
    index_content = "\n".join(index_items)
    with open(os.path.join(html_directory, "index.html"), "w") as f:
        f.write(index_content)
