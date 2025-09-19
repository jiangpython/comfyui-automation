#!/usr/bin/env python3
"""
测试main.py的简单版本，检查基本导入
"""

import sys
from pathlib import Path

def test_imports():
    print("🧪 测试主程序模块导入")

    # 添加src目录到Python路径
    sys.path.append(str(Path(__file__).parent / 'src'))

    try:
        print("1. 测试基础模块导入...")
        import logging
        import json
        import argparse
        print("   ✅ 基础模块导入成功")
        
        print("2. 测试YAML模块...")
        try:
            import yaml
            print("   ✅ PyYAML模块可用")
        except ImportError:
            print("   ❌ PyYAML模块未安装")
            print("   💡 请运行: pip install PyYAML")
            return False
        
        print("3. 测试批量处理器导入...")
        try:
            from src.batch_processor import BatchProcessor
            print("   ✅ BatchProcessor导入成功")
        except Exception as e:
            print(f"   ❌ BatchProcessor导入失败: {e}")
            return False
        
        print("4. 测试分析管理器导入...")
        try:
            from src.analysis_integration import AnalysisManager
            print("   ✅ AnalysisManager导入成功")
        except Exception as e:
            print(f"   ❌ AnalysisManager导入失败: {e}")
            return False
        
        print("5. 测试主系统类...")
        try:
            # 只测试导入，不初始化
            from main import ComfyUIAutomationSystem
            print("   ✅ ComfyUIAutomationSystem导入成功")
        except Exception as e:
            print(f"   ❌ ComfyUIAutomationSystem导入失败: {e}")
            return False
        
        print("\n🎉 所有模块导入测试成功！")
        print("📝 可以使用以下命令启动主程序:")
        print("   python main.py --help")
        print("   python main.py --interactive")
        return True

    except Exception as e:
        print(f"❌ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    test_imports()