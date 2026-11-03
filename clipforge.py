import json
import math
import os
from pathlib import Path
import queue
import re
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

import licensing
import updater

APP = 'ClipForge'
APP_VERSION = '1.3.0'
EXTS = {'.mp4', '.mkv', '.avi', '.mov', '.webm', '.m4v', '.flv', '.ts', '.mts', '.m2ts'}
DEFAULTS = dict(video_codec='h264', resolution='1280x720', scale_mode='Default',
                video_bitrate='2000', framerate='30', audio_codec='aac',
                audio_samplerate='44100', audio_bitrate='128', audio_channels='2', use_gpu=False)


def executable(name):
    base = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).parent
    local = base / 'bin' / (name + '.exe')
    result = str(local) if local.exists() else shutil.which(name)
    if not result:
        raise ValueError(f'Không tìm thấy {name}. Đặt {name}.exe và DLL cần thiết vào thư mục bin hoặc thêm vào PATH.')
    return result


def number(value, label, positive=False):
    try:
        n = float(str(value).replace(',', '.'))
    except ValueError:
        raise ValueError(f'{label}: cần nhập số.')
    if not math.isfinite(n) or n < 0 or (positive and n == 0):
        raise ValueError(f'{label}: giá trị không hợp lệ.')
    return n


def cut_range(total, mode, head, tail, offset, duration, side):
    if mode == 'trim':
        start, length = head, total - head - tail
    else:
        start = offset if side == 'head' else total - offset - duration
        length = duration
    if start < 0 or length <= 0 or start + length > total + .001:
        raise ValueError('Khoảng cắt nằm ngoài thời lượng video.')
    return start, length


