# DiktovkaMac – русский голосовой ввод в любое окно на Mac.
# Самостоятельный продукт для macOS: горячая клавиша, оверлей-шарик, вставка в любое окно.
# F8 – начать запись, F8 ещё раз – распознать и вставить текст туда, где стоит курсор.
# Распознаёт локально: Whisper (faster-whisper), на Mac – на процессоре (Core ML/ANE нет,
# но Apple Silicon справляется быстро).

import os, sys, json, time, threading, queue, subprocess, traceback

BASE = os.path.dirname(os.path.abspath(__file__))
os.environ.setdefault("HF_HOME", os.path.join(BASE, "models"))
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")
import warnings; warnings.filterwarnings("ignore")

LOG = os.path.join(BASE, "DiktovkaMac.log")
CFG_PATH = os.path.join(BASE, "config.json")
PID_PATH = os.path.join(BASE, "DiktovkaMac.pid")

DEFAULT_CFG = {
    "hotkey": "eisu",            # 英数 – клавиша слева от пробела на японской JIS-клавиатуре.
                                 # Другие варианты: "kana" (かな), "alt+space", "cmd+shift+d"…
                                 # НЕ f7–f12: на Mac это медиа-клавиши, до программ не доходят.
    "language": "ru",
    "model": "large-v3-turbo",   # на слабом Mac можно "small" (гораздо быстрее, чуть хуже качество)
    "device": "auto",            # auto / cpu (на macOS всегда cpu)
    "beep": False,               # звук при старте и остановке записи (выкл.)
    "auto_send": False,          # true – после вставки нажать Return (сразу отправить)
    "prompt": "Привет. Это голосовое сообщение на русском языке, с точками и запятыми.",
}


def log(*a):
    try:
        with open(LOG, "a", encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d %H:%M:%S ") + " ".join(str(x) for x in a) + "\n")
    except Exception:
        pass


def load_cfg():
    cfg = dict(DEFAULT_CFG)
    if os.path.exists(CFG_PATH):
        try:
            with open(CFG_PATH, encoding="utf-8-sig") as f:
                cfg.update(json.load(f))
        except Exception as e:
            log("config.json не прочитан:", e)
    else:
        with open(CFG_PATH, "w", encoding="utf-8") as f:
            json.dump(DEFAULT_CFG, f, ensure_ascii=False, indent=2)
    return cfg


# ---------- один экземпляр ----------

def single_instance():
    try:
        if os.path.exists(PID_PATH):
            with open(PID_PATH) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)
            return False  # уже работает
    except (ValueError, ProcessLookupError):
        pass
    except PermissionError:
        return False
    with open(PID_PATH, "w") as f:
        f.write(str(os.getpid()))
    return True


# ---------- модель ----------

