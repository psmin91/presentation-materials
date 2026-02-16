"""
조합 2️⃣ ProxyProvider 여러 개 + Visibility → 허브 공항 (게이트웨이)

✈️ 비유: 인천공항 출입국심사대.
   대한항공이든 아시아나든 모든 승객이 반드시 여기를 거칩니다.
   여권 확인(인증), 입국 기록(로깅), 입국 거부(정책)가 한 곳에서 처리됩니다.

사용하는 프리미티브:
  - ProxyProvider 여러 개 (= 여러 원격 서비스)
  - Visibility Transform (= 출입국심사 / 도구 필터링)

언제 쓰나요?
  - 여러 서비스에 보안/로깅 정책을 일괄 적용할 때
  - 내부용 도구를 외부에 숨기고 싶을 때

구조:
  Client ──▶ Gateway ─┬──▶ 서비스 A
             🛂       ├──▶ 서비스 B
                      └──▶ 서비스 C
"""

from fastmcp import FastMCP

# ============================================================
# 백엔드 서비스들 (실제로는 각각 별도 서버에서 실행)
# ============================================================

# 서비스 A: 날씨 (공개)
weather_service = FastMCP("날씨 서비스")

@weather_service.tool(tags={"public"})
def get_weather(city: str) -> str:
    """도시 날씨 조회 (공개)"""
    return f"🌤️ {city}: 맑음, 22°C"

@weather_service.tool(tags={"public"})
def get_alerts(region: str) -> str:
    """기상 특보 조회 (공개)"""
    return f"⚠️ {region}: 특보 없음"


# 서비스 B: 데이터베이스 (공개 + 내부)
db_service = FastMCP("DB 서비스")

@db_service.tool(tags={"public"})
def query_readonly(sql: str) -> str:
    """읽기 전용 쿼리 (공개)"""
    return f"📊 SELECT 결과: {sql}"

@db_service.tool(tags={"internal"})
def query_write(sql: str) -> str:
    """쓰기 쿼리 (내부 전용 — 외부에 노출하면 안 됨!)"""
    return f"⚠️ WRITE 실행: {sql}"

@db_service.tool(tags={"internal"})
def drop_table(table: str) -> str:
    """테이블 삭제 (내부 전용 — 절대 외부 노출 금지!)"""
    return f"🗑️ DROP TABLE {table}"


# 서비스 C: 시스템 관리 (내부 전용)
admin_service = FastMCP("시스템 관리")

@admin_service.tool(tags={"internal"})
def restart_server(server_name: str) -> str:
    """서버 재시작 (내부 전용)"""
    return f"🔄 {server_name} 재시작 완료"

@admin_service.tool(tags={"internal"})
def view_logs(service: str, lines: int = 100) -> str:
    """로그 조회 (내부 전용)"""
    return f"📋 {service} 최근 {lines}줄 로그"


# ============================================================
# 게이트웨이 = 인천공항 (모든 서비스를 통합 + 출입국심사)
# ============================================================

gateway = FastMCP("인천공항 (Gateway)")

# 각 서비스를 마운트 (실제로는 create_proxy()로 원격 연결)
gateway.mount(weather_service, namespace="weather")
gateway.mount(db_service, namespace="db")
gateway.mount(admin_service, namespace="admin")

# 🛂 출입국심사 = Visibility Transform
# 내부용(internal) 도구는 숨깁니다!
gateway.disable(tags={"internal"})

# 이렇게 하면:
# ✅ 보이는 도구: weather_get_weather, weather_get_alerts, db_query_readonly  (3개)
# ❌ 숨겨진 도구: db_query_write, db_drop_table, admin_restart_server, admin_view_logs  (4개)

# 또는 화이트리스트 방식도 가능:
# gateway.enable(tags={"public"}, only=True)  # public 태그만 허용

# 로컬 도구도 추가 가능
@gateway.tool(tags={"public"})
def gateway_status() -> str:
    """게이트웨이 상태 확인"""
    return "✅ Gateway is operational"


if __name__ == "__main__":
    print("=" * 60)
    print("🛂 조합 2: 게이트웨이 패턴 (출입국심사대)")
    print("=" * 60)
    print()
    print("  Client ──▶ Gateway(🛂) ─┬──▶ 날씨 서비스")
    print("                          ├──▶ DB 서비스")
    print("                          └──▶ 시스템 관리")
    print()
    print("  사용한 프리미티브: ProxyProvider N개 + Visibility Transform")
    print()
    print("  ✅ 공개 도구 (외부 노출):")
    print("     - weather_get_weather, weather_get_alerts")
    print("     - db_query_readonly")
    print("     - gateway_status")
    print()
    print("  ❌ 내부 도구 (숨김):")
    print("     - db_query_write, db_drop_table")
    print("     - admin_restart_server, admin_view_logs")
    print()
    print("  핵심: 보안 정책을 서버마다 구현할 필요 없이 Gateway 한 곳에서 관리!")
    print()

    gateway.run(transport="streamable-http", host="127.0.0.1", port=8001)
