#!/usr/bin/env python3
import subprocess
from simple_term_menu import TerminalMenu

def main():
    # 1. 定义你的菜单选项（对应不同的 Shell 脚本或参数）
    options = [
        "[1] 运行系统更新 (update.sh)",
        "[2] 查看磁盘空间 (df -h)",
        "[3] 重启系统服务 (systemctl)",
        "[4] 退出程序"
    ]
    
    # 2. 初始化菜单，启用鼠标支持 (show_shortcut_hints 显示快捷键提示)
    terminal_menu = TerminalMenu(
        options, 
        title="请使用 ⬆️⬇️ 键或鼠标滚轮选择要执行的脚本，点击或回车确认：",
        menu_cursor="👉 ",
        menu_cursor_style=("fg_green", "bold"),
        menu_highlight_style=("bg_black", "fg_cyan"),
        # === 添加以下三个参数来解决刷屏问题 ===
        # === 彻底禁用鼠标跟踪，只用键盘，绝不会再刷屏 ===
        disable_mouse=True
    )
    
    # 3. 显示菜单并获取用户选择的索引
    menu_entry_index = terminal_menu.show()
    
    if menu_entry_index is None:
        print("操作已取消")
        return

    print(f"你选择的是: {options[menu_entry_index]}\n")

    # 4. 根据选择执行相应的 Shell 命令或脚本
    try:
        if menu_entry_index == 0:
            # 示例：运行一个实际的 shell 脚本
            # subprocess.run(["/bin/bash", "./update.sh"])
            subprocess.run(["sudo", "apt", "update"], check=True)
            
        elif menu_entry_index == 1:
            # 示例：直接运行 shell 命令
            subprocess.run(["df", "-h"], check=True)
            
        elif menu_entry_index == 2:
            subprocess.run(["systemctl", "status", "cron"], check=True)
            
        elif menu_entry_index == 3:
            print("再见！")
            
    except subprocess.CalledProcessError as e:
        print(f"\n❌ 脚本执行出错: {e}")

if __name__ == "__main__":
    main()
