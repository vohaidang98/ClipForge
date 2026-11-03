# ClipForge Studio

Công cụ cắt và chuyển đổi video (Python + Tkinter + FFmpeg).

- Phiên bản hiện tại: **1.3.0** (hằng số `APP_VERSION` trong `clipforge.py` và `AppVersion` trong `installer.iss`).
- Tự cập nhật (chỉ bản đã kích hoạt): app đọc `version.json` trong thư mục cập nhật trên mạng LAN (chọn ở lần bấm "Cập nhật" đầu tiên,
  lưu ở `%APPDATA%\ClipForge\update.json`). Mã SHA-256 được kiểm tra trước khi cài.
- Kích hoạt: chưa nhập đúng mã thì không dùng được app (mở app là hiện hộp nhập mã, chữ hiện dấu *). Trong code chỉ lưu mã băm (`licensing.py`).
  Tạo mã băm mới: `python tools\make_hash.py`.

## Phát hành bản mới

1. Tăng số phiên bản trong `clipforge.py` và `installer.iss`.
2. Build: `python -m PyInstaller --noconfirm --windowed --name ClipForge --icon ClipForge.ico --add-data "ClipForge.ico;." clipforge.py`
3. Gom `ClipForge.exe`, `_internal`, `bin` (ffmpeg) cạnh `installer.iss` rồi biên dịch bằng Inno Setup (`ISCC.exe installer.iss`).
4. Tạo thư mục phát hành: `python tools\make_release.py <file cài đặt> <phiên bản> D:\Code\CAP_NHAT\ClipForge "ghi chú"`.
5. Thư mục `D:\Code\CAP_NHAT` được chia sẻ mạng (máy khác chỉ đọc). Ghi đè 2 file là xong.

Lưu ý: chỉ cho tài khoản quản trị quyền ghi vào thư mục chia sẻ.


