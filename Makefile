.PHONY: clean all

clean:
	rm -rf html
	rm -f table_for_DOIs.csv

html:
	mkdir -p html
	uv run python -c "from utils.catalog_utils import dump_html_output; dump_html_output('html')"
	uv run python generate_table_for_doi_team.py
	cp table_for_DOIs.csv html/table_for_DOIs.csv
	cp table_for_DOIs.html html/table_for_DOIs.html
	# Update index file
	echo "<h1>Product Catalogue</h1>" > html/index_new.html
	echo "<p><a href='table_for_DOIs.html'>CSV Table for DOI Team</a></p>" >> html/index_new.html
	echo "<h2>Individual Product Pages</h2>" >> html/index_new.html
	cat html/index.html >> html/index_new.html
	mv html/index_new.html html/index.html

all: html

serve:
	uv run python -m http.server 8000 --directory html
