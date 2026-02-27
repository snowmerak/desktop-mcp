import json
import os
import tempfile
import urllib.request
import urllib.error

from utils.image import encode_image_to_base64


def _resolve_settings(api_url, model, api_key=None):
    """api_url, model, api_key가 None이면 환경변수에서 채웁니다."""
    import os
    api_url = api_url or os.environ.get("PAG_API_URL", "http://localhost:1234/v1/chat/completions")
    model = model or os.environ.get("PAG_MODEL", "")
    api_key = api_key or os.environ.get("PAG_API_KEY", "")
    return api_url, model, api_key


def get_coordinates_from_image(
    image_path,
    feature_description,
    api_url=None,
    model=None,
):
    """
    이미지에서 자연어로 설명된 UI 요소의 중심 좌표를 LLM을 통해 반환합니다.

    Args:
        image_path:          분석할 스크린샷 경로
        feature_description: 찾고자 하는 UI 요소에 대한 자연어 설명
        api_url:             LM Studio OpenAI 호환 API URL
        model:               사용할 멀티모달 모델 이름

    Returns:
        (x, y) 튜플 — 0~1000 정규화 좌표. 실패 시 None.
    """
    api_url, model, api_key = _resolve_settings(api_url, model)
    img_str = encode_image_to_base64(image_path)

    prompt = (
        f"This is a screenshot of a desktop application. "
        f"Find the following UI element: {feature_description}. "
        "Return the EXACT coordinates of the center of that element. "
        "IMPORTANT: You MUST return the coordinates normalized between 0 and 1000, "
        "where (0,0) is the top-left corner of the image and (1000,1000) is the bottom-right corner. "
        "Your response MUST be ONLY a JSON format like this, and no other text:\n"
        '{"x": 500, "y": 300}'
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 100,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"LLM 응답: {content}")

        # 마크다운 코드 블록 파싱 처리
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()

        coords = json.loads(content)
        if "x" in coords and "y" in coords:
            return (float(coords["x"]), float(coords["y"]))

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"좌표 분석 중 오류: {e}")

    return None


def check_condition_from_image(
    image_path,
    condition_description,
    api_url=None,
    model=None,
):
    """
    이미지를 보고 자연어로 설명된 조건이 충족됐는지 여부를 반환합니다.

    Args:
        image_path:            분석할 스크린샷 경로
        condition_description: 확인할 조건에 대한 자연어 설명
        api_url:               LM Studio OpenAI 호환 API URL
        model:                 사용할 멀티모달 모델 이름

    Returns:
        True (조건 충족) / False (미충족) / None (분석 실패)
    """
    api_url, model, api_key = _resolve_settings(api_url, model)
    img_str = encode_image_to_base64(image_path)

    prompt = (
        f"This is a screenshot of a desktop. "
        f"Check whether the following condition is met: {condition_description}. "
        "Your response MUST be ONLY a JSON format like this, and no other text:\n"
        '{"result": true}'
        "\nor\n"
        '{"result": false}'
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 20,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"LLM 상태 확인 응답: {content}")

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()

        parsed = json.loads(content)
        return bool(parsed.get("result"))

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"조건 확인 중 오류: {e}")

    return None


def wait_until(
    condition_description,
    capture_fn,
    screenshot_path=os.path.join(tempfile.gettempdir(), "wait_screenshot.png"),
    interval=1.0,
    timeout=30.0,
    api_url=None,
    model=None,
):
    """
    조건이 충족될 때까지 interval초마다 스크린샷을 찍어 LLM으로 확인합니다.

    Args:
        condition_description: 충족 여부를 확인할 자연어 조건
        capture_fn:            스크린샷 캡처 함수 (경로 반환)
        screenshot_path:       스크린샷 저장 경로
        interval:              확인 주기 (초)
        timeout:               최대 대기 시간 (초)

    Returns:
        True (조건 충족) / False (타임아웃)
    """
    import time
    api_url, model, api_key = _resolve_settings(api_url, model)

    elapsed = 0.0
    while elapsed < timeout:
        path = capture_fn(screenshot_path)
        result = check_condition_from_image(path, condition_description, api_url, model)

        if result is True:
            print(f"조건 충족: '{condition_description}' ({elapsed:.1f}초 경과)")
            return True

        print(f"대기 중... ({elapsed:.1f}s / {timeout}s)")
        time.sleep(interval)
        elapsed += interval

    print(f"타임아웃: {timeout}초 내에 조건이 충족되지 않았습니다.")
    return False


