import subprocess
import base64
from io import BytesIO
from PIL import Image


def capture_screenshot(path="/tmp/screenshot.png"):
    """현재 화면을 캡처하여 지정된 경로에 저장합니다."""
    subprocess.run(["screencapture", "-x", path])
    return path


def encode_image_to_base64(image_path, max_dim=1024):
    """이미지를 로드하여 리사이즈 후 JPEG Base64 문자열로 인코딩합니다."""
    with Image.open(image_path) as img:
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")

        orig_w, orig_h = img.size
        if max(orig_w, orig_h) > max_dim:
            scale_factor = max(orig_w, orig_h) / max_dim
            new_w = int(orig_w / scale_factor)
            new_h = int(orig_h / scale_factor)
            img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)

        buffered = BytesIO()
        img.save(buffered, format="JPEG", quality=80)
        return base64.b64encode(buffered.getvalue()).decode("utf-8")


def mark_region_on_image(image_path, normalized_box, output_path=None, color="red", width=3, label=None):
    """
    이미지 위에 정규화 좌표(0~1000)로 지정된 영역을 사각형으로 마킹합니다.

    Args:
        image_path:     원본 이미지 경로
        normalized_box: (x1, y1, x2, y2) — 0~1000 정규화 좌표
        output_path:    저장 경로. None이면 원본을 덮어씁니다.
        color:          박스 색상 (예: "red", "#FF0000")
        width:          박스 두께 (픽셀)
        label:          박스 위에 표시할 텍스트 (선택)

    Returns:
        저장된 이미지 경로
    """
    from PIL import ImageDraw, ImageFont

    if output_path is None:
        output_path = image_path

    with Image.open(image_path) as img:
        img = img.convert("RGB")
        w, h = img.size
        x1, y1, x2, y2 = normalized_box
        px1 = int((x1 / 1000.0) * w)
        py1 = int((y1 / 1000.0) * h)
        px2 = int((x2 / 1000.0) * w)
        py2 = int((y2 / 1000.0) * h)

        draw = ImageDraw.Draw(img)
        draw.rectangle([px1, py1, px2, py2], outline=color, width=width)

        if label:
            draw.text((px1 + 4, py1 + 4), label, fill=color)

        img.save(output_path)

    return output_path
