"""
FastMCP 미들웨어 & Transform 예제
=================================
도구 필터링, 변형, 가드레일 적용 예제입니다.

실행: python middleware_example.py
"""

from fastmcp import FastMCP
from fastmcp.server.transforms import (
    Namespace,
    ToolTransform,
    VersionFilter,
)
from fastmcp.tools.tool_transform import ToolTransformConfig


# ============================================================
# 1. Visibility: 도구 노출 제어
# ============================================================
def visibility_example():
    """태그 기반으로 도구 노출을 제어하는 예제"""
    mcp = FastMCP("Visibility Demo")

    @mcp.tool(tags={"public"})
    def search(query: str) -> str:
        """데이터를 검색합니다"""
        return f"검색 결과: {query}"

    @mcp.tool(tags={"public"})
    def status() -> str:
        """서버 상태를 확인합니다"""
        return "running"

    @mcp.tool(tags={"admin"})
    def delete_all() -> str:
        """모든 데이터를 삭제합니다 (위험!)"""
        return "삭제 완료"

    @mcp.tool(tags={"admin"})
    def reset_config() -> str:
        """설정을 초기화합니다"""
        return "초기화 완료"

    # admin 도구 숨기기 → LLM에게 delete_all, reset_config이 보이지 않음
    mcp.disable(tags={"admin"})

    # 또는 allowlist 모드: public만 노출
    # mcp.enable(tags={"public"}, only=True)

    return mcp


# ============================================================
# 2. ToolTransform: 도구 이름/설명 변형
# ============================================================
def tool_transform_example():
    """자동 생성된 도구의 이름과 설명을 개선하는 예제"""
    mcp = FastMCP("ToolTransform Demo")

    @mcp.tool
    def usr_mgmt_get_all_active_users_v2(limit: int = 100) -> list:
        """Retrieves all active users from the database"""
        return [{"id": 1, "name": "홍길동"}]

    @mcp.tool
    def usr_mgmt_search_users_by_criteria(
        name: str = "", email: str = "", dept: str = ""
    ) -> list:
        """Searches users based on multiple criteria"""
        return []

    # 도구 이름과 설명을 에이전트 친화적으로 변형
    mcp.add_transform(ToolTransform({
        "usr_mgmt_get_all_active_users_v2": ToolTransformConfig(
            name="list_users",
            description="활성 사용자 목록을 조회합니다. limit으로 최대 개수를 지정합니다.",
        ),
        "usr_mgmt_search_users_by_criteria": ToolTransformConfig(
            name="search_users",
            description="이름, 이메일, 부서로 사용자를 검색합니다.",
        ),
    }))

    return mcp


# ============================================================
# 3. Namespace: 이름 충돌 방지
# ============================================================
def namespace_example():
    """여러 Provider의 도구 이름 충돌을 방지하는 예제"""
    from fastmcp.server.providers import LocalProvider

    # 동일한 이름의 도구를 가진 두 Provider
    hr_provider = LocalProvider()
    it_provider = LocalProvider()

    @hr_provider.tool
    def search(query: str) -> str:
        """인사 시스템에서 직원을 검색합니다"""
        return f"HR 검색: {query}"

    @it_provider.tool
    def search(query: str) -> str:
        """IT 자산을 검색합니다"""
        return f"IT 검색: {query}"

    # Namespace로 충돌 방지
    hr_provider.add_transform(Namespace("hr"))   # hr_search
    it_provider.add_transform(Namespace("it"))   # it_search

    mcp = FastMCP("Multi-Dept Server", providers=[hr_provider, it_provider])
    return mcp


# ============================================================
# 4. 종합 예제: 모든 Transform 조합
# ============================================================
def combined_example():
    """여러 Transform을 조합하는 종합 예제"""
    mcp = FastMCP("Production Server")

    @mcp.tool(tags={"query", "v1"})
    def search_v1(q: str) -> str:
        """검색 v1"""
        return f"v1: {q}"

    @mcp.tool(tags={"query", "v2"})
    def search_v2(q: str, filters: str = "") -> str:
        """검색 v2 (필터 지원)"""
        return f"v2: {q} (filters={filters})"

    @mcp.tool(tags={"admin"})
    def admin_panel() -> str:
        """관리자 패널"""
        return "admin"

    # Transform 스택:
    # 1. admin 도구 숨기기
    mcp.disable(tags={"admin"})

    # 2. 도구 설명 개선
    mcp.add_transform(ToolTransform({
        "search_v2": ToolTransformConfig(
            description="데이터를 검색합니다. filters에 JSON 형식으로 필터 조건을 전달할 수 있습니다.",
        ),
    }))

    return mcp


if __name__ == "__main__":
    # 원하는 예제를 선택하여 실행
    server = visibility_example()
    # server = tool_transform_example()
    # server = namespace_example()
    # server = combined_example()

    server.run()
