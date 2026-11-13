"""Chuẩn bị file để đăng lên GitHub Releases.

Chạy:
  python tools\\make_release.py <file cài đặt .exe>

Ví dụ:
  python tools\\make_release.py D:\\Code\\ClipForge-Setup-1.3.1.exe   (installer.iss xuất ra thư mục cha)
Kết quả: tạo <file cài đặt>.sha256 cạnh file cài đặt.
Sau đó tạo release tag vX.Y.Z trên repo GitHub, đính kèm cả file .exe và file .sha256.
"""
import hashlib
import sys
from pathlib import Path

if len(sys.argv) < 2:
    raise SystemExit(__doc__)
installer = Path(sys.argv[1])
if not installer.is_file():
    raise SystemExit(f'Không thấy file: {installer}')
digest = hashlib.sha256()
with installer.open('rb') as f:
    for chunk in iter(lambda: f.read(1 << 20), b''):
        digest.update(chunk)
target = installer.with_name(installer.name + '.sha256')
target.write_text(f'{digest.hexdigest()}  {installer.name}\n', encoding='ascii')
print('SHA256:', digest.hexdigest())
print('Da tao:', target)
