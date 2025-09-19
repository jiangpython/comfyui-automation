#!/usr/bin/env python3
"""
检查依赖和模块导入的简单脚本
"""

import sys
from pathlib import Path

def check_dependencies():
    print("检查主程序依赖...")

    # 添加src目录到Python路径
    sys.path.append(str(Path(__file__).parent / 'src'))

    missing_deps = []
    
    # 检查基本Python模块
    basic_modules = ['logging', 'json', 'argparse', 'pathlib', 'datetime', 'typing']
    for module in basic_modules:
        try:
            __import__(module)
            print(f"  [OK] {module}")
        except ImportError:
            print(f"  [FAIL] {module}")
            missing_deps.append(module)
    
    # 检查外部依赖
    external_deps = ['yaml', 'requests', 'jinja2']
    for dep in external_deps:
        try:
            if dep == 'yaml':
                import yaml
            elif dep == 'requests':
                import requests  
            elif dep == 'jinja2':
                import jinja2
            print(f"  [OK] {dep}")
        except ImportError:
            print(f"  [FAIL] {dep} - 需要安装")
            missing_deps.append(dep)
    
    if missing_deps:
        print(f"\n缺少依赖: {', '.join(missing_deps)}")
        print("请运行: pip install -r requirements.txt")
        return False
    else:
        print("\n所有依赖检查通过!")
        
        # 测试主要模块
        print("\n检查主要模块...")
        try:
            from src.batch_processor import BatchProcessor
            print("  [OK] BatchProcessor")
        except Exception as e:
            print(f"  [FAIL] BatchProcessor: {e}")
            return False
            
        try:
            from src.analysis_integration import AnalysisManager
            print("  [OK] AnalysisManager")
        except Exception as e:
            print(f"  [FAIL] AnalysisManager: {e}")
            return False
        
        print("\n所有模块检查通过!")
        print("可以运行: python main.py --help")
        return True

if __name__ == '__main__':
    success = check_dependencies()
    sys.exit(0 if success else 1)