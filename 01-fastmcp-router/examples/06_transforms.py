"""
Transform 시스템 — 컴포넌트 파이프라인 제어

Provider-level과 Server-level 2단계 Transform.
Namespace, ToolTransform, VersionFilter, 커스텀 Transform.
"""

from collections.abc import Sequence

from fastmcp import FastMCP
from fastmcp.server.providers import FastMCPProvider
from fastmcp.server.transforms import (
    GetToolNext,
    Namespace,
    ToolTransform,
    Transform,
    VersionFilter,
)
from fastmcp.tools import Tool
from fastmcp.tools.tool_transform import ToolTransformConfig

# ──────────────────────────────────────────────
# 1. Namespace Transform
# ──────────────────────────────────────────────

sub = FastMCP("Sub")


@sub.tool
def my_tool() -> str:
    return "hello"


main = FastMCP("Main")
main.mount(sub, namespace="api")
# my_tool → api_my_tool


# ──────────────────────────────────────────────
# 2. Transform 스태킹 (Provider-level)
# ──────────────────────────────────────────────

provider = FastMCPProvider(sub)
provider.add_transform(Namespace("api"))
provider.add_transform(
    ToolTransform(
        {
            "api_my_tool": ToolTransformConfig(
                name="short",
                description="에이전트에게 더 적합한 설명",
                tags={"optimized"},
            ),
        }
    )
)
# 흐름: "my_tool" → "api_my_tool" → "short"


# ──────────────────────────────────────────────
# 3. VersionFilter — API 버전 관리
# ──────────────────────────────────────────────

# api_v1 = FastMCP("API v1", providers=[components])
# api_v1.add_transform(VersionFilter(version_lt="2.0"))   # 2.0 미만만 노출
#
# api_v2 = FastMCP("API v2", providers=[components])
# api_v2.add_transform(VersionFilter(version_gte="2.0"))  # 2.0 이상만 노출


# ──────────────────────────────────────────────
# 4. 커스텀 Transform
# ──────────────────────────────────────────────


class TagFilter(Transform):
    """특정 태그를 가진 도구만 통과시키는 커스텀 Transform"""

    def __init__(self, required_tags: set[str]):
        self.required_tags = required_tags

    async def list_tools(self, tools: Sequence[Tool]) -> Sequence[Tool]:
        return [t for t in tools if t.tags & self.required_tags]

    async def get_tool(self, name: str, call_next: GetToolNext) -> Tool | None:
        tool = await call_next(name)
        return tool if tool and tool.tags & self.required_tags else None


# 사용 예:
# server.add_transform(TagFilter(required_tags={"production"}))


# ──────────────────────────────────────────────
# 5. Visibility 제어
# ──────────────────────────────────────────────

server = FastMCP("Server")


@server.tool(tags={"public"})
def public_api() -> str:
    return "public"


@server.tool(tags={"internal"})
def internal_api() -> str:
    return "internal"


# 방법 A: 블랙리스트
server.disable(tags={"internal"})

# 방법 B: 화이트리스트
# server.enable(tags={"public"}, only=True)


if __name__ == "__main__":
    main.run()
