# Backend

FastAPI Python application serving as the API backend for the chatbot demo.

## Overview

The backend handles:
- Multi-model LLM integration (local models)
- Document ingestion and vector storage for RAG
- WebSocket connections for real-time chat streaming
- Image processing and analysis
- Chat history management
- Model Control Protocol (MCP) integration

## Key Features

- **Multi-model support**: Integrates various LLM providers and local models
- **RAG pipeline**: Document processing, embedding generation, and retrieval
- **Streaming responses**: Real-time token streaming via WebSocket
- **Image analysis**: Multi-modal capabilities for image understanding
- **Vector database**: Efficient similarity search for document retrieval
- **Session management**: Chat history and context persistence

## Architecture

FastAPI application with async support, integrated with vector databases for RAG functionality and WebSocket endpoints for real-time communication.

## Revit MCP (Python)

This backend can optionally load a Revit MCP server via environment variables. First, enable it:

```bash
export REVIT_MCP_ENABLED=1
```

Two common setups:

1. Revit MCP Python repo (stdio): set `REVIT_MCP_MAIN` to the absolute path of `main.py`. The backend will run it with `uv run --with mcp[cli] mcp run /absolute/path/to/main.py` (the same pattern shown in the Revit MCP Python README).
2. Remote server (streamable HTTP): set `REVIT_MCP_URL` to the MCP endpoint (for example `http://localhost:8000/mcp`) and `REVIT_MCP_TRANSPORT=streamable_http`.
3. Remote server (HTTP/SSE): set `REVIT_MCP_URL` to the MCP endpoint (for example `http://localhost:8010/mcp`) and `REVIT_MCP_TRANSPORT=sse`.

Optional overrides:
- `REVIT_MCP_COMMAND` and `REVIT_MCP_ARGS` let you supply a custom command; `REVIT_MCP_ARGS` is parsed with shell-style quoting.

Example using the Revit MCP Python repo:
```bash
export REVIT_MCP_MAIN=/absolute/path/to/revit-mcp-python/main.py
```

Example using the `revit-mcp` Python package (uvx):
```bash
export REVIT_MCP_COMMAND=uvx
export REVIT_MCP_ARGS="revit-mcp"
```

### Per-Chat Revit MCP

You can bind a different Revit MCP server per chat. This is useful when each user has their own Revit instance.

Set (or clear) the Revit MCP endpoint for a chat (streamable HTTP):
```bash
curl -X POST http://localhost:8000/chat/<chat_id>/revit \
  -H "Content-Type: application/json" \
  -d '{"revit_mcp_url":"http://<windows-ip>:8000/mcp","revit_mcp_transport":"streamable_http"}'
```

HTTP/SSE variant:
```bash
curl -X POST http://localhost:8000/chat/<chat_id>/revit \
  -H "Content-Type: application/json" \
  -d '{"revit_mcp_url":"http://<windows-ip>:8010/mcp","revit_mcp_transport":"sse"}'
```

Fetch current settings:
```bash
curl http://localhost:8000/chat/<chat_id>/revit
```

Auto-configure Revit MCP using the caller's IP (no user input required):
```bash
curl -X POST http://localhost:8000/chat/<chat_id>/revit/auto
```

Optional headers (if you need non-defaults):
```bash
# defaults:
# - streamable_http: port=8000, path=/mcp
# - sse: port=8010, path=/mcp
curl -X POST http://localhost:8000/chat/<chat_id>/revit/auto \
  -H "x-revit-mcp-port: 8000" \
  -H "x-revit-mcp-path: /mcp" \
  -H "x-revit-mcp-transport: streamable_http"
```

Health checks:
```bash
# Uses the saved MCP URL/transport for the chat
curl http://localhost:8000/chat/<chat_id>/revit/health

# Uses caller headers (no chat required)
curl http://localhost:8000/revit/health \
  -H "x-revit-mcp-url: http://<windows-ip>:8000/mcp" \
  -H "x-revit-mcp-transport: streamable_http"
```

## Docker Troubleshooting

### Container Issues
- **Port conflicts**: Ensure port 8000 is not in use
- **Memory issues**: Backend requires significant RAM for model loading
- **Startup failures**: Check if required environment variables are set

### Model Loading Problems
```bash
# Check model download status
docker logs backend | grep -i "model"

# Verify model files exist
docker exec -it cbackend ls -la /app/models/

# Check available disk space
docker exec -it backend df -h
```

### Common Commands
```bash
# View backend logs
docker logs -f backend

# Restart backend container
docker restart backend

# Rebuild backend
docker-compose up --build -d backend

# Access container shell
docker exec -it backend /bin/bash

# Check API health
curl http://localhost:8000/health
```

### Performance Issues
- **Slow responses**: Check GPU availability and model size
- **Memory errors**: Increase Docker memory limit or use smaller models
- **Connection timeouts**: Verify WebSocket connections and firewall settings
