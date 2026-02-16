"""
패턴 4: 라우터 패턴 — 네임스페이스 기반 암묵적 라우팅

namespace 접두사가 곧 라우팅 키.
"weather_get_forecast" 호출 → weather 서버로 자동 라우팅.
"""

from fastmcp import FastMCP
from fastmcp.server.providers import Provider
from fastmcp.tools import Tool

# ──────────────────────────────────────────────
# 하위 서버 정의
# ──────────────────────────────────────────────

weather = FastMCP("Weather")


@weather.tool
def get_forecast(city: str) -> str:
    return f"{city}: 맑음"


db = FastMCP("Database")


@db.tool
def query(sql: str) -> str:
    return f"결과: {sql}"


git = FastMCP("Git")


@git.tool
def status() -> str:
    return "clean"


# ──────────────────────────────────────────────
# 암묵적 라우팅: namespace가 곧 라우팅 키
# ──────────────────────────────────────────────

router = FastMCP("Router")
router.mount(weather, namespace="weather")   # weather_get_forecast
router.mount(db, namespace="db")             # db_query
router.mount(git, namespace="git")           # git_status


# ──────────────────────────────────────────────
# 고급: 커스텀 Provider로 지능적 라우팅
# ──────────────────────────────────────────────

class SmartRouterProvider(Provider):
    """쿼리 복잡도에 따라 다른 모델/서버로 라우팅하는 커스텀 Provider"""

    async def list_tools(self) -> list[Tool]:
        return [
            Tool(
                name="smart_query",
                description="복잡도 기반 자동 라우팅",
            )
        ]

    async def get_tool(self, name: str) -> Tool | None:
        if name == "smart_query":
            # 실제 구현: 복잡도 분석 후 적절한 백엔드로 라우팅
            return self._create_routing_tool()
        return None

    def _create_routing_tool(self) -> Tool:
        # 실제 라우팅 로직 구현
        ...


# router.add_provider(SmartRouterProvider())


if __name__ == "__main__":
    router.run()
