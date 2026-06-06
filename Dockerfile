FROM python:3.12-slim@sha256:090ba77e2958f6af52a5341f788b50b032dd4ca28377d2893dcf1ecbdfdfe203

WORKDIR /app

# Install system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install ONNX Runtime + sentence-transformers (MLX/CoreML on Apple Silicon, CPU fallback elsewhere)
RUN pip install --no-cache-dir \
    onnxruntime \
    sentence-transformers \
    huggingface_hub \
    fastapi \
    uvicorn[standard] \
    pydantic \
    numpy \
    scipy

# Expose port
EXPOSE 8080

# Volume for model files
VOLUME ["/models"]

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "from sentence_transformers import SentenceTransformer; print('ok')" || exit 1

COPY server.py .

CMD ["python3", "server.py"]