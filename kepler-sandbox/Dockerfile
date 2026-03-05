# kepler-sandbox — isolated Python execution environment
# Build: docker build -t kepler-sandbox:latest ./kepler-sandbox
# No entrypoint — executed via `docker exec`

FROM python:3.11-slim

# Prevent interactive prompts and set working directory
ENV DEBIAN_FRONTEND=noninteractive \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# System deps for scientific / plotting libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
        gcc g++ libffi-dev libopenblas-dev libjpeg-dev libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Pre-install scientific Python stack
RUN pip install --no-cache-dir \
    pandas \
    numpy \
    matplotlib \
    seaborn \
    plotly \
    kaleido \
    scikit-learn \
    python-docx \
    reportlab \
    fpdf2 \
    openpyxl \
    python-pptx \
    xgboost \
    lightgbm \
    pillow \
    networkx \
    sympy \
    statsmodels \
    pyarrow \
    scipy \
    tabulate \
    joblib

# Create workspace dirs
RUN mkdir -p /workspace/input /workspace/output /workspace/code

WORKDIR /workspace

# No entrypoint — container stays alive via `tail -f /dev/null` or sleep
CMD ["tail", "-f", "/dev/null"]
