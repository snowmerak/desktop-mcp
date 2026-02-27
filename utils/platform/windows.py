import os
import tempfile
import subprocess
import shutil
from PIL import ImageGrab


def open_uri(uri):
    """URI 스킴을 가진 앱을 실행합니다."""
    subprocess.run(["start", uri], shell=True)


def open_app(app_name_or_path):
    """앱 이름 또는 절대 경로로 응용프로그램을 실행합니다."""
    if "\\" in app_name_or_path or "/" in app_name_or_path:
        subprocess.Popen([app_name_or_path])
    else:
        resolved = shutil.which(app_name_or_path)
        if resolved:
            subprocess.Popen([resolved])
        else:
            raise FileNotFoundError(f"앱을 찾을 수 없습니다: {app_name_or_path}")


def capture_screenshot(path=os.path.join(tempfile.gettempdir(), "screenshot.png")):
    """현재 화면을 캡처하여 지정된 경로에 저장합니다."""
    img = ImageGrab.grab()
    img.save(path)
    return path
