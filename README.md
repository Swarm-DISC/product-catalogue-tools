# Product catalogue tools

## Development setup

```
git clone --recurse-submodules git@github.com:Swarm-DISC/product-catalogue-tools.git
```

Create a virtual environment with Python 3.12 (example shows [uv](https://docs.astral.sh/uv/), but other tools can be used)
```
uv venv --python 3.12
source .venv/bin/activate
uv pip install -r requirements.dev.txt
```

Develop using any editor and test the dashboard in the browser:
```
panel serve editor.py --autoreload
```

Or use JupyterLab:
```
jupyterlab
```
Right click on `editor.py` and select `Open With / Notebook`.

## Deployment options

### Docker

See `Dockerfile`

### WASM and Pyodide

See <https://panel.holoviz.org/how_to/wasm/standalone.html>
```
panel convert editor.py --to pyodide-worker --out pyodide --requirements requirements.editor.txt
```
This seems to require `editor.py` to be self contained, without local imports. And the catalogue loading needs to be changed to make http requests?
