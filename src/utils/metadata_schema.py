"""任务元数据结构定义"""

import json
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field, asdict
from pathlib import Path
import hashlib

@dataclass
class TaskMetadata:
    """任务元数据"""
    
    # 基本信息
    task_id: str
    prompt: str
    workflow_type: str
    status: str = "pending"  # pending, running, completed, failed, cancelled
    
    # 时间信息
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # 工作流参数
    workflow_params: Dict[str, Any] = field(default_factory=dict)
    prompt_id: Optional[str] = None  # ComfyUI分配的prompt_id
    
    # 错误信息
    error_message: Optional[str] = None
    retry_count: int = 0
    
    # 提示词相关
    negative_prompt: str = ""
    prompt_hash: Optional[str] = None
    
    # 生成参数
    width: int = 1024
    height: int = 1024
    steps: int = 20
    cfg_scale: float = 7.0
    sampler: str = "euler"
    scheduler: str = "normal"
    seed: int = -1
    
    # 模型信息
    model_name: str = ""
    model_hash: Optional[str] = None
    
    # 质量信息
    quality_score: Optional[float] = None
    estimated_time: Optional[float] = None  # 预估时间(秒)
    actual_time: Optional[float] = None     # 实际时间(秒)
    
    # 用户标记
    user_rating: Optional[int] = None  # 1-5星评分
    user_tags: List[str] = field(default_factory=list)
    user_notes: str = ""
    is_favorite: bool = False
    
    # 系统信息
    comfyui_version: str = ""
    system_memory_mb: Optional[int] = None
    gpu_memory_mb: Optional[int] = None
    
    def __post_init__(self):
        """初始化后处理"""
        if self.prompt_hash is None:
            self.prompt_hash = self.calculate_prompt_hash()
    
    def calculate_prompt_hash(self) -> str:
        """计算提示词哈希"""
        combined_prompt = f"{self.prompt}|{self.negative_prompt}|{self.seed}"
        return hashlib.md5(combined_prompt.encode('utf-8')).hexdigest()[:8]
    
    def get_duration(self) -> Optional[float]:
        """获取任务执行时长(秒)"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
    
    def is_completed(self) -> bool:
        """检查任务是否已完成"""
        return self.status == "completed"
    
    def is_failed(self) -> bool:
        """检查任务是否失败"""
        return self.status == "failed"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        
        # 转换datetime为ISO格式字符串
        for key in ['created_at', 'started_at', 'completed_at']:
            if data[key] is not None:
                if isinstance(data[key], datetime):
                    data[key] = data[key].isoformat()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskMetadata':
        """从字典创建实例"""
        # 转换时间字符串为datetime对象
        for key in ['created_at', 'started_at', 'completed_at']:
            if data.get(key):
                if isinstance(data[key], str):
                    data[key] = datetime.fromisoformat(data[key])
        
        return cls(**data)

@dataclass 
class TaskResult:
    """任务结果"""
    
    # 关联任务
    task_id: str
    
    # 输出文件
    output_files: List[str] = field(default_factory=list)
    primary_image: Optional[str] = None  # 主要输出图片
    
    # 文件信息
    file_sizes_bytes: Dict[str, int] = field(default_factory=dict)
    image_dimensions: Dict[str, tuple] = field(default_factory=dict)  # (width, height)
    
    # ComfyUI输出信息
    comfyui_output: Dict[str, Any] = field(default_factory=dict)
    generation_log: List[str] = field(default_factory=list)
    
    # 性能指标
    generation_time: Optional[float] = None
    memory_usage: Optional[Dict[str, float]] = None
    gpu_utilization: Optional[float] = None
    
    # 图像分析结果（可选）
    image_analysis: Optional[Dict[str, Any]] = None
    
    # 存储位置
    storage_path: str = ""
    relative_paths: List[str] = field(default_factory=list)
    
    def get_primary_image_path(self) -> Optional[Path]:
        """获取主要图片路径"""
        if self.primary_image:
            if Path(self.primary_image).is_absolute():
                return Path(self.primary_image)
            else:
                return Path(self.storage_path) / self.primary_image
        elif self.output_files:
            # 使用第一个图片文件
            first_file = self.output_files[0]
            if Path(first_file).is_absolute():
                return Path(first_file)
            else:
                return Path(self.storage_path) / first_file
        return None
    
    def get_file_size_mb(self, filename: str) -> Optional[float]:
        """获取文件大小(MB)"""
        size_bytes = self.file_sizes_bytes.get(filename)
        return size_bytes / (1024 * 1024) if size_bytes else None
    
    def get_total_size_mb(self) -> float:
        """获取总文件大小(MB)"""
        total_bytes = sum(self.file_sizes_bytes.values())
        return total_bytes / (1024 * 1024)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'TaskResult':
        """从字典创建实例"""
        return cls(**data)

@dataclass
class GenerationStats:
    """生成统计信息"""
    
    # 时间范围
    start_date: datetime
    end_date: datetime
    
    # 任务统计
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    cancelled_tasks: int = 0
    
    # 成功率统计
    success_rate: float = 0.0
    average_generation_time: float = 0.0
    total_generation_time: float = 0.0
    
    # 资源使用
    total_storage_mb: float = 0.0
    total_images_generated: int = 0
    average_image_size_mb: float = 0.0
    
    # 流行度统计
    most_used_prompts: List[Dict[str, Any]] = field(default_factory=list)
    most_used_parameters: Dict[str, Any] = field(default_factory=dict)
    workflow_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 质量统计
    average_quality_score: Optional[float] = None
    quality_distribution: Dict[str, int] = field(default_factory=dict)
    
    # 用户反馈统计
    average_user_rating: Optional[float] = None
    total_favorites: int = 0
    most_popular_tags: List[Dict[str, Any]] = field(default_factory=list)
    
    def calculate_efficiency_score(self) -> float:
        """计算效率分数 (0-100)"""
        if self.total_tasks == 0:
            return 0.0
        
        # 基于成功率、平均时间等计算效率分数
        success_weight = 0.4
        time_weight = 0.3
        quality_weight = 0.3
        
        success_component = self.success_rate * success_weight
        
        # 时间效率 (假设理想时间为30秒)
        ideal_time = 30.0
        time_efficiency = min(1.0, ideal_time / (self.average_generation_time or ideal_time))
        time_component = time_efficiency * time_weight
        
        # 质量效率
        quality_efficiency = (self.average_quality_score or 0.5) / 5.0
        quality_component = quality_efficiency * quality_weight
        
        return (success_component + time_component + quality_component) * 100
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        
        # 转换datetime
        data['start_date'] = self.start_date.isoformat()
        data['end_date'] = self.end_date.isoformat()
        
        # 添加计算字段
        data['efficiency_score'] = self.calculate_efficiency_score()
        
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'GenerationStats':
        """从字典创建实例"""
        # 转换时间字符串
        data['start_date'] = datetime.fromisoformat(data['start_date'])
        data['end_date'] = datetime.fromisoformat(data['end_date'])
        
        # 移除计算字段
        data.pop('efficiency_score', None)
        
        return cls(**data)

# 辅助函数
def create_task_from_prompt_data(prompt_data: Dict[str, Any], 
                                workflow_type: str = "txt2img") -> TaskMetadata:
    """从提示词数据创建任务元数据"""
    
    task_id = prompt_data.get('task_id', f"task_{int(datetime.now().timestamp())}")
    
    return TaskMetadata(
        task_id=task_id,
        prompt=prompt_data.get('prompt', ''),
        negative_prompt=prompt_data.get('negative_prompt', ''),
        workflow_type=workflow_type,
        width=prompt_data.get('width', 1024),
        height=prompt_data.get('height', 1024),
        steps=prompt_data.get('steps', 20),
        cfg_scale=prompt_data.get('cfg_scale', 7.0),
        sampler=prompt_data.get('sampler', 'euler'),
        scheduler=prompt_data.get('scheduler', 'normal'),
        seed=prompt_data.get('seed', -1),
        workflow_params=prompt_data.get('workflow_params', {}),
        user_tags=prompt_data.get('tags', []),
        quality_score=prompt_data.get('quality_score')
    )

def create_result_from_comfyui_output(task_id: str, 
                                    output_data: Dict[str, Any],
                                    storage_path: str) -> TaskResult:
    """从ComfyUI输出创建任务结果"""
    
    return TaskResult(
        task_id=task_id,
        comfyui_output=output_data,
        storage_path=storage_path,
        generation_time=output_data.get('execution_time')
    )