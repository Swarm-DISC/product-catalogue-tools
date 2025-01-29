# Setup with uv
# https://docs.astral.sh/uv/guides/integration/docker/
FROM python:3.12-slim-bullseye
COPY --from=ghcr.io/astral-sh/uv:0.5.25 /uv /bin/uv
ENV UV_NO_CACHE=1

# Install Git
RUN apt-get update && apt-get install -y git && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install dependencies and activate environment
COPY pyproject.toml .
COPY uv.lock .
RUN uv sync --frozen
ENV PATH="/app/.venv/bin:$PATH"

COPY ./utils utils
COPY ./editor.py editor.py

RUN git clone https://github.com/Swarm-DISC/product-catalogue.git

CMD ["panel", "serve", "editor.py", "--address", "0.0.0.0", "--port", "5006",  "--allow-websocket-origin", "*"]
