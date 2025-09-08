"""系统配置管理"""

import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict

@dataclass
class ComfyUIConfig:
    """ComfyUI连接配置"""
    path: str = "D:/LM/ComfyUI"
    api_url: str = "http://127.0.0.1:8188"
    startup_mode: str = "auto"  # auto, manual, check_only
    startup_timeout: int = 120
    venv_python: str = ""  # 自动推导

@dataclass
class GenerationConfig:
    """生成任务配置"""
    default_resolution: tuple = (1024, 1024)
    default_steps: int = 20
    default_guidance: float = 3.5
    batch_size: int = 1
    max_concurrent_tasks: int = 1

@dataclass
class OutputConfig:
    """输出配置"""
    base_directory: str = "./output"
    organize_by: str = "date"  # date, subject, style
    save_metadata: bool = True
    generate_gallery: bool = True

class Settings:
    """配置管理器"""
    
    def __init__(self, config_file: Optional[str] = None):
        self.config_file = config_file or self._get_default_config_path()
        self.comfyui = ComfyUIConfig()
        self.generation = GenerationConfig()
        self.output = OutputConfig()
        
        self.load()
    
    def _get_default_config_path(self) -> Path:
        """获取默认配置文件路径"""
        return Path(__file__).parent.parent.parent / "config.yaml"
    
    def load(self):
        """加载配置文件"""
        config_path = Path(self.config_file)
        
        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f) or {}
                
                # 更新配置对象
                if 'comfyui' in data:
                    self._update_dataclass(self.comfyui, data['comfyui'])
                if 'generation' in data:
                    self._update_dataclass(self.generation, data['generation'])
                if 'output' in data:
                    self._update_dataclass(self.output, data['output'])
                    
            except Exception as e:
                print(f"警告: 配置文件加载失败 {e}")
        
        # 自动推导venv_python路径
        if not self.comfyui.venv_python:
            comfyui_path = Path(self.comfyui.path)
            self.comfyui.venv_python = str(comfyui_path / "venv" / "Scripts" / "python.exe")
    
    def _update_dataclass(self, obj, data: dict):
        """更新dataclass对象"""
        for key, value in data.items():
            if hasattr(obj, key):
                setattr(obj, key, value)
    
    def save(self):
        """保存配置到文件"""
        config_data = {
            'comfyui': asdict(self.comfyui),
            'generation': asdict(self.generation),
            'output': asdict(self.output)
        }
        
        config_path = Path(self.config_file)
        config_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config_data, f, default_flow_style=False, allow_unicode=True)
    
    def get_comfyui_config(self) -> Dict[str, Any]:
        """获取ComfyUI配置"""
        return asdict(self.comfyui)
    
    def get_output_directory(self) -> Path:
        """获取输出目录"""
        return Path(self.output.base_directory)
    
    def create_example_config(self, output_path: str):
        """创建示例配置文件"""
        example_config = {
            'comfyui': {
                'path': 'D:/LM/ComfyUI',
                'api_url': 'http://127.0.0.1:8188',
                'startup_mode': 'auto',
                'startup_timeout': 120
            },
            'generation': {
                'default_resolution': [1024, 1024],
                'default_steps': 20,
                'default_guidance': 3.5,
                'batch_size': 1,
                'max_concurrent_tasks': 1
            },
            'output': {
                'base_directory': './output',
                'organize_by': 'date',
                'save_metadata': True,
                'generate_gallery': True
            }
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            yaml.dump(example_config, f, default_flow_style=False, allow_unicode=True)

# 全局配置实例
settings = Settings()

def load_settings(config_file: Optional[str] = None) -> Dict[str, Any]:
    """加载配置并返回字典格式"""
    settings_instance = Settings(config_file)
    
    return {
        'comfyui': asdict(settings_instance.comfyui),
        'generation': asdict(settings_instance.generation),
        'output': asdict(settings_instance.output),
        'workflows': {
            'directory': './workflows'
        },
        'database': {
            'file_path': './data/database/tasks.db'
        }
    }