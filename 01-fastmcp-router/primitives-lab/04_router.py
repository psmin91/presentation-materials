"""
조합 4️⃣ mount() + Namespace → 탑승구 구역제 (라우터)

✈️ 비유: 탑승권에 B12라고 적혀있으면, 안내원한테 물어볼 필요 없이
   자동으로 B구역으로 가죠? 접두사가 곧 라우팅입니다.

사용하는 프리미티브:
  - Namespace Transform (접두사 = 라우팅 키)

언제 쓰나요?
  - 사실 조합 3(애그리게이터)을 쓰면 라우팅은 자동으로 따라옵니다!
  - namespace 접두사 자체가 라우팅 역할을 합니다.
  - 여기서는 라우팅이 어떻게 작동하는지에 초점을 맞춥니다.

구조:
  Client 호출: "sp_text2sql"
    → Main이 "sp_" 접두사를 보고 sp_server로 자동 전달!
"""

from fastmcp import FastMCP

# ============================================================
# 도메인별 서버 (SysProbe 프로젝트 예시)
# ============================================================

# A구역 = Text2SQL (서버 구성정보 조회)
sp_server = FastMCP("SysProbe - Text2SQL")

@sp_server.tool
def text2sql(question: str) -> str:
    """자연어 질문을 SQL로 변환하여 실행합니다"""
    return f"🔍 질문: {question}\n📊 SQL: SELECT * FROM servers WHERE ...\n✅ 결과: 24건"

@sp_server.tool
def rag_search(query: str) -> str:
    """스키마 정보를 RAG로 검색합니다"""
    return f"📚 '{query}' 관련 테이블: servers, cpu_info, memory_info"

@sp_server.tool
def db_query(sql: str) -> str:
    """SQL을 직접 실행합니다 (SELECT만 허용)"""
    return f"📊 실행: {sql} → 결과 반환"


# B구역 = OPMATE (작업 실행)
task_server = FastMCP("SysProbe - OPMATE")

@task_server.tool
def node_lookup(hostname: str) -> str:
    """OPMATE 노드 정보를 조회합니다"""
    return f"🖥️ {hostname}: 상태=active, OS=RHEL 8.9, IP=10.0.1.10"

@task_server.tool
def task_exec(task_name: str, target: str) -> str:
    """OPMATE 작업을 실행합니다"""
    return f"⚡ 작업 '{task_name}' → {target}에서 실행 중... (job_id: 12345)"


# C구역 = AutoDiscovery (자동 수집)
disc_server = FastMCP("SysProbe - AutoDiscovery")

@disc_server.tool
def collect(target: str) -> str:
    """서버 구성정보를 자동 수집합니다"""
    return f"📡 {target} 수집 시작... CPU, 메모리, 디스크 정보 수집 완료"

@disc_server.tool
def mapping(hostname: str) -> str:
    """호스트-소프트웨어 매핑 정보를 조회합니다"""
    return f"📋 {hostname}: Apache 2.4, MySQL 8.0, Python 3.12"


# D구역 = Scheduler (스케줄러)
sched_server = FastMCP("SysProbe - Scheduler")

@sched_server.tool
def create_schedule(name: str, cron: str, email: str) -> str:
    """스케줄 작업을 생성합니다"""
    return f"⏰ 생성: '{name}' → {cron} → 결과를 {email}로 발송"

@sched_server.tool
def list_schedules() -> str:
    """등록된 스케줄 목록을 조회합니다"""
    return "📋 1. 일일 장비 리포트 (매일 09:00)\n   2. EOS 점검 (매주 월 10:00)"


# ============================================================
# 메인 라우터 = 공항 통합 터미널
# ============================================================

main = FastMCP("SysProbe MCP Router")

# 각 구역에 서버 배치 (namespace = 탑승구 구역 번호)
main.mount(sp_server, namespace="sp")         # sp_text2sql, sp_rag_search, sp_db_query
main.mount(task_server, namespace="task")     # task_node_lookup, task_exec
main.mount(disc_server, namespace="disc")     # disc_collect, disc_mapping
main.mount(sched_server, namespace="sched")   # sched_create_schedule, sched_list_schedules

# 라우팅은 자동!
# "sp_text2sql" 호출 → sp_server로
# "task_exec" 호출 → task_server로
# 별도 라우팅 코드 없음!


if __name__ == "__main__":
    print("=" * 60)
    print("🚪 조합 4: 라우터 패턴 (탑승구 구역제)")
    print("=" * 60)
    print()
    print("  namespace 접두사가 곧 라우팅입니다:")
    print()
    print("  A구역 (sp_)    → Text2SQL    : sp_text2sql, sp_rag_search, sp_db_query")
    print("  B구역 (task_)  → OPMATE      : task_node_lookup, task_exec")
    print("  C구역 (disc_)  → AutoDiscovery: disc_collect, disc_mapping")
    print("  D구역 (sched_) → Scheduler   : sched_create_schedule, sched_list_schedules")
    print()
    print("  총 도구 수: 9개")
    print()
    print('  Client: "sp_text2sql 호출해줘"')
    print('    → Main: "sp_" 접두사니까 → A구역(sp_server)으로!')
    print("    → sp_server: text2sql 실행 → 결과 반환")
    print()
    print("  핵심: 라우팅 코드 0줄. namespace가 전부 해줍니다.")
    print()

    main.run(transport="streamable-http", host="127.0.0.1", port=8001)
