"""
패턴 1: 프록시 패턴 — 트랜스포트 브리징

프록시는 MCP 서버 중개자로, 요청을 백엔드 서버로 포워딩한다.
핵심 사용 사례: stdio ↔ HTTP 트랜스포트 변환
"""

from fastmcp.server import create_proxy
from fastmcp.client.transports import NpxStdioTransport, UvxStdioTransport

# ──────────────────────────────────────────────
# 1. HTTP → stdio 브리징
#    Claude Desktop(stdio)이 원격 HTTP 서버를 사용
# ──────────────────────────────────────────────

http_proxy = create_proxy(
    "http://example.com/mcp/sse",
    name="HTTP-to-stdio-Proxy",
)


# ──────────────────────────────────────────────
# 2. stdio → HTTP 브리징
#    로컬 서버를 네트워크에 HTTP로 노출
# ──────────────────────────────────────────────

local_proxy = create_proxy(
    "./my_local_server.py",
    name="stdio-to-HTTP-Proxy",
)


# ──────────────────────────────────────────────
# 3. NPM / UVX 패키지 기반 프록시
# ──────────────────────────────────────────────

github_proxy = create_proxy(
    NpxStdioTransport(package="@modelcontextprotocol/server-github"),
    name="GitHub-Proxy",
)

sqlite_proxy = create_proxy(
    UvxStdioTransport(tool_name="mcp-server-sqlite", tool_args=["--db", "data.db"]),
    name="SQLite-Proxy",
)


# ──────────────────────────────────────────────
# 실행
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # stdio로 실행 (Claude Desktop용)
    # http_proxy.run()

    # HTTP로 실행 (네트워크 노출)
    local_proxy.run(transport="http", host="0.0.0.0", port=8080)
