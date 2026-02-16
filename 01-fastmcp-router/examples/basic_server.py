"""
FastMCP 기본 서버 예제
=====================
가장 간단한 MCP 서버 생성 예제입니다.

실행: python basic_server.py
또는: fastmcp run basic_server.py
"""

from fastmcp import FastMCP

mcp = FastMCP("Basic Server")


@mcp.tool
def greet(name: str) -> str:
    """사용자에게 인사합니다"""
    return f"안녕하세요, {name}님!"


@mcp.tool
def calculate(a: float, b: float, op: str = "add") -> float:
    """두 수의 사칙연산을 수행합니다

    Args:
        a: 첫 번째 숫자
        b: 두 번째 숫자
        op: 연산자 (add, sub, mul, div)
    """
    ops = {
        "add": lambda: a + b,
        "sub": lambda: a - b,
        "mul": lambda: a * b,
        "div": lambda: a / b if b != 0 else float("inf"),
    }
    if op not in ops:
        raise ValueError(f"지원하지 않는 연산자: {op}. 사용 가능: {list(ops.keys())}")
    return ops[op]()


@mcp.resource("config://version")
def get_version() -> str:
    """서버 버전을 반환합니다"""
    return "1.0.0"


@mcp.prompt
def sql_helper(table_name: str) -> str:
    """SQL 작성을 도와주는 프롬프트"""
    return f"{table_name} 테이블에 대한 SQL 쿼리를 작성해주세요."


if __name__ == "__main__":
    mcp.run()