def load_model(cfg):
    from faster_whisper import WhisperModel
    dev = cfg.get("device", "auto")
    if dev in ("auto", "mps"):
        try:  # чип Apple (MPS) – в 2 раза быстрее процессора
            m = WhisperModel(cfg["model"], device="mps", compute_type="float16")
            warm(m, cfg)
            return m, "чип Apple (MPS)"
        except Exception as e:
            log("MPS не завелся, перехожу на процессор:", e)
    threads = max(2, (os.cpu_count() or 8) // 2)
    m = WhisperModel(cfg["model"], device="cpu", compute_type="int8", cpu_threads=threads)
    return m, "процессор (Apple Silicon)"


def warm(model, cfg):
    import numpy as np
    list(model.transcribe(np.zeros(16000, dtype="float32"), language=cfg["language"])[0])


def transcribe(model, audio, cfg):
    segs, _ = model.transcribe(
        audio, language=cfg["language"], beam_size=5, vad_filter=True,
        initial_prompt=cfg.get("prompt") or None, condition_on_previous_text=False,
    )
    return " ".join(s.text.strip() for s in segs).strip()


# ---------- горячая клавиша (Carbon RegisterEventHotKey через ctypes –
# работает без прав «Универсальный доступ», в отличие от глобальных мониторов) ----------

# keycode-ы macOS (клавиатура ANSI): f1..f12 и частые клавиши
KEYCODES = {
    # японская JIS-клавиатура: клавиши вокруг пробела
    "eisu": 102,                 # 英数 – слева от пробела
    "kana": 104,                 # かな – справа от пробела
    # латиница/цифры (раскладка ANSI)
    "f1": 122, "f2": 120, "f3": 99, "f4": 118, "f5": 96, "f6": 97,
    "f7": 98, "f8": 100, "f9": 101, "f10": 109, "f11": 103, "f12": 111,
    "space": 49, "tab": 48, "enter": 36, "return": 36, "escape": 53,
    "home": 115, "end": 119, "pageup": 116, "pagedown": 121,
    "insert": 114, "delete": 117, "forwarddelete": 117, "help": 114,
    "up": 126, "down": 125, "left": 123, "right": 124,
    "a": 0, "b": 11, "c": 8, "d": 2, "e": 14, "f": 3, "g": 5, "h": 4, "i": 34,
    "j": 38, "k": 40, "l": 37, "m": 46, "n": 45, "o": 31, "p": 35, "q": 12,
    "r": 15, "s": 1, "t": 17, "u": 32, "v": 9, "w": 13, "x": 7, "y": 16, "z": 6,
    "0": 29, "1": 18, "2": 19, "3": 20, "4": 21, "5": 23, "6": 22, "7": 26,
    "8": 28, "9": 25,
}
MODS = {"cmd": 0x100, "command": 0x100, "shift": 0x200, "opt": 0x800,
        "option": 0x800, "alt": 0x800, "ctrl": 0x1000, "control": 0x1000}

K_EVENT_CLASS_KEYBOARD = int.from_bytes(b"kbyn", "big")
K_EVENT_HOT_KEY_PRESSED = 5


def parse_hotkey(s):
    mods, keycode, cg_mods = 0, None, 0
    for part in s.lower().replace(" ", "").split("+"):
        if not part:
            continue
        if part in MODS:
            mods |= MODS[part]
            cg_mods |= CG_MODS[part]
        elif part in KEYCODES:
            keycode = KEYCODES[part]
        else:
            raise ValueError(f"Не понял клавишу «{part}» в config.json")
    if keycode is None:
        raise ValueError(f"Не понял клавишу «{s}» в config.json")
    return mods, keycode, cg_mods


# модификаторы в терминах CGEvent (для CGEventTap)
CG_MODS = {"cmd": 1 << 20, "command": 1 << 20, "shift": 1 << 17, "opt": 1 << 19,
           "option": 1 << 19, "alt": 1 << 19, "ctrl": 1 << 18, "control": 1 << 18}
CG_RELEVANT = CG_MODS["cmd"] | CG_MODS["shift"] | CG_MODS["opt"] | CG_MODS["ctrl"]

_TAP = {"tap": None, "keycode": None, "mods": 0, "cb": None}


def _try_install_tap(keycode, cg_mods, callback):
    """CGEventTap: ловит ЛЮБЫЕ клавиши (включая 英数/かな), но нужен «Универсальный доступ»."""
    from Quartz import (CGEventTapCreate, CGEventTapEnable, CFMachPortCreateRunLoopSource,
                        CFRunLoopGetCurrent, CFRunLoopAddSource, kCFRunLoopCommonModes,
                        kCGSessionEventTap, kCGHeadInsertEventTap, kCGEventTapOptionDefault,
                        kCGEventKeyDown, CGEventGetIntegerValueField, CGEventGetFlags,
                        kCGKeyboardEventKeycode, kCGKeyboardEventAutorepeat)

    def handler(proxy, etype, event, refcon):
        try:
            if etype == kCGEventKeyDown:
                # игнорируем автоповтор удерживаемой клавиши – иначе запись дёргается вкл/выкл
                if CGEventGetIntegerValueField(event, kCGKeyboardEventAutorepeat):
                    return None
                if CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode) == _TAP["keycode"]:
                    if (CGEventGetFlags(event) & CG_RELEVANT) == _TAP["mods"]:
                        _TAP["cb"]()
                        return None  # проглотить: не давать системе переключать раскладку
        except Exception:
            log(traceback.format_exc())
        return event

    mask = (1 << kCGEventKeyDown)
    tap = CGEventTapCreate(kCGSessionEventTap, kCGHeadInsertEventTap,
                           kCGEventTapOptionDefault, mask, handler, None)
    if tap is None:
        return False  # нет права «Универсальный доступ»
    src = CFMachPortCreateRunLoopSource(None, tap, 0)
    CFRunLoopAddSource(CFRunLoopGetCurrent(), src, kCFRunLoopCommonModes)
    CGEventTapEnable(tap, True)
    _TAP.update(tap=tap, keycode=keycode, mods=cg_mods, cb=callback)
    log("горячая клавиша: CGEventTap")
    return True


