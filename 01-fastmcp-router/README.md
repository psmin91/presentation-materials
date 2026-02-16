# FastMCP 3.x — MCP Router & 아키텍처 패턴 가이드

> **"별도의 Router 클래스는 없다. 세 가지 프리미티브의 조합이 모든 패턴을 만든다."**

---

## 목차

1. [현재 우리의 MCP 사용 현황](#1-현재-우리의-mcp-사용-현황)
2. [FastMCP 3.x에서 달라지는 것](#2-fastmcp-3x에서-달라지는-것)
3. [5가지 라우팅/아키텍처 패턴](#3-5가지-라우팅아키텍처-패턴)
4. [패턴별 비교표](#4-패턴별-비교표)
5. [Transform 시스템 상세](#5-transform-시스템-상세)
6. [실전 적용: SysProbe](#6-실전-적용-sysprobe)
7. [결론 & 마이그레이션 전략](#7-결론--마이그레이션-전략)

---

## 1. 현재 우리의 MCP 사용 현황

### 일반적인 MCP 서버 구조

```
┌──────────┐     ┌──────────────┐
│  Claude   │────▶│ MCP Server A │  (날씨)
│  Desktop  │     └──────────────┘
│           │     ┌──────────────┐
│  / Cursor │────▶│ MCP Server B │  (캘린더)
│           │     └──────────────┘
│  / IDE    │     ┌──────────────┐
│           │────▶│ MCP Server C │  (DB 조회)
│           │     └──────────────┘
│           │     ┌──────────────┐
│           │────▶│ MCP Server D │  (Git)
└──────────┘     └──────────────┘
```

각 MCP 서버가 **독립적으로 존재**하고, 클라이언트가 **개별 연결**을 관리한다.

### 현재의 한계점

| 문제 | 설명 |
|------|------|
| **클라이언트 설정 지옥** | 서버 10개면 설정 10개. 새 팀원 온보딩 = 설정 복붙 |
| **관리 복잡도 폭발** | 서버 추가될수록 연결 수 = N × M (클라이언트 × 서버) |
| **횡단 관심사 분산** | 인증, 로깅, 속도 제한을 서버마다 각각 구현 |
| **트랜스포트 불일치** | Claude Desktop은 stdio, 서버는 HTTP → 브리징 필요 |
| **도구 과부하** | 50개 서버의 도구가 한꺼번에 보이면 컨텍스트 윈도우 낭비 |

> 💡 **핵심 질문**: 이 서버들을 하나의 구조로 합치거나, 지능적으로 라우팅할 수 있다면?

---

## 2. FastMCP 3.x에서 달라지는 것

### v2 → v3 핵심 변경사항

| 항목 | v2 | v3 |
|------|-----|-----|
| 서버 조합 | `prefix` 매개변수 | `namespace` 매개변수 |
| 네이밍 | `prefix/tool` (슬래시) | `namespace_tool` (언더스코어) |
| 프록시 | `mount(server, as_proxy=True)` | `create_proxy()` 별도 함수 |
| 마운팅 내부 | 전문화된 마운팅 서브시스템 | `FastMCPProvider` + `Namespace` Transform |
| 프록싱 내부 | 전문화된 프록싱 서브시스템 | `ProxyProvider` |
| 가시성 | 독립 코드 경로 | Transform으로 통합 |

**가장 중요한 변화**: 전문화된 서브시스템 → **3가지 프리미티브로 통합**

### 3가지 프리미티브

```
┌─────────────────────────────────────────────────────────┐
│                    FastMCP 3.x 아키텍처                    │
├─────────────┬──────────────────┬────────────────────────┤
│  Component  │    Provider      │      Transform         │
│  ─────────  │    ────────      │      ─────────         │
│  Tool       │  LocalProvider   │  Namespace             │
│  Resource   │  FastMCPProvider │  Visibility (enable/   │
│  Prompt     │  ProxyProvider   │              disable)  │
│             │  FileSystem      │  ToolTransform         │
│             │  OpenAPI         │  VersionFilter         │
│             │  Skills          │  Custom Transform      │
├─────────────┴──────────────────┴────────────────────────┤
│  "모든 패턴이 이 3가지 프리미티브의 조합에서 창발된다"        │
└─────────────────────────────────────────────────────────┘
```

- **Component**: MCP의 원자 단위 (Tool, Resource, Prompt)
- **Provider**: "컴포넌트가 **어디서** 오는가?" — 데코레이터, 파일, OpenAPI, 원격 서버 등
- **Transform**: 컴포넌트 파이프라인의 미들웨어 — 이름 변경, 필터링, 인증 등

### 2단계 Transform 시스템

```
┌──────────┐   Provider-level    Server-level   ┌──────────┐
│ Provider │──▶ Transform ──────▶ Transform ───▶│ Client   │
│ A        │   (A에만 적용)       (전체 적용)     │          │
├──────────┤                                     │          │
│ Provider │──▶ Transform ──────▶               │          │
│ B        │   (B에만 적용)                      │          │
└──────────┘                                     └──────────┘
```

1. 서버가 모든 Provider에서 컴포넌트 수집
2. 각 Provider가 **자체 Transform 체인** 실행 (Provider-level)
3. 서버가 집계된 결과에 **서버-레벨 Transform 체인** 실행
4. 최종 결과가 클라이언트에 전달

---

## 3. 5가지 라우팅/아키텍처 패턴

### 패턴 1: 프록시 패턴 — 트랜스포트 브리징

> 단일 백엔드 서버를 다른 트랜스포트로 노출

```
┌──────────┐  stdio   ┌───────────┐  HTTP/SSE  ┌──────────────┐
│  Claude   │────────▶│   Proxy   │──────────▶│  원격 MCP     │
│  Desktop  │◀────────│  Server   │◀──────────│  Server       │
└──────────┘          └───────────┘            └──────────────┘
```

**핵심 API**: `create_proxy()`

```python
from fastmcp.server import create_proxy

# HTTP → stdio 브리징 (Claude Desktop이 원격 서버 사용)
proxy = create_proxy("http://example.com/mcp/sse", name="HTTP-to-stdio")
proxy.run()  # 기본: stdio

# stdio → HTTP 브리징 (로컬 서버를 네트워크에 노출)
proxy = create_proxy("./my_server.py", name="stdio-to-HTTP")
proxy.run(transport="http", host="0.0.0.0", port=8080)

# NPM 패키지 프록시
from fastmcp.client.transports import NpxStdioTransport
proxy = create_proxy(NpxStdioTransport(package="@modelcontextprotocol/server-github"))
```

| 장점 | 단점 |
|------|------|
| 투명한 트랜스포트 변환 | 지연 시간 증가 (300-500ms) |
| 클라이언트 변경 불필요 | 단일 백엔드만 지원 |
| MCP 기능 자동 포워딩 | 세션 격리로 상태 공유 불가 |

**적합한 상황**: Claude Desktop ↔ 원격 HTTP 서버 연결, 트랜스포트 불일치 해결

→ 예제: [`examples/01_proxy_pattern.py`](examples/01_proxy_pattern.py)

---

### 패턴 2: 게이트웨이 패턴 — 보안/정책 단일 진입점

> 여러 백엔드 서버 앞에 인증·로깅·정책을 적용하는 단일 진입점

```
                          ┌──────────────┐
                     ┌───▶│ Service A    │
┌──────────┐        │    └──────────────┘
│  Client   │  HTTP  │    ┌──────────────┐
│  (LLM)   │──────▶ Gateway ──▶│ Service B    │
└──────────┘        │    └──────────────┘
                     │    ┌──────────────┐
    [인증/로깅/      └───▶│ Service C    │
     속도제한]            └──────────────┘
```

**핵심 API**: `mount()` + `create_proxy()` + `enable()`/`disable()`

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

gateway = FastMCP("MCP Gateway")

# 백엔드 서비스 마운트
gateway.mount(create_proxy("http://service-a/mcp"), namespace="svc_a")
gateway.mount(create_proxy("http://service-b/mcp"), namespace="svc_b")

# 로컬 헬스체크
@gateway.tool
def gateway_health() -> str:
    return "Gateway is operational"

# 가시성 제어: 내부 도구 숨기기
gateway.disable(tags={"internal"})
# 또는 화이트리스트: 공개 도구만 노출
gateway.enable(tags={"public"}, only=True)

gateway.run(transport="http", host="0.0.0.0", port=8080)
```

| 장점 | 단점 |
|------|------|
| 횡단 관심사 중앙 집중 | 단일 장애점 리스크 |
| 접근 제어 통합 관리 | 게이트웨이 자체의 성능 부담 |
| 모니터링/로깅 일원화 | 설정 복잡도 증가 |

**적합한 상황**: 프로덕션 다중 서비스 운영, 보안 정책 적용 필요

**실제 사례**: LiteLLM Proxy (Key/Team 기반 접근 제어), MetaMCP

→ 예제: [`examples/02_gateway_pattern.py`](examples/02_gateway_pattern.py)

---

### 패턴 3: 애그리게이터 패턴 — N-to-1 통합

> 여러 MCP 서버를 단일 엔드포인트로 통합

```
                     ┌──────────────┐
                ┌───▶│ Weather      │  (FastMCPProvider)
┌──────────┐   │    └──────────────┘
│  Client   │──▶ Aggregator        ┌──────────────┐
│  (단일    │   │    Server   ┌───▶│ Remote API   │  (ProxyProvider)
│   연결)   │   │             │    └──────────────┘
└──────────┘   │             │    ┌──────────────┐
                └─────────────┴───▶│ ./tools/     │  (FileSystemProvider)
                                   └──────────────┘

노출: ping, weather_get_forecast, api_*, 파일 도구들
```

**핵심 API**: `mount()` + 다양한 Provider 조합

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy
from fastmcp.server.providers import FileSystemProvider

main = FastMCP("Aggregator")

# 로컬 도구
@main.tool
def ping() -> str:
    return "pong"

# 다른 FastMCP 서버 마운트
weather = FastMCP("Weather")
@weather.tool
def get_forecast(city: str) -> str:
    return f"{city}: 맑음"

main.mount(weather, namespace="weather")

# 원격 서버 프록시 마운트
main.mount(create_proxy("http://api.example.com/mcp"), namespace="api")

# 파일 기반 도구
main.add_provider(FileSystemProvider("./tools/"))

main.run()
```

**다중 서버 설정 기반 프록시** (가장 간편한 방법):

```python
config = {
    "mcpServers": {
        "weather": {"url": "https://weather-api.example.com/mcp", "transport": "http"},
        "calendar": {"url": "https://calendar-api.example.com/mcp", "transport": "http"}
    }
}
composite = create_proxy(config, name="AllServices")
# 자동 네임스페이싱: weather_*, calendar_*
```

| 장점 | 단점 |
|------|------|
| 클라이언트 설정 극적으로 단순화 | 최저 성능 백엔드에 종속 |
| 단일 연결로 모든 도구 접근 | 도구 이름 충돌 가능 (네임스페이스로 해결) |
| 다양한 Provider 유형 혼합 가능 | 복잡한 의존성 관리 |

**적합한 상황**: N-to-1 연결 문제, 팀 온보딩 단순화

→ 예제: [`examples/03_aggregator_pattern.py`](examples/03_aggregator_pattern.py)

---

### 패턴 4: 라우터 패턴 — 네임스페이스 기반 암묵적 라우팅

> `namespace_tool` 접두사가 곧 라우팅 키

```
                    namespace = 라우팅 키
                    ─────────────────────
┌──────────┐       ┌─────────────────────────────────┐
│  Client   │──────▶│           Main Server            │
│           │       │                                   │
│ 호출:     │       │  "weather_*" ──▶ Weather Server  │
│ weather_  │       │  "db_*"      ──▶ DB Server      │
│ get_      │       │  "git_*"     ──▶ Git Server     │
│ forecast  │       │                                   │
└──────────┘       └─────────────────────────────────┘
```

**암묵적 라우팅**: 별도의 라우터 로직 없이, `mount(server, namespace="...")` 자체가 라우팅

```python
main = FastMCP("Router")
main.mount(weather_server, namespace="weather")
main.mount(db_server, namespace="db")
main.mount(git_server, namespace="git")

# 클라이언트가 "weather_get_forecast" 호출
# → 자동으로 weather_server로 라우팅
```

**고급: 커스텀 Provider로 지능적 라우팅**

```python
from fastmcp.server.providers import Provider
from fastmcp.tools import Tool

class SmartRouterProvider(Provider):
    """쿼리 복잡도에 따라 다른 모델로 라우팅"""

    async def list_tools(self) -> list[Tool]:
        return [Tool(
            name="smart_query",
            description="복잡도 기반 자동 라우팅",
        )]

    async def get_tool(self, name: str) -> Tool | None:
        if name == "smart_query":
            return self._smart_query_tool
        return None
```

| 장점 | 단점 |
|------|------|
| 추가 코드 없이 네임스페이스로 라우팅 | 복잡한 라우팅 로직은 커스텀 필요 |
| 비용/성능 최적화 가능 | 네임스페이스 설계가 중요 |
| 이기종 백엔드 통합 | |

**적합한 상황**: 이기종 백엔드 관리, 비용 최적화 라우팅

→ 예제: [`examples/04_router_pattern.py`](examples/04_router_pattern.py)

---

### 패턴 5: 동적 도구 등록 패턴 — Progressive Disclosure

> 런타임에 도구를 추가/제거하고, 클라이언트에 알림

```
┌──────────────────────────────────────────────┐
│                시간 흐름 →                     │
│                                               │
│  [초기]     공개 도구 3개만 노출               │
│     │                                         │
│     ▼       사용자가 인증                     │
│  [인증 후]  admin 도구 5개 추가 노출           │
│     │       notifications/tools/list_changed  │
│     ▼                                         │
│  [필요 시]  search → add-actor → 도구 등록    │
│             (Apify 마켓플레이스 방식)          │
└──────────────────────────────────────────────┘
```

**핵심 메커니즘**: `notifications/tools/list_changed` + 라이브 마운팅

```python
from fastmcp import FastMCP

api = FastMCP("API")

@api.tool(tags={"public"})
def public_search(query: str) -> str:
    """공개 검색"""
    return f"결과: {query}"

@api.tool(tags={"admin"})
def admin_delete(record_id: str) -> str:
    """관리자 전용 삭제"""
    return f"삭제됨: {record_id}"

# 초기: 공개 도구만
app = FastMCP("Progressive App")
app.mount(api)
app.enable(tags={"public"}, only=True)

# 인증 후 → admin 도구 동적 노출
# 라이브 마운팅: 마운트 후 추가된 도구도 즉시 접근 가능
@dynamic_server.tool
def added_later() -> str:
    return "마운트 이후 추가됨!"
```

| 장점 | 단점 |
|------|------|
| 컨텍스트 윈도우 절약 | 클라이언트 지원 격차 |
| 필요한 도구만 점진적 노출 | 구현 복잡도 |
| 대규모 카탈로그 관리 | |

**적합한 상황**: 10,000+ 도구 카탈로그, 권한별 점진적 노출

**실제 사례**: Apify 마켓플레이스 (`search-actors` → `add-actor` → `list_changed`)

→ 예제: [`examples/05_dynamic_tools.py`](examples/05_dynamic_tools.py)

---

## 4. 패턴별 비교표

| 패턴 | 핵심 목적 | FastMCP API | 최대 장점 | 최대 단점 | 적합 상황 |
|------|-----------|-------------|-----------|-----------|-----------|
| **프록시** | 단일 백엔드 포워딩 | `create_proxy()` | 트랜스포트 브리징 투명성 | 지연 시간 (300-500ms) | 원격 서버 로컬 노출 |
| **게이트웨이** | 보안/정책 진입점 | `mount()` + 미들웨어 | 횡단 관심사 중앙 집중 | 단일 장애점 | 프로덕션 다중 서비스 |
| **애그리게이터** | 다중 서버 통합 | `mount()` / `import_server()` | 클라이언트 설정 단순화 | 최저 성능에 종속 | N-to-1 연결 문제 |
| **라우터** | 지능적 요청 분배 | 네임스페이스 암묵적 | 비용/성능 최적화 | 라우팅 로직 복잡 | 이기종 백엔드 |
| **동적 등록** | 런타임 도구 발견 | `list_changed` 알림 | 컨텍스트 윈도우 절약 | 클라이언트 지원 격차 | 대규모 카탈로그 |

### mount() vs import_server() 비교

| 특성 | `mount()` | `import_server()` |
|------|-----------|-------------------|
| 링크 유형 | 라이브 (동적) | 일회성 복사 (정적) |
| 업데이트 반영 | 즉시 | 반영 안 됨 |
| 성능 | 런타임 위임 (느림) | 빠름 — 위임 없음 |
| 용도 | 모듈형 런타임 조합 | 확정된 컴포넌트 번들링 |

### 내장 Provider 유형

| Provider | 소스 | 용도 |
|----------|------|------|
| **LocalProvider** | `@tool` 데코레이터 | 기본 도구 등록 |
| **FastMCPProvider** | 다른 FastMCP 인스턴스 | 서버 조합/마운팅 |
| **ProxyProvider** | 원격 MCP 서버 | 원격 서버 프록싱 |
| **FileSystemProvider** | 파일 디렉토리 | 핫리로드 개발 |
| **OpenAPIProvider** | OpenAPI 스펙 | REST API 자동 변환 |
| **SkillsProvider** | 스킬 파일 | 스킬 리소스 제공 |

---

## 5. Transform 시스템 상세

### 네임스페이싱 규칙

| 컴포넌트 유형 | 원본 | `namespace="api"` 적용 후 |
|---------------|------|---------------------------|
| Tool | `my_tool` | `api_my_tool` |
| Prompt | `my_prompt` | `api_my_prompt` |
| Resource | `data://info` | `data://api/info` |
| Template | `data://{id}` | `data://api/{id}` |

### Transform 스태킹 (체이닝)

```python
from fastmcp.server.transforms import Namespace, ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig
from fastmcp.server.providers import FastMCPProvider

provider = FastMCPProvider(sub_server)

# 1단계: 네임스페이싱
provider.add_transform(Namespace("api"))

# 2단계: 이름 재정의
provider.add_transform(ToolTransform({
    "api_verbose_auto_generated_name": ToolTransformConfig(
        name="short",
        description="에이전트에게 더 적합한 설명",
        tags={"optimized"},
    ),
}))

# 흐름: "verbose_auto_generated_name" → "api_verbose_auto_generated_name" → "short"
```

### Visibility (enable/disable)

```python
server = FastMCP("Server")

# 태그 기반 필터링
server.disable(tags={"internal"})          # internal 태그 숨기기
server.enable(tags={"public"}, only=True)  # public만 노출 (화이트리스트)
```

### VersionFilter

```python
from fastmcp.server.transforms import VersionFilter

api_v1 = FastMCP("API v1", providers=[components])
api_v1.add_transform(VersionFilter(version_lt="2.0"))   # 2.0 미만

api_v2 = FastMCP("API v2", providers=[components])
api_v2.add_transform(VersionFilter(version_gte="2.0"))  # 2.0 이상
```

### 커스텀 Transform 작성

```python
from fastmcp.server.transforms import Transform, GetToolNext
from fastmcp.tools import Tool
from collections.abc import Sequence

class TagFilter(Transform):
    """특정 태그를 가진 도구만 통과시키는 커스텀 Transform"""

    def __init__(self, required_tags: set[str]):
        self.required_tags = required_tags

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [t for t in tools if t.tags & self.required_tags]

    async def get_tool(self, name: str, call_next: GetToolNext) -> Tool | None:
        tool = await call_next(name)
        return tool if tool and tool.tags & self.required_tags else None
```

### Provider-level vs Server-level

```
Provider-level Transform              Server-level Transform
─────────────────────                  ─────────────────────
• 해당 Provider 컴포넌트에만 적용       • 모든 컴포넌트에 적용
• provider.add_transform()             • server.add_transform()
• 네임스페이싱, 이름 재정의 등          • 전역 필터링, 인증 등
```

→ 예제: [`examples/06_transforms.py`](examples/06_transforms.py)

---

## 6. 실전 적용: SysProbe

### 우리 프로젝트에서의 패턴 조합

SysProbe는 여러 패턴을 **조합**하여 사용한다:

```
┌─────────────────────────────────────────┐
│              SysProbe Main               │
│                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ Skill A │  │ Skill B │  │ Skill C │ │  ← 동적 도구 등록
│  └─────────┘  └─────────┘  └─────────┘ │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     Aggregator (mount 기반)      │   │  ← 애그리게이터
│  │  weather / calendar / db / ...   │   │
│  └──────────────────────────────────┘   │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │     Transform Pipeline           │   │  ← 가시성 제어
│  │  enable(tags={"active_skills"})  │   │
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

### Skills 패턴 = 동적 도구 등록의 변형

- **Skills**: 필요한 능력을 런타임에 로드/언로드
- 내부적으로 `SkillsProvider` + `enable()`/`disable()` 조합
- Progressive Disclosure 패턴의 실제 응용
- 에이전트가 필요한 도구만 활성화 → 컨텍스트 윈도우 효율 극대화

---

## 7. 결론 & 마이그레이션 전략

### 3.x 전환으로 얻는 이점

| 이점 | 설명 |
|------|------|
| **통합된 멘탈 모델** | 3가지 프리미티브만 이해하면 모든 패턴 구현 가능 |
| **클라이언트 설정 단순화** | N개 서버 → 1개 애그리게이터 연결 |
| **횡단 관심사 중앙화** | Transform으로 인증/로깅/필터링 일괄 적용 |
| **동적 도구 관리** | 라이브 마운팅 + list_changed로 런타임 유연성 |
| **커스텀 확장** | Provider/Transform 인터페이스로 무한 확장 |

### 단계별 마이그레이션 전략

```
Phase 1: 프록시 래핑
─────────────────────
기존 서버를 create_proxy()로 감싸기
→ 기존 코드 변경 없이 즉시 적용

Phase 2: 애그리게이터 구성
─────────────────────
프록시들을 하나의 서버에 mount()
→ 클라이언트 설정 N개 → 1개로 축소

Phase 3: Transform 적용
─────────────────────
네임스페이싱, 가시성 제어, 접근 제어
→ 운영 수준의 정책 적용

Phase 4: 네이티브 마이그레이션
─────────────────────
기존 서버를 FastMCP 3.x로 직접 재작성
→ 프록시 오버헤드 제거, 최대 성능
```

### 핵심 메시지

> **"조합 가능성이 곧 확장 가능성이다."**
>
> Router, Gateway, Aggregator 같은 전용 클래스를 만들지 않고,
> **Provider**(컴포넌트 소스) + **Transform**(컴포넌트 변환)의 조합만으로
> 모든 아키텍처 패턴을 구현한다.
>
> 프레임워크의 학습 곡선을 낮추면서 표현력을 극대화하는 설계.

---

## 예제 코드

| 파일 | 패턴 |
|------|------|
| [`examples/01_proxy_pattern.py`](examples/01_proxy_pattern.py) | 프록시 — 트랜스포트 브리징 |
| [`examples/02_gateway_pattern.py`](examples/02_gateway_pattern.py) | 게이트웨이 — 보안/정책 |
| [`examples/03_aggregator_pattern.py`](examples/03_aggregator_pattern.py) | 애그리게이터 — N-to-1 통합 |
| [`examples/04_router_pattern.py`](examples/04_router_pattern.py) | 라우터 — 네임스페이스 라우팅 |
| [`examples/05_dynamic_tools.py`](examples/05_dynamic_tools.py) | 동적 도구 등록 |
| [`examples/06_transforms.py`](examples/06_transforms.py) | Transform 시스템 |
