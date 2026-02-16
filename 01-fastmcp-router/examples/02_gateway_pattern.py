"""
패턴 2: 게이트웨이 패턴 — 보안/정책 단일 진입점

여러 백엔드 MCP 서버 앞에 인증·로깅·정책을 적용하는 단일 진입점.
FastMCP에는 전용 Gateway 클래스가 없다 — ProxyProvider + Transforms + 미들웨어 조합.
"""

from fastmcp import FastMCP
from fastmcp.server import create_proxy

# ──────────────────────────────────────────────
# 게이트웨이 서버 생성
# ──────────────────────────────────────────────

gateway = FastMCP("MCP Gateway")

# 복수의 백엔드 서비스 마운트
gateway.mount(create_proxy("http://service-a.internal/mcp"), namespace="svc_a")
gateway.mount(create_proxy("http://service-b.internal/mcp"), namespace="svc_b")
gateway.mount(create_proxy("http://service-c.internal/mcp"), namespace="svc_c")


# ──────────────────────────────────────────────
# 로컬 게이트웨이 도구
# ──────────────────────────────────────────────

@gateway.tool
def gateway_health() -> str:
    """게이트웨이 상태 확인"""
    return "Gateway is operational"


@gateway.tool(tags={"internal"})
def gateway_metrics() -> dict:
    """내부 메트릭스 (외부 비노출)"""
    return {"uptime": "99.9%", "requests": 12345}


# ──────────────────────────────────────────────
# 가시성 제어 — Transform 기반
# ──────────────────────────────────────────────

# 내부 태그 도구 숨기기
gateway.disable(tags={"internal"})

# 또는 화이트리스트 모드: 공개 도구만 노출
# gateway.enable(tags={"public"}, only=True)


# ──────────────────────────────────────────────
# 실행: HTTP로 단일 진입점 노출
# ──────────────────────────────────────────────

if __name__ == "__main__":
    gateway.run(transport="http", host="0.0.0.0", port=8080)
