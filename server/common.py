import sys
import os
import socket
def disable_quick_edit_if_win():
    """
    仅在 Windows 下运行：禁用控制台的快速编辑模式，
    防止点击控制台导致程序挂起。
    """
    if sys.platform == 'win32':
        try:
            import ctypes
            kernel32 = ctypes.windll.kernel32
            
            # 获取标准输入句柄
            hStdIn = kernel32.GetStdHandle(-10)
            
            # 获取当前控制台模式
            mode = ctypes.c_ulong()
            kernel32.GetConsoleMode(hStdIn, ctypes.byref(mode))
            
            # 定义 Quick Edit Mode 标志位 (0x0040)
            ENABLE_QUICK_EDIT_MODE = 0x0040
            
            # 移除 Quick Edit Mode 标志
            new_mode = mode.value & ~ENABLE_QUICK_EDIT_MODE
            
            # 设置新的控制台模式
            kernel32.SetConsoleMode(hStdIn, new_mode)
        except Exception as e:
            print(f"无法禁用快速编辑模式: {e}")
def get_local_ip():
    """获取局域网IP"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except:
        return "127.0.0.1"
def get_app_path():
    """
    获取应用程序的根目录路径。
    兼容开发环境（python main.py）和打包环境（PyInstaller）。
    """
    if getattr(sys, 'frozen', False):
        # 如果是 PyInstaller 打包后的环境
        # sys.executable 指向的是可执行文件的绝对路径
        application_path = os.path.dirname(os.path.abspath(sys.executable))
        # 注意：如果你在 macOS 上打成了 .app 包 (windowed mode)，
        # executable 可能在 MyArgs.app/Contents/MacOS/ 里面。
        # 如果你的资源文件放在 .app 外面，可能需要再往上 os.path.dirname 一两次。
        # 但如果是标准的文件夹模式 (--onedir)，上面这行就足够了。
        return application_path
    else:
        # 开发环境
        return os.path.dirname(os.path.abspath(__file__))