def convert_args(settings):
    s = settings
    codec = {'h264': 'libx264', 'h265': 'libx265', 'mpeg4': 'mpeg4'}[s['video_codec']]
    if s['use_gpu']:
        if s['video_codec'] == 'mpeg4':
            raise ValueError('NVENC chỉ dùng với H.264 hoặc H.265.')
        codec = {'h264': 'h264_nvenc', 'h265': 'hevc_nvenc'}[s['video_codec']]
    match = re.fullmatch(r'(\d+)[xX](\d+)', s['resolution'].strip())
    if not match:
        raise ValueError('Độ phân giải phải có dạng 1280x720.')
    w, h = map(int, match.groups())
    if w <= 0 or h <= 0 or w % 2 or h % 2:
        raise ValueError('Chiều rộng và cao phải là số chẵn dương.')
    vf = f'scale={w}:{h}'
    if s['scale_mode'] == 'Letterbox':
        vf = f'scale={w}:{h}:force_original_aspect_ratio=decrease,pad={w}:{h}:(ow-iw)/2:(oh-ih)/2'
    elif s['scale_mode'] == 'Crop':
        vf = f'scale={w}:{h}:force_original_aspect_ratio=increase,crop={w}:{h}'
    for key in ('video_bitrate', 'framerate', 'audio_samplerate', 'audio_bitrate'):
        number(s[key], key, True)
    for key in ('video_bitrate', 'audio_samplerate', 'audio_bitrate'):
        if not str(s[key]).isdigit():
            raise ValueError(f'{key}: cần nhập số nguyên dương.')
    return ['-vf', vf, '-c:v', codec, '-pix_fmt', 'yuv420p', '-b:v', s['video_bitrate']+'k',
            '-r', s['framerate'], '-c:a', s['audio_codec'], '-ar', s['audio_samplerate'],
            '-b:a', s['audio_bitrate']+'k', '-ac', s['audio_channels']]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        asset_dir = Path(getattr(sys, '_MEIPASS', Path(__file__).parent))
        icon_path = asset_dir / 'ClipForge.ico'
        if icon_path.exists():
            self.iconbitmap(str(icon_path))
        self.title(f'{APP} Studio • {APP_VERSION}')
        self.geometry('1120x900')
        self.minsize(1040, 840)
        self.events = queue.Queue()
        self.cancel = threading.Event()
        self.busy = False
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('.', font=('Segoe UI', 10))
        self.style.configure('TButton', padding=(15, 9))
        self.style.configure('Title.TLabel', font=('Segoe UI', 26, 'bold'))
        self.style.configure('Subtitle.TLabel', font=('Segoe UI', 10))
        self.style.configure('Section.TLabel', font=('Segoe UI', 12, 'bold'))
        header = ttk.Frame(self, padding=(28, 22))
        header.pack(fill='x')
        brand = ttk.Frame(header)
        brand.pack(side='left')
        ttk.Label(brand, text='CLIPFORGE', style='Title.TLabel').pack(anchor='w')
        ttk.Label(brand, text='VIDEO STUDIO  /  Cắt gọn. Chuyển nhanh.', style='Subtitle.TLabel').pack(anchor='w', pady=(3, 0))
        ttk.Button(header, text='Sáng / tối', command=self.theme).pack(side='right')
        ttk.Button(header, text='Cập nhật', command=lambda: self.check_update(True)).pack(side='right', padx=8)
        ttk.Label(header, text=f'Phiên bản {APP_VERSION}', style='Subtitle.TLabel').pack(side='right', padx=8)
        self.license_text = tk.StringVar()
        self.license_button = ttk.Button(header, text='Kích hoạt', command=self.ask_activation)
        self.license_button.pack(side='right', padx=8)
        ttk.Label(header, textvariable=self.license_text, style='Subtitle.TLabel').pack(side='right', padx=8)
        self.refresh_license()
        self.dark = False
        self.book = ttk.Notebook(self)
        self.book.pack(fill='both', expand=True, padx=24)
        self.tabs = {}
        self.make_tab('cut', 'Cắt video')
        self.make_tab('convert', 'Chuyển đổi')
        bottom = ttk.Frame(self, padding=(24, 14))
        bottom.pack(fill='x')
        ttk.Label(bottom, text='HOẠT ĐỘNG', style='Subtitle.TLabel').pack(anchor='w', pady=(0, 7))
        self.status = tk.StringVar(value='Sẵn sàng • Chọn video để bắt đầu')
        ttk.Label(bottom, textvariable=self.status).pack(anchor='w')
        self.progress = ttk.Progressbar(bottom)
        self.progress.pack(fill='x', pady=5)
        self.log = tk.Text(bottom, height=4, font=('Consolas', 9), state='disabled', relief='flat', padx=12, pady=10)
        self.log.pack(fill='x')
        self.theme()
        self.protocol('WM_DELETE_WINDOW', self.close)
        self.after(100, self.pump)
        self.updating = False
        self.after(3000, lambda: self.check_update(False))

    def refresh_license(self):
        if licensing.is_activated():
            self.license_text.set('Đã kích hoạt')
            self.license_button.state(['disabled'])
        else:
            self.license_text.set('Bản cơ bản')
            self.license_button.state(['!disabled'])

    def ask_activation(self):
        win = tk.Toplevel(self)
        win.title('Kích hoạt ' + APP)
        win.resizable(False, False)
        win.transient(self)
        frame = ttk.Frame(win, padding=22)
        frame.pack()
        ttk.Label(frame, text='Nhập mã kích hoạt để mở đầy đủ tính năng.').pack(anchor='w')
        code = tk.StringVar()
        entry = ttk.Entry(frame, textvariable=code, show='*', width=34)
        entry.pack(pady=(12, 4))
        message = tk.StringVar()
        ttk.Label(frame, textvariable=message, foreground='#c0392b').pack(anchor='w')

        def submit(event=None):
            if licensing.activate(code.get()):
                win.destroy()
                self.refresh_license()
                messagebox.showinfo(APP, 'Kích hoạt thành công.')
            else:
                code.set('')
                message.set('Mã không đúng. Hãy thử lại.')
        buttons = ttk.Frame(frame)
        buttons.pack(anchor='e', pady=(12, 0))
        ttk.Button(buttons, text='Huỷ', command=win.destroy).pack(side='right')
        ttk.Button(buttons, text='Kích hoạt', command=submit).pack(side='right', padx=8)
        entry.bind('<Return>', submit)
        entry.focus_set()
        win.grab_set()

    def check_update(self, manual):
        if self.updating:
            return
        if self.busy:
            if manual:
                messagebox.showinfo(APP, 'Đang xử lý video. Hãy đợi xong rồi cập nhật.')
            return
        folder = updater.get_folder(APP)
        if not folder:
            if not manual:
                return
            folder = filedialog.askdirectory(title='Chọn thư mục cập nhật (trên mạng LAN)')
            if not folder:
                return
            updater.set_folder(APP, folder)
        self.updating = True

        def work():
            try:
                info = updater.check_latest(folder, APP_VERSION)
                self.events.put(('update', (info, manual)))
            except Exception as exc:
                self.events.put(('update_error', (str(exc), manual)))
        threading.Thread(target=work, daemon=True).start()

    def offer_update(self, info, manual):
        if not info:
            self.updating = False
            if manual:
                messagebox.showinfo(APP, f'Bạn đang dùng bản mới nhất ({APP_VERSION}).')
            return
        notes = info['notes'].strip()[:600]
        text = f'Có bản mới {info["version"]} (đang dùng {APP_VERSION}).\n\n{notes}\n\nCập nhật ngay?'
        if self.busy or not messagebox.askyesno(APP, text):
            self.updating = False
            return
        self.status.set(f'Đang tải bản {info["version"]}…')

        def work():
            try:
                path = updater.download(info, lambda p: self.events.put(('progress', p)))
                self.events.put(('install', path))
            except Exception as exc:
                self.events.put(('update_error', (str(exc), True)))
        threading.Thread(target=work, daemon=True).start()

    def theme(self):
        self.dark = not self.dark
        bg, fg, field = ('#101721', '#e5edf8', '#1b2737') if self.dark else ('#f0f4f9', '#18283b', '#ffffff')
        muted = '#90a4be' if self.dark else '#60738b'
        accent = '#45d6ba' if self.dark else '#087f72'
        button = '#25354a' if self.dark else '#e0e8f2'
        self.configure(bg=bg)
        self.style.configure('.', background=bg, foreground=fg, fieldbackground=field)
        self.style.configure('TButton', background=button, borderwidth=0, focusthickness=0)
        self.style.map('TButton', background=[('active', '#365370' if self.dark else '#cbd9e9')], foreground=[('active', fg)])
        self.style.configure('Primary.TButton', background=accent, foreground='#081e1a' if self.dark else '#ffffff', font=('Segoe UI', 10, 'bold'), padding=(22, 11))
        self.style.map('Primary.TButton', background=[('active', '#70e6cf' if self.dark else '#09695e')], foreground=[('active', '#081e1a' if self.dark else '#ffffff')])
        self.style.configure('Danger.TButton', foreground='#ff9aab' if self.dark else '#ac2740')
        self.style.configure('Title.TLabel', foreground=fg)
        self.style.configure('Subtitle.TLabel', foreground=muted)
        self.style.configure('TNotebook', background=bg, borderwidth=0, tabmargins=(0, 0, 0, 10))
        self.style.configure('TNotebook.Tab', padding=(24, 12), background=bg, foreground=muted, borderwidth=0, font=('Segoe UI', 11, 'bold'))
        self.style.map('TNotebook.Tab', background=[('selected', field)], foreground=[('selected', accent)])
        self.style.configure('TLabelframe', bordercolor=button, relief='solid', borderwidth=1)
        self.style.configure('TLabelframe.Label', foreground=accent, font=('Segoe UI', 10, 'bold'))
        self.style.configure('TEntry', padding=7, bordercolor=button, lightcolor=button, darkcolor=button, insertcolor=fg)
        self.style.configure('TCombobox', padding=7, arrowcolor=muted, bordercolor=button)
        self.style.map('TCombobox', fieldbackground=[('readonly', field)], foreground=[('readonly', fg)], selectbackground=[('readonly', field)], selectforeground=[('readonly', fg)])
        self.style.map('TRadiobutton', background=[('active', bg)], foreground=[('active', accent)])
        self.style.map('TCheckbutton', background=[('active', bg)], foreground=[('active', accent)])
        self.style.configure('Horizontal.TProgressbar', background=accent, troughcolor=field, borderwidth=0, thickness=5)
        self.option_add('*TCombobox*Listbox.background', field)
        self.option_add('*TCombobox*Listbox.foreground', fg)
        self.option_add('*TCombobox*Listbox.selectBackground', accent)
        for tab in self.tabs.values():
            tab['list'].configure(bg=field, fg=fg, selectbackground='#265f69', selectforeground='#ffffff', highlightbackground=button, highlightcolor=accent)
            tab['empty'].configure(bg=field, fg=muted)
        self.log.configure(bg=field, fg=muted, insertbackground=fg)

    def make_tab(self, key, label):
        frame = ttk.Frame(self.book, padding=(18, 12))
        self.book.add(frame, text='  '+label+'  ')
        tab = self.tabs[key] = {'files': [], 'output': tk.StringVar(value='')}
        tab['count'] = tk.StringVar(value='01  /  NGUỒN VIDEO · 0 file')
        ttk.Label(frame, textvariable=tab['count'], style='Section.TLabel').pack(anchor='w', pady=(0, 8))
        bar = ttk.Frame(frame)
        bar.pack(fill='x')
        for text, command in [('Thêm file video', lambda: self.add(key)), ('Thêm từ thư mục', lambda: self.add_folder(key)), ('Bỏ mục chọn', lambda: self.remove(key)),
                              ('Xóa danh sách', lambda: self.remove(key, True))]:
            ttk.Button(bar, text=text, command=command).pack(side='left', padx=(0, 8))
        holder = ttk.Frame(frame)
        holder.pack(fill='both', expand=True, pady=10)
        listing = tab['list'] = tk.Listbox(holder, selectmode='extended', height=6, relief='flat', exportselection=False, font=('Segoe UI', 11), borderwidth=0, highlightthickness=1, activestyle='none')
        scroll = ttk.Scrollbar(holder, command=listing.yview)
        listing.configure(yscrollcommand=scroll.set)
        scroll.pack(side='right', fill='y')
        listing.pack(fill='both', expand=True)
        tab['empty'] = tk.Label(listing, text='＋  Thêm file video hoặc thêm từ thư mục\n\nCó thể chọn nhiều file và thêm nhiều lần vào danh sách', font=('Segoe UI', 11), justify='center')
        tab['empty'].place(relx=.5, rely=.5, anchor='center')
        tab['empty'].bind('<Button-1>', lambda event: self.add(key))
        out = ttk.Frame(frame)
        out.pack(fill='x', pady=(0, 10))
        ttk.Label(out, text='Thư mục lưu:').pack(side='left')
        ttk.Entry(out, textvariable=tab['output']).pack(side='left', fill='x', expand=True, padx=8)
        ttk.Button(out, text='Chọn…', command=lambda: self.output(key)).pack(side='right')
        opts = ttk.LabelFrame(frame, text=' 02  /  THIẾT LẬP XỬ LÝ ', padding=16)
        opts.pack(fill='x')
        if key == 'cut':
            tab['vars'] = {k: tk.StringVar(value=v) for k, v in dict(mode='trim', head='0', tail='0', offset='0', duration='10', side='head').items()}
            v = tab['vars']
            ttk.Radiobutton(opts, text='Bỏ đầu / đuôi', variable=v['mode'], value='trim').grid(row=0, column=0, sticky='w')
            ttk.Radiobutton(opts, text='Lấy đoạn theo thời lượng', variable=v['mode'], value='segment').grid(row=0, column=2, sticky='w')
            for row, (a, b) in enumerate([(('Bỏ đầu (giây)', 'head'), ('Offset (giây)', 'offset')),
                                         (('Bỏ đuôi (giây)', 'tail'), ('Thời lượng (giây)', 'duration'))], 1):
                self.field(opts, a[0], v[a[1]], row, 0)
                self.field(opts, b[0], v[b[1]], row, 2)
            ttk.Radiobutton(opts, text='Tính từ đầu', variable=v['side'], value='head').grid(row=3, column=2, sticky='w')
            ttk.Radiobutton(opts, text='Tính từ cuối', variable=v['side'], value='tail').grid(row=3, column=3, sticky='w')
            ttk.Label(opts, text='Cắt nhanh, giữ codec gốc. Điểm cắt có thể lệch theo keyframe.').grid(row=4, column=0, columnspan=4, sticky='w', pady=8)
        else:
            tab['vars'] = {k: (tk.BooleanVar(value=v) if isinstance(v, bool) else tk.StringVar(value=v)) for k, v in DEFAULTS.items()}
            v = tab['vars']
            fields = [('Video codec', 'video_codec', ['h264','h265','mpeg4']), ('Audio codec', 'audio_codec', ['aac','ac3','mp3']),
                      ('Độ phân giải WxH', 'resolution', None), ('Tần số âm thanh Hz', 'audio_samplerate', None),
                      ('Tỷ lệ khung hình', 'scale_mode', ['Default','Letterbox','Crop']), ('Audio bitrate kbps', 'audio_bitrate', None),
                      ('Video bitrate kbps', 'video_bitrate', None), ('Số kênh âm thanh', 'audio_channels', ['1','2']),
                      ('FPS', 'framerate', None)]
            for i, (text, name, choices) in enumerate(fields):
                self.field(opts, text, v[name], i//2, (i%2)*2, choices)
            ttk.Checkbutton(opts, text='GPU NVIDIA (NVENC)', variable=v['use_gpu']).grid(row=4, column=2, columnspan=2, sticky='w')
            presets = ttk.Frame(frame)
            presets.pack(fill='x', pady=8)
            ttk.Button(presets, text='Lưu preset JSON', command=self.save_preset).pack(side='left', padx=(0,8))
            ttk.Button(presets, text='Nạp preset JSON', command=self.load_preset).pack(side='left')
        for c in (1, 3):
            opts.columnconfigure(c, weight=1)
        actions = ttk.Frame(frame)
        actions.pack(fill='x', pady=(12, 0))
        ttk.Button(actions, text='▶  Bắt đầu xử lý', style='Primary.TButton', command=lambda: self.start(key)).pack(side='left')
        ttk.Button(actions, text='■  Dừng', style='Danger.TButton', command=self.stop).pack(side='left', padx=8)
        ttk.Label(actions, text='File gốc được giữ nguyên • Không ghi đè kết quả', style='Subtitle.TLabel').pack(side='right')

    def field(self, parent, text, var, row, col, choices=None):
        ttk.Label(parent, text=text).grid(row=row, column=col, sticky='w', padx=(0,8), pady=5)
        widget = ttk.Combobox(parent, textvariable=var, values=choices, state='readonly', width=17) if choices else ttk.Entry(parent, textvariable=var, width=19)
        widget.grid(row=row, column=col+1, sticky='ew', padx=(0,18), pady=5)

    def add(self, key):
        paths = filedialog.askopenfilenames(parent=self, title='Chọn một hoặc nhiều file video', filetypes=[('Video', ' '.join('*'+e for e in sorted(EXTS))), ('Tất cả', '*.*')])
        self.add_paths(key, paths)

    def add_folder(self, key):
        folder = filedialog.askdirectory(parent=self, title='Chọn thư mục chứa video')
        if not folder:
            return
        try:
            paths = sorted(Path(folder).iterdir(), key=lambda p: p.name.casefold())
            added = self.add_paths(key, paths)
        except OSError as e:
            return messagebox.showerror(APP, f'Không đọc được thư mục: {e}', parent=self)
        if added == 0:
            messagebox.showinfo(APP, 'Không có video mới để thêm. Chỉ lấy video trực tiếp trong thư mục đã chọn; bỏ qua file trùng.', parent=self)

    def add_paths(self, key, paths):
        t = self.tabs[key]
        existing = {os.path.normcase(os.path.realpath(p)) for p in t['files']}
        added = 0
        for p in paths:
            path = Path(p)
            normalized = os.path.normcase(os.path.realpath(path))
            if path.suffix.lower() in EXTS and path.is_file() and normalized not in existing:
                t['files'].append(str(path.resolve()))
                existing.add(normalized)
                added += 1
        self.refresh_files(key)
        return added

    def refresh_files(self, key):
        t = self.tabs[key]
        t['count'].set(f"01  /  NGUỒN VIDEO · {len(t['files'])} file")
        if t['files']:
            t['empty'].place_forget()
        else:
            t['empty'].place(relx=.5, rely=.5, anchor='center')
        t['list'].delete(0, 'end')
        for i, p in enumerate(t['files'], 1):
            t['list'].insert('end', f'   {i:02d}    {Path(p).name}     ·     {Path(p).parent}')

    def remove(self, key, all_items=False):
        t = self.tabs[key]
        indices = range(len(t['files'])) if all_items else t['list'].curselection()
        for i in reversed(list(indices)):
            del t['files'][i]
            t['list'].delete(i)
        self.refresh_files(key)

    def output(self, key):
        p = filedialog.askdirectory()
        if p:
            self.tabs[key]['output'].set(p)

    def save_preset(self):
        p = filedialog.asksaveasfilename(defaultextension='.json', filetypes=[('JSON', '*.json')])
        if p:
            try:
                Path(p).write_text(json.dumps({k:v.get() for k,v in self.tabs['convert']['vars'].items()}, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception as e:
                messagebox.showerror(APP, str(e))

    def load_preset(self):
        p = filedialog.askopenfilename(filetypes=[('JSON', '*.json')])
        if not p:
            return
        try:
            data = json.loads(Path(p).read_text(encoding='utf-8-sig'))
            if not isinstance(data, dict):
                raise ValueError('Preset phải là đối tượng JSON.')
            settings = dict(DEFAULTS)
            settings.update({k:val for k,val in data.items() if k in DEFAULTS})
            settings['use_gpu'] = str(settings['use_gpu']).lower() in ('true','1','yes','on')
            if settings['scale_mode'] not in ('Default','Letterbox','Crop') or settings['audio_codec'] not in ('aac','ac3','mp3') or str(settings['audio_channels']) not in ('1','2'):
                raise ValueError('Preset chứa tùy chọn không hỗ trợ.')
            convert_args(settings)
            for k, v in settings.items():
                self.tabs['convert']['vars'][k].set(v)
        except Exception as e:
            messagebox.showerror('Lỗi preset', str(e))

    def start(self, key):
        if self.busy:
            return messagebox.showinfo(APP, 'Đang xử lý. Hãy dừng hoặc chờ hoàn tất.')
        if key == 'convert' and not licensing.is_activated():
            messagebox.showinfo(APP, 'Chức năng Chuyển đổi cần kích hoạt. Bấm nút "Kích hoạt" và nhập mã.')
            return self.ask_activation()
        t = self.tabs[key]
        try:
            if not t['files']:
                raise ValueError('Chưa chọn video.')
            ffmpeg = executable('ffmpeg')
            settings = {k:v.get() for k,v in t['vars'].items()}
            if key == 'convert':
                args = convert_args(settings)
                probe = None
            else:
                args = None
                probe = executable('ffprobe')
                for k in ('head','tail','offset','duration'):
                    settings[k] = number(settings[k], k, k == 'duration' and settings['mode'] == 'segment')
            output = t['output'].get().strip()
            if output:
                Path(output).mkdir(parents=True, exist_ok=True)
        except Exception as e:
            return messagebox.showerror(APP, str(e))
        self.cancel.clear()
        self.busy = True
        self.progress.configure(value=0, maximum=len(t['files']))
        threading.Thread(target=self.worker, args=(key,list(t['files']),output,settings,ffmpeg,probe,args), daemon=True).start()

    def run_process(self, args):
        flags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
        if self.cancel.is_set():
            raise InterruptedError('Đã dừng')
        with subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=flags) as p:
            while True:
                try:
                    out, err = p.communicate(timeout=.2)
                    break
                except subprocess.TimeoutExpired:
                    if self.cancel.is_set():
                        p.terminate()
                        try:
                            p.communicate(timeout=3)
                        except subprocess.TimeoutExpired:
                            p.kill()
                            p.communicate()
                        raise InterruptedError('Đã dừng')
        if p.returncode:
            raise RuntimeError(err.decode('utf-8', errors='replace')[-2400:])
        return out.decode('utf-8', errors='replace')

    def worker(self, key, files, output, settings, ffmpeg, probe, args):
        ok = failed = 0
        for i, file in enumerate(files):
            if self.cancel.is_set():
                break
            dest = None
            try:
                source = Path(file)
                folder = Path(output) if output else source.parent / 'ClipForge_Output'
                folder.mkdir(parents=True, exist_ok=True)
                suffix = '.mp4' if key == 'convert' else source.suffix
                stem = source.stem + ('_convert' if key == 'convert' else '_cut')
                dest = folder / (stem + suffix)
                count = 1
                while dest.exists():
                    dest = folder / f'{stem}_{count}{suffix}'
                    count += 1
                self.events.put(('status', f'{i+1}/{len(files)} • {source.name}'))
                if key == 'cut':
                    total = float(self.run_process([probe,'-v','error','-show_entries','format=duration','-of','default=noprint_wrappers=1:nokey=1',file]).strip())
                    if not math.isfinite(total) or total <= 0:
                        raise ValueError('Không đọc được thời lượng hợp lệ.')
                    start, length = cut_range(total, **{k:settings[k] for k in ('mode','head','tail','offset','duration','side')})
                    command = [ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-ss',str(start),'-i',file,'-t',str(length),'-map','0','-c','copy',str(dest)]
                else:
                    command = [ffmpeg,'-hide_banner','-loglevel','error','-nostdin','-n','-i',file,*args,str(dest)]
                self.run_process(command)
                ok += 1
                self.events.put(('log', f'✓ {dest}'))
            except Exception as e:
                if dest is not None and dest.exists():
                    dest.unlink(missing_ok=True)
                if self.cancel.is_set():
                    break
                failed += 1
                self.events.put(('log', f'LỖI {Path(file).name}: {e}'))
            self.events.put(('progress', i+1))
        self.events.put(('done', f'{"Đã dừng" if self.cancel.is_set() else "Hoàn tất"} • {ok} thành công • {failed} lỗi'))

    def stop(self):
        if self.busy:
            self.cancel.set()
            self.status.set('Đang dừng…')

    def pump(self):
        try:
            while True:
                kind, data = self.events.get_nowait()
                if kind in ('status','done'):
                    self.status.set(data)
                    if kind == 'done':
                        self.busy = False
                elif kind == 'progress':
                    self.progress.configure(value=data)
                elif kind == 'log':
                    self.log.configure(state='normal')
                    self.log.insert('end', data+'\n')
                    self.log.see('end')
                    self.log.configure(state='disabled')
                elif kind == 'update':
                    self.offer_update(*data)
                elif kind == 'update_error':
                    self.updating = False
                    if data[1]:
                        self.status.set('Cập nhật thất bại')
                        messagebox.showerror(APP, f'Không cập nhật được:\n{data[0]}')
                        if messagebox.askyesno(APP, 'Chọn lại thư mục cập nhật?'):
                            updater.set_folder(APP, '')
                            self.after(100, lambda: self.check_update(True))
                elif kind == 'install':
                    updater.install(data)
                    self.destroy()
                    return
        except queue.Empty:
            pass
        self.after(100, self.pump)

    def close(self):
        if self.busy:
            self.stop()
            self.after(200, self.wait_close)
        else:
            self.destroy()

    def wait_close(self):
        if self.busy:
            self.after(200, self.wait_close)
        else:
            self.destroy()


if __name__ == '__main__':
    App().mainloop()
