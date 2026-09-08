import ctypes
from ctypes import wintypes

# Mouse movement flags
INPUT_MOUSE, MOUSEEVENTF_MOVE = 0, 0x0001
MOUSEEVENTF_ABSOLUTE, MOUSEEVENTF_VIRTUALDESK = 0x8000, 0x4000


class MOUSEINPUT(ctypes.Structure):
    _fields_ = [("dx", wintypes.LONG), ("dy", wintypes.LONG),
                ("mouseData", wintypes.DWORD), ("dwFlags", wintypes.DWORD),
                ("time", wintypes.DWORD), ("dwExtraInfo", ctypes.POINTER(wintypes.ULONG))]


class INPUT(ctypes.Structure):
    class _INPUT(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT),]
    _anonymous_, _fields_ = ("_input",), [("type", wintypes.DWORD), ("_input", _INPUT),]


# Mouse movement method
def move(x: int, y: int):
    user32 = ctypes.windll.user32
    screen_width = user32.GetSystemMetrics(0)
    screen_height = user32.GetSystemMetrics(1)
    absolute_x = round(x * 65535 / (screen_width - 1))
    absolute_y = round(y * 65535 / (screen_height - 1))

    extra = ctypes.c_ulong(0)
    mouse_input = MOUSEINPUT(dx=absolute_x, dy=absolute_y, mouseData=0, time=0,
                             dwFlags=MOUSEEVENTF_MOVE | MOUSEEVENTF_ABSOLUTE,
                             dwExtraInfo=ctypes.pointer(extra))
    input_event = INPUT(type=INPUT_MOUSE, mi=mouse_input,)
    if user32.SendInput(1, ctypes.byref(input_event), ctypes.sizeof(INPUT)) != 1:
        raise ctypes.WinError()
