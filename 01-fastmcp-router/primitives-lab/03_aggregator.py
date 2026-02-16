"""
조합 3️⃣ FastMCPProvider 여러 개 + Namespace → 스카이스캐너 (애그리게이터)

✈️ 비유: 항공사 사이트 10개를 하나하나 검색하시나요?
   스카이스캐너 하나면 모든 항공사를 한 화면에서 검색·예약할 수 있죠.
   이게 애그리게이터입니다!

사용하는 프리미티브:
  - FastMCPProvider 여러 개 (= 여러 로컬 서버)
  - Namespace Transform (= 접두사로 도구명 충돌 방지)

언제 쓰나요?
  - 여러 MCP 서버를 하나의 엔드포인트로 합칠 때
  - 클라이언트 설정을 N개 → 1개로 줄이고 싶을 때
  - ⭐ 가장 자주 쓰는 패턴!

구조:
  Client ──▶ Aggregator ─┬──▶ 날씨 서버
             (1개 연결!)  ├──▶ DB 서버
                          └──▶ 파일 서버
"""

from fastmcp import FastMCP

# ============================================================
# 개별 서버들 (각각 독립적으로 존재하는 서비스)
# ============================================================

# 서버 1: 날씨 서비스
weather = FastMCP("날씨 서비스")

@weather.tool
def get_forecast(city: str) -> str:
    """도시별 날씨 예보를 조회합니다"""
    forecasts = {
        "서울": "🌤️ 맑음, 15°C, 미세먼지 보통",
        "부산": "🌊 흐림, 18°C, 파도 1.5m",
        "도쿄": "🌸 맑음, 20°C, 벚꽃 시즌",
    }
    return forecasts.get(city, f"🌍 {city}: 정보 없음")

@weather.tool
def get_alerts(region: str) -> str:
    """기상 특보를 조회합니다"""
    return f"⚠️ {region}: 현재 발효 중인 특보 없음"

@weather.tool
def compare_weather(city_a: str, city_b: str) -> str:
    """두 도시의 날씨를 비교합니다"""
    return f"📊 {city_a} vs {city_b}: 기온 차이 약 3°C"


# 서버 2: 데이터베이스 서비스
db = FastMCP("DB 서비스")

@db.tool
def query(sql: str) -> str:
    """SQL 쿼리를 실행합니다"""
    return f"📊 결과: {sql} → 3건 조회됨"

@db.tool
def tables() -> list[str]:
    """테이블 목록을 조회합니다"""
    return ["users", "orders", "products", "inventory"]

@db.tool
def schema(table_name: str) -> str:
    """테이블 스키마를 조회합니다"""
    return f"📋 {table_name}: id(INT), name(VARCHAR), created_at(DATETIME)"


# 서버 3: 파일 서비스
files = FastMCP("파일 서비스")

@files.tool
def read_file(path: str) -> str:
    """파일을 읽습니다"""
    return f"📄 [{path}] 내용: Hello, World!"

@files.tool
def list_files(directory: str = ".") -> list[str]:
    """디렉토리의 파일 목록을 조회합니다"""
    return ["README.md", "config.yaml", "data.csv"]


# ============================================================
# 스카이스캐너 = 애그리게이터 (모든 서버를 하나로 통합!)
# ============================================================

app = FastMCP("통합 서버 (스카이스캐너)")

# mount()로 각 서버를 통합. namespace가 접두사를 자동으로 붙여줍니다.
app.mount(weather, namespace="weather")   # → weather_get_forecast, weather_get_alerts, weather_compare_weather
app.mount(db, namespace="db")             # → db_query, db_tables, db_schema
app.mount(files, namespace="fs")          # → fs_read_file, fs_list_files


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 조합 3: 애그리게이터 패턴 (스카이스캐너)")
    print("=" * 60)
    print()
    print("  [Before] 클라이언트가 서버 3개에 각각 연결")
    print("     Client ──▶ 날씨서버    도구: get_forecast, get_alerts, compare_weather")
    print("     Client ──▶ DB서버      도구: query, tables, schema")
    print("     Client ──▶ 파일서버    도구: read_file, list_files")
    print("     📋 설정 3개, 도구명 충돌 위험!")
    print()
    print("  [After] 클라이언트는 애그리게이터 1개만 연결")
    print("     Client ──▶ 통합서버    도구:")
    print("        weather_get_forecast, weather_get_alerts, weather_compare_weather")
    print("        db_query, db_tables, db_schema")
    print("        fs_read_file, fs_list_files")
    print("     📋 설정 1개, namespace로 충돌 방지 ✅")
    print()
    print("  사용한 프리미티브: FastMCPProvider 3개 + Namespace Transform")
    print()
    print("  총 도구 수: 8개 (날씨 3 + DB 3 + 파일 2)")
    print()

    app.run(transport="streamable-http", host="127.0.0.1", port=8001)
