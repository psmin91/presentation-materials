"""
FastMCP Proxy 서버 예제
=======================
원격 MCP 서버를 프록시하여 로컬 도구와 통합하는 예제입니다.

실행: python proxy_example.py
"""

from fastmcp import FastMCP
from fastmcp.server import create_proxy


# ============================================================
# 원격 MCP 서버를 프록시로 생성
# ============================================================

# 방법 1: create_proxy로 간단하게
remote_proxy = create_proxy("http://remote-server:9000/mcp")

# 방법 2: ProxyProvider를 직접 사용 (세밀한 제어)
# from fastmcp.server.providers import ProxyProvider
# from fastmcp import Client
#
# client = Client("http://remote-server:9000/mcp")
# provider = ProxyProvider(client=client)
# proxy_server = FastMCP("Custom Proxy", providers=[provider])


# ============================================================
# 하이브리드 Router: 로컬 + 원격
# ============================================================
router = FastMCP(
    name="Hybrid Router",
    instructions="로컬 도구와 원격 MCP 서버를 통합한 하이브리드 라우터입니다.",
)


@router.tool(tags={"core"})
def local_status() -> dict:
    """로컬 서버 상태를 확인합니다"""
    return {
        "status": "healthy",
        "local_tools": ["local_status"],
        "remote_prefix": "remote_*",
    }


# 원격 서버를 "remote" 네임스페이스로 마운트
router.mount(remote_proxy, prefix="remote")


# ============================================================
# 여러 원격 서버 통합 예제
# ============================================================
def create_multi_proxy_router():
    """여러 원격 MCP 서버를 하나의 Router로 통합"""
    multi_router = FastMCP("Multi-Proxy Router")

    # 각 원격 서버를 별도 네임스페이스로 마운트
    servers = {
        "db": "http://db-server:8001/mcp",
        "search": "http://search-server:8002/mcp",
        "notify": "http://notify-server:8003/mcp",
    }

    for prefix, url in servers.items():
        proxy = create_proxy(url)
        multi_router.mount(proxy, prefix=prefix)

    return multi_router


if __name__ == "__main__":
    router.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
        path="/mcp",
    )
