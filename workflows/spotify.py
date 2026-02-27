import urllib.parse
import time
import pyautogui

from utils.platform import open_uri, capture_screenshot
from utils.llm import get_coordinates_from_image
from utils.input import normalized_to_screen


def search_and_add_to_playlist(query):
    """Spotify에서 곡을 검색하고 첫 번째 결과를 재생목록에 추가합니다."""
    # 1. Spotify 검색창 열기
    encoded_query = urllib.parse.quote(query)
    print(f"'{query}' 검색 중...")
    open_uri(f"spotify:search:{encoded_query}")

    print("스포티파이 로딩 대기 (3초)...")
    time.sleep(3)

    # 2. 스크린샷 캡처
    print("화면 캡처 중...")
    screenshot_path = capture_screenshot("/tmp/spotify_screenshot.png")

    # 3. LLM으로 첫 번째 곡 좌표 분석
    print("LLM에게 첫 번째 곡 좌표 분석 요청 중...")
    coords = get_coordinates_from_image(
        screenshot_path,
        "the FIRST song result in the 'Songs' or 'Tracks' list",
    )

    if coords is None:
        print("좌표 정보를 찾지 못했습니다.")
        return

    # 4. 우클릭 → 키보드로 '재생목록에 추가' 메뉴 탐색
    logical_x, logical_y = normalized_to_screen(*coords)
    pyautogui.moveTo(logical_x, logical_y, duration=0.5)
    pyautogui.rightClick()
    print("우클릭하여 컨텍스트 메뉴를 열었습니다.")

    # 마우스를 구석으로 치워 방향키 입력 충돌 방지
    pyautogui.moveTo(10, 10, duration=0.2)
    time.sleep(0.5)

    # 일반적인 우클릭 메뉴 순서: 아래 3번 → 오른쪽(하위 메뉴) → Enter
    pyautogui.press("down", presses=3, interval=0.3)
    time.sleep(0.3)
    pyautogui.press("right")
    time.sleep(0.5)
    pyautogui.press("enter")

    print("재생목록 추가 시도 완료!")
