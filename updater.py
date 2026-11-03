"""Cập nhật tự động qua GitHub Releases (chỉ dùng thư viện chuẩn).

Quy ước bản phát hành trên GitHub:
  - tag dạng v1.3.0
  - có file cài đặt *Setup*.exe và file kiểm tra toàn vẹn <tên file>.sha256
"""
import hashlib
import json
import os
import re
import subprocess
import tempfile
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


def _open(url, timeout=20):
    _check_url(url)
    request = urllib.request.Request(url, headers={
        'User-Agent': 'App-Updater',
        'Accept': 'application/vnd.github+json, application/octet-stream',
    })
    response = urllib.request.urlopen(request, timeout=timeout)
    try:
        _check_url(response.geturl())
    except ValueError:
        response.close()
        raise
    return response


def check_latest(repo, current, asset_pattern=r'setup.*\.exe$'):
    """Trả về dict thông tin bản mới, hoặc None nếu đang là bản mới nhất."""
    with _open(f'https://api.github.com/repos/{repo}/releases/latest') as response:
        data = json.load(response)
    tag = data.get('tag_name', '')
    if not is_newer(tag, current):
        return None
    assets = {a['name']: a['browser_download_url'] for a in data.get('assets', [])}
    name = next((n for n in assets if re.search(asset_pattern, n, re.I)), None)
    if not name:
        raise ValueError(f'Bản {tag} chưa có file cài đặt.')
    if name + '.sha256' not in assets:
        raise ValueError(f'Bản {tag} thiếu file kiểm tra .sha256, không cập nhật để đảm bảo an toàn.')
    if not re.fullmatch(r'[\w.\-]+\.exe', name):
        raise ValueError('Tên file cập nhật không hợp lệ.')
    return {
        'version': tag.lstrip('vV'),
        'name': name,
        'url': assets[name],
        'sha_url': assets[name + '.sha256'],
        'notes': data.get('body') or '',
    }


def download(info, progress=None):
    """Tải file cài đặt, kiểm tra SHA-256, trả về đường dẫn file đã tải."""
    with _open(info['sha_url']) as response:
        expected = response.read(4096).decode('ascii', 'ignore').split()[0].lower()
    if not re.fullmatch(r'[0-9a-f]{64}', expected):
        raise ValueError('File .sha256 không hợp lệ.')
    folder = tempfile.mkdtemp(prefix='app_update_')
    path = os.path.join(folder, info['name'])
    digest = hashlib.sha256()
    with _open(info['url'], timeout=60) as response, open(path, 'wb') as out:
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
    if digest.hexdigest() != expected:
        os.remove(path)
        raise ValueError('File tải về bị lỗi (sai mã SHA-256), đã huỷ cập nhật.')
    return path


def install(path):
    """Chạy file cài đặt Inno Setup ở chế độ im lặng. Gọi xong thì đóng app."""
    flags = 0x00000008 | 0x00000200  # DETACHED_PROCESS | CREATE_NEW_PROCESS_GROUP
    subprocess.Popen([path, '/SILENT', '/SUPPRESSMSGBOXES', '/NORESTART', '/CLOSEAPPLICATIONS'],
                     close_fds=True, creationflags=flags)
