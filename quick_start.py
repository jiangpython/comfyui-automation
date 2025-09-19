#!/usr/bin/env python3
"""
ComfyUI 自动化系统 - 快速启动脚本
提供最简单的使用方式
"""

import sys
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / 'src'))

def quick_single_subject():
    """快速单主题生成"""
    print("🎯 快速单主题生成")
    print("="*40)
    
    subject = input("请输入主题描述: ").strip()
    if not subject:
        print("❌ 主题不能为空")
        return
    
    try:
        count_str = input("生成数量 (默认10): ").strip()
        count = int(count_str) if count_str else 10
    except ValueError:
        count = 10
    
    print(f"\n🚀 开始处理: {subject}")
    print(f"📊 生成数量: {count}")
    print("⏳ 正在处理，请稍候...")
    
    # 使用main.py处理
    import subprocess
    cmd = [
        sys.executable, "main.py",
        "--subject", subject,
        "--count", str(count),
        "--analyze"
    ]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 处理完成!")
        print("📱 查看结果: 打开 output/gallery.html")
    except subprocess.CalledProcessError:
        print("❌ 处理失败，请检查系统状态")

def quick_batch_prompts():
    """快速批量处理"""
    print("📦 快速批量处理")
    print("="*40)
    
    prompts = []
    print("请输入提示词，每行一个，空行结束:")
    
    while True:
        prompt = input(f"提示词 #{len(prompts) + 1}: ").strip()
        if not prompt:
            break
        prompts.append(prompt)
    
    if not prompts:
        print("❌ 没有输入任何提示词")
        return
    
    print(f"\n🚀 开始批量处理")
    print(f"📊 提示词数量: {len(prompts)}")
    print("⏳ 正在处理，请稍候...")
    
    # 使用main.py处理
    import subprocess
    cmd = [sys.executable, "main.py", "--prompts"] + prompts + ["--analyze"]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 批量处理完成!")
        print("📱 查看结果: 打开 output/gallery.html")
    except subprocess.CalledProcessError:
        print("❌ 处理失败，请检查系统状态")

def quick_analysis():
    """快速分析"""
    print("📊 快速数据分析")
    print("="*40)
    
    import subprocess
    cmd = [sys.executable, "analysis_cli.py", "analyze"]
    
    try:
        subprocess.run(cmd, check=True)
        print("\n🎉 分析完成!")
        print("📄 查看报告: output/analysis/ 目录")
    except subprocess.CalledProcessError:
        print("❌ 分析失败，请检查数据")

def main():
    """主菜单"""
    print("\n🎨 ComfyUI 自动化系统 - 快速启动")
    print("="*50)
    print("这是最简单的使用方式，适合新手快速上手")
    print("="*50)
    
    while True:
        try:
            print("\n📋 请选择操作:")
            print("1. 🎯 单主题生成变体 (推荐新手)")
            print("2. 📦 批量提示词处理")  
            print("3. 📊 数据分析")
            print("4. 🖼️ 查看画廊")
            print("5. 🧪 系统测试")
            print("6. ⚙️ 完整功能 (main.py)")
            print("0. 👋 退出")
            
            choice = input("\n请选择 (0-6): ").strip()
            
            if choice == '0':
                print("👋 再见!")
                break
            elif choice == '1':
                quick_single_subject()
            elif choice == '2':
                quick_batch_prompts()
            elif choice == '3':
                quick_analysis()
            elif choice == '4':
                print("🌐 打开画廊...")
                import subprocess
                gallery_path = Path("output/gallery.html")
                if gallery_path.exists():
                    if sys.platform.startswith('win'):
                        subprocess.run(["start", str(gallery_path)], shell=True)
                    elif sys.platform.startswith('darwin'):
                        subprocess.run(["open", str(gallery_path)])
                    else:
                        subprocess.run(["xdg-open", str(gallery_path)])
                    print("✅ 已在浏览器中打开画廊")
                else:
                    print("❌ 画廊文件不存在，请先运行生成任务")
            elif choice == '5':
                print("🧪 运行系统测试...")
                import subprocess
                subprocess.run([sys.executable, "simple_test.py"])
            elif choice == '6':
                print("🚀 启动完整功能...")
                import subprocess
                subprocess.run([sys.executable, "main.py", "--interactive"])
            else:
                print("❌ 无效选择，请重试")
                
        except KeyboardInterrupt:
            print("\n👋 用户取消，退出程序")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

if __name__ == '__main__':
    main()