def keep_tap_enabled():
    """macOS отключает тап, если приложение подвисло – включаем обратно."""
    tap = _TAP.get("tap")
    if tap is None:
        return
    try:
        from Quartz import CGEventTapIsEnabled, CGEventTapEnable
        if not CGEventTapIsEnabled(tap):
            CGEventTapEnable(tap, True)
    except Exception:
        pass


def upgrade_hotkey_if_possible(hotkey_str, callback):
    """Если право «Универсальный доступ» выдали уже после запуска – ставим тап."""
    if _TAP["tap"] is not None or not accessibility_granted():
        return
    try:
        _, keycode, cg_mods = parse_hotkey(hotkey_str)
        _try_install_tap(keycode, cg_mods, callback)
    except Exception:
        log(traceback.format_exc())


def _install_carbon_hotkey(hotkey_str, callback):
    import ctypes
    from ctypes import (CDLL, CFUNCTYPE, Structure, c_long, c_uint32, c_void_p,
                        byref, cast, POINTER)

    carbon = CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")
    # явные сигнатуры – иначе ctypes обрезает 64-битные указатели до 32 бит
    carbon.GetApplicationEventTarget.restype = c_void_p
    carbon.GetApplicationEventTarget.argtypes = []
    carbon.InstallEventHandler.restype = c_long
    carbon.InstallEventHandler.argtypes = [c_void_p, c_void_p, c_uint32,
                                           POINTER(c_uint32), c_void_p, POINTER(c_void_p)]
    carbon.RegisterEventHotKey.restype = c_long
    carbon.RegisterEventHotKey.argtypes = [c_uint32, c_uint32, c_void_p,
                                           c_void_p, c_uint32, POINTER(c_void_p)]

    class EventHotKeyID(Structure):
        _fields_ = [("signature", c_uint32), ("id", c_uint32)]

    mods, keycode, _ = parse_hotkey(hotkey_str)
    HANDLER = CFUNCTYPE(c_long, c_void_p, c_void_p, c_void_p)
    hotkey_ref = c_void_p()

    def _handler(next_handler, event, user_data):
        try:
            callback()
        except Exception:
            log(traceback.format_exc())
        return 0  # noErr

    cb = HANDLER(_handler)  # держим ссылку, иначе GC соберёт
    install_hotkey._cb = cb

    target = carbon.GetApplicationEventTarget()
    spec = (c_uint32 * 2)(K_EVENT_CLASS_KEYBOARD, K_EVENT_HOT_KEY_PRESSED)
    out_handler = c_void_p()
    status = carbon.InstallEventHandler(target, cast(cb, c_void_p), 1,
                                        spec, None, byref(out_handler))
    if status != 0:
        raise RuntimeError(f"InstallEventHandler вернул {status}")
    hotkey_id = EventHotKeyID(int.from_bytes(b"dikt", "big"), 1)
    status = carbon.RegisterEventHotKey(keycode, mods, byref(hotkey_id), target, 0,
                                        byref(hotkey_ref))
    if status != 0:
        raise RuntimeError(f"RegisterEventHotKey вернул {status} – клавиша «{hotkey_str}» занята?")
    log("горячая клавиша: Carbon (без прав на спец-клавиши JIS)")


def install_hotkey(hotkey_str, callback):
    if accessibility_granted():
        try:
            if _try_install_tap(*parse_hotkey(hotkey_str)[1:], callback):
                return
        except Exception:
            log(traceback.format_exc())
    _install_carbon_hotkey(hotkey_str, callback)


