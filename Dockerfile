# Start with a Python 3.12 slim image
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONFAULTHANDLER=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONHASHSEED=random \
    PIP_DEFAULT_TIMEOUT=100

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv directly using pip
RUN pip install --no-cache-dir uv

# Create and set working directory
WORKDIR /app

# Copy only necessary files for installation
COPY pyproject.toml poetry.lock* README.md ./
COPY imas_standard_names/ ./imas_standard_names/

# Copy git files essential  for versioning
COPY .git/HEAD ./.git/HEAD
COPY .git/refs/ ./.git/refs/
COPY .git/objects/ ./.git/objects/
COPY .git/packed-refs ./.git/packed-refs
COPY .git/config ./.git/config

# Install dependencies with uv, including the agent extra
RUN uv pip install --no-cache-dir --system --editable .[agent]

# Create a slim production image
FROM python:3.12-slim AS runtime

WORKDIR /app

# Copy installed packages and necessary application files from builder
COPY --from=builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=builder /app/imas_standard_names /app/imas_standard_names
COPY --from=builder /app/pyproject.toml /app/

# Set the entrypoint
ENTRYPOINT ["python", "-m", "imas_standard_names.mcp_imas"]