"""
패턴 3: 애그리게이터 패턴 — N-to-1 통합

여러 MCP 서버를 단일 엔드포인트로 통합.
클라이언트 설정 N개 → 1개로 축소.
"""

from fastmcp import FastMCP
from fastmcp.server import create_proxy

# ──────────────────────────────────────────────
# 하위 서버 정의
# ──────────────────────────────────────────────

weather = FastMCP("Weather")


@weather.tool
def get_forecast(city: str) -> str:
    """도시별 날씨 예보 조회"""
    return f"{city}: 맑음, 23°C"


@weather.resource("data://cities")
def list_cities() -> list[str]:
    return ["서울", "부산", "도쿄"]


calendar = FastMCP("Calendar")


@calendar.tool
def get_events(date: str) -> str:
    """일정 조회"""
    return f"{date}: 회의 2건"


# ──────────────────────────────────────────────
# 애그리게이터 구성
# ──────────────────────────────────────────────

main = FastMCP("Aggregator")


# 로컬 도구
@main.tool
def ping() -> str:
    """헬스체크"""
    return "pong"


# FastMCP 서버 마운트 (FastMCPProvider + Namespace)
main.mount(weather, namespace="weather")
main.mount(calendar, namespace="calendar")

# 원격 서버 프록시 마운트 (ProxyProvider + Namespace)
main.mount(create_proxy("http://api.example.com/mcp"), namespace="api")

# ──────────────────────────────────────────────
# 다중 서버 설정 기반 — 가장 간편한 방법
# ──────────────────────────────────────────────

config = {
    "mcpServers": {
        "github": {"url": "https://github-mcp.example.com/mcp", "transport": "http"},
        "slack": {"url": "https://slack-mcp.example.com/mcp", "transport": "http"},
    }
}
composite = create_proxy(config, name="ExternalServices")
# 자동 네임스페이싱: github_*, slack_*

# ──────────────────────────────────────────────
# 노출되는 도구:
#   ping, weather_get_forecast, calendar_get_events, api_*, github_*, slack_*
# 노출되는 리소스:
#   data://weather/cities
# ──────────────────────────────────────────────

if __name__ == "__main__":
    main.run()