def get_bounding_box_from_image(
    image_path,
    region_description,
    api_url=None,
    model=None,
):
    """
    이미지에서 자연어로 설명된 영역의 바운딩 박스를 반환합니다.

    Returns:
        (x1, y1, x2, y2) 튜플 — 0~1000 정규화 좌표. 실패 시 None.
    """
    api_url, model, api_key = _resolve_settings(api_url, model)
    img_str = encode_image_to_base64(image_path)

    prompt = (
        f"This is a screenshot of a desktop application. "
        f"Find the bounding box of the following region: {region_description}. "
        "Return the coordinates normalized between 0 and 1000, "
        "where (0,0) is the top-left and (1000,1000) is the bottom-right. "
        "Your response MUST be ONLY a JSON format like this, and no other text:\n"
        '{"x1": 100, "y1": 200, "x2": 400, "y2": 350}'
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 60,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"LLM 바운딩 박스 응답: {content}")

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()

        box = json.loads(content)
        if all(k in box for k in ("x1", "y1", "x2", "y2")):
            return (float(box["x1"]), float(box["y1"]), float(box["x2"]), float(box["y2"]))

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"바운딩 박스 분석 중 오류: {e}")

    return None


def read_text_from_screen(
    image_path,
    region_description,
    api_url=None,
    model=None,
):
    """
    이미지에서 자연어로 설명된 영역의 텍스트를 읽어 반환합니다.

    Returns:
        텍스트 문자열. 실패 시 None.
    """
    api_url, model, api_key = _resolve_settings(api_url, model)
    img_str = encode_image_to_base64(image_path)

    prompt = (
        f"This is a screenshot of a desktop application. "
        f"Read and return ALL the text found in the following region: {region_description}. "
        "Your response MUST be ONLY a JSON format like this, and no other text:\n"
        '{"text": "the extracted text here"}'
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 500,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"LLM 텍스트 읽기 응답: {content}")

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.replace("```", "").strip()

        parsed = json.loads(content)
        return parsed.get("text")

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"텍스트 읽기 중 오류: {e}")

    return None


def find_all_elements(
    image_path,
    description,
    api_url=None,
    model=None,
):
    """
    이미지에서 자연어 설명에 맞는 UI 요소를 모두 찾아 좌표 리스트를 반환합니다.

    Args:
        image_path:   분석할 스크린샷 경로
        description:  찾을 요소에 대한 자연어 설명 (복수)

    Returns:
        [(x, y), ...] — 0~1000 정규화 좌표 리스트. 실패 시 빈 리스트.
    """
    api_url, model, api_key = _resolve_settings(api_url, model)
    img_str = encode_image_to_base64(image_path)

    prompt = (
        f"This is a screenshot of a desktop application. "
        f"Find ALL elements matching: {description}. "
        "Return the center coordinates of EACH element, normalized between 0 and 1000, "
        "where (0,0) is top-left and (1000,1000) is bottom-right. "
        "Your response MUST be ONLY a JSON array like this, and no other text:\n"
        '[{"x": 100, "y": 200}, {"x": 300, "y": 400}]'
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 512,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"LLM 다중 요소 응답: {content}")

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        items = json.loads(content)
        if isinstance(items, list):
            return [(float(item["x"]), float(item["y"])) for item in items if "x" in item and "y" in item]

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"다중 요소 분석 중 오류: {e}")

    return []


