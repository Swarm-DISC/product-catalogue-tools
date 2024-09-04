# Setup with uv
# https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.12-slim-bullseye
COPY --from=ghcr.io/astral-sh/uv:0.4.4 /uv /bin/uv
ENV UV_NO_CACHE=1

WORKDIR /app

# Install dependencies and activate environment
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

COPY ./utils utils
COPY ./editor.py editor.py
COPY product-catalogue product-catalogue

CMD ["panel", "serve", "editor.py", "--address", "0.0.0.0", "--port", "5006",  "--allow-websocket-origin", "*"]
