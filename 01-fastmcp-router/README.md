# FastMCP 3.x — MCP Router & 아키텍처 패턴 가이드

> **"별도의 Router 클래스는 없다. 세 가지 프리미티브의 조합이 모든 패턴을 만든다."**

---

## 목차

1. [현재 우리의 MCP 사용 현황](#1-현재-우리의-mcp-사용-현황)
2. [MCP Router — 한계를 해결하는 핵심 개념](#2-mcp-router--한계를-해결하는-핵심-개념)
3. [FastMCP 3.x에서 달라지는 것](#3-fastmcp-3x에서-달라지는-것)
4. [5가지 라우팅/아키텍처 패턴](#4-5가지-패턴-요약)
5. [참고: 비교표 & Transform 상세](#5-참고-비교표--transform-상세)
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

## 2. MCP Router — 한계를 해결하는 핵심 개념

### MCP Router란?

**MCP Router**는 흩어져 있는 여러 MCP 서버를 **하나의 중앙 서버 뒤에 통합**하는 아키텍처 패턴이다.

클라이언트는 Router 하나만 연결하면 뒤에 있는 모든 서버의 도구를 사용할 수 있다.

```
[기존] 클라이언트가 각 서버를 직접 연결 (N:N)
─────────────────────────────────────────────

┌──────────┐     ┌──────────────┐
│           │────▶│ MCP Server A │
│  Client   │────▶│ MCP Server B │
│           │────▶│ MCP Server C │
│           │────▶│ MCP Server D │
└──────────┘     └──────────────┘
  연결 4개, 설정 4개, 관리 4배


[Router 도입] 클라이언트는 Router 하나만 연결 (N:1:N)
─────────────────────────────────────────────

                  ┌──────────────────────────────┐
                  │          MCP Router           │
┌──────────┐     │                               │
│  Client   │───▶│  ┌────────┐  ┌────────┐     │
│  (1개     │     │  │Server A│  │Server B│     │
│   연결)   │     │  └────────┘  └────────┘     │
└──────────┘     │  ┌────────┐  ┌────────┐     │
                  │  │Server C│  │Server D│     │
                  │  └────────┘  └────────┘     │
                  └──────────────────────────────┘
  연결 1개, 설정 1개, 관리 중앙화
```

### Router가 해결하는 문제들

앞서 본 5가지 한계점을 Router가 어떻게 해결하는지:

| 한계점 | Router의 해결 방식 |
|--------|-------------------|
| **클라이언트 설정 지옥** | 서버 10개든 100개든 **클라이언트는 Router 1개만 설정**. 새 팀원? Router URL 하나만 공유하면 끝 |
| **관리 복잡도 폭발** | N × M 연결 → **N × 1**. 서버가 추가되면 Router 설정만 업데이트 |
| **횡단 관심사 분산** | 인증, 로깅, 속도 제한을 **Router 한 곳에서 일괄 적용**. 각 서버는 비즈니스 로직에만 집중 |
| **트랜스포트 불일치** | Router가 중간에서 **트랜스포트 변환**을 담당. stdio↔HTTP 브리징 자동 |
| **도구 과부하** | Router가 **필요한 도구만 선별하여 노출**. 50개 중 5개만 보여주는 것도 가능 |

### Router의 핵심 역할 3가지

> ✈️ **공항 비유**: Router는 **공항 통합 터미널**이다.

**1. 통합 (Aggregation)** — 여러 항공사를 한 터미널에 모은다

```
Router = 통합 터미널
├── 날씨 서버 (대한항공 카운터)
├── DB 서버 (아시아나 카운터)
├── Git 서버 (에미레이트 카운터)
└── 파일 서버 (루프트한자 카운터)

→ 승객(Client)은 터미널 하나만 들어오면 모든 항공사 이용 가능
```

**2. 라우팅 (Routing)** — 요청을 올바른 서버로 자동 전달한다

```
Client: "weather_get_forecast 호출해줘"
   │
   ▼
Router: "weather_" 접두사 → 날씨 서버로 전달
   │
   ▼
날씨 서버: get_forecast 실행 → 결과 반환

→ 탑승구 번호(namespace)만 보면 어디로 가야 하는지 자동으로 알 수 있다
```

**3. 제어 (Control)** — 보안, 필터링, 정책을 중앙에서 관리한다

```
Router (출입국심사대)
├── 🔒 인증: 이 클라이언트가 접근 권한이 있는가?
├── 👁️ 필터링: 이 사용자에게 admin 도구를 보여줄 것인가?
├── 📝 로깅: 누가 언제 어떤 도구를 호출했는가?
├── ⏱️ 속도제한: 초당 몇 번까지 허용할 것인가?
└── 🔄 변환: 도구 이름이나 설명을 사용자에 맞게 바꿀 것인가?

→ 각 서버는 이런 걸 신경 쓸 필요 없다. Router가 다 처리한다.
```

### 그런데, Router를 어떻게 만들지?

여기서 **FastMCP 3.x**가 등장한다.

기존 MCP SDK로도 Router를 만들 수 있지만, 통합·라우팅·제어를 **직접 코딩**해야 한다.
FastMCP 3.x는 이걸 **3가지 프리미티브의 조합**으로 선언적으로 해결한다.

```python
# 기존 방식: Router를 직접 구현해야 함 (수백 줄)
class MyRouter:
    def __init__(self):
        self.servers = {}
    def add_server(self, name, server): ...
    def route_request(self, tool_name): ...
    def apply_auth(self, request): ...
    def filter_tools(self, user_role): ...
    # ... 수백 줄의 라우팅/필터링 로직

# FastMCP 3.x 방식: 3줄이면 충분
router = FastMCP("Router")
router.mount(server_a, namespace="a")  # 통합 + 라우팅
router.disable(tags={"internal"})       # 제어 (필터링)
```

> 💡 **이것이 FastMCP 3.x의 핵심 가치**: Router의 3가지 역할(통합, 라우팅, 제어)을
> **Component, Provider, Transform** 3가지 프리미티브의 조합으로 표현한다.
> 다음 섹션에서 이 프리미티브들을 자세히 살펴보자.

---

## 3. FastMCP 3.x에서 달라지는 것

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

> ✈️ **공항으로 이해하는 v2 vs v3**
>
> **v2 = 항공사마다 전용 터미널이 있는 공항**
> - 대한항공 전용 터미널, 아시아나 전용 터미널, 외항사 전용 터미널...
> - 터미널마다 보안검색, 수하물 시스템, 탑승구가 각각 따로 존재
> - 새 항공사가 취항하면? 또 새 터미널을 지어야 함
>
> **v3 = 통합 터미널 공항**
> - 모든 항공사가 같은 터미널, 같은 보안검색대, 같은 탑승구를 공유
> - 3가지 핵심 인프라만 있으면 됨: **승객**(Component), **항공사**(Provider), **검색대**(Transform)
> - 새 항공사? 기존 인프라에 바로 입점

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

> ✈️ **공항으로 이해하는 3가지 프리미티브**
>
> - **Component** = ✈️ **승객** — 실제로 이동하는 대상 (Tool=비즈니스 승객, Resource=화물, Prompt=VIP)
> - **Provider** = 🛫 **항공사** — 승객을 보내는 출처 (대한항공=LocalProvider, 코드쉐어=FastMCPProvider, 외항사=ProxyProvider, LCC=OpenAPIProvider)
> - **Transform** = 🛂 **보안검색대/출입국심사** — 승객이 거치는 필터 (Namespace=탑승구 배정, Visibility=출입 제한, ToolTransform=좌석 업그레이드)
>
> **핵심**: 어떤 항공사(Provider)에서 온 승객(Component)이든, 같은 보안검색(Transform)을 통과한다.

### 프리미티브를 조합하면 패턴이 된다

> ✈️ **공항 비유: 레고처럼 조합하기**
>
> 3가지 인프라(승객, 항공사, 검색대)를 **어떻게 조합하느냐**에 따라 전혀 다른 공항이 만들어진다.
> v2에서는 프록시, 게이트웨이, 라우터가 각각 **별도 코드**였지만,
> v3에서는 **같은 3가지 블록의 조합**으로 전부 만든다.

#### 조합 1️⃣ ProxyProvider → 경유 공항 (프록시)

> ✈️ 인천→파리 직항이 없으면, **두바이 경유**. 승객은 결국 파리에 도착하지만 중간에 공항 하나를 거친다.

```python
from fastmcp.server import create_proxy

# "두바이 경유 공항" = 프록시 서버
# 원격 HTTP 서버를 로컬 stdio로 중계
proxy = create_proxy("http://remote-server:8080/mcp", name="경유공항")
proxy.run()  # Claude Desktop(stdio) ↔ Proxy ↔ 원격 서버(HTTP)
```

```
승객(Client)  ──stdio──▶  두바이(Proxy)  ──HTTP──▶  파리(원격 서버)
```

#### 조합 2️⃣ ProxyProvider 여러 개 + Visibility → 허브 공항 (게이트웨이)

> ✈️ 인천공항 출입국심사대. 대한항공이든 아시아나든 **모든 승객이 여기를 거친다**.
> 여권 확인(인증), 입국 기록(로깅), 입국 거부(정책)가 한 곳에서 처리.

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

# "인천공항" = 게이트웨이 서버
gateway = FastMCP("인천공항")

# 각 항공사(원격 서비스)를 마운트
gateway.mount(create_proxy("http://weather-api/mcp"), namespace="weather")
gateway.mount(create_proxy("http://db-api/mcp"), namespace="db")
gateway.mount(create_proxy("http://git-api/mcp"), namespace="git")

# 출입국심사 = Visibility Transform
# 내부용(직원 전용) 도구는 숨기기
gateway.disable(tags={"internal"})

# 또는 공개 도구만 허용 (화이트리스트)
gateway.enable(tags={"public"}, only=True)

gateway.run(transport="http", host="0.0.0.0", port=8080)
```

```
                        🛂 출입국심사 (Visibility)
                        │
승객(Client) ──▶ 인천공항(Gateway) ──▶ 대한항공(weather-api)
                        │           ──▶ 아시아나(db-api)
                        │           ──▶ 에미레이트(git-api)
```

#### 조합 3️⃣ FastMCPProvider 여러 개 + Namespace → 스카이스캐너 (애그리게이터)

> ✈️ 항공사 사이트를 10개씩 들어갈 필요 없이, **스카이스캐너 하나**로 전부 검색.
> 각 항공사의 노선이 `대한항공_인천파리`, `아시아나_인천도쿄`처럼 접두사로 구분된다.

```python
from fastmcp import FastMCP

# 개별 항공사 서버 (각각 독립적으로 존재)
weather_server = FastMCP("날씨 서비스")
@weather_server.tool
def get_forecast(city: str) -> str:
    """도시별 날씨 예보"""
    return f"{city}: 맑음, 23°C"

@weather_server.tool
def get_alerts(region: str) -> str:
    """기상 특보 조회"""
    return f"{region}: 특보 없음"

db_server = FastMCP("DB 서비스")
@db_server.tool
def query(sql: str) -> str:
    """SQL 쿼리 실행"""
    return f"결과: {sql}"

@db_server.tool
def tables() -> list[str]:
    """테이블 목록"""
    return ["users", "orders", "products"]

file_server = FastMCP("파일 서비스")
@file_server.tool
def read_file(path: str) -> str:
    """파일 읽기"""
    return f"내용: {path}"

# 스카이스캐너 = 애그리게이터 서버
aggregator = FastMCP("통합 서버")
aggregator.mount(weather_server, namespace="weather")  # weather_get_forecast, weather_get_alerts
aggregator.mount(db_server, namespace="db")            # db_query, db_tables
aggregator.mount(file_server, namespace="fs")          # fs_read_file

aggregator.run()

# 클라이언트는 aggregator 하나만 연결하면 6개 도구 모두 사용 가능!
# 기존: 서버 3개 × 개별 연결 = 설정 3개
# 지금: 서버 1개 연결 = 설정 1개
```

```
기존: Client ──▶ 날씨서버     도구명: get_forecast, get_alerts
      Client ──▶ DB서버       도구명: query, tables
      Client ──▶ 파일서버     도구명: read_file
      (설정 3개, 도구명 충돌 위험)

통합: Client ──▶ 애그리게이터  도구명: weather_get_forecast, weather_get_alerts,
                               db_query, db_tables, fs_read_file
      (설정 1개, namespace로 충돌 방지)
```

#### 조합 4️⃣ mount() + Namespace → 탑승구 구역제 (라우터)

> ✈️ 탑승권에 `B12`라고 적혀있으면 자동으로 B구역으로 이동.
> **접두사가 곧 라우팅** — 별도 안내원(라우팅 로직) 필요 없음.

```python
from fastmcp import FastMCP

main = FastMCP("공항 메인")

# A구역 = 국내선 (sp 서버)
main.mount(sp_server, namespace="sp")       # sp_text2sql, sp_rag_search, sp_db_query

# B구역 = 일본/중국 (task 서버)  
main.mount(task_server, namespace="task")   # task_node_lookup, task_exec

# C구역 = 유럽/미주 (disc 서버)
main.mount(disc_server, namespace="disc")   # disc_collect, disc_mapping

# D구역 = 스케줄러
main.mount(sched_server, namespace="sched") # sched_create, sched_list

# 클라이언트가 "sp_text2sql" 호출 → 자동으로 sp_server로 라우팅
# 클라이언트가 "task_exec" 호출 → 자동으로 task_server로 라우팅
# 라우팅 코드가 별도로 없다! namespace 접두사 자체가 라우팅.
```

```
Client: "sp_text2sql 호출해줘"
   │
   ▼
Main Server: "sp_" 접두사 → A구역(sp_server)으로 자동 전달
   │
   ▼
sp_server: text2sql 실행 → 결과 반환
```

#### 조합 5️⃣ enable/disable + 라이브 마운팅 → 등급별 라운지 (동적 등록)

> ✈️ 일반 탑승권 = 대합실만. 비즈니스 업그레이드 = 라운지 해금. 퍼스트 = 전용 게이트 오픈.
> 처음부터 전부 보여주면 복잡하니까, **등급에 따라 점진적으로 공개**.

```python
from fastmcp import FastMCP

# 모든 서비스를 가진 서버
services = FastMCP("공항 서비스")

@services.tool(tags={"economy"})        # 이코노미 = 기본
def flight_status(flight_no: str) -> str:
    """항공편 상태 조회"""
    return f"{flight_no}: 정시 출발"

@services.tool(tags={"economy"})
def gate_info(flight_no: str) -> str:
    """탑승구 안내"""
    return f"{flight_no}: B12 게이트"

@services.tool(tags={"business"})       # 비즈니스 = 업그레이드 후 해금
def lounge_access(terminal: str) -> str:
    """라운지 위치 안내"""
    return f"{terminal} 라운지: 3층 동편"

@services.tool(tags={"business"})
def priority_boarding(flight_no: str) -> str:
    """우선 탑승 안내"""
    return f"{flight_no}: 우선 탑승 가능"

@services.tool(tags={"first"})          # 퍼스트 = 최고 등급
def limousine_service(destination: str) -> str:
    """리무진 서비스 예약"""
    return f"{destination}행 리무진 예약 완료"

# === 초기 상태: 이코노미 승객 ===
app = FastMCP("Progressive Airport")
app.mount(services)
app.enable(tags={"economy"}, only=True)
# 보이는 도구: flight_status, gate_info (2개)

# === 비즈니스 업그레이드 후 ===
app.enable(tags={"economy", "business"}, only=True)
# 보이는 도구: flight_status, gate_info, lounge_access, priority_boarding (4개)
# → notifications/tools/list_changed 알림 → 클라이언트가 새 도구 목록 갱신

# === 퍼스트 클래스 ===
app.enable(tags={"economy", "business", "first"}, only=True)
# 보이는 도구: 전체 5개
```

```
시간 흐름 →

[이코노미]  flight_status, gate_info                    (2개)
    │
    ▼  업그레이드!
[비즈니스]  + lounge_access, priority_boarding          (4개)
    │        ↑ list_changed 알림 → 클라이언트 갱신
    ▼  업그레이드!
[퍼스트]    + limousine_service                         (5개)
             ↑ list_changed 알림 → 클라이언트 갱신
```

#### 🧩 조합 요약

| 사용한 프리미티브 | 만들어지는 패턴 | 공항 비유 | 핵심 코드 |
|------------------|----------------|-----------|-----------|
| `ProxyProvider` 1개 | 프록시 | 경유 공항 | `create_proxy(url)` |
| `ProxyProvider` N개 + `Visibility` | 게이트웨이 | 출입국심사 허브 | `mount(create_proxy()) + disable()` |
| `FastMCPProvider` N개 + `Namespace` | 애그리게이터 | 스카이스캐너 | `mount(server, namespace=)` |
| `Namespace` 접두사 | 라우터 | 탑승구 구역제 | `mount(server, namespace=)` |
| `enable/disable` + 라이브 마운팅 | 동적 등록 | 등급별 라운지 | `enable(tags=, only=True)` |

### 2단계 Transform 시스템

> ✈️ **공항으로 이해하는 2단계 Transform**
>
> - **Provider-level** = 항공사 체크인 카운터 — 대한항공 승객은 대한항공 기준으로, 아시아나 승객은 아시아나 기준으로 수하물 검사
> - **Server-level** = 공항 보안검색대 — 어떤 항공사든 **모든 승객이 동일하게** 통과해야 하는 검문소
>
> 항공사별 체크인(개별 검수) → 공항 보안검색(통합 검수) — **2단계 필터링**.

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

## 4. 5가지 패턴 요약

> 조합 예제는 위 섹션 2에서 코드와 함께 상세히 다뤘습니다.
> 여기서는 각 패턴의 핵심만 정리합니다.

| # | 패턴 | 한 줄 요약 | 공항 비유 |
|---|------|-----------|-----------|
| 1 | **프록시** | 트랜스포트가 다른 두 지점을 중계 | ✈️ 경유편 (인천→두바이→파리) |
| 2 | **게이트웨이** | 모든 요청이 거치는 보안/정책 진입점 | 🛂 출입국심사대 |
| 3 | **애그리게이터** | N개 서버를 1개 엔드포인트로 통합 | 🔍 스카이스캐너 |
| 4 | **라우터** | 네임스페이스 접두사가 곧 라우팅 | 🚪 탑승구 구역제 |
| 5 | **동적 등록** | 런타임에 도구를 점진적으로 공개 | 🎫 등급별 라운지 |

→ 각 패턴별 상세 예제 코드: `examples/01~05_*.py`

---

## 5. 참고: 비교표 & Transform 상세

> 💡 이 섹션은 레퍼런스용입니다. 발표 시에는 필요한 부분만 참조하세요.

### 패턴별 비교

| 패턴 | FastMCP API | 장점 | 단점 |
|------|-------------|------|------|
| **프록시** | `create_proxy()` | 트랜스포트 브리징 | 지연 300-500ms |
| **게이트웨이** | `mount()` + `disable()` | 횡단 관심사 중앙 집중 | 단일 장애점 |
| **애그리게이터** | `mount(server, namespace=)` | 클라이언트 설정 단순화 | 최저 성능에 종속 |
| **라우터** | `namespace` 접두사 | 코드 없이 라우팅 | 네임스페이스 설계 중요 |
| **동적 등록** | `enable/disable` + 라이브 | 컨텍스트 윈도우 절약 | 클라이언트 지원 격차 |

### mount() vs import_server()

| 특성 | `mount()` | `import_server()` |
|------|-----------|-------------------|
| 링크 | 라이브 (동적) | 일회성 복사 (정적) |
| 업데이트 | 즉시 반영 | 반영 안 됨 |
| 용도 | 런타임 조합 | 확정된 번들링 |

### 내장 Transform 종류

| Transform | 역할 | 예시 |
|-----------|------|------|
| `Namespace` | 접두사 추가 | `tool` → `api_tool` |
| `Visibility` | 도구 숨김/노출 | `disable(tags={"admin"})` |
| `ToolTransform` | 이름/설명 변형 | 긴 이름을 짧게 |
| `VersionFilter` | 버전별 필터링 | v1/v2 동시 운영 |
| 커스텀 | 비즈니스 로직 | 태그 기반 필터 등 |

→ 상세 코드: [`examples/06_transforms.py`](examples/06_transforms.py)

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

> ✈️ **공항 비유: 공항 현대화 프로젝트**
> - Phase 1 = 기존 터미널에 셔틀버스 연결 (프록시 래핑 — 기존 서버 건드리지 않고 연결만)
> - Phase 2 = 셔틀버스를 통합 터미널로 모으기 (애그리게이터 — 하나의 입구)
> - Phase 3 = 통합 보안검색대 설치 (Transform — 정책/필터링 적용)
> - Phase 4 = 모든 항공사를 통합 터미널로 이전 (네이티브 — 셔틀버스 제거, 최대 효율)

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
