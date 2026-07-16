"""
Điểm khởi chạy ứng dụng. Chạy: python -m app.main
(hoặc khi đã đóng gói: double-click file .exe sinh ra từ build.spec)
"""

import os
import sys

import webview

from app import config

FRONTEND_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "frontend")


def resource_path(relative_path):
    """
    Trả về đường dẫn đúng cả khi chạy bằng `python -m app.main` lẫn khi đã
    đóng gói bằng PyInstaller (lúc đó file nằm trong thư mục tạm sys._MEIPASS).
    """
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), relative_path)


def main():
    from app.api import Api

    api = Api()
    index_path = resource_path(os.path.join("frontend", "index.html"))

    webview.create_window(
        title=config.WINDOW_TITLE,
        url=index_path,
        js_api=api,
        width=config.WINDOW_WIDTH,
        height=config.WINDOW_HEIGHT,
        min_size=(1000, 600),
    )
    webview.start()


if __name__ == "__main__":
    main()
