# ClipForge Studio

Công cụ cắt và chuyển đổi video (Python + Tkinter + FFmpeg).

- Phiên bản hiện tại: **1.3.0** (hằng số `APP_VERSION` trong `clipforge.py` và `AppVersion` trong `installer.iss`).
- Tự cập nhật: app kiểm tra GitHub Releases của repo phát hành `vohaidang98/clipforge-releases`.
- Kích hoạt: nhập mã để mở tab Chuyển đổi. Trong code chỉ lưu mã băm (`licensing.py`).
  Tạo mã băm mới: `python tools\make_hash.py`.

## Phát hành bản mới

1. Tăng số phiên bản trong `clipforge.py` và `installer.iss`.
2. Build: `python -m PyInstaller --noconfirm --windowed --name ClipForge --icon ClipForge.ico --add-data "ClipForge.ico;." clipforge.py`
3. Gom `ClipForge.exe`, `_internal`, `bin` (ffmpeg) cạnh `installer.iss` rồi biên dịch bằng Inno Setup (`ISCC.exe installer.iss`).
4. Tạo file `<tên file cài đặt>.sha256` (SHA-256 của file cài đặt).
5. Tạo release tag `vX.Y.Z` trên repo `clipforge-releases`, đính kèm file cài đặt và file `.sha256`.