def extract_structured_data(
    image_path,
    schema: dict,
    context_description: str = "",
    api_url=None,
    model=None,
):
    """
    이미지에서 JSON 스키마에 맞는 구조화된 데이터를 추출합니다.

    Args:
        image_path:           분석할 스크린샷 경로
        schema:               추출할 데이터 구조를 나타내는 예시 JSON (dict 또는 list)
        context_description:  어떤 데이터를 찾을지 보조 설명 (선택)

    Returns:
        파싱된 Python 객체 (dict 또는 list). 실패 시 None.

    Example:
        extract_structured_data(
            path,
            schema=[{"title": "", "viewer_count": 0, "streamer": ""}],
            context_description="live broadcast items on the page",
        )
    """
    api_url, model, api_key = _resolve_settings(api_url, model)
    img_str = encode_image_to_base64(image_path)

    schema_str = json.dumps(schema, ensure_ascii=False, indent=2)
    context_hint = f" Focus on: {context_description}." if context_description else ""

    prompt = (
        f"This is a screenshot of a desktop application.{context_hint} "
        "Extract the data visible on screen and return it in the exact JSON structure shown below. "
        "Fill in actual values from the screenshot. "
        "Your response MUST be ONLY valid JSON matching the schema, no explanation:\n\n"
        f"{schema_str}"
    )

    payload = {
        "model": model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_str}"},
                    },
                ],
            }
        ],
        "temperature": 0.1,
        "max_tokens": 1024,
    }

    req = urllib.request.Request(
        api_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"LLM 구조화 데이터 응답: {content[:200]}...")

        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        return json.loads(content)

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"구조화 데이터 추출 중 오류: {e}")

    return None


# 사용 가능한 유틸리티 함수 목록 — 코드 생성 시 LLM에 제공하는 시스템 프롬프트용
AVAILABLE_FUNCTIONS_DOC = """
You generate Python automation workflow code using the following pre-imported utility functions.
All functions are already imported and ready to use. Do NOT add any import statements.

## Input / Interaction
- `click_on(description)` — find and left-click a UI element described in natural language
- `double_click_on(description)` — find and double-click a UI element
- `right_click_on(description)` — find and right-click a UI element
- `hover_on(description)` — move cursor over a UI element without clicking (opens dropdowns, tooltips)
- `wait_and_click(condition_description, click_description=None)` — wait until condition is met, then click
- `drag_from_to(from_description, to_description)` — drag from one described element to another
- `type_text(text)` — type text via clipboard (works for Korean, English, symbols)
- `scroll(amount, x=None, y=None)` — scroll at position; positive=up, negative=down
- `press(key)` — press a keyboard key (e.g. "enter", "escape", "tab")
- `hotkey(*keys)` — press a key combination (e.g. hotkey("command", "a"))
- `move_to(x, y)` — move cursor to screen coordinates without clicking
- `drag(from_xy, to_xy)` — drag between two (x, y) screen coordinate tuples
- `get_clipboard()` — read current clipboard text

## Screen / Vision
- `capture_screenshot(path)` — capture the current screen, returns path
- `get_coordinates_from_image(image_path, feature_description)` — returns (x, y) normalized 0-1000
- `get_bounding_box_from_image(image_path, region_description)` — returns (x1, y1, x2, y2) normalized 0-1000
- `check_condition_from_image(image_path, condition_description)` — returns True/False
- `read_text_from_screen(image_path, region_description)` — returns text string
- `find_all_elements(image_path, description)` — returns list of (x, y) for all matching elements
- `extract_structured_data(image_path, schema, context_description)` — returns structured dict/list matching the given schema
- `wait_until(condition_description, capture_fn, interval=1.0, timeout=30.0)` — polls until condition is met
- `normalized_to_screen(nx, ny)` — converts 0-1000 coords to actual screen pixels
- `mark_region_on_image(image_path, normalized_box, output_path, color, label)` — draws bbox on image

## App Launch
- `open_uri(uri)` — open a URI scheme (e.g. "spotify:search:...")
- `open_app(app_name_or_path)` — launch an app by name or path

## Timing
- `time.sleep(seconds)` — wait for given seconds

## Guidelines
- Always use `wait_until(...)` after launching an app or navigating to a new page.
- Use `capture_screenshot()` before calling any vision function.
- ALWAYS wrap the main logic in a function named `run()` AND call it at the very last line. The final two lines MUST be the function definition closing and then `run()` on its own line.
- Keep the code concise and readable.
- Do NOT use any imports — all functions are pre-imported.
- `open_uri(uri)` is for app URI schemes only (e.g. `spotify:`, `slack://`). Do NOT use it for http/https URLs.
- To navigate to a web URL: use `click_on("address bar")`, then `hotkey("command", "a")` (mac) or `hotkey("ctrl", "a")` (win), then `type_text(url)`, then `press("enter")`.
- `scroll(amount)` uses pyautogui scroll click units, NOT pixels. Use small values like -3 to -10 for normal scrolling.
- When reading multiple items from a page (e.g. list of titles), capture one screenshot and call `read_text_from_screen` once with a broad region description (e.g. "all visible live broadcast titles on the page") rather than calling it multiple times with narrow regions.
- `wait_until` condition descriptions should be specific and verifiable from a screenshot (e.g. "the Soop Live homepage is loaded and live broadcast thumbnails are visible").
"""


