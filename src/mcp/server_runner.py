#!/usr/bin/env python3
"""
MCP Server Runner - Entry point for Code Intern MCP Server.

MCP Protocol runs on STDIO (not HTTP) for Claude Desktop integration.
Optional: HTTP debug server on port 9876 for testing.

Usage:
    # MCP mode (stdio - for Claude Desktop):
    python -m src.mcp.server_runner

    # HTTP debug mode (port 9876 - for browser testing):
    python -m src.mcp.server_runner --http
"""

import sys
import argparse
import dspy
from src.common.config import settings


def configure_dspy():
    """Configure DSPy with Ollama"""
    print(f"[DSPy] Configuring with model: {settings.model_name}", file=sys.stderr)
    print(f"[DSPy] Ollama base URL: {settings.ollama_base_url}", file=sys.stderr)

    lm = dspy.LM(
        model=f"ollama_chat/{settings.model_name}",
        api_base=settings.ollama_base_url,
        api_key="",  # Not needed for Ollama
        temperature=settings.temperature,
        max_tokens=settings.max_tokens
    )

    dspy.configure(lm=lm)
    print("[DSPy] Configured successfully ✓", file=sys.stderr)


def run_mcp_server():
    """Run MCP server on stdio (for Claude Desktop)"""
    from src.mcp.fastmcp_server import mcp

    print("[MCP] Starting Code Intern MCP Server", file=sys.stderr)
    print("[MCP] Protocol: stdio (JSON-RPC)", file=sys.stderr)
    print("[MCP] Waiting for MCP client connection...", file=sys.stderr)
    print("", file=sys.stderr)

    # FastMCP.run() uses stdio by default
    mcp.run()


def run_http_server():
    """Run HTTP debug server on port 9876"""
    from src.mcp.fastmcp_server import mcp

    PORT = 9876  # Uncommon port to avoid conflicts

    print(f"[HTTP] Starting HTTP Debug Server", file=sys.stderr)
    print(f"[HTTP] URL: http://localhost:{PORT}", file=sys.stderr)
    print(f"[HTTP] Open in browser to test tools/resources", file=sys.stderr)
    print("", file=sys.stderr)

    # Run HTTP server for debugging
    mcp.run(transport="sse", port=PORT)


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Code Intern MCP Server"
    )
    parser.add_argument(
        "--http",
        action="store_true",
        help="Run HTTP debug server (port 9876) instead of stdio"
    )

    args = parser.parse_args()

    try:
        # Configure DSPy first
        configure_dspy()

        # Run appropriate server mode
        if args.http:
            run_http_server()
        else:
            run_mcp_server()

    except KeyboardInterrupt:
        print("\n[Server] Shutting down...", file=sys.stderr)
    except Exception as e:
        print(f"\n[Error] {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
