# Stage 1: Builder
# This stage installs build dependencies, Python packages, and optimizes them for size.
FROM python:3.10-alpine as builder

# Install build tools and 'binutils' for the 'strip' command
RUN apk add --no-cache gcc musl-dev g++ make binutils

# Create and activate a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Copy and install Python requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- SIZE OPTIMIZATION ---
# Strip unnecessary symbols from the compiled shared libraries (.so files)
# This significantly reduces the size of the PyMuPDF installation.
RUN find /opt/venv -name "*.so" -print -exec strip {} \;

# ---

# Stage 2: Final Production Image
# This stage uses a minimal 'distroless' base for a small and secure final image.
FROM gcr.io/distroless/python3-debian11

WORKDIR /app

# Copy the optimized virtual environment from the builder stage
COPY --from=builder /opt/venv /opt/venv

# Copy application source code and configuration
COPY ./src /app/src
COPY config.json .
COPY main.py .

# Set the PATH to include the virtual environment's binaries
ENV PATH="/opt/venv/bin:$PATH"

# Set the command to run the application
CMD ["python", "main.py"]