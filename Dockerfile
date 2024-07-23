# Setup with uv
# https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
FROM python:3.12-slim-bullseye
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv
ENV UV_SYSTEM_PYTHON=1

WORKDIR /app

COPY requirements.editor.txt .
RUN uv pip install -r requirements.editor.txt

COPY ./utils utils
COPY ./editor.py editor.py
COPY product-catalogue product-catalogue

CMD ["panel", "serve", "editor.py", "--address", "0.0.0.0", "--port", "5006",  "--allow-websocket-origin", "*"]
