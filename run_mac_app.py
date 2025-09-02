#!/usr/bin/env python3
"""
File2LongImage macOS应用启动器
选择运行不同版本
"""

import sys
import os

def main():
    print("=" * 60)
    print("File2LongImage macOS 应用启动器")
    print("=" * 60)
    print("\n请选择要运行的版本：\n")
    print("1. 📱 标准版 (mac_app.py)")
    print("   - 增强进度显示")
    print("   - 步骤级反馈")
    print("   - 实时时间更新")
    print("")
    print("2. 🚀 并行版 (mac_app_parallel.py) [推荐]")
    print("   - 多文件并行处理")
    print("   - 独立进度控制")
    print("   - 性能提升2-3倍")
    print("")
    print("3. ⚡ 优化版 (mac_app_optimized.py)")
    print("   - 极速图片合并")
    print("   - 智能压缩策略")
    print("")
    print("q. 退出")
    print("-" * 60)
    
    choice = input("\n请输入选择 (1/2/3/q): ").strip()
    
    if choice == '1':
        print("\n启动标准版...")
        import mac_app
        from tkinter import Tk
        root = Tk()
        app = mac_app.File2LongImageApp(root)
        root.mainloop()
        
    elif choice == '2':
        print("\n启动并行版...")
        import mac_app_parallel
        mac_app_parallel.main()
        
    elif choice == '3':
        print("\n优化版仅包含核心优化函数，请使用标准版或并行版")
        print("优化已集成到 mac_app.py 中")
        
    elif choice.lower() == 'q':
        print("\n再见！")
        sys.exit(0)
        
    else:
        print("\n无效选择，默认启动并行版...")
        import mac_app_parallel
        mac_app_parallel.main()

if __name__ == "__main__":
    main()