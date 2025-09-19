#!/usr/bin/env python3
"""
简单测试main.py核心功能
"""

import sys
import json
from pathlib import Path

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / 'src'))

def test_config_creation():
    """测试配置文件创建"""
    print("测试配置文件创建功能...")
    
    try:
        from main import create_sample_config
        create_sample_config()
        
        # 检查文件是否创建
        config_file = Path("config.json")
        if config_file.exists():
            print("[OK] 配置文件创建成功")
            
            # 验证JSON格式
            with open(config_file, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            print(f"[OK] 配置文件包含 {len(config_data)} 个主要配置项")
            return True
        else:
            print("[FAIL] 配置文件未创建")
            return False
            
    except Exception as e:
        print(f"[FAIL] 配置文件创建失败: {e}")
        return False

def test_system_class():
    """测试系统主类"""
    print("测试ComfyUIAutomationSystem类...")
    
    try:
        from main import ComfyUIAutomationSystem
        
        # 测试类创建（使用简单配置）
        system = ComfyUIAutomationSystem()
        print("[OK] 系统类创建成功")
        
        # 测试配置加载
        if 'batch_processing' in system.config:
            print("[OK] 配置加载正常")
        else:
            print("[FAIL] 配置加载异常")
            return False
            
        return True
        
    except Exception as e:
        print(f"[FAIL] 系统类测试失败: {e}")
        return False

def main():
    print("main.py 核心功能测试")
    print("=" * 40)
    
    results = []
    
    # 测试配置创建
    results.append(test_config_creation())
    
    # 测试系统类
    results.append(test_system_class())
    
    print("\n测试总结:")
    print(f"成功: {sum(results)} / {len(results)}")
    
    if all(results):
        print("所有测试通过! main.py 可以正常使用")
        print("\n可用命令:")
        print("  python main.py --help         # 查看帮助")  
        print("  python main.py --interactive  # 交互模式")
        print("  python quick_start.py         # 快速启动")
        print("  双击 start.bat               # Windows启动")
    else:
        print("部分测试失败，请检查错误信息")
    
    return 0 if all(results) else 1

if __name__ == '__main__':
    sys.exit(main())