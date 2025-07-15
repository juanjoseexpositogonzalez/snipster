## ----------------------------------------- Builder Stage ----------------------------------------- ##
FROM python:3.13 AS builder

# Install system dependencies and upgrade packages to fix vulnerabilities
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
    # && apt-get upgrade -y \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install UV package manager
ADD https://astral.sh/uv/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

# Add uv to PATH
ENV PATH="/root/.local/bin/:$PATH"

# Desactiva el uso de .venv
ENV UV_VIRTUALENV_MANAGED=off

# Set working directory
WORKDIR /app

# Copy project files
COPY pyproject.toml uv.lock README.md snipster.db ./
COPY src ./src

# Install dependencies (locked to `pyproject.toml`)
RUN uv sync --no-dev

## ----------------------------------------- Production Stage ----------------------------------------- ##
FROM python:3.13 AS production

# Install only runtime dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Install system dependencies and upgrade packages to fix vulnerabilities
RUN useradd --create-home appuser
# Switch to non-root user
USER appuser

# Set working directory
WORKDIR /app

# COPY src ./src
# COPY --from=builder /app/.venv .venv
# Copy only source code and virtual environment
COPY --chown=appuser:appuser src ./src
COPY --from=builder --chown=appuser:appuser /app/.venv .venv
COPY --from=builder --chown=appuser:appuser /app/snipster.db snipster.db
# Copy uv executable from builder stage
# COPY --from=builder /root/.local/bin/uv /usr/local/bin/uv
COPY --from=builder --chown=appuser:appuser /root/.local/bin/uv /usr/local/bin/uv

# Set up environment variables for production
ENV PATH="/usr/local/bin:$PATH"

# Expose Streamlit port
EXPOSE 8501

# Expose API port
EXPOSE 8000

# Launch both API server and Streamlit app
CMD ["sh", "-c", "uv run fastapi dev src/snipster/api.py & uv run streamlit run src/snipster/streamlit_app.py"]
# CMD ["sh", "-c", "python -m snipster.api & streamlit run src/snipster/streamlit_app.py"]