# ---------- шарик-индикатор (NSWindow, не забирает фокус) ----------
#
# Вместо текстовой полосы: небольшой 3D-шарик над полем ввода.
# Запись – переливание фиолетовый ↔ розовый (пульс под речь).
# Стоп – вспышка зелёно-синим и плавное исчезновение. Больше никаких полос.

import math

import objc
from AppKit import NSObject, NSView

PINK = (0.98, 0.35, 0.65)    # розовый сегмент спиннера (вместо чёрного у Kimi)
TEAL = (0.13, 0.83, 0.72)    # зелёно-синий «готово»
RED = (0.94, 0.27, 0.27)     # ошибка


def _lerp(a, b, t):
    return tuple(x + (y - x) * t for x, y in zip(a, b))


class _Animator(NSObject):
    """Тикает в главном цикле Cocoa (60 fps) и двигает анимацию шарика."""

    def initWithOverlay_(self, ov):
        self = objc.super(_Animator, self).init()
        if self is None:
            return None
        self.ov = ov
        return self

    def tick_(self, timer):
        try:
            self.ov._tick()
        except Exception:
            log(traceback.format_exc())


class SphereView(NSView):
    def drawRect_(self, rect):
        try:
            from AppKit import (NSColor, NSBezierPath, NSGradient, NSGraphicsContext,
                                NSMakeRect, NSMakePoint)
            import math as _m
            ov = self._ov
            r = ov.BALL * ov.scale
            cx = cy = ov.SIZE / 2.0
            rgb = ov.rgb
            seg = NSColor.colorWithCalibratedRed_green_blue_alpha_(rgb[0], rgb[1], rgb[2], 1.0)
            white = NSColor.whiteColor()
            # спиннер как в чате Kimi: сегменты пляжного мяча, крутятся вокруг полюсов
            NSGraphicsContext.saveGraphicsState()
            clip = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(cx - r, cy - r, r * 2, r * 2))
            clip.addClip()
            SEG = 6
            step = 2 * _m.pi / SEG
            for i in range(SEG):
                a1 = ov.rotation + i * step
                a2 = a1 + step
                pth = NSBezierPath.alloc().init()
                pth.moveToPoint_(NSMakePoint(cx, cy + r))            # северный полюс
                pth.curveToPoint_controlPoint1_controlPoint2_(
                    NSMakePoint(cx, cy - r),                          # южный полюс
                    NSMakePoint(cx + 2.2 * r * _m.cos(a1), cy + 0.6 * r),
                    NSMakePoint(cx + 2.2 * r * _m.cos(a1), cy - 0.6 * r))
                pth.curveToPoint_controlPoint1_controlPoint2_(
                    NSMakePoint(cx, cy + r),
                    NSMakePoint(cx + 2.2 * r * _m.cos(a2), cy - 0.6 * r),
                    NSMakePoint(cx + 2.2 * r * _m.cos(a2), cy + 0.6 * r))
                pth.closePath()
                (seg if i % 2 == 0 else white).setFill()
                pth.fill()
            # объём: блик сверху слева
            light = NSGradient.alloc().initWithColors_(
                [white.colorWithAlphaComponent_(0.5), NSColor.clearColor()])
            ball_path = NSBezierPath.bezierPathWithOvalInRect_(NSMakeRect(cx - r, cy - r, r * 2, r * 2))
            light.drawInBezierPath_relativeCenterPosition_(ball_path, NSMakePoint(-0.35, 0.4))
            NSGraphicsContext.restoreGraphicsState()
        except Exception:
            log(traceback.format_exc())


