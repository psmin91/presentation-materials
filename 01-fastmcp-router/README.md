# FastMCP 3.x — MCP Router 아키텍처 패턴

> **"별도의 Router 클래스는 없다. 세 가지 프리미티브의 조합이 모든 패턴을 만든다."**

---

## 목차

1. [현재 우리의 MCP 사용 현황](#1-현재-우리의-mcp-사용-현황)
2. [MCP Router — 한계를 해결하는 핵심 개념](#2-mcp-router--한계를-해결하는-핵심-개념)
3. [FastMCP 3.x — Router를 만드는 새로운 방법](#3-fastmcp-3x--router를-만드는-새로운-방법)
4. [프리미티브 조합 실습 — 5가지 패턴 만들기](#4-프리미티브-조합-실습--5가지-패턴-만들기)
5. [실전 적용: SysProbe 프로젝트](#5-실전-적용-sysprobe-프로젝트)
6. [결론 & 마이그레이션 가이드](#6-결론--마이그레이션-가이드)

---

## 1. 현재 우리의 MCP 사용 현황

지금 우리가 MCP 서버를 어떻게 쓰고 있는지부터 이야기해볼게요.

### 일반적인 구조

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

각 MCP 서버가 독립적으로 존재하고, 클라이언트가 **개별 연결**을 관리하는 구조입니다.
익숙하죠? 이게 현재 대부분의 MCP 사용 방식입니다.

### 그런데 이 구조, 서버가 많아지면 문제가 생깁니다

| 문제 | 체감 |
|------|------|
| **설정 지옥** | 서버 10개면 설정 10개. 새 팀원 온보딩? 설정 복붙부터... |
| **관리 복잡도** | 서버 추가될 때마다 클라이언트 전부 설정 업데이트 |
| **인증/로깅 분산** | 보안 정책을 서버마다 각각 구현해야 함 |
| **트랜스포트 불일치** | Claude Desktop은 stdio인데 서버는 HTTP... 연결이 안 됨 |
| **도구 폭발** | 서버 50개의 도구가 한꺼번에 보이면 AI가 혼란 |

서버가 3~4개일 때는 괜찮은데, 10개, 20개 넘어가면 감당이 안 됩니다.

> 💡 **그래서 생각해봅니다**: 이 서버들을 하나로 합칠 수는 없을까?

---

## 2. MCP Router — 한계를 해결하는 핵심 개념

### 아이디어는 간단합니다

**MCP Router**는 흩어진 MCP 서버들을 **하나의 중앙 서버 뒤에 통합**하는 패턴입니다.
클라이언트는 Router 하나만 연결하면 됩니다.

```
[현재] 클라이언트 → 서버 직접 연결 (1:N)

┌──────────┐     ┌──────────────┐
│           │────▶│ Server A     │
│  Client   │────▶│ Server B     │     설정 4개
│           │────▶│ Server C     │     관리 4배
│           │────▶│ Server D     │
└──────────┘     └──────────────┘


[Router 도입] 클라이언트 → Router → 서버들 (1:1:N)

                  ┌──────────────────────────────┐
┌──────────┐     │          MCP Router           │
│  Client   │───▶│                               │
│           │     │  ┌────────┐  ┌────────┐     │     설정 1개
│  (1개     │     │  │Server A│  │Server B│     │     관리 중앙화
│   연결!)  │     │  └────────┘  └────────┘     │
└──────────┘     │  ┌────────┐  ┌────────┐     │
                  │  │Server C│  │Server D│     │
                  │  └────────┘  └────────┘     │
                  └──────────────────────────────┘
```

### 아까 그 문제들, Router로 어떻게 해결될까요?

| 문제 | Router의 해결 |
|------|--------------|
| **설정 지옥** | 서버 100개여도 클라이언트는 **URL 1개**만 설정 |
| **관리 복잡도** | 서버 추가? **Router 설정만 업데이트**. 클라이언트는 건드릴 필요 없음 |
| **인증/로깅 분산** | **Router 한 곳에서 일괄 적용**. 서버는 비즈니스 로직만 신경 |
| **트랜스포트 불일치** | Router가 중간에서 **자동 변환** (stdio↔HTTP) |
| **도구 폭발** | Router가 **필요한 도구만 골라서** 노출 |

### Router의 3가지 역할

Router가 하는 일을 정리하면 딱 3가지입니다.

> ✈️ 공항에 비유하면 Router는 **통합 터미널**입니다.

**① 통합 (Aggregation)** — 여러 항공사를 한 터미널에 모은다

```
Router (= 통합 터미널)
├── 날씨 서버  (대한항공 카운터)
├── DB 서버    (아시아나 카운터)
├── Git 서버   (에미레이트 카운터)
└── 파일 서버  (루프트한자 카운터)

→ 승객(Client)은 터미널 하나만 들어오면 모든 항공사를 이용할 수 있다
```

**② 라우팅 (Routing)** — 요청을 올바른 서버로 자동 전달한다

```
Client: "weather_get_forecast 호출해줘"
         ↓
Router: "weather_" 접두사니까 → 날씨 서버로!
         ↓
날씨 서버: 결과 반환

→ 탑승구 번호만 보면 어디로 가야 하는지 바로 안다
```

**③ 제어 (Control)** — 보안, 필터링, 정책을 중앙에서 관리한다

```
Router (= 출입국심사대)
├── 🔒 인증     — 이 클라이언트, 접근 권한 있어?
├── 👁️ 필터링   — admin 도구 보여줄까 말까?
├── 📝 로깅     — 누가 언제 뭘 호출했지?
└── ⏱️ 속도제한 — 초당 몇 번까지 OK?
```

### 좋습니다. 그런데 Router를 어떻게 만들죠?

기존 MCP SDK로도 만들 수 있습니다. 하지만 통합·라우팅·제어를 **직접 코딩**해야 합니다.

```python
# 직접 구현하면? → 수백 줄...
class MyRouter:
    def add_server(self, name, server): ...
    def route_request(self, tool_name): ...
    def apply_auth(self, request): ...
    def filter_tools(self, user_role): ...
    # 🥲 이걸 언제 다 짜나...
```

여기서 **FastMCP 3.x**가 등장합니다.

```python
# FastMCP 3.x로 하면? → 3줄
router = FastMCP("Router")
router.mount(server_a, namespace="a")  # 통합 + 라우팅
router.disable(tags={"internal"})       # 제어 (필터링)
# 끝!
```

어떻게 이게 가능한 걸까요? 다음 섹션에서 살펴보겠습니다.

---

## 3. FastMCP 3.x — Router를 만드는 새로운 방법

### 먼저, 2.x에서 뭐가 바뀌었나요?

| 항목 | v2 (기존) | v3 (신규) |
|------|-----------|-----------|
| 서버 조합 | `prefix` 매개변수 | `namespace` 매개변수 |
| 네이밍 | `prefix/tool` (슬래시) | `namespace_tool` (언더스코어) |
| 프록시 | `mount(server, as_proxy=True)` | `create_proxy()` 별도 함수 |
| 내부 구현 | 마운팅/프록싱/가시성 **각각 별도 코드** | **3가지 프리미티브**로 전부 통합 |

핵심 변화는 마지막 줄입니다. 기능별로 따로 있던 코드가 **3가지 조합 가능한 블록**으로 통합됐습니다.

> ✈️ **공항으로 비유하면:**
>
> **v2** = 항공사마다 **전용 터미널**이 있는 공항
> - 대한항공 터미널, 아시아나 터미널, 외항사 터미널이 각각 따로
> - 터미널마다 보안검색, 수하물 시스템이 별도
> - 새 항공사 취항? → 또 새 터미널을 지어야 함 😩
>
> **v3** = **통합 터미널** 공항
> - 모든 항공사가 같은 터미널, 같은 시설을 공유
> - 3가지 인프라만 있으면 됨
> - 새 항공사? → 카운터 하나만 추가하면 끝 ✅

### 그 3가지 프리미티브가 뭔데요?

```
┌─────────────────────────────────────────────────────────┐
│                    FastMCP 3.x                           │
├─────────────┬──────────────────┬────────────────────────┤
│  Component  │    Provider      │      Transform         │
│  ─────────  │    ────────      │      ─────────         │
│  Tool       │  LocalProvider   │  Namespace             │
│  Resource   │  FastMCPProvider │  Visibility            │
│  Prompt     │  ProxyProvider   │  ToolTransform         │
│             │  FileSystem      │  VersionFilter         │
│             │  OpenAPI         │  Custom Transform      │
└─────────────┴──────────────────┴────────────────────────┘
```

> ✈️ **공항으로 이해하기**
>
> | 프리미티브 | 정의 | 공항 비유 |
> |-----------|------|-----------|
> | **Component** | MCP의 원자 단위 (Tool, Resource, Prompt) | ✈️ **승객** — 실제로 이동하는 대상 |
> | **Provider** | 컴포넌트가 **어디서** 오는가 | 🛫 **항공사** — 승객을 보내는 출처 |
> | **Transform** | 컴포넌트를 **어떻게** 변형/필터링하는가 | 🛂 **보안검색대** — 승객이 거치는 필터 |
>
> 어떤 항공사(Provider)에서 온 승객(Component)이든,
> 같은 보안검색대(Transform)를 통과합니다.

쉽게 말해:
- **Component** = "뭐가 있지?" (도구, 리소스, 프롬프트)
- **Provider** = "그게 어디서 오지?" (로컬 코드, 다른 서버, 원격 API, 파일...)
- **Transform** = "그걸 어떻게 가공하지?" (이름 바꾸기, 숨기기, 접두사 붙이기...)

### 이 3개를 어떻게 조합하느냐에 따라 패턴이 달라집니다

이게 FastMCP 3.x의 **핵심 아이디어**입니다.

v2에서는 "프록시 기능", "마운팅 기능", "필터링 기능"이 각각 별도로 구현되어 있었습니다.
v3에서는 **같은 3가지 블록을 다르게 조합**하면 프록시도, 게이트웨이도, 라우터도 만들 수 있습니다.

레고 블록으로 집도, 차도, 비행기도 만들 수 있는 것처럼요.

| 이 블록들을 이렇게 조합하면 | 이런 패턴이 됩니다 |
|---------------------------|-------------------|
| `ProxyProvider` 1개 | → **프록시** (경유 공항) |
| `ProxyProvider` N개 + `Visibility` | → **게이트웨이** (출입국심사 허브) |
| `FastMCPProvider` N개 + `Namespace` | → **애그리게이터** (스카이스캐너) |
| `Namespace` 접두사 기반 | → **라우터** (탑승구 구역제) |
| `enable/disable` + 라이브 마운팅 | → **동적 등록** (등급별 라운지) |

말로만 하면 와닿지 않으니, 실제 코드로 하나씩 만들어보겠습니다.

---

## 4. 프리미티브 조합 실습 — 5가지 패턴 만들기

### 조합 1️⃣ ProxyProvider → 경유 공항 (프록시)

> ✈️ 인천→파리 직항이 없을 때, **두바이 경유**로 가는 겁니다.
> 승객은 결국 파리에 도착하지만, 중간에 두바이 공항을 거치죠.

**언제 쓰나요?** Claude Desktop(stdio)에서 원격 HTTP 서버를 써야 할 때.

```python
from fastmcp.server import create_proxy

# 원격 서버를 로컬에서 쓸 수 있게 중계
proxy = create_proxy("http://remote-server:8080/mcp", name="경유공항")
proxy.run()  # stdio로 실행 → Claude Desktop에서 바로 사용 가능
```

```
승객(Client)  ──stdio──▶  두바이(Proxy)  ──HTTP──▶  파리(원격 서버)
```

핵심: 기존 서버 코드를 **한 줄도 안 바꾸고**, 다른 트랜스포트로 노출할 수 있습니다.

---

### 조합 2️⃣ ProxyProvider 여러 개 + Visibility → 허브 공항 (게이트웨이)

> ✈️ 인천공항 출입국심사대를 생각해보세요.
> 대한항공이든 아시아나든 **모든 승객이 반드시 여기를 거칩니다**.
> 여권 확인(인증), 입국 기록(로깅), 입국 거부(정책)가 **한 곳에서** 처리됩니다.

**언제 쓰나요?** 여러 서비스에 보안/로깅 정책을 일괄 적용할 때.

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

# 인천공항 = 게이트웨이
gateway = FastMCP("인천공항")

# 항공사(원격 서비스)들을 입점시킵니다
gateway.mount(create_proxy("http://weather-api/mcp"), namespace="weather")
gateway.mount(create_proxy("http://db-api/mcp"), namespace="db")
gateway.mount(create_proxy("http://git-api/mcp"), namespace="git")

# 출입국심사 = 도구 필터링
gateway.disable(tags={"internal"})               # 내부용 도구 숨기기
# 또는
gateway.enable(tags={"public"}, only=True)       # 공개 도구만 허용 (화이트리스트)

gateway.run(transport="http", host="0.0.0.0", port=8080)
```

```
                       🛂 출입국심사 (Visibility)
                       │
Client ──▶ 인천공항(Gateway) ─┬──▶ weather-api (날씨)
                              ├──▶ db-api (DB)
                              └──▶ git-api (Git)
```

핵심: 인증/로깅/필터링을 서버마다 구현할 필요 없이, **Gateway 한 곳에서 관리**.

---

### 조합 3️⃣ FastMCPProvider + Namespace → 스카이스캐너 (애그리게이터)

> ✈️ 항공사 10개 사이트를 하나하나 들어가서 비교하시나요?
> 스카이스캐너 하나면 **모든 항공사를 한 화면에서 검색**할 수 있죠.
> 이게 애그리게이터입니다.

**언제 쓰나요?** 여러 MCP 서버를 하나의 엔드포인트로 합칠 때. (가장 자주 쓰는 패턴!)

```python
from fastmcp import FastMCP

# === 개별 서버들 (각각 독립적으로 존재) ===

weather = FastMCP("날씨 서비스")

@weather.tool
def get_forecast(city: str) -> str:
    """도시별 날씨 예보"""
    return f"{city}: 맑음, 23°C"

@weather.tool
def get_alerts(region: str) -> str:
    """기상 특보 조회"""
    return f"{region}: 특보 없음"

db = FastMCP("DB 서비스")

@db.tool
def query(sql: str) -> str:
    """SQL 쿼리 실행"""
    return f"결과: {sql}"

@db.tool
def tables() -> list[str]:
    """테이블 목록"""
    return ["users", "orders", "products"]

files = FastMCP("파일 서비스")

@files.tool
def read_file(path: str) -> str:
    """파일 읽기"""
    return f"내용: {path}"


# === 스카이스캐너 = 애그리게이터로 통합! ===

app = FastMCP("통합 서버")
app.mount(weather, namespace="weather")   # → weather_get_forecast, weather_get_alerts
app.mount(db, namespace="db")             # → db_query, db_tables
app.mount(files, namespace="fs")          # → fs_read_file

app.run()
```

**Before vs After:**
```
기존:  Client ──▶ 날씨서버    도구: get_forecast, get_alerts
       Client ──▶ DB서버      도구: query, tables
       Client ──▶ 파일서버    도구: read_file
       📋 설정 3개, 도구명 충돌 위험!

통합:  Client ──▶ 애그리게이터  도구: weather_get_forecast, weather_get_alerts,
                                     db_query, db_tables, fs_read_file
       📋 설정 1개, namespace로 충돌 방지 ✅
```

핵심: 클라이언트는 **연결 하나**로 모든 서버의 도구를 씁니다.
namespace가 자동으로 접두사를 붙여서 이름 충돌도 방지합니다.

---

### 조합 4️⃣ mount() + Namespace → 탑승구 구역제 (라우터)

> ✈️ 탑승권에 `B12`라고 적혀있으면, 안내원한테 물어볼 필요 없이
> 자동으로 B구역으로 가죠? **접두사가 곧 라우팅**입니다.

**언제 쓰나요?** 사실 조합 3️⃣을 쓰면 라우팅은 **자동으로 따라옵니다**.

```python
main = FastMCP("공항 메인")

# A구역 = Text2SQL
main.mount(sp_server, namespace="sp")         # sp_text2sql, sp_rag_search

# B구역 = OPMATE 작업
main.mount(task_server, namespace="task")     # task_node_lookup, task_exec

# C구역 = AutoDiscovery
main.mount(disc_server, namespace="disc")     # disc_collect, disc_mapping

# D구역 = Scheduler
main.mount(sched_server, namespace="sched")   # sched_create, sched_list
```

```
Client: "sp_text2sql 호출해줘"
   ↓
Main: "sp_" 접두사 → sp_server로 자동 전달!
   ↓
sp_server: text2sql 실행 → 결과 반환
```

핵심: **별도 라우팅 코드가 없습니다**. namespace 자체가 라우팅입니다.

---

### 조합 5️⃣ enable/disable + 라이브 마운팅 → 등급별 라운지 (동적 등록)

> ✈️ 공항에서 이코노미 승객에게 퍼스트 클래스 라운지를 보여줄 필요가 있을까요?
> 처음엔 기본 서비스만 보여주고, **등급이 올라가면 새 서비스가 열리는** 방식입니다.

**언제 쓰나요?** 도구가 많을 때, 상황에 따라 필요한 것만 보여주고 싶을 때.

```python
from fastmcp import FastMCP

services = FastMCP("공항 서비스")

# --- 이코노미 (기본) ---
@services.tool(tags={"economy"})
def flight_status(flight_no: str) -> str:
    """항공편 상태 조회"""
    return f"{flight_no}: 정시 출발"

@services.tool(tags={"economy"})
def gate_info(flight_no: str) -> str:
    """탑승구 안내"""
    return f"{flight_no}: B12 게이트"

# --- 비즈니스 (업그레이드 후 해금) ---
@services.tool(tags={"business"})
def lounge_access(terminal: str) -> str:
    """라운지 위치 안내"""
    return f"{terminal} 라운지: 3층 동편"

@services.tool(tags={"business"})
def priority_boarding(flight_no: str) -> str:
    """우선 탑승 안내"""
    return f"{flight_no}: 우선 탑승 가능"

# --- 퍼스트 (최고 등급) ---
@services.tool(tags={"first"})
def limousine_service(destination: str) -> str:
    """리무진 서비스 예약"""
    return f"{destination}행 리무진 예약 완료"


# === 등급에 따라 보이는 도구가 달라진다 ===

app = FastMCP("Progressive Airport")
app.mount(services)

# 이코노미 → 2개만 보임
app.enable(tags={"economy"}, only=True)

# 비즈니스 업그레이드! → 4개로 늘어남
app.enable(tags={"economy", "business"}, only=True)
# → 클라이언트에 list_changed 알림 → 자동 갱신

# 퍼스트 클래스! → 전체 5개
app.enable(tags={"economy", "business", "first"}, only=True)
```

```
시간 흐름 →

[이코노미]  flight_status, gate_info                     (2개)
     │
     ▼  업그레이드!
[비즈니스]  + lounge_access, priority_boarding            (4개)
     │        ↑ 자동 알림 → 클라이언트 새 도구 인식
     ▼  업그레이드!
[퍼스트]    + limousine_service                           (5개)
```

핵심: **도구가 50개, 100개여도 사용자에게는 지금 필요한 것만 보여줍니다**.
AI의 컨텍스트 윈도우 낭비를 막는 핵심 패턴입니다.

---

### 🧩 5가지 조합 정리

| 프리미티브 조합 | 패턴 | 공항 비유 | 핵심 코드 |
|----------------|------|-----------|-----------|
| `ProxyProvider` | 프록시 | ✈️ 경유편 | `create_proxy(url)` |
| `ProxyProvider` N개 + `Visibility` | 게이트웨이 | 🛂 출입국심사 | `mount(proxy) + disable()` |
| `FastMCPProvider` N개 + `Namespace` | 애그리게이터 | 🔍 스카이스캐너 | `mount(server, namespace=)` |
| `Namespace` 접두사 | 라우터 | 🚪 탑승구 구역제 | 자동 (mount하면 됨) |
| `enable/disable` | 동적 등록 | 🎫 등급별 라운지 | `enable(tags=, only=True)` |

> 💡 **기억하세요**: 이 5가지 패턴은 전부 **Component + Provider + Transform** 조합입니다.
> 별도의 ProxyServer, GatewayServer, AggregatorServer 클래스 같은 건 없습니다.

---

## 5. 실전 적용: SysProbe 프로젝트

실제로 이 패턴들을 우리 프로젝트에서 어떻게 조합했는지 보겠습니다.

### SysProbe의 아키텍처

```
┌─────────────────────────────────────────┐
│        SysProbe MCP Router (8001)        │
│                                          │
│  ┌─────────┐  ┌─────────┐  ┌─────────┐ │
│  │ sp_*    │  │ task_*  │  │ disc_*  │ │  ← 애그리게이터 + 라우터
│  │ Text2SQL│  │ OPMATE  │  │AutoDisc │ │     (mount + namespace)
│  └─────────┘  └─────────┘  └─────────┘ │
│                                          │
│  ┌──────────────────────────────────┐   │
│  │  Skills: load_skill / list_skill │   │  ← 동적 등록
│  │  (필요한 도구만 런타임 활성화)     │   │     (enable/disable)
│  └──────────────────────────────────┘   │
└─────────────────────────────────────────┘
```

사용된 패턴:
- **애그리게이터**: sp, task, disc, sched 4개 서버를 하나로 통합
- **라우터**: namespace 접두사로 자동 라우팅 (`sp_text2sql` → sp 서버)
- **동적 등록**: Skills 시스템으로 필요한 도구만 활성화

### Skills = 동적 등록의 실전 버전

에이전트가 모든 도구를 한꺼번에 보면 혼란스럽습니다.
그래서 이렇게 합니다:

1. 처음엔 `list_skills`, `load_skill` 2개만 보임
2. 에이전트가 `load_skill("text2sql")` 호출
3. → sp_text2sql, sp_rag_search 등이 **동적으로 활성화**
4. 다른 스킬이 필요하면 다시 `load_skill("scheduler")` 호출

이게 바로 조합 5️⃣(동적 등록)의 실전 적용입니다.

---

## 6. 결론 & 마이그레이션 가이드

### 정리하면

| FastMCP 3.x의 핵심 | 설명 |
|-------------------|------|
| **3가지 프리미티브** | Component, Provider, Transform — 이것만 알면 됩니다 |
| **조합이 곧 패턴** | 프록시, 게이트웨이, 애그리게이터, 라우터, 동적 등록 — 전부 같은 블록의 조합 |
| **Router 클래스는 없다** | 별도 추상화 대신, 프리미티브 조합으로 "창발"되는 구조 |

### 기존 서버를 어떻게 옮기나요?

> ✈️ **공항 현대화 프로젝트**처럼 단계적으로 진행합니다.

```
Phase 1: 기존 터미널에 셔틀버스 연결
─────────────────────────────────────
기존 서버를 create_proxy()로 감싸기
→ 기존 코드 한 줄도 안 건드림. 바로 적용 가능!

Phase 2: 셔틀버스를 통합 터미널로 모으기
─────────────────────────────────────
프록시들을 하나의 서버에 mount()
→ 클라이언트 설정 N개 → 1개로 축소

Phase 3: 통합 보안검색대 설치
─────────────────────────────────────
Transform 적용 (네임스페이싱, 필터링, 접근 제어)
→ 운영 수준의 정책 관리

Phase 4: 모든 항공사를 통합 터미널로 이전
─────────────────────────────────────
기존 서버를 FastMCP 3.x 네이티브로 재작성
→ 프록시 오버헤드 제거, 최대 성능
```

### 한 줄로 요약

> **"조합 가능성이 곧 확장 가능성이다."**
>
> 같은 3가지 블록으로 어떤 아키텍처든 만들 수 있습니다.

---

## 부록: 참고 테이블

### 패턴별 장단점

| 패턴 | 장점 | 단점 | 적합 상황 |
|------|------|------|-----------|
| **프록시** | 트랜스포트 브리징 | 지연 300-500ms | stdio↔HTTP 연결 |
| **게이트웨이** | 보안 중앙 집중 | 단일 장애점 | 프로덕션 보안 정책 |
| **애그리게이터** | 설정 극적 단순화 | 느린 서버에 영향 | N-to-1 통합 |
| **라우터** | 코드 없이 라우팅 | 네이밍 설계 중요 | 도메인별 분리 |
| **동적 등록** | 컨텍스트 절약 | 클라이언트 호환성 | 대규모 도구 |

### 내장 Transform 종류

| Transform | 하는 일 | 예시 코드 |
|-----------|---------|-----------|
| `Namespace` | 접두사 추가 | `tool` → `api_tool` |
| `Visibility` | 도구 숨김/노출 | `disable(tags={"admin"})` |
| `ToolTransform` | 이름/설명 변형 | 긴 이름 → 짧게 |
| `VersionFilter` | 버전별 필터 | v1/v2 동시 운영 |

### mount() vs import_server()

| | `mount()` | `import_server()` |
|---|-----------|-------------------|
| 특성 | 라이브 (동적) | 일회성 복사 |
| 업데이트 | 즉시 반영 | 반영 안 됨 |
| 용도 | 런타임 조합 | 확정 번들링 |

---

## 예제 코드

| 파일 | 패턴 |
|------|------|
| [`examples/01_proxy_pattern.py`](examples/01_proxy_pattern.py) | 프록시 — 트랜스포트 브리징 |
| [`examples/02_gateway_pattern.py`](examples/02_gateway_pattern.py) | 게이트웨이 — 보안/정책 |
| [`examples/03_aggregator_pattern.py`](examples/03_aggregator_pattern.py) | 애그리게이터 — N-to-1 통합 |
| [`examples/04_router_pattern.py`](examples/04_router_pattern.py) | 라우터 — 네임스페이스 |
| [`examples/05_dynamic_tools.py`](examples/05_dynamic_tools.py) | 동적 도구 등록 |
| [`examples/06_transforms.py`](examples/06_transforms.py) | Transform 시스템 |

---

## 참고 자료

| 리소스 | URL |
|--------|-----|
| FastMCP 공식 문서 | https://gofastmcp.com |
| FastMCP GitHub | https://github.com/jlowin/fastmcp |
| MCP 공식 사이트 | https://modelcontextprotocol.io |

---

> 📝 발표자: [이름] | 📅 발표일: 2026-02-XX | 🏢 [팀명]
