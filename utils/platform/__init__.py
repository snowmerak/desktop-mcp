import sys

if sys.platform == "darwin":
    from utils.platform.macos import open_uri, open_app, capture_screenshot
elif sys.platform == "win32":
    from utils.platform.windows import open_uri, open_app, capture_screenshot
else:
    raise OSError(f"지원하지 않는 플랫폼입니다: {sys.platform}")
