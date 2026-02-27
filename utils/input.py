import sys
import pyautogui
import pyperclip


def normalized_to_screen(nx, ny):
    """0~1000 정규화 좌표를 실제 화면 논리 좌표로 변환합니다."""
    screen_width, screen_height = pyautogui.size()
    return int((nx / 1000.0) * screen_width), int((ny / 1000.0) * screen_height)


def type_text(text):
    """
    텍스트를 클립보드를 통해 붙여넣습니다.
    IME 상태에 무관하게 한글/영어/특수문자 모두 입력 가능합니다.
    """
    pyperclip.copy(text)
    if sys.platform == "darwin":
        pyautogui.hotkey("command", "v")
    elif sys.platform == "win32":
        pyautogui.hotkey("ctrl", "v")
    else:
        raise OSError(f"지원하지 않는 플랫폼입니다: {sys.platform}")


def scroll(amount, x=None, y=None):
    """
    스크롤합니다.

    Args:
        amount: 스크롤 양. 양수면 위(↑), 음수면 아래(↓).
        x, y:   스크롤할 화면 좌표. None이면 현재 커서 위치에서 스크롤.
    """
    if x is not None and y is not None:
        pyautogui.moveTo(x, y, duration=0.2)
    pyautogui.scroll(amount)


def press(*args, **kwargs):
    """pyautogui.press 래퍼. 예: press("enter"), press("down", presses=3)"""
    pyautogui.press(*args, **kwargs)


def hotkey(*args):
    """pyautogui.hotkey 래퍼. 예: hotkey("command", "a"), hotkey("ctrl", "z")"""
    pyautogui.hotkey(*args)


def move_to(x, y, duration=0.3):
    """
    지정한 화면 좌표로 커서를 이동합니다 (클릭 없음).
    호버 효과, 드롭다운 열기 등에 유용합니다.

    Args:
        x, y:     실제 화면 좌표 (normalized_to_screen 결과값)
        duration: 이동 시간 (초)
    """
    pyautogui.moveTo(x, y, duration=duration)


def drag(from_xy: tuple, to_xy: tuple, duration=0.5):
    """
    한 좌표에서 다른 좌표로 드래그합니다.

    Args:
        from_xy:  시작 좌표 (x, y) — 실제 화면 좌표
        to_xy:    끝 좌표 (x, y) — 실제 화면 좌표
        duration: 드래그 소요 시간 (초)
    """
    pyautogui.moveTo(from_xy[0], from_xy[1], duration=0.2)
    pyautogui.dragTo(to_xy[0], to_xy[1], duration=duration, button="left")


def get_clipboard() -> str:
    """클립보드의 현재 텍스트를 반환합니다."""
    return pyperclip.paste()


def click(x, y, button="left", clicks=1):
    """
    지정한 화면 좌표를 클릭합니다.

    Args:
        x, y:    실제 화면 좌표
        button:  "left" | "right" | "middle"
        clicks:  클릭 횟수 (2이면 더블클릭)
    """
    pyautogui.click(x, y, button=button, clicks=clicks)
