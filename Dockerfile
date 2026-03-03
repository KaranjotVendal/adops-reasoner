FROM python:3.13-slim

WORKDIR /app

# Install uv for fast package management
RUN pip install uv

# Copy dependency files
COPY pyproject.toml ./

# Install dependencies
RUN uv sync --frozen --no-dev

# Copy source code
COPY src/ ./src/

# Expose port
EXPOSE 8080

# Default command (will be overridden by Cloud Run)
CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
