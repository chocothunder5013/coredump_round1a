# Universal PDF Outline Extractor (Production - v4 Ultra-Lite)

An enterprise-grade, containerized solution for extracting structured outlines from any PDF file. This version is rebuilt for universal compatibility, supporting complex, multilingual, and unconventional layouts while maintaining a minimal footprint for production environments.

## Key Enhancements
- **Universal Compatibility**: A new style-based analysis engine detects headings by clustering font properties (size, weight, family). This allows it to understand the structure of complex, non-standard, and highly stylized documents, not just traditional business reports.
- **Enhanced Multilingual Support**: The core logic is language-agnostic, operating on visual cues rather than text content. This ensures consistent performance across documents in any language.
- **Ultra-Lite Docker Image**: Through advanced optimization, including binary stripping, the final `distroless` image size is reduced to **~180MB**, ensuring faster deployments and a minimal security footprint.

## How to Build and Run

### 1. Build the Docker Image
    docker build --platform linux/amd64 -t coredump:final-v4 .

### 2. Run the Container
    docker run --rm -v $(pwd)/input:/app/input -v $(pwd)/output:/app/output --network none coredump:final-v4

## Container Behavior
- The container processes all `*.pdf` files in `/app/input`.
- For each `filename.pdf`, a corresponding `filename.json` is generated in `/app/output`.