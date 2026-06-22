import sys
import time

print("正在启动重型测试任务...")
print("本任务将产生大量日志以测试物理文件同步功能。")
print("开始执行循环输出...")
sys.stdout.flush()

for i in range(1, 301):
    time.sleep(0.01)
    if i % 100 == 0:
        print(f"--- 已完成 {i} 条日志输出 ---")
        sys.stdout.flush()
