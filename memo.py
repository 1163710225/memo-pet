import tkinter as tk
from tkinter import messagebox
import tkinter.font as tkfont
from PIL import Image, ImageDraw, ImageFilter, ImageTk, ImageGrab
import json
import os
import sys
import io
import ctypes
from ctypes import wintypes
import base64
import uuid
from datetime import datetime

# PyInstaller 兼容：打包后 __file__ 指向虚拟路径，数据文件通过 sys._MEIPASS 访问
if getattr(sys, "frozen", False):
    _APP_DIR = os.path.dirname(sys.executable)
    _DATA_DIR = sys._MEIPASS
else:
    _APP_DIR = os.path.dirname(os.path.abspath(__file__))
    _DATA_DIR = _APP_DIR

DATA_FILE = os.path.join(_APP_DIR, "memo_data.json")   # 可写，放 exe 同目录
ICON_FILE = os.path.join(_DATA_DIR, "widget_icon.png")  # 只读，从包内读取

BG = "#F6F6F8"
SIDEBAR_BG = "#FAFAFC"
EDITOR_BG = "#FFFFFF"
ACCENT = "#5B5BD6"
ACCENT_DARK = "#4338CA"
ACCENT_SOFT = "#EEF0FF"
TEXT = "#1C1C1F"
SUB = "#9A9AA6"
FAINT = "#C6C6CE"
DIVIDER = "#EAEAEF"
DANGER = "#F04250"
FONT = "Microsoft YaHei UI"

# Windows -transparentcolor 专用的抠色键：桌宠悬浮窗把这个颜色设为
# "完全透明"，凡是自定义图标里被判定为背景/透明的像素，最终都会合成
# 成这个颜色，这样窗口显示出来就是镂空的。选一个基本不会在正常图标里
# 出现的青色，避免误伤真实内容。
TRANSPARENT_KEY = "#0ABAB5"

WIDGET_SIZE = 72
FULL_W, FULL_H = 620, 440
SIDEBAR_W = 168


def load_notes():
    if not os.path.exists(DATA_FILE):
        return []
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_notes(notes):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


# ---- 默认图标渲染 ----
def _lerp_color(c1, c2, t):
    return tuple(int(c1[i] + (c2[i] - c1[i]) * t) for i in range(3))


