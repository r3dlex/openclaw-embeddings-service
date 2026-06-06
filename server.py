#!/usr/bin/env python3
"""
Openclaw Embeddings Service
Provides text embeddings using sentence-transformers with CoreML/ONNX acceleration on Apple Silicon.
"""
import logging
import os

import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("embeddings-service")

app = FastAPI(title="Openclaw Embeddings Service", version="1.0.0")

MODEL_NAME = os.environ.get("MODEL_NAME", "mlx-community/all-MiniLM-L6-v2-4bit")
MAX_BATCH_SIZE = int(os.environ.get("MAX_BATCH_SIZE", "32"))

_model = None


def get_model():
    global _model
    if _model is None:
        logger.info(f"Loading model: {MODEL_NAME}")
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(MODEL_NAME)
            logger.info("Model loaded successfully")
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            raise HTTPException(status_code=503, detail=f"Model loading failed: {e}") from e
    return _model


class EmbedRequest(BaseModel):
    texts: list[str]
    normalize: bool = True


class EmbedResponse(BaseModel):
    embeddings: list[list[float]]
    model: str
    dimensions: int


@app.get("/health")
async def health():
    return {"status": "ok", "model": MODEL_NAME}


@app.post("/embed", response_model=EmbedResponse)
async def embed(request: EmbedRequest):
    """Compute embeddings for a list of texts."""
    if not request.texts:
        raise HTTPException(status_code=400, detail="texts list cannot be empty")

    if len(request.texts) > MAX_BATCH_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"Batch size {len(request.texts)} exceeds maximum {MAX_BATCH_SIZE}"
        )

    try:
        model = get_model()

        # Encode with normalization
        embeddings = model.encode(
            request.texts,
            normalize_embeddings=request.normalize,
            convert_to_numpy=True
        )

        return EmbedResponse(
            embeddings=embeddings.tolist(),
            model=MODEL_NAME,
            dimensions=embeddings.shape[1]
        )
    except Exception as e:
        logger.error(f"Embedding failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8080"))
    uvicorn.run(app, host="0.0.0.0", port=port)