class Overlay:
    SIZE = 72    # окно (включая свечение)
    BALL = 15    # радиус шарика

    def __init__(self):
        from AppKit import (NSWindow, NSColor, NSView, NSMakeRect,
                            NSWindowCollectionBehaviorCanJoinAllSpaces,
                            NSWindowCollectionBehaviorStationary,
                            NSWindowCollectionBehaviorIgnoresCycle,
                            NSFloatingWindowLevel)
        import Quartz
        from Foundation import NSTimer
        screen = Quartz.CGDisplayBounds(Quartz.CGMainDisplayID())
        w = h = self.SIZE
        x = int((screen.size.width - w) / 2)
        y = 230  # над полем ввода, не перекрывает его
        win = NSWindow.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, w, h), 0, 2, False)  # borderless
        win.setLevel_(NSFloatingWindowLevel)
        win.setBackgroundColor_(NSColor.clearColor())
        win.setOpaque_(False)
        win.setAlphaValue_(0.0)
        win.setIgnoresMouseEvents_(True)
        win.setHasShadow_(False)
        win.setCollectionBehavior_(NSWindowCollectionBehaviorCanJoinAllSpaces
                                   | NSWindowCollectionBehaviorStationary
                                   | NSWindowCollectionBehaviorIgnoresCycle)
        self.view = SphereView.alloc().initWithFrame_(NSMakeRect(0, 0, w, h))
        self.view._ov = self
        win.setContentView_(self.view)
        self.win = win

        self.q = queue.Queue()
        self.state = "hidden"       # hidden | shimmer | fade
        self.phase = 0.0
        self.rotation = 0.0
        self.scale = 1.0
        self.alpha = 0.0
        self.rgb = PINK
        self.speed = 1.0
        self.fade_t = 0.0
        self.fade_from = PINK
        self.fade_to = TEAL
        self.shimmer_until = None
        self._last = time.time()
        self._shown = False

        self.animator = _Animator.alloc().initWithOverlay_(self)
        NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            1.0 / 60.0, self.animator, "tick:", None, True)

    # --- вызовы из любого потока ---
    def shimmer(self, speed=1.0, seconds=None):
        """Переливание фиолетовый ↔ розовый. seconds – авто-исчезновение."""
        self.q.put(("shimmer", speed, seconds))

    def finish_fade(self, color=TEAL):
        """Вспышка цветом (по умолчанию зелёно-синим) и исчезновение."""
        self.q.put(("fade", color))

    def error_fade(self):
        self.q.put(("fade", RED))

    def hide(self):
        self.q.put(("hide",))

    def _place(self):
        """Ставим окно в центр того экрана, где сейчас мышь (там и поле ввода),
        заново при каждом показе. Координаты пишем в лог для диагностики."""
        from AppKit import NSScreen, NSEvent, NSMakeRect
        from Foundation import NSMouseInRect
        loc = NSEvent.mouseLocation()
        screen = None
        for s in NSScreen.screens():
            if NSMouseInRect(loc, s.frame(), False):
                screen = s
                break
        if screen is None:
            screen = NSScreen.mainScreen() or NSScreen.screens()[0]
        vf = screen.visibleFrame()
        w = h = self.SIZE
        x = vf.origin.x + (vf.size.width - w) / 2
        y = vf.origin.y + 9  # самый низ экрана (центр шарика ~45 pt от нижнего края)
        log("шарик: x=%d y=%d экран=%dx%d" % (x, y, vf.size.width, vf.size.height))
        self.win.setFrame_display_(NSMakeRect(x, y, w, h), True)

    # --- тикает в главном потоке ---
    def _tick(self):
        now = time.time()
        dt = min(now - self._last, 0.1)
        self._last = now
        try:
            while True:
                cmd = self.q.get_nowait()
                if cmd[0] == "shimmer":
                    self.state = "shimmer"
                    self.speed = cmd[1]
                    self.shimmer_until = now + cmd[2] if cmd[2] else None
                elif cmd[0] == "fade":
                    self.state = "fade"
                    self.fade_from = self.rgb
                    self.fade_to = cmd[1]
                    self.fade_t = 0.0
                elif cmd[0] == "hide":
                    self.state = "hidden"
                    self.alpha = 0.0
        except queue.Empty:
            pass

        if self.state == "shimmer":
            self.phase += dt * self.speed * 3.0
            self.rotation += dt * self.speed * 3.5   # кручение спиннера
            self.rgb = PINK
            self.scale = 1.0 + 0.05 * math.sin(self.phase * 0.6)  # лёгкое «дыхание»
            self.alpha = min(1.0, self.alpha + dt * 5)
            if self.shimmer_until and now >= self.shimmer_until:
                self.state = "fade"
                self.fade_from = self.rgb
                self.fade_to = TEAL
                self.fade_t = 0.0
        elif self.state == "fade":
            self.rotation += dt * 2.0 * max(0.0, 1.0 - self.fade_t)
            self.fade_t += dt / 0.45
            t = min(self.fade_t, 1.0)
            self.rgb = _lerp(self.fade_from, self.fade_to, min(t * 2, 1))
            self.alpha = 1.0 - max(0.0, t * 1.2 - 0.2)
            if t >= 1.0:
                self.state = "hidden"
                self.alpha = 0.0

        if self.alpha > 0.003:
            if not self._shown:
                self._place()  # центр экрана – считаем заново при каждом показе
                self.win.orderFrontRegardless()
                self._shown = True
            if self.win.alphaValue() != self.alpha:
                self.win.setAlphaValue_(self.alpha)
            self.view.setNeedsDisplay_(True)
        elif self._shown:
            self.win.setAlphaValue_(0.0)
            self.win.orderOut_(None)
            self._shown = False