def _render_badge_icon(size=WIDGET_SIZE, hover=False, count=0):
    scale = 4
    s = size * scale
    pad = int(size * 0.14) * scale
    canvas_sz = s + pad * 2
    layer = Image.new("RGBA", (canvas_sz, canvas_sz), (0, 0, 0, 0))

    # 投影
    shadow_alpha = 95 if hover else 70
    shadow_off = (10 if hover else 6) * scale // 4
    shadow = Image.new("RGBA", (canvas_sz, canvas_sz), (0, 0, 0, 0))
    sd = ImageDraw.Draw(shadow)
    sd.rounded_rectangle(
        [pad, pad + shadow_off, pad + s, pad + s + shadow_off],
        radius=s * 0.34, fill=(30, 24, 70, shadow_alpha))
    shadow = shadow.filter(ImageFilter.GaussianBlur(s * 0.045))
    layer.alpha_composite(shadow)

    # 渐变主体
    top = (129, 140, 248) if not hover else (144, 154, 250)
    bottom = (79, 70, 229) if not hover else (91, 82, 240)
    body = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    bd = ImageDraw.Draw(body)
    for y in range(s):
        col = _lerp_color(top, bottom, y / s) + (255,)
        bd.line([(0, y), (s, y)], fill=col)
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=s * 0.34, fill=255)
    body.putalpha(mask)

    # 玻璃高光
    gloss = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    gd = ImageDraw.Draw(gloss)
    gd.ellipse([s * 0.08, -s * 0.18, s * 0.92, s * 0.42], fill=(255, 255, 255, 46))
    gloss.putalpha(Image.composite(gloss.split()[3], Image.new("L", (s, s), 0), mask))
    body = Image.alpha_composite(body, gloss)
    layer.alpha_composite(body, (pad, pad))

    # 便签纸
    nw, nh = s * 0.46, s * 0.50
    nx = pad + (s - nw) / 2
    ny = pad + (s - nh) / 2 - s * 0.02
    fold = nw * 0.28
    note = Image.new("RGBA", (canvas_sz, canvas_sz), (0, 0, 0, 0))
    nd = ImageDraw.Draw(note)
    nd.rounded_rectangle([nx, ny, nx + nw, ny + nh], radius=nw * 0.14, fill=(255, 255, 255, 235))
    nd.polygon(
        [(nx + nw - fold, ny), (nx + nw, ny + fold), (nx + nw - fold, ny + fold)],
        fill=(224, 226, 250, 255))
    lc = (150, 148, 214, 255)
    for i, ly in enumerate([0.42, 0.60, 0.78]):
        lw = nw * (0.62 if i < 2 else 0.40)
        nd.rounded_rectangle(
            [nx + nw * 0.16, ny + nh * ly,
             nx + nw * 0.16 + lw, ny + nh * ly + s * 0.018],
            radius=s * 0.01, fill=lc)
    layer.alpha_composite(note)

    # 数量角标
    if count:
        br = s * 0.15
        bx, by = pad + s * 0.86, pad + s * 0.14
        badge = Image.new("RGBA", (canvas_sz, canvas_sz), (0, 0, 0, 0))
        bdd = ImageDraw.Draw(badge)
        bdd.ellipse([bx - br, by - br, bx + br, by + br], fill=(240, 66, 80, 255),
                    outline=(255, 255, 255, 255), width=int(s * 0.012))
        layer.alpha_composite(badge)

    return layer.resize((canvas_sz // scale, canvas_sz // scale), Image.LANCZOS)


class DeskWidget:
    def __init__(self):
        self.root = tk.Tk()
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.configure(bg=BG)

        self.notes = load_notes()
        self._make_icons()

        # RGBA 图标：启用透明色键让背景消失
        if self._use_transparent_key:
            self.root.configure(bg=TRANSPARENT_KEY)
            self.root.attributes("-transparentcolor", TRANSPARENT_KEY)

        w, h = self._sz
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self._x = sw - w - 30
        self._y = sh - h - 90
        self.root.geometry(f"{w}x{h}+{self._x}+{self._y}")

        canvas_bg = TRANSPARENT_KEY if self._use_transparent_key else BG
        self.canvas = tk.Canvas(self.root, width=w, height=h,
                                highlightthickness=0, bg=canvas_bg)
        self.canvas.pack()

        self.app = None
        self._was_drag = False
        self._hover = False
        self._draw()

        self.canvas.bind("<Button-1>", self._press)
        self.canvas.bind("<B1-Motion>", self._drag)
        self.canvas.bind("<ButtonRelease-1>", self._release)
        self.canvas.bind("<Enter>", lambda e: self._seth(True))
        self.canvas.bind("<Leave>", lambda e: self._seth(False))
        self.canvas.bind("<Button-3>", self._menu)

    def _make_icons(self):
        count = len(self.notes)
        self._icon_normal = _render_badge_icon(hover=False, count=count)
        self._icon_hover = _render_badge_icon(hover=True, count=count)
        self._sz = self._icon_normal.size
        self._badge_count = count

        self._custom = None
        self._use_transparent_key = False
        if os.path.exists(ICON_FILE):
            try:
                # 先在原图分辨率上抠背景、换成透明色键，最后再缩小。
                # 如果先缩小再抠图，缩小时的插值会把图标边缘和白色背景混出一圈
                # 过渡灰白色，这些过渡像素和四角采样到的背景色差异超过容差，
                # 抠不干净，形成一圈残留的白边。先抠图再缩小，缩小时插值
                # 发生在“图标颜色↔色键”之间，就不会再混出白色了。
                raw = Image.open(ICON_FILE).convert("RGBA")
                keyed, self._use_transparent_key = self._remove_bg(raw)
                keyed = keyed.resize(self._sz, Image.LANCZOS)
                # 缩小插值还可能留下极少量偏色像素，收尾再吸附一次色键
                self._custom = self._snap_to_key(keyed)
            except Exception as e:
                # 以前这里出错会被静默地吸掉，导致自定义图标没生效也看不出来；
                # 现在写入日志方便排查（比如 numpy 没装就会记在这里）。
                try:
                    log_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memo_debug.log")
                    with open(log_path, "a", encoding="utf-8") as f:
                        f.write(f"[{datetime.now()}] 自定义图标加载失败: {e!r}\n")
                except Exception:
                    pass
                self._custom = None

    @staticmethod
    def _remove_bg(img):
        # img 必须已经是 RGBA。
        # 不再用 PIL 报告的原始 mode 判断有没有透明通道——很多 PNG 实际是
        # P(调色板+透明索引)或 LA 模式,mode 不等于 RGBA,但一样有真实透明
        # 信息,之前按 mode 判断会把这类图片误判成不透明。
        # 现在统一转成 RGBA 后,直接看 alpha 通道里有没有真的小于 255 的值,
        # 不管原图是哪种模式都能正确识别;两种情况最终都合成到透明色键上,
        # 这样 -transparentcolor 才能真正把背景挖空,而不是残留一块实色。
        import numpy as np
        key_rgb = np.array(_hex_to_rgb(TRANSPARENT_KEY), dtype=np.uint8)
        arr = np.array(img, dtype=np.uint8)
        alpha_channel = arr[:, :, 3]

        if alpha_channel.min() < 250:
            # 图片自带真实透明通道
            alpha = alpha_channel.astype(float) / 255.0
            alpha = alpha[:, :, np.newaxis]
            result = (arr[:, :, :3] * alpha + key_rgb * (1 - alpha)).astype(np.uint8)
            # fromarray 会根据数组形状自动识别成 RGB，不用再传 mode 参数
            # (新版 Pillow 里显式传 mode 会报 DeprecationWarning)
            return Image.fromarray(result), True

        # 完全不透明:按四角颜色猜背景色再抠掉,同样合成到透明色键,
        # 而不是像之前那样合成到不透明的 BG 色。
        arr16 = arr.astype(np.int16)
        corners = np.array([
            arr16[0, 0, :3], arr16[0, -1, :3],
            arr16[-1, 0, :3], arr16[-1, -1, :3]
        ])
        bg_color = corners.mean(axis=0)
        diff = np.abs(arr16[:, :, :3] - bg_color)
        bg_mask = (diff.max(axis=2) < 30) & (diff.min(axis=2) < 12)
        a = np.where(bg_mask, 0, 255).astype(np.uint8)
        alpha = a.astype(float) / 255.0
        alpha = alpha[:, :, np.newaxis]
        result = (arr[:, :, :3] * alpha + key_rgb * (1 - alpha)).astype(np.uint8)
        return Image.fromarray(result), True

    @staticmethod
    def _snap_to_key(img):
        """缩放插值会在图标边缘和色键之间留下极少量介于两者之间的杂色
        像素，这里把和色键足够接近的像素直接吸附成纯色键，避免残留色边。"""
        import numpy as np
        key_rgb = np.array(_hex_to_rgb(TRANSPARENT_KEY), dtype=np.int16)
        arr = np.array(img.convert("RGB"), dtype=np.int16)
        diff = np.abs(arr - key_rgb)
        close = diff.max(axis=2) < 18
        arr[close] = key_rgb
        return Image.fromarray(arr.astype(np.uint8))

    @staticmethod
    def _flood_alpha(img):
        """Flood-fill from corners to remove solid background."""
        import collections
        w, h = img.size
        rgba = img.convert("RGBA")
        px = rgba.load()

        # 采样四角区域算平均背景色
        corner_pixels = []
        for x, y in [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]:
            for dx in range(3):
                for dy in range(3):
                    nx, ny = min(x+dx, w-1), min(y+dy, h-1)
                    corner_pixels.append(px[nx, ny][:3])
        bg = tuple(sum(c[i] for c in corner_pixels) // len(corner_pixels) for i in range(3))

        # 标记要清除的像素
        tol = 30
        mask = set()
        queue = collections.deque()
        for x, y in [(0, 0), (w-1, 0), (0, h-1), (w-1, h-1)]:
            if (x, y) not in mask:
                mask.add((x, y))
                queue.append((x, y))

        while queue:
            x, y = queue.popleft()
            for nx, ny in [(x-1, y), (x+1, y), (x, y-1), (x, y+1)]:
                if 0 <= nx < w and 0 <= ny < h and (nx, ny) not in mask:
                    r, g, b, _ = px[nx, ny]
                    if (abs(r-bg[0]) < tol and abs(g-bg[1]) < tol and abs(b-bg[2]) < tol):
                        mask.add((nx, ny))
                        queue.append((nx, ny))

        for x, y in mask:
            r, g, b, a = px[x, y]
            px[x, y] = (r, g, b, 0)

        return rgba

    def _seth(self, v):
        self._hover = v
        self._draw()

    def _draw(self):
        c = self.canvas
        c.delete("all")
        w, h = self._sz
        lift = 3 if self._hover else 0

        if self._custom:
            # _remove_bg 已输出合成好的 RGB 图片，直接显示
            self._tk_img = ImageTk.PhotoImage(self._custom)
            count = len(self.notes)
            if count:
                bx, by = w - 12, 10 + lift
                c.create_oval(bx - 8, by - 8, bx + 8, by + 8,
                              fill=DANGER, outline="#FFFFFF", width=1)
                c.create_text(bx, by, text=str(count if count < 100 else "99+"),
                              fill="#FFFFFF", font=(FONT, 8, "bold"))
        else:
            bg_rgb = _hex_to_rgb(BG)
            img = self._icon_hover if self._hover else self._icon_normal
            flat = Image.new("RGB", img.size, bg_rgb)
            flat.paste(img, (0, 0), img)
            self._tk_img = ImageTk.PhotoImage(flat)

        c.create_image(w // 2, h // 2 - lift, image=self._tk_img, anchor="center")

    def _press(self, event):
        self._px, self._py = event.x, event.y
        self._was_drag = False

    def _drag(self, event):
        if abs(event.x - self._px) > 3 or abs(event.y - self._py) > 3:
            self._was_drag = True
        nx = self._x + event.x - self._px
        ny = self._y + event.y - self._py
        self._x, self._y = nx, ny
        self.root.geometry(f"+{nx}+{ny}")

    def _release(self, event):
        if not self._was_drag:
            self.expand()

    def _menu(self, event):
        m = tk.Menu(self.root, tearoff=0, bg="#FFFFFF", fg=TEXT,
                     activebackground=ACCENT, activeforeground="#FFFFFF",
                     font=(FONT, 10), bd=0)
        m.add_command(label="打开", command=self.expand)
        m.add_separator()
        m.add_command(label="退出", command=self._quit)
        m.tk_popup(event.x_root, event.y_root)

    def expand(self):
        if self.app is None:
            self.app = MemoWindow(self)
        else:
            self.app.refresh()
        self.root.withdraw()
        self.app.show()

    def show_widget(self):
        self._draw()
        self.root.deiconify()

    def refresh(self):
        self.notes = load_notes()
        if len(self.notes) != self._badge_count:
            self._make_icons()
            if self._use_transparent_key:
                self.root.configure(bg=TRANSPARENT_KEY)
                self.root.attributes("-transparentcolor", TRANSPARENT_KEY)
                self.canvas.configure(bg=TRANSPARENT_KEY)
            else:
                self.root.configure(bg=BG)
                self.canvas.configure(bg=BG)
        self._draw()

    def _quit(self):
        if self.app:
            self.app._save_if_dirty()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


def _hex_to_rgb(h):
    return tuple(int(h[i:i+2], 16) for i in (1, 3, 5))


def _get_work_area():
    SPI_GETWORKAREA = 0x0030
    rect = wintypes.RECT()
    ctypes.windll.user32.SystemParametersInfoW(SPI_GETWORKAREA, 0, ctypes.byref(rect), 0)
    return rect.left, rect.top, rect.right - rect.left, rect.bottom - rect.top


# ---- MemoWindow ----
class MemoWindow:
    RESIZE_MARGIN = 3

    def __init__(self, widget):
        self.widget = widget
        self.root = tk.Toplevel()
        self.root.overrideredirect(True)
        self.root.configure(bg=DIVIDER)
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        self.root.geometry(f"{FULL_W}x{FULL_H}+{(sw - FULL_W)//2}+{(sh - FULL_W)//2}")
        self.root.minsize(420, 320)

        self.notes = list(self.widget.notes)
        self.current_index = None
        self._dirty = False
        self._tid = None
        self._row_widgets = []
        self._resize_dir = None
        self._build()
        self._ensure_taskbar_icon()

    def _ensure_taskbar_icon(self):
        """overrideredirect(True) 的窗口 Windows 默认不会放到任务栏、
        也进不了 Alt+Tab 列表，以前只能靠一直置顶 (-topmost) 来保证
        还能找得到它，但常驻置顶又会一直挡在别的应用上面。
        这里直接改 Windows 的扩展窗口样式：把 WS_EX_TOOLWINDOW 换成
        WS_EX_APPWINDOW，这样即使不置顶也能正常出现在任务栏、能被
        Alt+Tab 切换到——这跟 overrideredirect 完全是两回事，不会因此
        把系统自带的边框标题栏带回来。"""
        try:
            GWL_EXSTYLE = -20
            WS_EX_APPWINDOW = 0x00040000
            WS_EX_TOOLWINDOW = 0x00000080
            self.root.update_idletasks()
            hwnd = ctypes.windll.user32.GetParent(self.root.winfo_id())
            if not hwnd:
                hwnd = self.root.winfo_id()
            style = ctypes.windll.user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
            style = (style & ~WS_EX_TOOLWINDOW) | WS_EX_APPWINDOW
            ctypes.windll.user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
            # 改完扩展样式后任务栏未必马上刷新，隐藏再显示一次强制刷新
            self.root.withdraw()
            self.root.after(10, self.root.deiconify)
        except Exception:
            pass

    def _build(self):
        card = tk.Frame(self.root, bg=BG)
        card.pack(fill="both", expand=True, padx=1, pady=1)

        bar = tk.Frame(card, bg=BG, height=40)
        bar.pack(fill="x")
        bar.pack_propagate(False)
        bar.bind("<Button-1>", self._ds)
        bar.bind("<B1-Motion>", self._dm)

        title = tk.Label(bar, text="备忘录", bg=BG, fg=TEXT, font=(FONT, 12, "bold"))
        title.pack(side="left", padx=(18, 0))
        title.bind("<Button-1>", self._ds)
        title.bind("<B1-Motion>", self._dm)

        self._close_canvas = tk.Canvas(bar, width=28, height=28, bg=BG,
                                        highlightthickness=0, cursor="hand2")
        self._close_canvas.pack(side="right", padx=(0, 14))
        self._draw_close(False)
        self._close_canvas.bind("<Button-1>", lambda e: self.collapse())
        self._close_canvas.bind("<Enter>", lambda e: self._draw_close(True))
        self._close_canvas.bind("<Leave>", lambda e: self._draw_close(False))

        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x")

        body = tk.Frame(card, bg=BG)
        body.pack(fill="both", expand=True)

        # 窗口大小调整
        self.root.bind("<Motion>", self._on_root_motion)
        self.root.bind("<Button-1>", self._on_root_press)
        self.root.bind("<B1-Motion>", self._on_root_drag)
        self.root.bind("<ButtonRelease-1>", lambda e: setattr(self, "_resize_dir", None))

        sb = tk.Frame(body, bg=SIDEBAR_BG, width=SIDEBAR_W)
        sb.pack(side="left", fill="y")
        sb.pack_propagate(False)
        self._sidebar = sb

        tk.Frame(body, bg=DIVIDER, width=1).pack(side="left", fill="y")

        sh = tk.Frame(sb, bg=SIDEBAR_BG, height=40)
        sh.pack(fill="x")
        sh.pack_propagate(False)

        self._add_lbl = tk.Label(sh, text="＋ 新建便签", bg=SIDEBAR_BG, fg=ACCENT,
                                  font=(FONT, 10, "bold"), cursor="hand2", anchor="w")
        self._add_lbl.pack(side="left", padx=16, pady=8)
        self._add_lbl.bind("<Button-1>", lambda e: self._add())
        self._add_lbl.bind("<Enter>", lambda e: self._add_lbl.config(fg=ACCENT_DARK))
        self._add_lbl.bind("<Leave>", lambda e: self._add_lbl.config(fg=ACCENT))

        list_wrap = tk.Frame(sb, bg=SIDEBAR_BG)
        list_wrap.pack(fill="both", expand=True)

        self._list_canvas = tk.Canvas(list_wrap, bg=SIDEBAR_BG, highlightthickness=0, bd=0)
        self._list_canvas.pack(side="left", fill="both", expand=True)
        self._list_inner = tk.Frame(self._list_canvas, bg=SIDEBAR_BG)
        self._list_win = self._list_canvas.create_window((0, 0), window=self._list_inner, anchor="nw")
        self._list_inner.bind("<Configure>", self._sync_scrollregion)
        self._list_canvas.bind("<Configure>",
                                lambda e: self._list_canvas.itemconfig(self._list_win, width=e.width))

        self._list_canvas.bind("<MouseWheel>", self._on_wheel)
        self._list_inner.bind("<MouseWheel>", self._on_wheel)

        editor_wrap = tk.Frame(body, bg=EDITOR_BG)
        editor_wrap.pack(side="left", fill="both", expand=True)

        self._meta_lbl = tk.Label(editor_wrap, text="", bg=EDITOR_BG, fg=SUB, font=(FONT, 9))
        self._meta_lbl.pack(anchor="e", padx=24, pady=(14, 0))

        self._text = tk.Text(editor_wrap, wrap="word", bg=EDITOR_BG, fg=TEXT,
                              font=(FONT, 12), bd=0, padx=24, pady=10,
                              undo=True, maxundo=50,
                              insertbackground=ACCENT,
                              selectbackground=ACCENT_SOFT,
                              selectforeground=TEXT,
                              spacing3=4, relief="flat")
        self._text.pack(side="left", fill="both", expand=True, padx=(0, 4))
        self._text.bind("<KeyRelease>", self._on_type)
        self._text.bind("<Control-v>", self._on_paste)
        self._text.bind("<Double-Button-1>", self._on_dbl_click)
        self._text.bind("<FocusIn>", lambda e: self._maybe_clear_placeholder())

        self._populate()

    # ---- resize ----
    def _resize_dir_at(self, screen_x, screen_y):
        m = self.RESIZE_MARGIN
        rx = self.root.winfo_x()
        ry = self.root.winfo_y()
        rw = self.root.winfo_width()
        rh = self.root.winfo_height()
        x, y = screen_x - rx, screen_y - ry
        if x < m and y < m: return "nw"
        if x > rw - m and y < m: return "ne"
        if x < m and y > rh - m: return "sw"
        if x > rw - m and y > rh - m: return "se"
        if x < m: return "w"
        if x > rw - m: return "e"
        if y < m: return "n"
        if y > rh - m: return "s"
        return None

    def _on_root_motion(self, event):
        d = self._resize_dir_at(event.x_root, event.y_root)
        cursors = {"nw": "size_nw_se", "ne": "size_ne_sw", "sw": "size_ne_sw",
                   "se": "size_nw_se", "n": "size_ns", "s": "size_ns",
                   "e": "size_we", "w": "size_we"}
        self.root.config(cursor=cursors.get(d, "arrow"))

    def _on_root_press(self, event):
        d = self._resize_dir_at(event.x_root, event.y_root)
        if d:
            self._resize_dir = d
            self._rsx = event.x_root
            self._rsy = event.y_root
            self._rw = self.root.winfo_width()
            self._rh = self.root.winfo_height()
            self._rx = self.root.winfo_x()
            self._ry = self.root.winfo_y()

    def _on_root_drag(self, event):
        if not self._resize_dir:
            return
        d = self._resize_dir
        dx = event.x_root - self._rsx
        dy = event.y_root - self._rsy
        new_w = max(420, self._rw + (dx if "e" in d else (-dx if "w" in d else 0)))
        new_h = max(320, self._rh + (dy if "s" in d else (-dy if "n" in d else 0)))
        new_x = self._rx + (dx if "w" in d else 0)
        new_y = self._ry + (dy if "n" in d else 0)
        self.root.geometry(f"{new_w}x{new_h}+{new_x}+{new_y}")

    # ---- scroll ----
    def _sync_scrollregion(self, event=None):
        self._list_inner.update_idletasks()
        bbox = self._list_canvas.bbox("all")
        if bbox:
            self._list_canvas.configure(scrollregion=bbox)
        ch = self._list_canvas.winfo_height()
        if bbox and bbox[3] <= ch:
            self._list_canvas.yview_moveto(0)

    def _on_wheel(self, event):
        bbox = self._list_canvas.bbox("all")
        if bbox and bbox[3] > self._list_canvas.winfo_height():
            self._list_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    # ---- drag ----
    def _ds(self, event):
        self._dx = event.x_root - self.root.winfo_x()
        self._dy = event.y_root - self.root.winfo_y()

    def _dm(self, event):
        self.root.geometry(f"+{event.x_root - self._dx}+{event.y_root - self._dy}")

    # ---- close ----
    def _draw_close(self, hover):
        c = self._close_canvas
        c.delete("all")
        if hover:
            c.create_oval(2, 2, 26, 26, fill="#FCE8E9", outline="")
            fg = DANGER
        else:
            fg = SUB
        c.create_line(11, 11, 17, 17, fill=fg, width=2, capstyle="round")
        c.create_line(17, 11, 11, 17, fill=fg, width=2, capstyle="round")

    # ---- notes ----
    def _populate(self):
        for w in self._row_widgets:
            w.destroy()
        self._row_widgets = []

        if not self.notes:
            empty = tk.Label(self._list_inner, text="暂无便签\n点击上方新建", bg=SIDEBAR_BG,
                              fg=FAINT, font=(FONT, 10), justify="center")
            empty.pack(pady=30)
            self._row_widgets.append(empty)
            return

        for i, n in enumerate(self.notes):
            t = n.get("title", "").strip()
            content = n.get("content", "")
            # 从 segments 或纯文本中提取预览
            snippet = ""
            if isinstance(content, list):
                for seg in content:
                    if seg[0] == "text":
                        text_content = seg[1]
                        if not t:
                            t = text_content.strip().split("\n")[0][:16]
                        if not snippet:
                            lines = text_content.strip().split("\n")
                            if len(lines) > 1:
                                for line in lines[1:]:
                                    if line.strip():
                                        snippet = line.strip()
                                        break
                            elif seg[1] != content[0][1] if len(content) > 1 else True:
                                pass
                            else:
                                for s in content:
                                    if s[0] == "text" and s[1].strip():
                                        for line in s[1].strip().split("\n")[1:]:
                                            if line.strip():
                                                snippet = line.strip()
                                                break
                                        if snippet:
                                            break
                    elif seg[0] == "image" and not snippet:
                        snippet = "[图片]"
            else:
                c = str(content)
                if not t and c:
                    t = c.split("\n")[0][:16]
                lines = c.strip().split("\n")
                for line in lines[1:]:
                    if line.strip():
                        snippet = line.strip()
                        break
            if not t:
                t = "无标题"
            row = self._make_row(i, t, snippet)
            self._row_widgets.append(row)

    def _ellipsize(self, text, max_px, bold=False):
        """按字体实际渲染宽度截断文字，超出 max_px 就用“…”结尾，
        确保标题 Label 永远不会把右侧的删除按钮挤出可视范围。"""
        f = tkfont.Font(family=FONT, size=10, weight="bold" if bold else "normal")
        if f.measure(text) <= max_px:
            return text
        ell = "…"
        lo, hi = 0, len(text)
        while lo < hi:
            mid = (lo + hi + 1) // 2
            if f.measure(text[:mid] + ell) <= max_px:
                lo = mid
            else:
                hi = mid - 1
        return (text[:lo] + ell) if lo < len(text) else text

    def _make_row(self, index, title_text, snippet_text):
        selected = index == self.current_index
        bg = ACCENT_SOFT if selected else SIDEBAR_BG
        row = tk.Frame(self._list_inner, bg=bg, cursor="hand2")
        row.pack(fill="x", padx=6, pady=1)

        pad = tk.Frame(row, bg=bg)
        pad.pack(fill="x", padx=10, pady=7)

        # 标题和删除按钮同一行，标题占据剩余宽度，X 贴在右侧，这样
        # 每一行都能直接点右上角删除，不用先选中再去底部找删除链接
        header = tk.Frame(pad, bg=bg)
        header.pack(fill="x")

        # 标题文字过长时要省略号截断，不然 Label 会按完整文字宽度
        # 请求空间，超出侧边栏实际宽度后右侧的 X 就会被挤出可视范围，
        # 看起来像是“不见了”。按字体实际像素宽度测量后截断，比按
        # 字符数盲猜准确，中英文混排时也不会误判。
        avail_px = SIDEBAR_W - 64  # 几块 padding 加 X 按钮自身宽度的大致留白
        display_title = self._ellipsize(title_text, avail_px, bold=selected)

        t_lbl = tk.Label(header, text=display_title, bg=bg,
                          fg=(ACCENT_DARK if selected else TEXT),
                          font=(FONT, 10, "bold" if selected else "normal"), anchor="w")
        t_lbl.pack(side="left", fill="x", expand=True)

        x_btn = tk.Label(header, text="\u2715", bg=bg, fg=FAINT,
                          font=(FONT, 9), cursor="hand2")
        x_btn.pack(side="right", padx=(6, 0))
        x_btn.bind("<Button-1>", lambda e, i=index: self._delete_row(i))
        x_btn.bind("<Enter>", lambda e: x_btn.config(fg=DANGER))
        x_btn.bind("<Leave>", lambda e: x_btn.config(fg=FAINT))

        widgets = [row, pad, header, t_lbl]
        if snippet_text:
            s_lbl = tk.Label(pad, text=snippet_text, bg=bg, fg=SUB, font=(FONT, 8), anchor="w")
            s_lbl.pack(fill="x", pady=(2, 0))
            widgets.append(s_lbl)

        def on_enter(e):
            if index != self.current_index:
                for w in widgets: w.config(bg="#F1F1F6")
                x_btn.config(bg="#F1F1F6")
        def on_leave(e):
            if index != self.current_index:
                for w in widgets: w.config(bg=SIDEBAR_BG)
                x_btn.config(bg=SIDEBAR_BG)
        def on_click(e):
            self._select(index)

        for w in widgets:
            w.bind("<Enter>", on_enter)
            w.bind("<Leave>", on_leave)
            w.bind("<Button-1>", on_click)

        return row

    def _select(self, i):
        if not self.notes or i >= len(self.notes):
            return
        if self.current_index is not None and self.current_index != i:
            self._save()
        self.current_index = i
        n = self.notes[i]
        self._text.delete("1.0", "end")
        # 初始化图片引用
        self._images = {}
        self._img_name_map = {}
        if not hasattr(self, '_tk_images'):
            self._tk_images = []
        content = n.get("content", "")
        # 兼容旧格式（纯文本字符串）
        if isinstance(content, str):
            if content:
                self._text.insert("1.0", content)
        # 新格式（segments 数组）
        elif isinstance(content, list):
            for seg in content:
                if seg[0] == "text":
                    self._text.insert("end", seg[1])
                elif seg[0] == "image":
                    try:
                        img_data = base64.b64decode(seg[1])
                        img = Image.open(io.BytesIO(img_data))
                        tk_img = ImageTk.PhotoImage(img)
                        img_id = seg[2] if len(seg) > 2 else str(uuid.uuid4())[:8]
                        self._images[img_id] = seg[1]
                        img_tk_name = self._text.image_create("end", image=tk_img)
                        if not hasattr(self, '_img_name_map'):
                            self._img_name_map = {}
                        self._img_name_map[img_tk_name] = img_id
                        # 保持引用防止被GC
                        if not hasattr(self, '_tk_images'):
                            self._tk_images = []
                        self._tk_images.append(tk_img)
                    except Exception:
                        pass
        self._dirty = False
        self._text.focus_set()
        ts = n.get("updated_at", "")
        if ts:
            try:
                dt = datetime.fromisoformat(ts)
                self._meta_lbl.config(text=f"最后编辑 {dt.strftime('%m月%d日 %H:%M')}")
            except Exception:
                self._meta_lbl.config(text="")
        self._populate()

    def _add(self):
        self._save()
        n = {"id": datetime.now().strftime("%Y%m%d%H%M%S%f"),
             "title": "", "content": [],
             "created_at": datetime.now().isoformat(),
             "updated_at": datetime.now().isoformat()}
        self.notes.insert(0, n)
        self._flush()
        self.current_index = None
        self._text.delete("1.0", "end")
        self._meta_lbl.config(text="")
        self._populate()
        self._select(0)

    def _delete_row(self, i):
        """直接删除第 i 行，不需要先选中。如果删的是当前选中的那条，
        清空编辑区；如果删的行在当前选中项前面，后面所有行都会整体
        前移一位，需要同步修正 current_index，不然会选中错行。"""
        if i == self.current_index:
            self.current_index = None
            self._text.delete("1.0", "end")
            self._meta_lbl.config(text="")
            self._dirty = False
        elif self.current_index is not None and i < self.current_index:
            self.current_index -= 1
        del self.notes[i]
        self._flush()
        self._populate()

    def _save(self):
        if self.current_index is None:
            return
        # 构建 segments：遍历 Text 内容，提取文本和图片
        segments = []
        text_lines = self._text.get("1.0", "end-1c").split("\n")

        # 简化方案：纯文本 + 图片标记，保存为 segments
        # 先收集所有文本并标记图片位置
        full_text = self._text.get("1.0", "end")
        # 用 dump 获取所有内容（文本 + 图片引用）
        dumped = self._text.dump("1.0", "end-1c")
        current_text = []
        for item in dumped:
            if item[0] == "text":
                current_text.append(item[1])
            elif item[0] == "image":
                if current_text:
                    txt = "".join(current_text)
                    if txt.rstrip("\n"):
                        segments.append(["text", txt])
                    current_text = []
                # item[1] 是 tk 内部自动生成的图片句柄（比如 "image1"），
                # 不能直接拿它去 self._images 里找——self._images 的 key 是
                # uuid 而不是这个句柄。两者的对应关系存在 self._img_name_map 里，
                # 要先翻译成 img_id 再去查 self._images，之前直接用 tk 句柄查
                # 永远查不到，图片 segment 就会被静默跳过，保存后图片就丢了。
                tk_name = item[1]
                img_id = getattr(self, '_img_name_map', {}).get(tk_name)
                if img_id and img_id in getattr(self, '_images', {}):
                    segments.append(["image", self._images[img_id], img_id])
        if current_text:
            txt = "".join(current_text)
            if txt.rstrip("\n"):
                segments.append(["text", txt])

        # 获取标题
        first_text = ""
        for seg in segments:
            if seg[0] == "text":
                first_text = seg[1].strip().split("\n")[0][:50]
                break
        self.notes[self.current_index].update(
            content=segments, title=first_text,
            updated_at=datetime.now().isoformat())
        self._dirty = False
        self._flush()

    def _flush(self):
        save_notes(self.notes)
        self.widget.notes = list(self.notes)
        self.widget.refresh()

    def _maybe_clear_placeholder(self):
        pass

    def _on_dbl_click(self, event):
        """双击图片放大查看"""
        try:
            pos = self._text.index(f"@{event.x},{event.y}")
            dumped = self._text.dump(f"{pos} linestart", f"{pos} lineend+1c")
            for item in dumped:
                if item[0] == "image":
                    tk_name = item[1]
                    img_map = getattr(self, '_img_name_map', {})
                    img_id = img_map.get(tk_name)
                    if img_id and img_id in getattr(self, '_images', {}):
                        b64 = self._images[img_id]
                        img_data = base64.b64decode(b64)
                        img = Image.open(io.BytesIO(img_data))
                        self._show_image_popup(img)
                        return
        except Exception:
            pass

    def _show_image_popup(self, pil_img):
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()

        pad = 24
        bottom = 30

        def compute_snug():
            max_w = int(sw * 0.95)
            max_h = int(sh * 0.92)
            avail_w = max_w - pad * 2
            avail_h = max_h - pad * 2 - bottom
            fs = min(avail_w / pil_img.width, avail_h / pil_img.height, 1.0)
            dw = max(1, int(pil_img.width * fs))
            dh = max(1, int(pil_img.height * fs))
            w_ = max(700, dw + pad * 2)
            h_ = max(520, dh + pad * 2 + bottom)
            return w_, h_

        def compute_maxed():
            l, t, w, h = _get_work_area()
            state["_wa_left"], state["_wa_top"] = l, t
            return w, h

        ww, wh = compute_snug()
        wx, wy = (sw - ww) // 2, (sh - wh) // 2
        snug_geom = (ww, wh, wx, wy)

        preview_bg = "#E8E8EC"
        text_dim = "#8B8B92"
        text_hover = ACCENT_DARK

        win = tk.Toplevel(self.root)
        win.withdraw()
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.geometry(f"{ww}x{wh}+{wx}+{wy}")
        win.configure(bg=preview_bg)

        canvas = tk.Canvas(win, bg=preview_bg, highlightthickness=0, cursor="hand2")
        canvas.pack(fill="both", expand=True)

        state = {
            "scale": 1.0,
            "fit_scale": 1.0,
            "ox": 0.0, "oy": 0.0,
            "tk_img": None,
            "dragging": False,
            "win_x": wx, "win_y": wy,
            "cur_w": ww, "cur_h": wh,
            "maximized": False,
            "snug_geom": snug_geom,
            "has_press": False,
            "_anim": None,
            "_closing": False,
        }

        def calc_fit_scale(w_, h_):
            avail_w = w_ - pad * 2
            avail_h = h_ - pad * 2 - bottom
            return min(avail_w / pil_img.width, avail_h / pil_img.height, 1.0)

        def clamp_offset():
            if state["scale"] <= state["fit_scale"] + 0.001:
                state["ox"] = 0.0
                state["oy"] = 0.0

        def render():
            cw, ch = state["cur_w"], state["cur_h"]
            s = state["scale"]
            nw = max(1, int(pil_img.width * s))
            nh = max(1, int(pil_img.height * s))
            resized = pil_img.resize((nw, nh), Image.LANCZOS)
            state["tk_img"] = ImageTk.PhotoImage(resized)
            canvas.delete("img")
            cx = cw / 2 + state["ox"]
            cy = (ch - bottom) / 2 + state["oy"]
            canvas.create_image(cx, cy, image=state["tk_img"], anchor="center", tags="img")

        def cancel_anim():
            if state["_anim"] is not None:
                win.after_cancel(state["_anim"])
                state["_anim"] = None

        def animate_to_scale(target):
            cancel_anim()
            def step():
                cur = state["scale"]
                if abs(cur - target) < 0.0005:
                    state["scale"] = target
                    clamp_offset()
                    render()
                    return
                state["scale"] = cur + (target - cur) * 0.18
                clamp_offset()
                render()
                state["_anim"] = win.after(16, step)
            state["_anim"] = win.after(1, step)

        def zoom_in(step=0):
            total, fps = 5, 60
            progress = min(1.0, step / total)
            eased = 1 - (1 - progress) ** 3
            s = 0.92 + 0.08 * eased
            cur_w = int(ww * s)
            cur_h = int(wh * s)
            cx = wx + (ww - cur_w) // 2
            cy = wy + (wh - cur_h) // 2
            win.geometry(f"{cur_w}x{cur_h}+{cx}+{cy}")
            state["cur_w"], state["cur_h"] = cur_w, cur_h
            state["win_x"], state["win_y"] = cx, cy
            if progress < 1.0:
                state["_anim"] = win.after(1000 // fps, lambda: zoom_in(step + 1))
            else:
                render()
                state["_anim"] = None

        def close_with_zoom():
            if state["_closing"]:
                return
            state["_closing"] = True
            cancel_anim()
            bw, bh = state["cur_w"], state["cur_h"]
            bx, by = state["win_x"], state["win_y"]
            def zoom_out(step=0):
                total, fps = 3, 60
                progress = min(1.0, step / total)
                s = 1.0 - 0.08 * progress
                cur_w = int(bw * s)
                cur_h = int(bh * s)
                cx = bx + (bw - cur_w) // 2
                cy = by + (bh - cur_h) // 2
                win.geometry(f"{cur_w}x{cur_h}+{cx}+{cy}")
                if progress < 1.0:
                    state["_anim"] = win.after(1000 // fps, lambda: zoom_out(step + 1))
                else:
                    win.destroy()
            zoom_out(0)

        state["fit_scale"] = calc_fit_scale(ww, wh)
        state["scale"] = state["fit_scale"]
        render()

        max_btn = tk.Canvas(win, width=26, height=26, bg=preview_bg,
                             highlightthickness=0, cursor="hand2")
        max_btn.place(relx=1.0, x=-72, y=12)

        def draw_max_btn(hover=False):
            max_btn.delete("all")
            if hover:
                max_btn.create_oval(1, 1, 25, 25, fill="#DCDCE2", outline="")
            fg = text_hover if hover else text_dim
            if state["maximized"]:
                max_btn.create_rectangle(9, 7, 18, 16, outline=fg, width=1.4)
                max_btn.create_rectangle(7, 10, 16, 19, outline=fg, width=1.4, fill=preview_bg)
            else:
                max_btn.create_rectangle(7, 7, 19, 19, outline=fg, width=1.4)

        draw_max_btn()

        def toggle_maximize(event=None):
            cancel_anim()
            if not state["maximized"]:
                state["snug_geom"] = (state["cur_w"], state["cur_h"],
                                       state["win_x"], state["win_y"])
                mw, mh = compute_maxed()
                mx, my = state["_wa_left"], state["_wa_top"]
                win.geometry(f"{mw}x{mh}+{mx}+{my}")
                state["cur_w"], state["cur_h"] = mw, mh
                state["win_x"], state["win_y"] = mx, my
                state["maximized"] = True
            else:
                w_, h_, x_, y_ = state["snug_geom"]
                win.geometry(f"{w_}x{h_}+{x_}+{y_}")
                state["cur_w"], state["cur_h"] = w_, h_
                state["win_x"], state["win_y"] = x_, y_
                state["maximized"] = False
            state["ox"] = 0.0
            state["oy"] = 0.0
            state["fit_scale"] = calc_fit_scale(state["cur_w"], state["cur_h"])
            state["scale"] = state["fit_scale"]
            draw_max_btn()
            render()

        max_btn.bind("<Button-1>", toggle_maximize)
        max_btn.bind("<Enter>", lambda e: draw_max_btn(True))
        max_btn.bind("<Leave>", lambda e: draw_max_btn(False))

        close_btn = tk.Label(win, text="\u2715", fg=text_dim, bg=preview_bg,
                              font=(FONT, 14), cursor="hand2")
        close_btn.place(relx=1.0, x=-40, y=12)
        close_btn.bind("<Button-1>", lambda e: close_with_zoom())
        close_btn.bind("<Enter>", lambda e: close_btn.config(fg=text_hover))
        close_btn.bind("<Leave>", lambda e: close_btn.config(fg=text_dim))

        hint = tk.Label(win, text="点击图片可放大 / 缩小 \u00b7 滚轮缩放 \u00b7 拖动空白移动窗口 \u00b7 Esc 关闭",
                        fg=text_dim, bg=preview_bg, font=(FONT, 9))
        hint.place(relx=0.5, rely=1.0, y=-20, anchor="center")

        def on_image(x, y):
            bbox = canvas.bbox("img")
            return bbox and bbox[0] <= x <= bbox[2] and bbox[1] <= y <= bbox[3]

        def toggle_zoom():
            cancel_anim()
            if state["scale"] <= state["fit_scale"] + 0.001:
                target = 1.0 if 1.0 > state["fit_scale"] else state["fit_scale"] * 2.2
            else:
                target = state["fit_scale"]
            animate_to_scale(target)

        def on_press(event):
            state["has_press"] = True
            state["press_xy"] = (event.x, event.y)
            state["press_root_xy"] = (event.x_root, event.y_root)
            state["press_on_img"] = on_image(event.x, event.y)
            state["start_offset"] = (state["ox"], state["oy"])
            state["start_win_xy"] = (state["win_x"], state["win_y"])
            state["dragging"] = False

        def on_drag(event):
            if not state["has_press"]:
                return
            dx = event.x - state["press_xy"][0]
            dy = event.y - state["press_xy"][1]
            if abs(dx) > 4 or abs(dy) > 4:
                state["dragging"] = True
            if not state["dragging"]:
                return
            if state["press_on_img"]:
                if state["scale"] > state["fit_scale"] + 0.001:
                    state["ox"] = state["start_offset"][0] + dx
                    state["oy"] = state["start_offset"][1] + dy
                    render()
            elif not state["maximized"]:
                rdx = event.x_root - state["press_root_xy"][0]
                rdy = event.y_root - state["press_root_xy"][1]
                state["win_x"] = state["start_win_xy"][0] + rdx
                state["win_y"] = state["start_win_xy"][1] + rdy
                win.geometry(f"+{state['win_x']}+{state['win_y']}")

        def on_release(event):
            if not state["has_press"]:
                return
            was_drag = state["dragging"]
            state["dragging"] = False
            state["has_press"] = False
            if was_drag:
                return
            if state["press_on_img"]:
                toggle_zoom()
            else:
                close_with_zoom()

        def on_wheel(event):
            cancel_anim()
            factor = 1.15 if event.delta > 0 else (1 / 1.15)
            target = state["scale"] * factor
            target = max(state["fit_scale"] * 0.7, min(target, state["fit_scale"] * 8))
            animate_to_scale(target)

        canvas.bind("<ButtonPress-1>", on_press)
        canvas.bind("<B1-Motion>", on_drag)
        canvas.bind("<ButtonRelease-1>", on_release)
        canvas.bind("<MouseWheel>", on_wheel)
        win.bind("<Escape>", lambda e: close_with_zoom())
        win.grab_set()
        win.focus_force()

        win.deiconify()
        zoom_in(0)

    def _on_paste(self, event=None):
        """拦截 Ctrl+V：如果剪贴板有图片则插入图片，否则正常粘贴文本"""
        try:
            img = ImageGrab.grabclipboard()
            if img is not None:
                # 限制最大宽度
                if img.width > 400:
                    ratio = 400 / img.width
                    img = img.resize((400, int(img.height * ratio)), Image.LANCZOS)
                # 转 base64
                buf = io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode()
                img_id = str(uuid.uuid4())[:8]
                if not hasattr(self, '_images'):
                    self._images = {}
                self._images[img_id] = b64
                # 显示
                tk_img = ImageTk.PhotoImage(img)
                img_tk_name = self._text.image_create(tk.INSERT, image=tk_img)
                self._text.insert(tk.INSERT, "\n")
                # 映射 tk 内部名称到 UUID
                if not hasattr(self, '_img_name_map'):
                    self._img_name_map = {}
                self._img_name_map[img_tk_name] = img_id
                # 保持引用
                if not hasattr(self, '_tk_images'):
                    self._tk_images = []
                self._tk_images.append(tk_img)
                self._dirty = True
                if self._tid:
                    self.root.after_cancel(self._tid)
                self._tid = self.root.after(1200, self._auto_save)
                return "break"
        except Exception:
            pass
        # 没有图片，正常文本粘贴（不做任何处理，让默认行为执行）

    def _on_type(self, event=None):
        self._dirty = True
        if self._tid:
            self.root.after_cancel(self._tid)
        self._tid = self.root.after(1200, self._auto_save)

    def _auto_save(self):
        if self._dirty and self.current_index is not None:
            self._save()
            self._populate()
        self._tid = None

    def _save_if_dirty(self):
        if self._dirty and self.current_index is not None:
            self._save()

    def refresh(self):
        self.notes = list(self.widget.notes)
        self._populate()

    def show(self):
        self._populate()
        # 平时不常驻置顶，但打开的瞬间短暂置顶一下，保证能真正跳到
        # 当前焦点应用前面（光用 lift() 有时押不过别的窗口），
        # 过一下子就取消，不会一直挡在别的应用上面。
        self.root.attributes("-topmost", True)
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()
        self.root.after(200, lambda: self.root.attributes("-topmost", False))

    def collapse(self):
        self._save_if_dirty()
        self.root.withdraw()
        self.widget.show_widget()


if __name__ == "__main__":
    DeskWidget().run()
