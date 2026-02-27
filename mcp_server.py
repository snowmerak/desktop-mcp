"""
PAG MCP Server

실행 방법:
    python mcp_server.py

Claude Desktop 설정 예시 (claude_desktop_config.json):
    {
        "mcpServers": {
            "pag": {
                "command": "uv",
                "args": ["--directory", "/path/to/pag", "run", "mcp_server.py"],
                "env": {
                    "PAG_API_URL": "http://localhost:1234/v1/chat/completions",
                    "PAG_MODEL": "your-multimodal-model"
                }
            }
        }
    }
"""

import base64
import json
import os
import sys
import time
from pathlib import Path

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server
from mcp.server.models import InitializationOptions

# 프로젝트 루트를 sys.path에 추가
sys.path.insert(0, str(Path(__file__).parent))

import pyautogui
from utils.platform import capture_screenshot as _capture_screenshot, open_app, open_uri
from utils.input import type_text, scroll, press, hotkey, move_to, drag, get_clipboard, normalized_to_screen
from utils.actions import click_on, double_click_on, right_click_on, hover_on, wait_and_click, drag_from_to
from utils.llm import (
    get_coordinates_from_image,
    get_bounding_box_from_image,
    check_condition_from_image,
    read_text_from_screen,
    find_all_elements,
    extract_structured_data,
    wait_until,
    fetch_models,
    mark_region_on_image,
)
from utils.image import encode_image_to_base64


server = Server("pag")

SCREENSHOT_PATH = "/tmp/pag_mcp_screenshot.png"


def _image_content(image_path: str) -> list:
    """이미지를 MCP ImageContent로 변환합니다."""
    try:
        with open(image_path, "rb") as f:
            data = base64.b64encode(f.read()).decode("utf-8")
        return [
            types.TextContent(type="text", text=f"Screenshot saved: {image_path}"),
            types.ImageContent(type="image", data=data, mimeType="image/png"),
        ]
    except Exception as e:
        return [types.TextContent(type="text", text=f"이미지 로드 실패: {e}")]


def _text(msg: str) -> list:
    return [types.TextContent(type="text", text=str(msg))]


# ── 스크린샷 / 비전 ────────────────────────────────────────────

