import pyautogui

from utils.platform import capture_screenshot
from utils.llm import get_coordinates_from_image, wait_until
from utils.input import normalized_to_screen, move_to, drag


def click_on(description, screenshot_path="/tmp/action_screenshot.png", double=False, right=False):
    """
    화면에서 자연어로 설명된 UI 요소를 찾아 클릭합니다.

    Args:
        description:     클릭할 요소에 대한 자연어 설명
        screenshot_path: 스크린샷 저장 경로
        double:          True면 더블클릭
        right:           True면 우클릭

    Returns:
        클릭한 (x, y) 화면 좌표. 실패 시 None.
    """
    path = capture_screenshot(screenshot_path)
    coords = get_coordinates_from_image(path, description)

    if coords is None:
        print(f"요소를 찾지 못했습니다: '{description}'")
        return None

    x, y = normalized_to_screen(*coords)
    pyautogui.moveTo(x, y, duration=0.3)

    if right:
        pyautogui.rightClick()
    elif double:
        pyautogui.doubleClick()
    else:
        pyautogui.click()

    print(f"클릭 완료: '{description}' → ({x}, {y})")
    return (x, y)


def double_click_on(description, screenshot_path="/tmp/action_screenshot.png"):
    """화면에서 자연어로 설명된 UI 요소를 찾아 더블클릭합니다."""
    return click_on(description, screenshot_path, double=True)


def right_click_on(description, screenshot_path="/tmp/action_screenshot.png"):
    """화면에서 자연어로 설명된 UI 요소를 찾아 우클릭합니다."""
    return click_on(description, screenshot_path, right=True)


def hover_on(description, screenshot_path="/tmp/action_screenshot.png"):
    """
    화면에서 자연어로 설명된 UI 요소 위로 커서를 이동합니다 (클릭 없음).
    드롭다운 열기, 툴팁 확인 등에 유용합니다.

    Returns:
        호버한 (x, y) 화면 좌표. 실패 시 None.
    """
    path = capture_screenshot(screenshot_path)
    coords = get_coordinates_from_image(path, description)

    if coords is None:
        print(f"요소를 찾지 못했습니다: '{description}'")
        return None

    x, y = normalized_to_screen(*coords)
    move_to(x, y)
    print(f"호버 완료: '{description}' → ({x}, {y})")
    return (x, y)


def wait_and_click(
    condition_description,
    click_description=None,
    capture_fn=None,
    interval=1.0,
    timeout=30.0,
):
    """
    조건이 충족될 때까지 대기한 뒤 요소를 클릭합니다.
    `click_description`이 None이면 조건 설명과 동일한 요소를 클릭합니다.

    Args:
        condition_description: wait_until에 전달할 조건 설명
        click_description:     클릭할 요소 설명 (None이면 condition_description 사용)
        capture_fn:            스크린샷 함수 (None이면 기본 capture_screenshot 사용)
        interval:              폴링 주기 (초)
        timeout:               최대 대기 시간 (초)

    Returns:
        클릭한 (x, y) 화면 좌표. 실패 시 None.
    """
    if capture_fn is None:
        capture_fn = capture_screenshot

    ok = wait_until(condition_description, capture_fn, interval=interval, timeout=timeout)
    if not ok:
        print(f"타임아웃: '{condition_description}'")
        return None

    return click_on(click_description or condition_description)


def drag_from_to(
    from_description,
    to_description,
    screenshot_path="/tmp/action_screenshot.png",
    duration=0.5,
):
    """
    화면에서 두 요소를 자연어로 설명하여 드래그합니다.

    Args:
        from_description: 드래그 시작 요소 설명
        to_description:   드래그 끝 요소 설명
        duration:         드래그 소요 시간 (초)

    Returns:
        (from_xy, to_xy) 튜플. 실패 시 None.
    """
    path = capture_screenshot(screenshot_path)

    from_coords = get_coordinates_from_image(path, from_description)
    if from_coords is None:
        print(f"시작 요소를 찾지 못했습니다: '{from_description}'")
        return None

    to_coords = get_coordinates_from_image(path, to_description)
    if to_coords is None:
        print(f"끝 요소를 찾지 못했습니다: '{to_description}'")
        return None

    from_xy = normalized_to_screen(*from_coords)
    to_xy = normalized_to_screen(*to_coords)

    drag(from_xy, to_xy, duration=duration)
    print(f"드래그 완료: '{from_description}' → '{to_description}'")
    return (from_xy, to_xy)