# ---------- звук ----------

def beep(cfg, name):
    if not cfg.get("beep"):
        return
    sounds = {"start": "/System/Library/Sounds/Tink.aiff",
              "stop": "/System/Library/Sounds/Pop.aiff"}
    try:
        subprocess.Popen(["afplay", sounds.get(name, sounds["stop"])],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


# ---------- вставка текста ----------

def frontmost_app():
    from AppKit import NSWorkspace
    return NSWorkspace.sharedWorkspace().frontmostApplication()


def post_cmd_v(also_return=False):
    """Cmd+V (и Return) через CGEvent – нужно право «Универсальный доступ»."""
    from Quartz import (CGEventCreateKeyboardEvent, CGEventSetFlags, CGEventPost,
                        kCGHIDEventTap, kCGEventFlagMaskCommand)

    def key(code, down, cmd=False):
        ev = CGEventCreateKeyboardEvent(None, code, down)
        CGEventSetFlags(ev, kCGEventFlagMaskCommand if cmd else 0)
        CGEventPost(kCGHIDEventTap, ev)

    key(9, True, cmd=True)   # V down
    key(9, False, cmd=True)  # V up
    time.sleep(0.15)
    if also_return:
        key(36, True)   # Return
        key(36, False)


def accessibility_granted():
    from ApplicationServices import AXIsProcessTrusted
    try:
        return bool(AXIsProcessTrusted())
    except Exception:
        return False


def request_accessibility_prompt():
    """Показать системный диалог 'Диктовка хочет управлять этим компьютером'
    – после него программа появится в списке Универсального доступа."""
    from ApplicationServices import AXIsProcessTrustedWithOptions
    try:
        AXIsProcessTrustedWithOptions({"AXTrustedCheckOptionPrompt": True})
    except Exception as e:
        log("запрос доступности:", e)


# ---------- основная логика ----------

class App:
    def __init__(self, cfg, overlay):
        self.cfg = cfg
        self.ov = overlay
        self.model = None
        self.recording = False
        self.busy = False
        self.done_at = 0.0  # момент последнего завершения – для игнора повторного нажатия
        self.chunks = []
        self.stream = None
        self.target = None  # NSRunningApplication, которому будем вставлять текст
        self.lock = threading.Lock()
        self.key = cfg["hotkey"]

    def toggle(self):
        with self.lock:
            if self.busy:
                return
            if self.model is None:
                self.ov.shimmer(seconds=2.0)
                return
            if not self.recording:
                if time.time() - self.done_at < 1.0:
                    return  # повторное нажатие сразу после вставки – игнор
                self.start()
            else:
                self.recording = False
                self.busy = True
                threading.Thread(target=self.finish, daemon=True).start()

    def start(self):
        import sounddevice as sd
        try:
            self.target = frontmost_app()
        except Exception:
            self.target = None
        self.chunks = []

        def cb(indata, frames, t, status):
            self.chunks.append(indata[:, 0].copy())

        try:
            self.stream = sd.InputStream(samplerate=16000, channels=1, dtype="float32", callback=cb)
            self.stream.start()
        except Exception as e:
            log("микрофон:", e)
            self.ov.error_fade()
            return
        self.recording = True
        log("запись началась")
        beep(self.cfg, "start")
        self.ov.shimmer(speed=1.4)

    def finish(self):
        import numpy as np
        try:
            self.stream.stop(); self.stream.close()
            beep(self.cfg, "stop")
            audio = np.concatenate(self.chunks) if self.chunks else np.zeros(0, dtype="float32")
            log(f"запись остановлена, {len(audio)/16000:.1f} с")
            if len(audio) < 16000 * 0.3:
                self.ov.error_fade()
                return
            self.ov.finish_fade()  # гаснем сразу: распознавание идёт молча
            t0 = time.time()
            text = transcribe(self.model, audio, self.cfg)
            log(f"{len(audio)/16000:.1f} с речи → {time.time()-t0:.1f} с: {text}")
            if not text:
                self.ov.error_fade()
                return
            self.paste(text)
        except Exception:
            log(traceback.format_exc())
            self.ov.error_fade()
        finally:
            self.busy = False
            self.done_at = time.time()

    def paste(self, text):
        import pyperclip
        if not accessibility_granted():
            pyperclip.copy(text)
            log("текст скопирован в буфер – нет права Универсальный доступ")
            self.ov.error_fade()
            return
        try:
            old = pyperclip.paste()
        except Exception:
            old = None
        pyperclip.copy(text)
        if self.target is not None:
            try:
                from AppKit import NSApplicationActivateIgnoringOtherApps
                self.target.activateWithOptions_(NSApplicationActivateIgnoringOtherApps)
                time.sleep(0.15)
            except Exception:
                pass
        time.sleep(0.05)
        post_cmd_v(bool(self.cfg.get("auto_send")))
        time.sleep(0.4)
        if old is not None:
            try:
                pyperclip.copy(old)
            except Exception:
                pass

    def load(self):
        try:
            self.ov.shimmer(speed=0.8)
            t0 = time.time()
            self.model, where = load_model(self.cfg)
            log(f"модель {self.cfg['model']} загружена на {where} за {time.time()-t0:.1f} с")
            self.ov.finish_fade()  # вспышка «готово» и исчезновение
        except Exception:
            log(traceback.format_exc())
            self.ov.error_fade()


# ---------- меню-бар (rumps) ----------

def run_tray(app, cfg):
    import rumps

    class DiktovkaApp(rumps.App):
        @rumps.clicked("Записать / остановить")
        def record(self, _):
            app.toggle()

        @rumps.clicked("Настройки (config.json)")
        def open_cfg(self, _):
            subprocess.Popen(["open", CFG_PATH])

        @rumps.clicked("Папка Диктовки")
        def open_dir(self, _):
            subprocess.Popen(["open", BASE])

        @rumps.clicked("Выход")
        def quit_(self, _):
            try:
                os.remove(PID_PATH)
            except OSError:
                pass
            os._exit(0)

    tray_app = DiktovkaApp("🎙", title="", icon=os.path.join(BASE, "icon.png"), quit_button=None)
    tray_app.menu = ["Записать / остановить", "Настройки (config.json)",
                     "Папка Диктовки", None, "Выход"]

    def _pump(_):
        upgrade_hotkey_if_possible(cfg["hotkey"], app.toggle)  # права дали после запуска?
        keep_tap_enabled()                                     # macOS мог отключить тап

    rumps.Timer(_pump, 0.1).start()
    log("запущена, клавиша", cfg["hotkey"])
    tray_app.run()


def main():
    cfg = load_cfg()

    if "--download" in sys.argv:  # скачать модель и проверить, что она работает
        m, where = load_model(cfg)
        warm(m, cfg)
        print(f"OK: модель {cfg['model']} работает, считает на {where}")
        return

    if not single_instance():
        print("Диктовка уже запущена – значок микрофона в меню-баре.")
        return

    ov = Overlay()
    app = App(cfg, ov)
    if not accessibility_granted():
        request_accessibility_prompt()  # диалог + появимся в списке Универсального доступа
    try:
        install_hotkey(cfg["hotkey"], app.toggle)
    except Exception as e:
        log("горячая клавиша:", e)
        ov.error_fade()
    threading.Thread(target=app.load, daemon=True).start()
    run_tray(app, cfg)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        log(traceback.format_exc())
        raise
