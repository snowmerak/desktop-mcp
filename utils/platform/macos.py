import os
import tempfile
import subprocess


def open_uri(uri):
    """URI 스킴을 가진 앱을 실행합니다."""
    subprocess.run(["open", uri])


def open_app(app_name_or_path):
    """앱 이름 또는 .app 경로로 응용프로그램을 실행합니다."""
    subprocess.run(["open", "-a", app_name_or_path])


def capture_screenshot(path=os.path.join(tempfile.gettempdir(), "screenshot.png")):
    """현재 화면을 캡처하여 지정된 경로에 저장합니다."""
    subprocess.run(["screencapture", "-x", path])
    return path
