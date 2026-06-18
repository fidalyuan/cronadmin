import subprocess
import sys

def show_menu():
    # 定义 whiptail 菜单命令
    # 语法: whiptail --title "标题" --menu "说明" 高度 宽度 菜单项高度 [标签 选项]...
    cmd = [
        "whiptail", "--title", "脚本执行管理器", 
        "--menu", "请使用鼠标或上下键选择一个操作:", "15", "60", "4",
        "1", "运行系统更新",
        "2", "查看磁盘空间",
        "3", "重启 Cron 服务",
        "4", "退出"
    ]
    
    # 运行 whiptail 并捕获用户的标准错误输出（whiptail 的选择结果输出到 stderr）
    result = subprocess.run(cmd, stderr=subprocess.PIPE, text=True)
    
    # 如果用户点击了 Cancel(取消) 或按了 ESC，返回码不为 0
    if result.returncode != 0:
        return None
        
    return result.stderr.strip()

def main():
    choice = show_menu()
    
    if not choice:
        print("操作已取消。")
        sys.exit(0)
        
    print(f"开始执行选项 [{choice}] 对应的脚本...\n")
    
    # 根据编号执行 Shell 脚本
    if choice == "1":
        subprocess.run(["sudo", "apt", "update"])
    elif choice == "2":
        subprocess.run(["df", "-h"])
    elif choice == "3":
        subprocess.run(["sudo", "systemctl", "restart", "cron"])
    elif choice == "4":
        print("已退出。")

if __name__ == "__main__":
    main()
