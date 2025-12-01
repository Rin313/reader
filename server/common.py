import sys

def disable_quick_edit():
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