@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        # 스크린샷
        types.Tool(
            name="capture_screenshot",
            description="현재 화면을 캡처하고 이미지를 반환합니다. 모든 비전 분석의 첫 단계입니다.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # 비전 (로컬 LLM 사용)
        types.Tool(
            name="get_coordinates",
            description="스크린샷에서 자연어로 설명된 UI 요소의 중심 좌표를 반환합니다 (0~1000 정규화).",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "스크린샷 파일 경로"},
                    "description": {"type": "string", "description": "찾을 UI 요소 설명"},
                },
                "required": ["image_path", "description"],
            },
        ),
        types.Tool(
            name="get_bounding_box",
            description="스크린샷에서 자연어로 설명된 영역의 바운딩 박스를 반환합니다 (0~1000 정규화).",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "스크린샷 파일 경로"},
                    "description": {"type": "string", "description": "찾을 영역 설명"},
                },
                "required": ["image_path", "description"],
            },
        ),
        types.Tool(
            name="check_condition",
            description="스크린샷에서 자연어로 설명된 조건이 충족됐는지 확인합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "스크린샷 파일 경로"},
                    "condition": {"type": "string", "description": "확인할 조건"},
                },
                "required": ["image_path", "condition"],
            },
        ),
        types.Tool(
            name="read_text",
            description="스크린샷의 특정 영역에서 텍스트를 읽어 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "스크린샷 파일 경로"},
                    "region": {"type": "string", "description": "텍스트를 읽을 영역 설명"},
                },
                "required": ["image_path", "region"],
            },
        ),
        types.Tool(
            name="find_all_elements",
            description="스크린샷에서 조건에 맞는 UI 요소를 모두 찾아 좌표 리스트를 반환합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "스크린샷 파일 경로"},
                    "description": {"type": "string", "description": "찾을 요소 설명"},
                },
                "required": ["image_path", "description"],
            },
        ),
        types.Tool(
            name="extract_structured_data",
            description="스크린샷에서 JSON 스키마에 맞는 구조화된 데이터를 추출합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "스크린샷 파일 경로"},
                    "schema": {"type": "string", "description": "추출할 데이터 구조의 JSON 스키마 예시 (문자열)"},
                    "context": {"type": "string", "description": "추출할 데이터에 대한 보조 설명 (선택)"},
                },
                "required": ["image_path", "schema"],
            },
        ),
        types.Tool(
            name="mark_region",
            description="스크린샷 위에 바운딩 박스를 그려 저장합니다. 디버깅·시각화용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "image_path": {"type": "string", "description": "원본 이미지 경로"},
                    "box": {
                        "type": "string",
                        "description": 'JSON 형식 바운딩 박스: {"x1":0,"y1":0,"x2":500,"y2":300}',
                    },
                    "output_path": {"type": "string", "description": "저장 경로 (선택, 기본값: 원본 덮어씀)"},
                    "color": {"type": "string", "description": "박스 색상 (기본값: red)"},
                    "label": {"type": "string", "description": "박스 위 표시할 텍스트 (선택)"},
                },
                "required": ["image_path", "box"],
            },
        ),
        # 대기
        types.Tool(
            name="wait_until",
            description="조건이 충족될 때까지 반복적으로 화면을 캡처해 확인합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "condition": {"type": "string", "description": "충족 여부를 확인할 조건"},
                    "interval": {"type": "number", "description": "확인 주기 (초, 기본값 1.0)"},
                    "timeout": {"type": "number", "description": "최대 대기 시간 (초, 기본값 30.0)"},
                },
                "required": ["condition"],
            },
        ),
        # 클릭 / 액션
        types.Tool(
            name="click_on",
            description="화면에서 자연어로 설명된 UI 요소를 찾아 클릭합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "클릭할 요소 설명"},
                    "double": {"type": "boolean", "description": "더블클릭 여부 (기본값 false)"},
                    "right": {"type": "boolean", "description": "우클릭 여부 (기본값 false)"},
                },
                "required": ["description"],
            },
        ),
        types.Tool(
            name="hover_on",
            description="화면에서 자연어로 설명된 UI 요소 위로 커서를 이동합니다 (클릭 없음).",
            inputSchema={
                "type": "object",
                "properties": {
                    "description": {"type": "string", "description": "호버할 요소 설명"},
                },
                "required": ["description"],
            },
        ),
        types.Tool(
            name="drag_from_to",
            description="화면에서 두 요소를 자연어로 설명해 드래그합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "from_description": {"type": "string", "description": "드래그 시작 요소 설명"},
                    "to_description": {"type": "string", "description": "드래그 끝 요소 설명"},
                },
                "required": ["from_description", "to_description"],
            },
        ),
        types.Tool(
            name="wait_and_click",
            description="조건이 충족될 때까지 대기한 뒤 요소를 클릭합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "condition": {"type": "string", "description": "대기할 조건"},
                    "click_description": {
                        "type": "string",
                        "description": "클릭할 요소 설명 (생략 시 조건 설명과 동일하게 클릭)",
                    },
                    "timeout": {"type": "number", "description": "최대 대기 시간 (초, 기본값 30.0)"},
                },
                "required": ["condition"],
            },
        ),
        # 키보드
        types.Tool(
            name="type_text",
            description="텍스트를 클립보드를 통해 입력합니다. 한글/영어/특수문자 모두 지원.",
            inputSchema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "입력할 텍스트"},
                },
                "required": ["text"],
            },
        ),
        types.Tool(
            name="press",
            description='키를 누릅니다. 예: "enter", "escape", "tab", "down".',
            inputSchema={
                "type": "object",
                "properties": {
                    "key": {"type": "string", "description": "누를 키 이름"},
                    "presses": {"type": "integer", "description": "반복 횟수 (기본값 1)"},
                },
                "required": ["key"],
            },
        ),
        types.Tool(
            name="hotkey",
            description='키 조합을 누릅니다. 예: ["command", "a"], ["ctrl", "c"].',
            inputSchema={
                "type": "object",
                "properties": {
                    "keys": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": '누를 키 목록. 예: ["command", "a"]',
                    },
                },
                "required": ["keys"],
            },
        ),
        # 스크롤 / 마우스
        types.Tool(
            name="scroll",
            description="스크롤합니다. amount 양수=위, 음수=아래. 일반적으로 -3 ~ -10 사용.",
            inputSchema={
                "type": "object",
                "properties": {
                    "amount": {"type": "integer", "description": "스크롤 양 (양수=위, 음수=아래)"},
                    "x": {"type": "integer", "description": "스크롤 위치 X (선택, 없으면 현재 커서)"},
                    "y": {"type": "integer", "description": "스크롤 위치 Y (선택, 없으면 현재 커서)"},
                },
                "required": ["amount"],
            },
        ),
        types.Tool(
            name="get_clipboard",
            description="현재 클립보드의 텍스트를 읽어 반환합니다.",
            inputSchema={"type": "object", "properties": {}, "required": []},
        ),
        # 앱 실행
        types.Tool(
            name="open_app",
            description="앱 이름 또는 경로로 GUI 응용프로그램을 실행합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "app_name_or_path": {"type": "string", "description": "앱 이름 또는 경로"},
                },
                "required": ["app_name_or_path"],
            },
        ),
        types.Tool(
            name="open_uri",
            description="URI 스킴으로 앱을 실행합니다. 예: spotify:search:...",
            inputSchema={
                "type": "object",
                "properties": {
                    "uri": {"type": "string", "description": "URI 스킴 문자열"},
                },
                "required": ["uri"],
            },
        ),
        types.Tool(
            name="sleep",
            description="지정한 시간(초) 동안 대기합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "seconds": {"type": "number", "description": "대기할 시간 (초)"},
                },
                "required": ["seconds"],
            },
        ),
        # 설정
        types.Tool(
            name="set_llm_config",
            description="비전 분석에 사용할 로컬 LLM의 API URL, 모델, API 키를 설정합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "API URL (예: http://localhost:1234/v1/chat/completions)"},
                    "model": {"type": "string", "description": "모델 이름"},
                    "api_key": {"type": "string", "description": "API 키 (선택)"},
                },
                "required": ["api_url", "model"],
            },
        ),
        types.Tool(
            name="fetch_models",
            description="로컬 LLM 서버에서 사용 가능한 모델 목록을 조회합니다.",
            inputSchema={
                "type": "object",
                "properties": {
                    "api_url": {"type": "string", "description": "LLM 서버 베이스 URL (예: http://localhost:1234)"},
                },
                "required": ["api_url"],
            },
        ),
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent | types.ImageContent]:
    try:
        # ── 스크린샷 ─────────────────────────────────────────
        if name == "capture_screenshot":
            path = _capture_screenshot(SCREENSHOT_PATH)
            return _image_content(path)

        # ── 비전 ─────────────────────────────────────────────
        elif name == "get_coordinates":
            result = get_coordinates_from_image(arguments["image_path"], arguments["description"])
            if result:
                return _text(json.dumps({"x": result[0], "y": result[1]}))
            return _text("요소를 찾지 못했습니다.")

        elif name == "get_bounding_box":
            result = get_bounding_box_from_image(arguments["image_path"], arguments["description"])
            if result:
                return _text(json.dumps({"x1": result[0], "y1": result[1], "x2": result[2], "y2": result[3]}))
            return _text("영역을 찾지 못했습니다.")

        elif name == "check_condition":
            result = check_condition_from_image(arguments["image_path"], arguments["condition"])
            return _text(json.dumps({"result": result}))

        elif name == "read_text":
            result = read_text_from_screen(arguments["image_path"], arguments["region"])
            return _text(result or "텍스트를 읽지 못했습니다.")

        elif name == "find_all_elements":
            result = find_all_elements(arguments["image_path"], arguments["description"])
            return _text(json.dumps([{"x": x, "y": y} for x, y in result]))

        elif name == "extract_structured_data":
            schema = json.loads(arguments["schema"])
            result = extract_structured_data(
                arguments["image_path"],
                schema,
                arguments.get("context", ""),
            )
            return _text(json.dumps(result, ensure_ascii=False, indent=2))

        elif name == "mark_region":
            box_dict = json.loads(arguments["box"])
            box = (box_dict["x1"], box_dict["y1"], box_dict["x2"], box_dict["y2"])
            out = mark_region_on_image(
                arguments["image_path"],
                box,
                output_path=arguments.get("output_path"),
                color=arguments.get("color", "red"),
                label=arguments.get("label"),
            )
            return _image_content(out)

        # ── 대기 ─────────────────────────────────────────────
        elif name == "wait_until":
            result = wait_until(
                arguments["condition"],
                _capture_screenshot,
                interval=arguments.get("interval", 1.0),
                timeout=arguments.get("timeout", 30.0),
            )
            return _text("조건 충족" if result else "타임아웃")

        # ── 클릭 / 액션 ───────────────────────────────────────
        elif name == "click_on":
            result = click_on(
                arguments["description"],
                double=arguments.get("double", False),
                right=arguments.get("right", False),
            )
            return _text(f"클릭 완료: {result}" if result else "요소를 찾지 못했습니다.")

        elif name == "hover_on":
            result = hover_on(arguments["description"])
            return _text(f"호버 완료: {result}" if result else "요소를 찾지 못했습니다.")

        elif name == "drag_from_to":
            result = drag_from_to(arguments["from_description"], arguments["to_description"])
            return _text(f"드래그 완료: {result}" if result else "요소를 찾지 못했습니다.")

        elif name == "wait_and_click":
            result = wait_and_click(
                arguments["condition"],
                arguments.get("click_description"),
                timeout=arguments.get("timeout", 30.0),
            )
            return _text(f"클릭 완료: {result}" if result else "타임아웃 또는 요소 없음")

        # ── 키보드 ────────────────────────────────────────────
        elif name == "type_text":
            type_text(arguments["text"])
            return _text(f"입력 완료: {arguments['text']!r}")

        elif name == "press":
            pyautogui.press(arguments["key"], presses=arguments.get("presses", 1))
            return _text(f"키 입력: {arguments['key']}")

        elif name == "hotkey":
            pyautogui.hotkey(*arguments["keys"])
            return _text(f"단축키: {'+'.join(arguments['keys'])}")

        # ── 스크롤 / 마우스 ───────────────────────────────────
        elif name == "scroll":
            scroll(arguments["amount"], x=arguments.get("x"), y=arguments.get("y"))
            return _text(f"스크롤: {arguments['amount']}")

        elif name == "get_clipboard":
            return _text(get_clipboard())

        # ── 앱 실행 ───────────────────────────────────────────
        elif name == "open_app":
            open_app(arguments["app_name_or_path"])
            return _text(f"앱 실행: {arguments['app_name_or_path']}")

        elif name == "open_uri":
            open_uri(arguments["uri"])
            return _text(f"URI 열기: {arguments['uri']}")

        elif name == "sleep":
            time.sleep(arguments["seconds"])
            return _text(f"{arguments['seconds']}초 대기 완료")

        # ── 설정 ─────────────────────────────────────────────
        elif name == "set_llm_config":
            os.environ["PAG_API_URL"] = arguments["api_url"]
            os.environ["PAG_MODEL"] = arguments["model"]
            if "api_key" in arguments:
                os.environ["PAG_API_KEY"] = arguments["api_key"]
            return _text(f"설정 완료 — URL: {arguments['api_url']}, 모델: {arguments['model']}")

        elif name == "fetch_models":
            models = fetch_models(arguments["api_url"])
            return _text(json.dumps(models, ensure_ascii=False))

        else:
            return _text(f"알 수 없는 툴: {name}")

    except Exception as e:
        return _text(f"오류 ({name}): {e}")


async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="pag",
                server_version="0.1.0",
                capabilities=server.get_capabilities(
                    notification_options=None,
                    experimental_capabilities={},
                ),
            ),
        )


def main_sync():
    """uvx / pyproject.toml 스크립트 진입점."""
    import asyncio
    asyncio.run(main())


if __name__ == "__main__":
    main_sync()
