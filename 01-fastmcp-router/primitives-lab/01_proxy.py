"""
조합 1️⃣ ProxyProvider → 경유 공항 (프록시)

✈️ 비유: 인천→파리 직항이 없으면, 두바이 경유로 갑니다.
   승객(Client)은 결국 파리에 도착하지만, 중간에 두바이(Proxy)를 거칩니다.

사용하는 프리미티브:
  - ProxyProvider 1개

언제 쓰나요?
  - Claude Desktop(stdio)에서 원격 HTTP 서버를 써야 할 때
  - 기존 서버 코드를 한 줄도 안 바꾸고, 다른 트랜스포트로 노출하고 싶을 때

구조:
  Client(stdio) ──▶ Proxy Server ──▶ 원격 서버(HTTP)
"""

from fastmcp import FastMCP
from fastmcp.server import create_proxy

# ============================================================
# 예제 1: 원격 HTTP 서버를 로컬 stdio로 중계
# ============================================================
# Claude Desktop은 stdio만 지원하는데, 서버는 HTTP로 동작할 때
# Proxy가 중간에서 트랜스포트를 변환해줍니다.

# proxy = create_proxy("http://remote-server:8080/mcp", name="경유공항")
# proxy.run()  # stdio로 실행 → Claude Desktop에서 바로 사용


# ============================================================
# 예제 2: 로컬 서버를 HTTP로 노출
# ============================================================
# 반대 방향도 가능합니다. 로컬에서만 돌던 서버를 네트워크에 공개할 때.

# proxy = create_proxy("./my_local_server.py", name="stdio-to-HTTP")
# proxy.run(transport="http", host="0.0.0.0", port=8080)


# ============================================================
# 예제 3: 실제로 실행해볼 수 있는 데모
# ============================================================
# 원격 서버 역할을 하는 로컬 서버를 만들고, 프록시로 감싸봅니다.

# 1) "파리" = 원격 서버 (실제로는 로컬에서 실행)
paris_server = FastMCP("파리 공항 (원격 서버)")

@paris_server.tool
def check_weather(city: str) -> str:
    """파리의 날씨를 확인합니다"""
    return f"🗼 {city}: 맑음, 18°C, 에펠탑이 잘 보이는 날씨입니다"

@paris_server.tool
def translate(text: str, to_lang: str = "fr") -> str:
    """텍스트를 번역합니다"""
    translations = {"hello": "bonjour", "goodbye": "au revoir", "thank you": "merci"}
    result = translations.get(text.lower(), f"[{to_lang}] {text}")
    return f"🇫🇷 번역: {text} → {result}"

# 2) "두바이" = 프록시 서버 (파리를 감싸서 중계)
#    실제로는 create_proxy("http://paris:8080/mcp") 이지만,
#    데모에서는 로컬 서버를 직접 프록시합니다.
dubai_proxy = create_proxy(paris_server, name="두바이 경유 공항")


if __name__ == "__main__":
    print("=" * 60)
    print("✈️ 조합 1: 프록시 패턴 (경유 공항)")
    print("=" * 60)
    print()
    print("  Client(stdio) ──▶ 두바이(Proxy) ──▶ 파리(원격 서버)")
    print()
    print("  사용한 프리미티브: ProxyProvider 1개")
    print("  핵심: 기존 서버 코드 변경 없이 트랜스포트 변환")
    print()
    print("  서버를 실행합니다... (Ctrl+C로 종료)")
    print("  다른 터미널에서 fastmcp inspect로 확인해보세요:")
    print("    fastmcp inspect --transport streamable-http --host 127.0.0.1 --port 8001")
    print()

    dubai_proxy.run(transport="streamable-http", host="127.0.0.1", port=8001)
