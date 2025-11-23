# Code Intern MCP Server - Quick Start

## Running the Server in VSCode

### Option 1: Terminal (Recommended for testing)

Open VSCode integrated terminal and run:

```bash
# MCP mode (stdio) - for Claude Desktop integration
python -m src.mcp.server_runner

# HTTP debug mode - for browser testing (port 9876)
python -m src.mcp.server_runner --http
```

### Option 2: Python Debugger

1. Press `F5` or click "Run and Debug" in VSCode
2. Select one of:
   - **"🦖 MCP Server (stdio)"** - For Claude Desktop
   - **"🌐 MCP Server (HTTP Debug)"** - For browser testing at http://localhost:9876

---

## Understanding MCP vs HTTP

### MCP Mode (stdio)
- **Protocol**: JSON-RPC over stdin/stdout
- **Port**: None (uses standard input/output)
- **Use**: Claude Desktop, MCP clients
- **How it works**: The server waits for JSON messages on stdin and responds on stdout

### HTTP Debug Mode (port 9876)
- **Protocol**: HTTP/SSE (Server-Sent Events)
- **Port**: 9876 (uncommon port to avoid conflicts)
- **Use**: Testing in browser, Postman, curl
- **URL**: http://localhost:9876

**Why not FastAPI?** MCP uses a different protocol (JSON-RPC) that doesn't need HTTP. FastMCP can expose HTTP for debugging, but the real MCP protocol is stdio-based.

---

## Testing the Server

### Test with HTTP mode:

1. Start server:
   ```bash
   python -m src.mcp.server_runner --http
   ```

2. Open browser to http://localhost:9876

3. You should see FastMCP interface with available tools:
   - `start_coding_task`
   - `answer_requirement`
   - `get_task_status`
   - etc.

### Test with MCP mode:

1. Start server:
   ```bash
   python -m src.mcp.server_runner
   ```

2. Server will wait for MCP client connection via stdin

3. Configure Claude Desktop to use this server (see MCP_SETUP.md)

---

## Expected Output

### Stdio mode:
```
[DSPy] Configuring with model: mistral:7b
[DSPy] Ollama base URL: http://localhost:11434
[DSPy] Configured successfully ✓
[MCP] Starting Code Intern MCP Server
[MCP] Protocol: stdio (JSON-RPC)
[MCP] Waiting for MCP client connection...
```

### HTTP mode:
```
[DSPy] Configuring with model: mistral:7b
[DSPy] Ollama base URL: http://localhost:11434
[DSPy] Configured successfully ✓
[HTTP] Starting HTTP Debug Server
[HTTP] URL: http://localhost:9876
[HTTP] Open in browser to test tools/resources
```

---

## Troubleshooting

### Port 9876 already in use?

Change the port in `src/mcp/server_runner.py` line 56:
```python
PORT = 9876  # Change to any uncommon port (9999, 8765, etc.)
```

### Ollama not running?

Start Ollama first:
```bash
ollama serve
```

### Model not found?

Pull the model:
```bash
ollama pull mistral:7b
# or
ollama pull qwen3:8b
```

### Import errors?

Make sure you're in the project root and PYTHONPATH is set:
```bash
cd /home/riju279/Downloads/demo
export PYTHONPATH=/home/riju279/Downloads/demo
python -m src.mcp.server_runner
```

---

## Next Steps

1. **Test locally**: Use HTTP mode to test tools
2. **Integrate with Claude**: Use stdio mode with Claude Desktop
3. **Run demo**: `python demosaur.py` for full workflow demo

See `docs/MCP_IMPROVEMENTS.md` for features and capabilities.