def generate_workflow_code(
    nl_command: str,
    api_url: str,
    model: str,
) -> str | None:
    """
    자연어 명령어를 받아 워크플로우 Python 코드를 생성합니다.

    Args:
        nl_command: 자연어로 작성된 자동화 명령
        api_url:    LLM API 베이스 URL (예: http://localhost:1234)
        model:      사용할 모델 이름

    Returns:
        생성된 Python 코드 문자열. 실패 시 None.
    """
    import re

    url = api_url.rstrip("/") + "/v1/chat/completions"

    payload = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": AVAILABLE_FUNCTIONS_DOC,
            },
            {
                "role": "user",
                "content": (
                    f"Generate a Python automation workflow for the following task:\n\n"
                    f"{nl_command}\n\n"
                    "Return ONLY the Python code, no explanation, no markdown code blocks."
                ),
            },
        ],
        "temperature": 0.2,
        "max_tokens": 1024,
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
        },
    )

    try:
        with urllib.request.urlopen(req) as response:
            result = json.loads(response.read().decode("utf-8"))

        content = result["choices"][0]["message"]["content"].strip()
        print(f"[generate] 원본 응답 길이: {len(content)}자")

        # <think>...</think> 블록 제거 (Qwen3 등 thinking 모델 대응)
        content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

        # 마크다운 코드 블록 제거
        if "```python" in content:
            content = content.split("```python")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        print(f"[generate] 파싱 후 코드 길이: {len(content)}자")
        return content if content else None

    except urllib.error.HTTPError as e:
        print(f"HTTP 오류: {e.read().decode('utf-8')}")
    except Exception as e:
        print(f"코드 생성 중 오류: {e}")

    return None


def fetch_models(api_url: str, api_key: str = None) -> list[str]:
    """
    LLM 서버에서 사용 가능한 모델 목록을 가져옵니다.

    Args:
        api_url:  LLM API 베이스 URL (예: http://localhost:1234)
        api_key:  API 키 (선택, 없으면 PAG_API_KEY 환경변수 사용)

    Returns:
        모델 이름 리스트. 실패 시 빈 리스트.
    """
    import os
    api_key = api_key or os.environ.get("PAG_API_KEY", "")
    url = api_url.rstrip("/") + "/v1/models"
    headers = {
        "Content-Type": "application/json",
        **({"Authorization": f"Bearer {api_key}"} if api_key else {}),
    }
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=5) as response:
            result = json.loads(response.read().decode("utf-8"))
        return [m["id"] for m in result.get("data", [])]
    except Exception as e:
        print(f"모델 목록 조회 오류: {e}")
        return []
