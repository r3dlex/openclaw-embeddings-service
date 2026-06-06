# Openclaw Embeddings Service

Centralized MLX text embeddings service for the Openclaw multi-agent system. Runs locally on Apple Silicon and is reachable by all containerized agents via `http://host.docker.internal:18795`. Provides fast, memory-efficient vector embeddings using a 4-bit quantized model — no GPU required.

**Requires Apple Silicon (ARM64)** — uses the Apple MLX framework for on-device inference.

## Features

- Single `POST /embed` endpoint accepting batches of texts
- 4-bit quantized `all-MiniLM-L6-v2` model via `mlx-community`
- Under 512MB memory footprint
- Shared across all Openclaw agents via `EMBEDDINGS_URL=http://host.docker.internal:18795`

## Architecture

- **Language**: Python / FastAPI
- **IAMQ ID**: N/A (infrastructure service, not an agent)
- **Runtime**: Docker (ARM64 / Apple Silicon required)
- **Port**: `18795`

## Setup

```bash
docker build -t openclaw-embeddings .
docker run -p 18795:18795 openclaw-embeddings
```

Verify:

```bash
curl http://localhost:18795/health
```

## API

### `GET /health`

Returns service status.

```json
{"status": "ok", "model": "mlx-community/all-MiniLM-L6-v2-4bit"}
```

### `POST /embed`

Compute embeddings for one or more texts.

**Request:**
```json
{
  "texts": ["Hello world", "Another text"],
  "normalize": true
}
```

**Response:**
```json
{
  "embeddings": [[0.1, 0.2, ...], [0.3, 0.4, ...]],
  "model": "mlx-community/all-MiniLM-L6-v2-4bit",
  "dimensions": 384
}
```

## Agent Integration

All Openclaw agents connect via the `EMBEDDINGS_URL` environment variable, which is pre-configured in each agent's `docker-compose.yml`:

```yaml
environment:
  - EMBEDDINGS_URL=http://host.docker.internal:18795
```

No additional configuration is required in individual agents.

## Links

- [openclaw-inter-agent-message-queue](https://github.com/r3dlex/openclaw-inter-agent-message-queue) — IAMQ backbone
- [Openclaw Documentation](https://docs.openclaw.ai/)
