# ---
# jupyter:
#   jupytext:
#     formats: py:percent
#     text_representation:
#       extension: .py
#       format_name: percent
#       format_version: '1.3'
#       jupytext_version: 1.16.4
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %% [markdown]
# # Tool for creating/editing Swarm product metadata

# %% [markdown]
# ## Preamble

# %%
from copy import deepcopy
import subprocess
import json

import panel as pn

# Update the product-catalogue submodule so we use the latest version online
try:
    subprocess.run(["git", "submodule", "update", "--init", "--recursive", "--remote"], check=True)
except subprocess.CalledProcessError:
    # when running in the docker container:
    subprocess.run(["git", "-C", "product-catalogue", "pull"], check=True)

# 'quill' is not working (used for TextEditor)
pn.extension('ace', 'jsoneditor', 'texteditor', 'tabulator', notifications=True, sizing_mode="stretch_width")

# %%
from utils.definitions import SPACECRAFT, SC2MISSIONS, THEMATIC_AREAS
from utils.catalog_utils import Product, Catalog, load_catalog, load_schema

# %%
def load_authors():
    """Load authors from authors.json file"""
    try:
        with open("authors.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        print("authors.json file not found")
        return {}

# %%
CATALOG = load_catalog()
SCHEMA = load_schema()
AUTHORS = load_authors()


# %%
# # Identify directory of this file
# try:
#     # when running in notebook
#     _here = globals()['_dh'][0]
# except KeyError:
#     try:
#         # when running in regular interpreter
#         _here = os.path.dirname(__file__)
#     except NameError:
#         pass
#         # some other options...
#         # _here = os.path.dirname(os.path.abspath(sys.argv[0]))
#         # command_output = subprocess.run("git rev-parse --show-toplevel".split(" "), stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
#         # git_dir = command_output.stdout.decode("utf-8").strip()
#         # _here = os.path.join(git_dir, "json")

# # CSV_PATH = os.path.join(_here, "input/overview.csv")
# # CSV_VARTABLES_PATH = os.path.join(_here, "input/vartables")
# JSON_FILES_PATH = os.path.join(_here, "catalog")
# JSON_SCHEMA_PATH = os.path.join(_here, "schema.json")
# # nb will only work when running from the same directory as this file
# # JSON_FILES_PATH = "catalog"
# # JSON_SCHEMA_PATH = "schema.json"

# %% [markdown]
# ## Demo Product & Catalog usage

# %%
# product = Product(
#     product_id="MAGx_LR_1B",
#     definition="Magnetic field (1Hz) from VFM and ASM",
#     description="The MAGX_LR_1B Product contains magnetic vector and scalar data at 1 Hz rate. The S/C data are processed to provide MAGX_LR_1B data at exact UTC seconds, i.e. both VFM vector and ASM scalar data are interpolated to yield these data. Hence, small gaps in the VFM or ASM data need not cause gaps in the product as the gaps may be filled by this interpolation. Any gaps, however, will have an impact on the error estimate of the associated product element.",
# )

# print(product.markdown_preview)

# %%
# c = Catalog(products={product.product_id: product})
# c.product_ids

# %%
# # Bulk fix files
# for id in CATALOG.product_ids:
#     p = CATALOG.get_product(id)
#     # new_id = id.replace("-", "_")
#     # p.product_id = new_id
#     # p.related_resources = ""
#     # for i in [0, 1]:
#     #     p.thematic_areas[i] = p.thematic_areas[i].strip()
#     # p.thematic_areas = [i for i in p.thematic_areas if i in Product.allowed_thematic_areas()]
#     # write them to a new directory
#     with open(f"catalog-2/{p.product_id}.json", "w") as f:
#         f.write(p.as_json())

# %% [markdown]
# ## Dashboard

# %%
class ProductMetadataDashboard:
    def __init__(self):
        # Internal product state, initialise empty
        self.product = Product()
        # Widgets to alter product state (call .refresh to trigger the update from these)
        # names (dict keys) must match properties of Product
        self.widgets = dict(
            product_id = pn.widgets.TextInput(name="product_id:", value=self.product.product_id),
            definition = pn.widgets.TextInput(name="definition:", value=self.product.definition),
            authors_container = pn.Column(),
            creation_year = pn.widgets.TextInput(
                name="creation_year:",
                value="",
                placeholder="e.g., 2024"
            ),
            product_types = pn.widgets.TextInput(
                name="product_types (comma-separated):",
                value=", ".join(self.product.product_types) if self.product.product_types else "",
                placeholder="e.g. SW_MAGA_LR_1B, SW_MAGB_LR_1B, SW_MAGC_LR_1B"
            ),
            applicable_spacecraft = pn.widgets.MultiChoice(name="applicable_spacecraft:", options=Product.allowed_spacecraft(), styles={"background": "white"}),
            # description = pn.widgets.TextEditor(
            #     name="description:", value=self.product.description,
            #     toolbar=[["bold", "italic", "code"], ["link"], [{ 'list': 'ordered'}, { 'list': 'bullet' }]],
            #     height=300, styles={"background": "white"}
            # ),
            description = pn.widgets.TextAreaInput(name="description: [text/html]", value=self.product.description, height=200, max_length=1000000),
            thematic_areas = pn.widgets.MultiChoice(name='Thematic areas:', options=Product.allowed_thematic_areas(), styles={"background": "white"}),
            link_files_http = pn.widgets.TextInput(placeholder='link_files_http'),
            link_files_ftp = pn.widgets.TextInput(placeholder='link_files_ftp'),
            link_vires_gui = pn.widgets.TextInput(placeholder='link_vires_gui'),
            link_notebook = pn.widgets.TextInput(placeholder='link_notebook'),
            link_hapi = pn.widgets.TextInput(placeholder='link_hapi'),
            variables_table = pn.widgets.TextAreaInput(name="variables_table [csv]:", value=self.product.variables_table, height=200, max_length=1000000),
            # details = pn.widgets.TextEditor(
            #     name="details:", value=self.product.details,
            #     toolbar=[["bold", "italic", "code"], ["link"], [{ 'list': 'ordered'}, { 'list': 'bullet' }], ["image"]],
            #     height=400, styles={"background": "white"}
            # ),
            details = pn.widgets.TextAreaInput(name="details: [text/html]", value=self.product.details, height=200, max_length=1000000),
            related_resources = pn.widgets.TextAreaInput(name="related_resources: [text/html]", value=self.product.related_resources, height=200),
            changelog = pn.widgets.TextAreaInput(name="changelog: [text/html]", value=self.product.related_resources, height=200),
            fast_processing = pn.widgets.Checkbox(name='Fast Processing'),
        )
        # Widgets to control dashboard
        self.widgets_extra = dict(
            product_id_selector=pn.widgets.AutocompleteInput(options=CATALOG.product_ids, placeholder="Start typing SW_MAG...", min_characters=1, case_sensitive=False, width=200),
            refresh_editor_button=pn.widgets.Button(name="Load", width=50, button_type="primary"),
            refresh_view_button=pn.widgets.Button(name="Refresh!", width=50, button_type="primary"),
            external_file_loader=pn.widgets.FileInput(),
            refresh_editor_button_from_file=pn.widgets.Button(name="Load", width=50, button_type="primary"),
        )
        self.widgets_extra["refresh_editor_button"].on_click(self.refresh_from_local)
        self.widgets_extra["refresh_view_button"].on_click(self.refresh_output)
        self.widgets_extra["refresh_editor_button_from_file"].on_click(self.refresh_from_external_file)
        
        # Initialize authors management
        self.author_widgets = []
        self.setup_authors_interface()
        # Tools to show the output view of the product
        self.json_viewer = pn.widgets.JSONEditor(
            value=self.product.as_dict(), schema=SCHEMA,
            mode="view",  max_height=1000
        )
        self.json_file = self.product.get_json_file()
        self.json_downloader = pn.widgets.FileDownload(
            file=self.json_file.name,
            filename=f"{self.product.product_id}.json",
        )
        self.markdown_viewer = pn.pane.Markdown(self.product.markdown_preview, styles={"background": "white"}, sizing_mode="stretch_both", max_height=1000)
#         self.html_viewer = pn.pane.HTML(self.product.html_preview)

        # Instantiate from URL key
        pid_from_url = pn.state.location.search.strip("?") if pn.state.location else ""
        pid_to_load = pid_from_url if pid_from_url else "SW_MAGx_LR_1B"
        self.widgets_extra["product_id_selector"].value = pid_to_load
        self.refresh_from_local(None)
    
    @staticmethod
    def _sanitise_text_input(s):
        return s.replace("\n", "").replace("\t", "")
    
    def setup_authors_interface(self):
        """Initialize the authors interface with existing authors or one empty author"""
        self.author_widgets = []
        
        # Add existing authors or at least one empty author
        if self.product.authors:
            for author in self.product.authors:
                self.add_author_widget(author)
        else:
            self.add_author_widget()
        
        self.update_authors_container()
    
    def add_author_widget(self, author=None):
        """Add a new author widget set"""
        author = author or {"name": "", "ror": ""}
        
        # Find matching abbreviation for existing author
        selected_abbrev = ""
        if author.get("name"):
            for abbrev, info in AUTHORS.items():
                if info["name"] == author["name"] or info.get("ror", "") == author.get("ror", ""):
                    selected_abbrev = abbrev
                    break
        
        author_select = pn.widgets.Select(
            name=f"Organization {len(self.author_widgets) + 1}:",
            options=[""] + list(AUTHORS.keys()),
            value=selected_abbrev,
            width=200
        )
        
        author_name = pn.widgets.TextInput(
            name="Name:",
            value=author.get("name", ""),
            placeholder="Organization name",
            disabled=True,
            width=250
        )
        
        author_ror = pn.widgets.TextInput(
            name="ROR:",
            value=author.get("ror", ""),
            placeholder="https://ror.org/xxxxxxxxx",
            disabled=True,
            width=250
        )
        
        remove_button = pn.widgets.Button(
            name="Remove",
            button_type="danger",
            width=80,
            margin=(25, 5, 5, 5)
        )
        
        # Set up callbacks
        author_index = len(self.author_widgets)
        author_select.param.watch(
            lambda event, idx=author_index: self.on_author_select(event, idx), 
            "value"
        )
        remove_button.on_click(
            lambda event, idx=author_index: self.remove_author_widget(idx)
        )
        
        author_widget_set = {
            "select": author_select,
            "name": author_name,
            "ror": author_ror,
            "remove": remove_button
        }
        
        self.author_widgets.append(author_widget_set)
        
        # Update the select widget to trigger the callback
        if selected_abbrev:
            self.on_author_select(type('Event', (), {'new': selected_abbrev})(), author_index)
    
    def remove_author_widget(self, index):
        """Remove an author widget set"""
        if len(self.author_widgets) > 1:  # Keep at least one author widget
            self.author_widgets.pop(index)
            # Re-index the remaining widgets
            for i, widget_set in enumerate(self.author_widgets):
                widget_set["select"].name = f"Organization {i + 1}:"
                # Update callbacks with new indices
                widget_set["select"].param.unwatch(widget_set["select"].param.watchers)
                widget_set["select"].param.watch(
                    lambda event, idx=i: self.on_author_select(event, idx), 
                    "value"
                )
                widget_set["remove"].on_click(
                    lambda event, idx=i: self.remove_author_widget(idx)
                )
            self.update_authors_container()
    
    def on_author_select(self, event, author_index):
        """Update author name and ROR when organization is selected"""
        selected_abbrev = event.new
        if author_index < len(self.author_widgets):
            if selected_abbrev and selected_abbrev in AUTHORS:
                self.author_widgets[author_index]["name"].value = AUTHORS[selected_abbrev]["name"]
                self.author_widgets[author_index]["ror"].value = AUTHORS[selected_abbrev].get("ror", "")
            else:
                self.author_widgets[author_index]["name"].value = ""
                self.author_widgets[author_index]["ror"].value = ""
    
    def add_new_author(self, event):
        """Add a new empty author widget"""
        self.add_author_widget()
        self.update_authors_container()
    
    def update_authors_container(self):
        """Update the authors container with current widgets"""
        author_rows = []
        
        for widget_set in self.author_widgets:
            author_row = pn.Row(
                widget_set["select"],
                widget_set["name"],
                widget_set["ror"],
                widget_set["remove"],
                sizing_mode="stretch_width"
            )
            author_rows.append(author_row)
        
        add_button = pn.widgets.Button(
            name="+ Add Author",
            button_type="primary",
            width=120
        )
        add_button.on_click(self.add_new_author)
        
        self.widgets["authors_container"][:] = [
            pn.pane.Markdown("**Authors:**"),
            *author_rows,
            add_button
        ]
    
    def refresh_output(self, event):
        # Update Product attributes
        for k in self.widgets.keys():
            # Skip authors_container as it's handled separately
            if k == "authors_container":
                continue
                
            value = self.widgets[k].value
            # Special handling for creation_year field
            if k == "creation_year":
                if value and value.strip():
                    try:
                        value = int(value.strip())  # Store as integer year
                    except ValueError:
                        value = None  # Invalid year input
                else:
                    value = None
            # Special handling for product_types comma-separated input
            elif k == "product_types":
                if isinstance(value, str):
                    value = [item.strip() for item in value.split(",") if item.strip()]
            # if k in ("details", "related_resources"):
            #     value = self._sanitise_text_input(value)
            setattr(self.product, k, value)
        
        # Handle authors from multiple author widgets
        authors = []
        for widget_set in self.author_widgets:
            author_name = widget_set["name"].value.strip()
            author_ror = widget_set["ror"].value.strip()
            if author_name:  # Only add authors with names
                author = {"name": author_name}
                if author_ror:
                    author["ror"] = author_ror
                authors.append(author)
        self.product.authors = authors
            
        self.product.applicable_spacecraft.sort()
        self.product.applicable_missions = list(set([SC2MISSIONS.get(sc, "ERROR") for sc in self.product.applicable_spacecraft]))
        self.product.applicable_missions.sort()
        # Update
        self.json_file = self.product.get_json_file()
        self.json_downloader.file = self.json_file.name
        self.json_downloader.filename = f"{self.product.product_id}.json"
        self.json_viewer.value = self.product.as_dict()
        self.markdown_viewer.object = self.product.markdown_preview
#         self.html_viewer.object = self.product.html_preview
        # Update url of dashboard
        if pn.state.location:
            pn.state.location.search = f"?{self.product.product_id}"
    
    def refresh_from_local(self, event):
        product_id = self.widgets_extra["product_id_selector"].value
        if product_id in CATALOG.product_ids:
            self.update_product(CATALOG.get_product(product_id))
    
    def refresh_from_external_file(self, event):
        self.update_product(
            Product.from_json(self.widgets_extra["external_file_loader"].value)
        )
    
    def update_product(self, product):
        self.product = deepcopy(product)
        for k in self.widgets.keys():
            # Skip authors_container as it's handled separately
            if k == "authors_container":
                continue
            else:
                value = getattr(self.product, k)
                # Special handling for creation_year field - handle both integer and string formats
                if k == "creation_year" and value:
                    try:
                        if isinstance(value, int):
                            value = str(value)  # Convert integer year to string for display
                        elif isinstance(value, str):
                            # Handle legacy ISO datetime strings - extract year
                            year = value.split('-')[0]
                            value = year
                        else:
                            value = ""
                    except (ValueError, TypeError, IndexError):
                        value = ""
                # Special handling for product_types to display as comma-separated
                elif k == "product_types" and isinstance(value, list):
                    value = ", ".join(value)
            self.widgets[k].value = value
        
        # Handle authors separately - recreate author widgets
        self.setup_authors_interface()
        self.refresh_output(None)    

    @property
    def loader(self):
        return pn.Row(
            pn.Column(
                "**Load from existing records**",
                pn.Row(
                    self.widgets_extra["product_id_selector"],
                    self.widgets_extra["refresh_editor_button"],
                ),
                styles={"background": "orange"},
                margin=10,
                sizing_mode="stretch_both"
            ),
            pn.Column(
                "**Load from local file**",
                pn.Row(
                    self.widgets_extra["external_file_loader"],
                    self.widgets_extra["refresh_editor_button_from_file"],
                ),
                styles={"background": "orange"},
                margin=10,
                sizing_mode="stretch_both"
            ),
            sizing_mode="stretch_both"
        )
    
    @property
    def instructions(self):
        return pn.pane.Markdown(
            """
            This tool helps generate records held at <https://github.com/Swarm-DISC/product-catalogue> which are used to generate the [Swarm Product Handbook](https://swarmhandbook.earth.esa.int/catalogue/index).
            You can also see [previews here](https://swarm-disc.github.io/product-catalogue-tools/).
            
            - **Left panel:** data entry; **Right panel:** preview (JSON | Output preview)
            - Enter information in the left panel, then click "Refresh!" at the top right to update the preview
            - Download the new/updated json file and [upload to Ashley to review here](https://cloud.mag.earth/s/K52yEk8cyraFQZQ) or make a PR to the [git repo](https://github.com/Swarm-DISC/product-catalogue)
            - See more notes [in the wiki](https://github.com/Swarm-DISC/product-catalogue/wiki)
            - **Hints:**
                - For HTML fields (description, details), use an editor such as <https://onlinehtmleditor.dev/>
                - Might be useful for working with tables: <https://tableconvert.com/> and <https://www.tablesgenerator.com/html_tables>
                - Some validation of the inputs is indicated in the JSON viewer - ignore the warnings on empty fields
                - Point to this dashboard preloaded with an existing record by adding the product id to the end of the url, e.g.:  
                  <https://dev.swarmdisc.org/product-catalogue-tools/editor?SW_FAC_LLS_2F>
            """
        )
        
    @property
    def editor(self):
        return pn.Column(
            self.widgets["product_id"],
            self.widgets["fast_processing"],
            self.widgets["definition"],
            self.widgets["authors_container"],
            self.widgets["creation_year"],
            self.widgets["product_types"],
            self.widgets["thematic_areas"],
            self.widgets["applicable_spacecraft"],
            "Links:",
            self.widgets["link_files_http"],
            self.widgets["link_files_ftp"],
            self.widgets["link_vires_gui"],
            self.widgets["link_notebook"],
            self.widgets["link_hapi"],
            self.widgets["description"],
            self.widgets["variables_table"],
            self.widgets["details"],
            self.widgets["related_resources"],
            self.widgets["changelog"],
            # styles={"background": "lightblue"},
            sizing_mode="stretch_both"
        )

    @property
    def viewer(self):
        return pn.Card(
            pn.Column(
                pn.Column(
                    "**Check display preview and download output json**",
                    self.widgets_extra["refresh_view_button"],
                    self.json_downloader,
                    styles={"background": "lightgreen"},
                ),
                pn.Tabs(
                    ("Output preview", self.markdown_viewer),
                    ("JSON", self.json_viewer),
                    sizing_mode="stretch_both",
                ),
                # styles={"background": "lightgreen"},
                sizing_mode="stretch_both",
            ),
            sizing_mode="stretch_both",
            title="Previews",
            collapsible=False,
            margin=10,
        )

    @property
    def complete(self):
        gspec = pn.GridSpec(sizing_mode="stretch_both", margin=10)#min_height=3000)
        gspec[:, 0] = pn.Accordion(
            ("Instructions", self.instructions),
            ("Load data", self.loader),
            ("Edit properties", self.editor),
            margin=10,
            # sizing_mode="stretch_both",
            active = [0, 1, 2]
        )
        gspec[:, 1] = self.viewer
        return gspec


# %%
# pn.config.exception_handler = lambda x: pn.state.notifications.error(x, duration=3000)
# pn.state.notifications.position = 'top-right'

# %%
dashboard = ProductMetadataDashboard()

# %%
dashboard.complete.servable(title="JSON author - Swarm Data Handbook")
