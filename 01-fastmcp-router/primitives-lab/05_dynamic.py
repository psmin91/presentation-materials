"""
조합 5️⃣ enable/disable + 라이브 마운팅 → 등급별 라운지 (동적 등록)

✈️ 비유: 공항에서 이코노미 승객에게 퍼스트 라운지를 보여줄 필요가 있을까요?
   처음엔 기본 서비스만, 등급이 올라가면 새 서비스가 열립니다.

사용하는 프리미티브:
  - Visibility Transform (enable/disable)
  - 라이브 마운팅 (mount 이후 추가된 도구도 즉시 접근 가능)

언제 쓰나요?
  - 도구가 많을 때, 상황에 따라 필요한 것만 보여주고 싶을 때
  - 권한/등급에 따라 점진적으로 기능을 공개할 때
  - AI의 컨텍스트 윈도우 낭비를 줄이고 싶을 때

구조:
  [이코노미]  2개 도구
      ↓ 업그레이드
  [비즈니스]  4개 도구 (+2 해금)
      ↓ 업그레이드
  [퍼스트]    6개 도구 (+2 해금)
"""

from fastmcp import FastMCP
import asyncio

# ============================================================
# 모든 서비스를 가진 서버 (등급별 태그 지정)
# ============================================================

services = FastMCP("공항 서비스")

# --- 이코노미 등급 (기본) ---
@services.tool(tags={"economy"})
def flight_status(flight_no: str) -> str:
    """항공편 상태를 조회합니다"""
    statuses = {
        "KE001": "✈️ KE001 인천→파리: 정시 출발 (14:30)",
        "OZ202": "⏰ OZ202 인천→도쿄: 30분 지연",
    }
    return statuses.get(flight_no, f"✈️ {flight_no}: 정보를 찾을 수 없습니다")

@services.tool(tags={"economy"})
def gate_info(flight_no: str) -> str:
    """탑승구 정보를 안내합니다"""
    gates = {"KE001": "🚪 B12 게이트 (2터미널)", "OZ202": "🚪 A05 게이트 (1터미널)"}
    return gates.get(flight_no, f"🚪 {flight_no}: 탑승구 미배정")

# --- 비즈니스 등급 (업그레이드 후 해금) ---
@services.tool(tags={"business"})
def lounge_access(terminal: str) -> str:
    """비즈니스 라운지 위치를 안내합니다"""
    lounges = {
        "T1": "🛋️ 1터미널 라운지: 동편 3층 (샤워실, 뷔페, 수면실)",
        "T2": "🛋️ 2터미널 라운지: 중앙 4층 (바, 뷔페, 마사지)",
    }
    return lounges.get(terminal, f"🛋️ {terminal}: 라운지 정보 없음")

@services.tool(tags={"business"})
def priority_boarding(flight_no: str) -> str:
    """우선 탑승 안내를 합니다"""
    return f"⭐ {flight_no}: 비즈니스 클래스 우선 탑승 가능 (출발 40분 전)"

# --- 퍼스트 등급 (최고 등급) ---
@services.tool(tags={"first"})
def limousine_service(destination: str) -> str:
    """공항 리무진 서비스를 예약합니다"""
    return f"🚗 {destination}행 전용 리무진 예약 완료 (BMW 7시리즈)"

@services.tool(tags={"first"})
def personal_concierge(request: str) -> str:
    """개인 컨시어지 서비스를 이용합니다"""
    return f"🎩 컨시어지 접수: '{request}' — 담당자가 곧 연락드리겠습니다"


# ============================================================
# Progressive Disclosure: 등급에 따라 도구가 점진적으로 공개
# ============================================================

app = FastMCP("Progressive Airport")
app.mount(services)


async def demo_progressive_disclosure():
    """등급별로 보이는 도구가 어떻게 달라지는지 데모"""

    print("=" * 60)
    print("🎫 조합 5: 동적 등록 패턴 (등급별 라운지)")
    print("=" * 60)
    print()

    # --- 이코노미 ---
    app.enable(tags={"economy"}, only=True)
    tools = await app.get_tools()
    print("  [이코노미 등급] 보이는 도구:")
    for name in sorted(tools.keys()):
        print(f"    ✅ {name}")
    print(f"  → 총 {len(tools)}개")
    print()

    # --- 비즈니스 업그레이드 ---
    app.enable(tags={"economy", "business"}, only=True)
    tools = await app.get_tools()
    print("  ⬆️  비즈니스로 업그레이드!")
    print("  [비즈니스 등급] 보이는 도구:")
    for name in sorted(tools.keys()):
        new = "🆕" if "lounge" in name or "priority" in name else "  "
        print(f"    {new} ✅ {name}")
    print(f"  → 총 {len(tools)}개 (+2 해금!)")
    print()

    # --- 퍼스트 클래스 ---
    app.enable(tags={"economy", "business", "first"}, only=True)
    tools = await app.get_tools()
    print("  ⬆️  퍼스트 클래스로 업그레이드!")
    print("  [퍼스트 등급] 보이는 도구:")
    for name in sorted(tools.keys()):
        new = "🆕" if "limousine" in name or "concierge" in name else "  "
        print(f"    {new} ✅ {name}")
    print(f"  → 총 {len(tools)}개 (+2 해금!)")
    print()

    print("  핵심: 도구 50개여도 사용자에게는 지금 필요한 것만 보여줍니다.")
    print("  → AI 컨텍스트 윈도우 낭비 방지!")
    print()
    print("  사용한 프리미티브: Visibility Transform (enable/disable)")
    print("  MCP 알림: notifications/tools/list_changed → 클라이언트 자동 갱신")


if __name__ == "__main__":
    asyncio.run(demo_progressive_disclosure())
