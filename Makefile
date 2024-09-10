.PHONY: clean

clean:
	rm -rf html

html:
	mkdir html
	uv run python -c "from utils.catalog_utils import dump_html_output; dump_html_output('html')"
