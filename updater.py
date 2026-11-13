"""Cập nhật tự động qua GitHub Releases (chỉ dùng thư viện chuẩn).

Quy ước bản phát hành trên GitHub (repo UPDATE_REPO trong clipforge.py):
  - tag dạng v1.3.1
  - đính kèm file cài đặt ClipForge-Setup-<phiên bản>.exe (do Inno Setup tạo ra)
  - nên đính kèm thêm <tên file cài đặt>.sha256 (tạo bằng: python tools\\make_release.py ...)

Mã SHA-256 để kiểm tra lấy theo thứ tự: file .sha256 đính kèm, rồi trường "digest"
GitHub tự tính cho từng file. Có mã thì bắt buộc khớp mới cài.
"""
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import urllib.error
import urllib.request
from urllib.parse import urlparse

ALLOWED_HOSTS = {
    'api.github.com',
    'github.com',
    'objects.githubusercontent.com',
    'release-assets.githubusercontent.com',
}


def parse_version(text):
    match = re.search(r'(\d+(?:\.\d+){0,3})', str(text))
    return tuple(int(part) for part in match.group(1).split('.')) if match else ()


def is_newer(latest, current):
    a, b = parse_version(latest), parse_version(current)
    if not a:
        return False
    size = max(len(a), len(b))
    a += (0,) * (size - len(a))
    b += (0,) * (size - len(b))
    return a > b


def _check_url(url):
    parts = urlparse(url)
    if parts.scheme != 'https' or parts.hostname not in ALLOWED_HOSTS:
        raise ValueError('Địa chỉ cập nhật không hợp lệ.')


def _open(url, timeout=20, accept='application/vnd.github+json'):
    _check_url(url)
    request = urllib.request.Request(url, headers={'User-Agent': 'ClipForge-Updater', 'Accept': accept})
    response = urllib.request.urlopen(request, timeout=timeout)
    try:
        _check_url(response.geturl())
    except ValueError:
        response.close()
        raise
    return response


def _parse_sha(text):
    parts = str(text or '').strip().split()
    sha = parts[0].lower() if parts else ''
    if sha.startswith('sha256:'):
        sha = sha[7:]
    return sha if re.fullmatch(r'[0-9a-f]{64}', sha) else ''


def check_latest(repo, current, prefix='ClipForge-Setup-'):
    """Trả về dict thông tin bản mới, hoặc None nếu đang là bản mới nhất.

    Dict: {'version', 'name', 'url', 'sha256' ('' nếu không có), 'notes'}.
    """
    try:
        with _open(f'https://api.github.com/repos/{repo}/releases/latest') as response:
            data = json.load(response)
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            raise ValueError('Chưa có bản phát hành nào trên GitHub.') from exc
        raise ValueError(f'GitHub trả về lỗi {exc.code}.') from exc
    except urllib.error.URLError as exc:
        raise ValueError(f'Không kết nối được GitHub: {exc.reason}') from exc
    tag = str(data.get('tag_name', ''))
    if not is_newer(tag, current):
        return None
    version = tag.lstrip('vV')
    assets = {str(a.get('name', '')): a for a in data.get('assets', [])}
    name = f'{prefix}{version}.exe'
    if name not in assets:
        # Dự phòng: file cài đặt duy nhất có tiền tố đúng.
        found = [n for n in assets if n.lower().startswith(prefix.lower()) and n.lower().endswith('.exe')]
        if len(found) != 1:
            raise ValueError(f'Bản {tag} chưa có file cài đặt {name}.')
        name = found[0]
    if not re.fullmatch(r'[\w.\-]+\.exe', name):
        raise ValueError('Tên file cập nhật không hợp lệ.')
    sha = ''
    sha_asset = assets.get(name + '.sha256')
    if sha_asset:
        with _open(sha_asset['browser_download_url'], accept='application/octet-stream') as response:
            sha = _parse_sha(response.read(4096).decode('ascii', 'ignore'))
        if not sha:
            raise ValueError('File .sha256 không hợp lệ, không cập nhật để đảm bảo an toàn.')
    if not sha:
        sha = _parse_sha(assets[name].get('digest'))
    return {'version': version, 'name': name, 'url': assets[name]['browser_download_url'],
            'sha256': sha, 'notes': str(data.get('body') or '')}


def download(info, progress=None):
    """Tải file cài đặt, kiểm tra SHA-256 (nếu có), trả về đường dẫn file trên máy."""
    folder = tempfile.mkdtemp(prefix='app_update_')
    dest = os.path.join(folder, info['name'])
    digest = hashlib.sha256()
    try:
        with _open(info['url'], timeout=60, accept='application/octet-stream') as response, \
                open(dest, 'wb') as out:
            total = int(response.headers.get('Content-Length') or 0)
            done = 0
            while True:
                chunk = response.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
                digest.update(chunk)
                done += len(chunk)
                if progress and total:
                    progress(done * 100 / total)
    except Exception:
        shutil.rmtree(folder, ignore_errors=True)
        raise
    if info.get('sha256') and digest.hexdigest() != info['sha256']:
        shutil.rmtree(folder, ignore_errors=True)
        raise ValueError('File cập nhật bị lỗi (sai mã SHA-256), đã huỷ cập nhật.')
    return dest


def install(path):
    """Chạy file cài đặt Inno Setup ở chế độ im lặng. Gọi xong thì đóng app."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path, '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS'],
                     close_fds=True, creationflags=flags)
