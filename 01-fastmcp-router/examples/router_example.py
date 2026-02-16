"""
FastMCP Router 예제
===================
여러 sub-server를 하나의 Router로 마운트하는 예제입니다.

실행: python router_example.py
"""

from fastmcp import FastMCP

# ============================================================
# Sub-server 1: 데이터베이스 서버
# ============================================================
db_server = FastMCP("DB Server")


@db_server.tool
def query(sql: str) -> str:
    """SQL 쿼리를 실행합니다

    Args:
        sql: 실행할 SQL 쿼리
    """
    # 실제로는 DB 연결 후 실행
    return f"[쿼리 결과] {sql}"


@db_server.tool
def tables() -> list[str]:
    """사용 가능한 테이블 목록을 조회합니다"""
    return ["users", "orders", "products", "logs"]


@db_server.tool
def describe_table(table_name: str) -> dict:
    """테이블 스키마를 조회합니다

    Args:
        table_name: 조회할 테이블명
    """
    schemas = {
        "users": {"id": "int", "name": "varchar", "email": "varchar"},
        "orders": {"id": "int", "user_id": "int", "amount": "decimal"},
        "products": {"id": "int", "name": "varchar", "price": "decimal"},
    }
    return schemas.get(table_name, {"error": f"테이블 '{table_name}'을 찾을 수 없습니다"})


# ============================================================
# Sub-server 2: 파일 관리 서버
# ============================================================
file_server = FastMCP("File Server")


@file_server.tool
def read_file(path: str) -> str:
    """파일 내용을 읽습니다

    Args:
        path: 파일 경로
    """
    try:
        with open(path, "r") as f:
            return f.read()
    except FileNotFoundError:
        return f"파일을 찾을 수 없습니다: {path}"


@file_server.tool
def list_files(directory: str = ".") -> list[str]:
    """디렉토리의 파일 목록을 조회합니다

    Args:
        directory: 조회할 디렉토리 경로
    """
    import os
    try:
        return os.listdir(directory)
    except FileNotFoundError:
        return [f"디렉토리를 찾을 수 없습니다: {directory}"]


# ============================================================
# Sub-server 3: 모니터링 서버
# ============================================================
monitor_server = FastMCP("Monitor Server")


@monitor_server.tool
def cpu_usage() -> dict:
    """현재 CPU 사용률을 조회합니다"""
    return {"cpu_percent": 45.2, "cores": 8}


@monitor_server.tool
def memory_usage() -> dict:
    """현재 메모리 사용률을 조회합니다"""
    return {"total_gb": 16, "used_gb": 8.5, "percent": 53.1}


# ============================================================
# Router: 모든 서버를 하나로 통합
# ============================================================
router = FastMCP(
    name="Main Router",
    instructions=(
        "통합 MCP Router입니다. "
        "db_* 도구로 데이터베이스를, fs_* 도구로 파일을, mon_* 도구로 모니터링을 수행합니다."
    ),
)

# 마운트: prefix가 네임스페이스 역할
router.mount(db_server, prefix="db")      # db_query, db_tables, db_describe_table
router.mount(file_server, prefix="fs")    # fs_read_file, fs_list_files
router.mount(monitor_server, prefix="mon") # mon_cpu_usage, mon_memory_usage


# Router 자체 도구 (core)
@router.tool(tags={"core"})
def help() -> str:
    """사용 가능한 서브시스템을 안내합니다"""
    return """
    사용 가능한 서브시스템:
    - db_*  : 데이터베이스 조회 (query, tables, describe_table)
    - fs_*  : 파일 관리 (read_file, list_files)
    - mon_* : 시스템 모니터링 (cpu_usage, memory_usage)
    """


if __name__ == "__main__":
    router.run(
        transport="streamable-http",
        host="0.0.0.0",
        port=8001,
        path="/mcp",
    )
