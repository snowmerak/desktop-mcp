"""
PAG — Personal Automation GUI (Library)

사용 예시:

    from utils.actions import click_on
    from utils.input import type_text, scroll, press, hotkey
    from utils.platform import open_app, open_uri, capture_screenshot
    from utils.llm import (
        get_coordinates_from_image,
        get_bounding_box_from_image,
        check_condition_from_image,
        read_text_from_screen,
        wait_until,
        generate_workflow_code,
        fetch_models,
    )

환경변수:
    PAG_API_URL  — LLM API URL (기본값: http://localhost:1234/v1/chat/completions)
    PAG_MODEL    — 사용할 모델 이름
"""

import time
import pyautogui

from utils.platform import open_app, capture_screenshot
from utils.llm import wait_until, read_text_from_screen
from utils.actions import click_on
from utils.input import type_text, scroll, normalized_to_screen, press, hotkey


def run():
    open_app("Google Chrome")
    wait_until("the browser is ready and address bar is visible", capture_screenshot)

    click_on("address bar")
    hotkey("command", "a")
    type_text("www.sooplive.co.kr")
    press("enter")

    wait_until(
        "the Soop Live homepage is loaded and live broadcast thumbnails are visible",
        capture_screenshot,
    )

    screenshot_path = capture_screenshot()
    titles = read_text_from_screen(
        screenshot_path,
        "all visible live broadcast titles on the page",
    )
    print(titles)


if __name__ == "__main__":
    run()
