# FastMCP 3.x — MCP Router 아키텍처 Deep Dive

> 사내 기술 발표자료 | 2026-02-16

---

## 목차

1. [MCP (Model Context Protocol) 개요](#1-mcp-model-context-protocol-개요)
2. [FastMCP 3.x 소개](#2-fastmcp-3x-소개)
3. [MCP Router 아키텍처](#3-mcp-router-아키텍처)
4. [코드 예제](#4-코드-예제)
5. [실전 활용 사례 — SysProbe](#5-실전-활용-사례--sysprobe)
6. [다른 MCP 프레임워크 비교](#6-다른-mcp-프레임워크-비교)
7. [결론 및 향후 전망](#7-결론-및-향후-전망)

---

## 1. MCP (Model Context Protocol) 개요

### 1.1 MCP란 무엇인가

**Model Context Protocol (MCP)** 은 Anthropic이 2024년에 공개한 오픈 표준 프로토콜로, **LLM(대규모 언어 모델)과 외부 도구·데이터를 연결하는 표준 인터페이스**입니다.

기존에는 각 AI 에이전트 프레임워크마다 도구(Tool) 연결 방식이 제각각이었습니다. MCP는 이를 **USB-C처럼 하나의 표준**으로 통일합니다.

```
┌─────────────┐     MCP Protocol      ┌─────────────────┐
│  LLM Agent  │ ◄──────────────────► │   MCP Server    │
│ (Client)    │   JSON-RPC over       │  (Tools, Data)  │
│             │   stdio / HTTP / SSE  │                 │
└─────────────┘                       └─────────────────┘
```

### 1.2 왜 필요한가

| 문제 | MCP의 해결 |
|------|-----------|
| LLM마다 도구 연결 방식이 다름 | 표준 프로토콜로 통일 |
| 도구가 많아지면 LLM이 혼란 | 도구 필터링·네임스페이싱 지원 |
| 원격 서비스 연결이 복잡 | Proxy 패턴으로 투명하게 연결 |
| 도구 메타데이터 관리 어려움 | 스키마·설명·태그 표준화 |

### 1.3 MCP 생태계 현황

- **공식 SDK**: Python (`mcp` 패키지), TypeScript
- **주요 프레임워크**: FastMCP (Python), mcp-framework (TS)
- **호스트 지원**: Claude Desktop, Cursor, VS Code Copilot, Windsurf 등
- **도입 현황**: FastMCP 기반 서버가 전체 MCP 서버의 약 70%를 차지 (2025년 기준)
- **일일 다운로드**: FastMCP 약 100만 회/일

---

## 2. FastMCP 3.x 소개

### 2.1 FastMCP란

**FastMCP**는 [Prefect](https://www.prefect.io/) 팀이 개발한 **Python MCP 프레임워크**입니다.

- 2024년: FastMCP 1.0이 공식 MCP Python SDK에 편입
- 현재: 독립 프로젝트로 계속 발전, **3.0 RC** 출시 (2026년 1월)

```python
from fastmcp import FastMCP

mcp = FastMCP("Demo 🚀")

@mcp.tool
def add(a: int, b: int) -> int:
    """두 수를 더합니다"""
    return a + b

mcp.run()
```

### 2.2 2.x vs 3.x 핵심 차이점

| 항목 | FastMCP 2.x | FastMCP 3.x |
|------|-------------|-------------|
| **아키텍처** | 기능별 독립 서브시스템 | **3가지 핵심 프리미티브** (Component, Provider, Transform) |
| **서버 구성** | mount, proxy 등 개별 구현 | Provider + Transform 조합으로 통일 |
| **미들웨어** | 요청 레벨만 | **Transform(컴포넌트 레벨)** + Middleware(요청 레벨) 분리 |
| **도구 소싱** | 데코레이터만 | 데코레이터, 파일시스템, OpenAPI, 원격 서버, DB 등 |
| **버전 관리** | 없음 | 컴포넌트 버전 필터링 지원 |
| **재사용성** | 서버에 종속 | LocalProvider를 여러 서버에 attach 가능 |
| **핫 리로드** | 없음 | FileSystemProvider의 `reload=True` |

### 2.3 3.x의 3가지 핵심 프리미티브

```
┌──────────────────────────────────────────────────────────┐
│                     FastMCP Server                        │
│                                                          │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐        │
│  │  Provider   │  │  Provider   │  │  Provider   │        │
│  │ (Local)     │  │ (Proxy)     │  │ (OpenAPI)   │        │
│  │             │  │             │  │             │        │
│  │ Transform[] │  │ Transform[] │  │ Transform[] │        │
│  └─────┬──────┘  └─────┬──────┘  └─────┬──────┘        │
│        │               │               │                │
│        └───────────────┼───────────────┘                │
│                        ▼                                │
│              Server Transform Chain                      │
│              (Visibility, Auth, etc.)                     │
│                        │                                │
│                        ▼                                │
│                   Client Response                        │
└──────────────────────────────────────────────────────────┘
```

1. **Components** — MCP의 원자 단위 (Tool, Resource, Prompt)
2. **Providers** — 컴포넌트의 소스 (어디서 오는가?)
3. **Transforms** — 컴포넌트 파이프라인 미들웨어 (어떻게 변형하는가?)

---

## 3. MCP Router 아키텍처

### 3.1 Router 패턴이란

MCP Router는 **여러 MCP 서버(sub-server)를 하나의 진입점으로 통합**하는 패턴입니다.

FastMCP 3.x에서는 Router가 별도 개념이 아니라, **Provider + Transform의 자연스러운 조합**으로 구현됩니다.

```
                    ┌─────────────────────────────┐
                    │      MCP Router (Main)       │
                    │                             │
   Client ───────► │  ┌─────┐ ┌─────┐ ┌──────┐  │
   (LLM Agent)     │  │ sp_ │ │task_│ │disc_ │  │
                    │  │서버  │ │서버  │ │서버   │  │
                    │  └─────┘ └─────┘ └──────┘  │
                    │                             │
                    │  + Core Tools               │
                    │    (list_skills, load_skill) │
                    └─────────────────────────────┘
```

### 3.2 Sub-server 마운트 개념

`mount()`는 내부적으로 두 가지 프리미티브의 조합입니다:

1. **FastMCPProvider**: 다른 FastMCP 서버 인스턴스에서 컴포넌트를 소싱
2. **Namespace Transform**: 접두사(prefix)를 추가하여 이름 충돌 방지

```python
router = FastMCP("Main Router")
sub = FastMCP("Sub Server")

@sub.tool
def query(sql: str) -> str:
    """SQL 실행"""
    return execute(sql)

# mount → "query" 도구가 "sp_query"로 노출됨
router.mount(sub, prefix="sp")
```

### 3.3 Proxy 서버 패턴

원격 MCP 서버를 로컬처럼 노출하는 패턴입니다. **ProxyProvider**가 MCP 클라이언트를 래핑하여 원격 서버의 컴포넌트를 로컬로 가져옵니다.

```python
from fastmcp.server import create_proxy

# 원격 서버를 프록시로 노출
proxy = create_proxy("http://remote-server:8080/mcp")
proxy.run()
```

```
Client ──► Proxy Server ──► Remote MCP Server A
                        ──► Remote MCP Server B
```

### 3.4 도구 필터링 / Transforms

#### Visibility (도구 노출 제어)

```python
mcp.disable(tags={"admin"})           # admin 태그 도구 숨김
mcp.disable(names={"dangerous_tool"}) # 특정 도구 숨김
mcp.enable(tags={"public"}, only=True) # allowlist 모드
```

#### Namespace (네임스페이싱)

```python
from fastmcp.server.transforms import Namespace
provider.add_transform(Namespace("api"))
# "search" → "api_search"
```

#### ToolTransform (도구 변형)

```python
from fastmcp.server.transforms import ToolTransform
from fastmcp.tools.tool_transform import ToolTransformConfig

provider.add_transform(ToolTransform({
    "verbose_auto_generated_name": ToolTransformConfig(
        name="short_name",
        description="에이전트에 최적화된 설명",
        tags={"category"},
    ),
}))
```

#### VersionFilter (버전 필터링)

```python
from fastmcp.server.transforms import VersionFilter

api_v1 = FastMCP("API v1", providers=[components])
api_v1.add_transform(VersionFilter(version_lt="2.0"))

api_v2 = FastMCP("API v2", providers=[components])
api_v2.add_transform(VersionFilter(version_gte="2.0"))
```

### 3.5 미들웨어 vs Transform

| 구분 | Transform | Middleware |
|------|-----------|------------|
| **대상** | 컴포넌트 (도구 목록, 스키마) | 요청 (도구 호출, 리소스 읽기) |
| **역할** | 어떤 컴포넌트가 존재하는지 형성 | 요청이 어떻게 실행되는지 처리 |
| **예시** | 네임스페이싱, 필터링, 이름 변경 | 인증, 로깅, 속도 제한 |
| **적용 레벨** | Provider 레벨 + Server 레벨 | Server 레벨 |

### 3.6 전체 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────┐
│                        FastMCP Router                                │
│                                                                     │
│  ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐  │
│  │  FastMCPProvider  │  │  FastMCPProvider  │  │  ProxyProvider   │  │
│  │  (sp_server)      │  │  (task_server)    │  │  (remote)        │  │
│  │                   │  │                   │  │                  │  │
│  │  Transform:       │  │  Transform:       │  │  Transform:      │  │
│  │  └ Namespace("sp")│  │  └ Namespace("task")│ │  └ Namespace("r")│  │
│  └────────┬─────────┘  └────────┬─────────┘  └────────┬─────────┘  │
│           │                     │                      │            │
│           └─────────────────────┼──────────────────────┘            │
│                                 ▼                                   │
│                    Server-Level Transforms                           │
│                    ├─ Visibility (태그 기반 필터링)                     │
│                    ├─ ToolTransform (이름/설명 변형)                    │
│                    └─ Auth Middleware (인증/인가)                      │
│                                 │                                   │
│                                 ▼                                   │
│                    ┌────────────────────┐                            │
│                    │   Client Response   │                            │
│                    └────────────────────┘                            │
│                                                                     │
│  Core Tools: list_skills, load_skill, register_tool, ...            │
│  Health: GET /health                                                │
│  Transport: streamable-http / stdio / SSE                           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 4. 코드 예제

> 모든 예제는 `examples/` 디렉토리에 실행 가능한 파일로 제공됩니다.

### 4.1 기본 MCP 서버 생성

📄 [`examples/basic_server.py`](examples/basic_server.py)

```python
from fastmcp import FastMCP

mcp = FastMCP("Basic Server")

@mcp.tool
def greet(name: str) -> str:
    """사용자에게 인사합니다"""
    return f"안녕하세요, {name}님!"

@mcp.tool
def calculate(expression: str) -> float:
    """수학 표현식을 계산합니다"""
    return eval(expression)  # 실제 서비스에서는 안전한 파서 사용

@mcp.resource("config://version")
def get_version() -> str:
    return "1.0.0"

if __name__ == "__main__":
    mcp.run()
```

### 4.2 Router로 여러 서버 마운트

📄 [`examples/router_example.py`](examples/router_example.py)

```python
from fastmcp import FastMCP

# Sub-server 1: 데이터베이스
db_server = FastMCP("DB Server")

@db_server.tool
def query(sql: str) -> str:
    """SQL 쿼리를 실행합니다"""
    return f"[결과] {sql}"

@db_server.tool
def tables() -> list[str]:
    """테이블 목록을 조회합니다"""
    return ["users", "orders", "products"]

# Sub-server 2: 파일 관리
file_server = FastMCP("File Server")

@file_server.tool
def read_file(path: str) -> str:
    """파일을 읽습니다"""
    return f"[내용] {path}"

# Router: 통합
router = FastMCP("Main Router")
router.mount(db_server, prefix="db")     # db_query, db_tables
router.mount(file_server, prefix="fs")   # fs_read_file

if __name__ == "__main__":
    router.run(transport="streamable-http", host="0.0.0.0", port=8001)
```

### 4.3 Proxy 서버로 원격 MCP 연결

📄 [`examples/proxy_example.py`](examples/proxy_example.py)

```python
from fastmcp import FastMCP
from fastmcp.server import create_proxy

# 원격 MCP 서버를 프록시
remote_proxy = create_proxy("http://remote-host:9000/mcp")

# 로컬 도구 + 원격 프록시를 하나의 Router로 통합
router = FastMCP("Hybrid Router")

@router.tool
def local_status() -> str:
    """로컬 서버 상태를 확인합니다"""
    return "healthy"

router.mount(remote_proxy, prefix="remote")

if __name__ == "__main__":
    router.run(transport="streamable-http", host="0.0.0.0", port=8001)
```

### 4.4 미들웨어/가드레일 적용

📄 [`examples/middleware_example.py`](examples/middleware_example.py)

```python
from fastmcp import FastMCP
from fastmcp.server.transforms import Namespace, ToolTransform, Visibility
from fastmcp.tools.tool_transform import ToolTransformConfig

# --- 서버 생성 ---
mcp = FastMCP("Guarded Server")

@mcp.tool(tags={"public"})
def search(query: str) -> str:
    """검색을 수행합니다"""
    return f"결과: {query}"

@mcp.tool(tags={"admin"})
def delete_all() -> str:
    """모든 데이터를 삭제합니다 (위험!)"""
    return "삭제 완료"

@mcp.tool(tags={"public"})
def status() -> str:
    """서버 상태를 확인합니다"""
    return "running"

# --- Transform 적용 ---

# 1. admin 도구 숨기기
mcp.disable(tags={"admin"})

# 2. 도구 이름/설명 변형
mcp.add_transform(ToolTransform({
    "search": ToolTransformConfig(
        description="자연어로 검색합니다. 키워드나 문장을 입력하세요.",
    ),
}))

if __name__ == "__main__":
    mcp.run()
```

---

## 5. 실전 활용 사례 — SysProbe

### 5.1 SysProbe 프로젝트 개요

SysProbe는 **서버 구성정보 관리 시스템**으로, MCP Router 패턴을 활용하여 여러 도메인의 도구를 하나의 엔드포인트로 통합합니다.

### 5.2 아키텍처

```
┌──────────────────────────────────────────────────────┐
│              SysProbe MCP Router                      │
│              (FastMCP, port 8001)                     │
│                                                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────┐│
│  │ sp_*     │  │ task_*   │  │ disc_*   │  │sched_*││
│  │ Text2SQL │  │ OPMATE   │  │ AutoDisc │  │Sched  ││
│  │          │  │          │  │          │  │       ││
│  │ sp_      │  │ task_    │  │ disc_    │  │sched_ ││
│  │ text2sql │  │ node_    │  │ process_ │  │create ││
│  │ db_query │  │ lookup   │  │ collect  │  │list   ││
│  │ rag_     │  │ task_    │  │ mapping  │  │       ││
│  │ search   │  │ exec     │  │ eos_chk  │  │       ││
│  └──────────┘  └──────────┘  └──────────┘  └──────┘│
│                                                      │
│  Core Tools:                                         │
│  ├─ list_skills    (사용 가능한 스킬 목록)              │
│  ├─ load_skill     (스킬 로드 → 도구 활성화)            │
│  ├─ register_tool  (동적 도구 등록)                    │
│  ├─ unregister_tool (동적 도구 해제)                   │
│  └─ list_dynamic_tools (동적 도구 목록)                │
│                                                      │
│  GET /health → 서버 상태 확인                          │
└──────────────────────────────────────────────────────┘
```

### 5.3 핵심 코드 (실제 프로젝트)

```python
from fastmcp import FastMCP

def create_fastmcp_router():
    # Sub-server 생성
    from app.mcp.servers.sysprobe_server import create_sysprobe_server
    from app.mcp.servers.task_server import create_task_server
    from app.mcp.servers.discovery_server import create_discovery_server
    from app.mcp.servers.scheduler_server import create_scheduler_server

    sp_server = create_sysprobe_server()
    task_server = create_task_server()
    disc_server = create_discovery_server()
    sched_server = create_scheduler_server()

    # Router 생성 & 마운트
    router = FastMCP(
        name="SysProbe MCP Router",
        instructions=(
            "서버 구성정보 관리 MCP Router. "
            "list_skills → load_skill 순서로 호출하여 워크플로우를 시작하세요."
        ),
    )

    router.mount(sp_server, prefix="sp")
    router.mount(task_server, prefix="task")
    router.mount(disc_server, prefix="disc")
    router.mount(sched_server, prefix="sched")

    # Core tools 등록
    router.tool(list_skills, name="list_skills", tags={"core"})
    router.tool(load_skill, name="load_skill", tags={"core"})

    return router
```

### 5.4 Skills 기반 도구 필터링

SysProbe에서는 **Skills 패턴**을 사용하여 LLM에게 필요한 도구만 노출합니다:

1. 에이전트가 `list_skills` 호출 → 사용 가능한 스킬 목록 반환
2. 에이전트가 `load_skill("text2sql")` 호출 → 해당 도구들만 활성화
3. 나머지 도구는 비활성 상태 유지

이 패턴의 장점:
- **토큰 절약**: 수십 개 도구 대신 3~4개의 core 도구만 초기 노출
- **컨텍스트 오염 방지**: LLM이 관련 없는 도구에 혼란되지 않음
- **동적 확장**: 런타임에 도구 등록/해제 가능

### 5.5 기업 환경 확장 가능성

| 시나리오 | 구현 방법 |
|---------|----------|
| 부서별 도구 분리 | 부서별 sub-server + Namespace |
| 권한별 도구 노출 | Visibility Transform + Auth Middleware |
| 멀티 환경 (dev/stg/prd) | ProxyProvider로 환경별 원격 서버 연결 |
| API 통합 | OpenAPIProvider로 기존 REST API를 MCP 도구화 |
| 도구 버전 관리 | VersionFilter로 v1/v2 동시 운영 |

---

## 6. 다른 MCP 프레임워크 비교

| 항목 | **FastMCP 3.x** | **mcp (공식 SDK)** | **LangChain Tools** |
|------|----------------|-------------------|---------------------|
| **언어** | Python | Python / TypeScript | Python |
| **추상화 수준** | High (프레임워크) | Low (SDK) | High (프레임워크) |
| **서버 구성** | Provider + Transform | 수동 핸들러 등록 | Agent 내부 도구 |
| **서버 합성** | mount, proxy 내장 | 직접 구현 | 해당 없음 |
| **도구 필터링** | Visibility, Tags, Version | 직접 구현 | 직접 구현 |
| **OpenAPI 통합** | OpenAPIProvider 내장 | 없음 | APIChain |
| **타입 안전** | Pydantic 기반 자동 스키마 | 수동 스키마 | Pydantic |
| **프로토콜 준수** | MCP 표준 | MCP 표준 | 자체 규격 |
| **호스트 호환** | 모든 MCP 호스트 | 모든 MCP 호스트 | LangChain 전용 |
| **커뮤니티** | 70% 점유율, 100만/일 DL | 공식 | 대규모 |

**핵심 차이**: FastMCP는 "MCP 서버를 잘 만드는 것"에 집중하고, LangChain은 "에이전트 내부에서 도구를 잘 쓰는 것"에 집중합니다. 공식 SDK는 프로토콜 구현만 제공하므로 프로덕션 패턴(Router, Proxy 등)은 직접 구현해야 합니다.

---

## 7. 결론 및 향후 전망

### 핵심 요약

1. **MCP**는 LLM ↔ 도구 연결의 사실상 표준으로 자리잡음
2. **FastMCP 3.x**는 Component/Provider/Transform 3가지 프리미티브로 아키텍처를 혁신
3. **Router 패턴**은 Provider + Transform의 자연스러운 조합 — 특별한 코드 불필요
4. **SysProbe**는 이 패턴을 실제 프로덕션에 적용한 사례

### 향후 전망

- **MCP 생태계 확대**: 더 많은 IDE, AI 에이전트가 MCP 지원
- **FastMCP 3.0 정식 릴리스**: 현재 RC → 곧 stable
- **MCP Apps**: FastMCP 3.x Beta 2에서 도입된 독립 실행형 MCP 앱
- **CIMD (Context-Informed Model Dispatch)**: 모델 라우팅 기능
- **엔터프라이즈 인증**: Google, GitHub, Azure, Auth0 등 통합 내장
- **Prefect Horizon**: FastMCP 서버 무료 호스팅 서비스

### 참고 자료

| 리소스 | URL |
|--------|-----|
| FastMCP 공식 문서 | https://gofastmcp.com |
| FastMCP GitHub | https://github.com/jlowin/fastmcp |
| FastMCP 3.0 소개 블로그 | https://www.jlowin.dev/blog/fastmcp-3-whats-new |
| MCP 공식 사이트 | https://modelcontextprotocol.io |
| FastMCP PyPI | https://pypi.org/project/fastmcp |

---

> 📝 발표자: [이름] | 📅 발표일: 2026-02-XX | 🏢 [팀명]
