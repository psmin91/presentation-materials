"""
패턴 5: 동적 도구 등록 패턴 — Progressive Disclosure

런타임에 도구를 추가/제거하고 클라이언트에 알림.
MCP 프로토콜의 notifications/tools/list_changed 활용.
"""

from fastmcp import FastMCP

# ──────────────────────────────────────────────
# Progressive Disclosure: 태그 기반 점진적 노출
# ──────────────────────────────────────────────

api = FastMCP("API")


@api.tool(tags={"public"})
def public_search(query: str) -> str:
    """공개 검색 — 모든 사용자에게 노출"""
    return f"검색 결과: {query}"


@api.tool(tags={"public"})
def public_info() -> str:
    """공개 정보 조회"""
    return "서비스 v3.0"


@api.tool(tags={"admin"})
def admin_delete(record_id: str) -> str:
    """관리자 전용 삭제 — 인증 후에만 노출"""
    return f"삭제됨: {record_id}"


@api.tool(tags={"admin"})
def admin_config(key: str, value: str) -> str:
    """관리자 전용 설정 변경"""
    return f"설정 변경: {key}={value}"


# ──────────────────────────────────────────────
# 초기에는 공개 도구만 노출
# ──────────────────────────────────────────────

app = FastMCP("Progressive App")
app.mount(api)
app.enable(tags={"public"}, only=True)

# 인증 후 → admin 도구가 세션에 동적으로 노출
# 클라이언트는 notifications/tools/list_changed를 수신하여 목록 갱신


# ──────────────────────────────────────────────
# 라이브 마운팅: 마운트 후 추가된 도구도 즉시 접근
# ──────────────────────────────────────────────

dynamic_server = FastMCP("Dynamic")
app.mount(dynamic_server, namespace="dyn")


# 이 도구는 마운트 이후에 추가되지만, 라이브 링크로 즉시 접근 가능
@dynamic_server.tool
def added_later() -> str:
    """마운트 이후 동적으로 추가된 도구"""
    return "동적으로 추가됨!"


if __name__ == "__main__":
    app.run()
