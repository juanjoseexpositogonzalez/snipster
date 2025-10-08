## ----------------------------------------- Builder Stage ----------------------------------------- ##
FROM python:3.13 AS builder

# Install system dependencies (no PostgreSQL needed)
RUN apt-get update && apt-get install --no-install-recommends -y \
    build-essential \
    curl \
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
COPY pyproject.toml uv.lock README.md ./
COPY src ./src

# Copy database if exists (SQLite is just a file)
COPY snipster.db* ./

# Install dependencies
RUN uv sync --no-dev

## ----------------------------------------- Production Stage ----------------------------------------- ##
FROM python:3.13-slim AS production

# Install only minimal runtime dependencies
RUN apt-get update && apt-get install --no-install-recommends -y \
    ca-certificates \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/* \
    && rm -rf /tmp/* \
    && rm -rf /var/tmp/*

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser

# Set working directory
WORKDIR /app

# Copy everything with correct ownership
COPY --from=builder --chown=appuser:appuser /app/.venv .venv
COPY --from=builder --chown=appuser:appuser /app/src ./src
COPY --from=builder --chown=appuser:appuser /app/snipster.db* ./
COPY --from=builder --chown=appuser:appuser /root/.local/bin/uv /usr/local/bin/uv

# Create startup script
RUN echo '#!/bin/bash\n\
set -e\n\
echo "Starting FastAPI server..."\n\
.venv/bin/python -m uvicorn snipster.api:app --host 0.0.0.0 --port 8000 &\n\
API_PID=$!\n\
echo "API started with PID: $API_PID"\n\
\n\
echo "Waiting for API to be ready..."\n\
sleep 10\n\
\n\
echo "Starting Streamlit app..."\n\
.venv/bin/streamlit run src/snipster/streamlit_app.py --server.port 8501 --server.address 0.0.0.0 &\n\
STREAMLIT_PID=$!\n\
echo "Streamlit started with PID: $STREAMLIT_PID"\n\
\n\
# Wait for any process to exit\n\
wait -n\n\
\n\
# Exit with status of process that exited first\n\
exit $?\n\
' > /app/start.sh && chmod +x /app/start.sh && chown appuser:appuser /app/start.sh

# Switch to non-root user
USER appuser

# Set up environment variables
ENV PATH="/app/.venv/bin:/usr/local/bin:$PATH"
ENV PYTHONPATH="/app/src"

# Expose ports
EXPOSE 8000 8501

# Use the startup script
CMD ["/app/start.sh"]
