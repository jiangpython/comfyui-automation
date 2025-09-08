"""工作流配置类"""

import json
import yaml
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class ParameterConfig:
    """参数配置"""
    node_id: str
    input_name: str
    description: str = ""
    required: bool = False
    param_type: str = "string"
    default: Any = None
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    step: Optional[float] = None
    options: Optional[List[Any]] = None

@dataclass
class WorkflowInfo:
    """工作流基本信息"""
    name: str
    version: str = "1.0.0"
    description: str = ""
    author: str = ""
    created_date: str = ""

@dataclass
class NodeValidation:
    """节点验证规则"""
    id: str
    class_type: str
    description: str = ""

@dataclass
class OutputConfig:
    """输出配置"""
    output_directory: str = "output"
    filename_template: str = "{task_id}_{timestamp}"
    supported_formats: List[str] = field(default_factory=lambda: ["png"])
    save_metadata: bool = True
    metadata_format: str = "json"

@dataclass
class PerformanceConfig:
    """性能配置"""
    task_timeout: int = 600
    max_retries: int = 3
    memory_limit_mb: int = 8192
    max_concurrent_tasks: int = 1

@dataclass
class CompatibilityInfo:
    """兼容性信息"""
    comfyui_version_min: str = "0.1.0"
    required_custom_nodes: List[Dict[str, str]] = field(default_factory=list)

class WorkflowConfig:
    """工作流配置管理类"""
    
    def __init__(self, config_file: Path):
        self.config_file = Path(config_file)
        self.workflow_dir = self.config_file.parent
        
        # 配置数据
        self.workflow_info: WorkflowInfo
        self.workflow_file: str
        self.default_params: Dict[str, Any]
        self.parameter_mapping: Dict[str, ParameterConfig]
        self.node_validation: List[NodeValidation]
        self.output_config: OutputConfig
        self.performance: PerformanceConfig
        self.compatibility: CompatibilityInfo
        
        # 工作流JSON数据
        self._workflow_data: Optional[Dict[str, Any]] = None
        
        self.load_config()
    
    def load_config(self):
        """加载配置文件"""
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            
            # 解析配置
            self._parse_config(config_data)
            
            # 加载工作流JSON文件
            self._load_workflow_json()
            
            logger.info(f"工作流配置加载成功: {self.workflow_info.name}")
            
        except Exception as e:
            logger.error(f"加载工作流配置失败: {e}")
            raise
    
    def _parse_config(self, config_data: Dict[str, Any]):
        """解析配置数据"""
        
        # 基本信息
        info_data = config_data.get('workflow_info', {})
        self.workflow_info = WorkflowInfo(**info_data)
        
        # 工作流文件
        self.workflow_file = config_data.get('workflow_file', 'workflow.json')
        
        # 默认参数
        self.default_params = config_data.get('default_params', {})
        
        # 参数映射
        mapping_data = config_data.get('parameter_mapping', {})
        self.parameter_mapping = {}
        for param_name, param_config in mapping_data.items():
            self.parameter_mapping[param_name] = ParameterConfig(
                node_id=param_config['node_id'],
                input_name=param_config['input_name'],
                description=param_config.get('description', ''),
                required=param_config.get('required', False),
                param_type=param_config.get('type', 'string'),
                default=param_config.get('default'),
                min_value=param_config.get('min'),
                max_value=param_config.get('max'),
                step=param_config.get('step'),
                options=param_config.get('options')
            )
        
        # 节点验证
        validation_data = config_data.get('node_validation', {}).get('required_nodes', [])
        self.node_validation = [
            NodeValidation(**node) for node in validation_data
        ]
        
        # 输出配置
        output_data = config_data.get('output_config', {})
        self.output_config = OutputConfig(**output_data)
        
        # 性能配置
        perf_data = config_data.get('performance', {})
        self.performance = PerformanceConfig(**perf_data)
        
        # 兼容性配置
        compat_data = config_data.get('compatibility', {})
        self.compatibility = CompatibilityInfo(**compat_data)
    
    def _load_workflow_json(self):
        """加载工作流JSON文件"""
        workflow_path = self.workflow_dir / self.workflow_file
        
        try:
            with open(workflow_path, 'r', encoding='utf-8') as f:
                self._workflow_data = json.load(f)
            
            logger.debug(f"工作流JSON加载成功: {workflow_path}")
            
        except Exception as e:
            logger.error(f"加载工作流JSON失败: {e}")
            raise
    
    def get_workflow_data(self) -> Dict[str, Any]:
        """获取工作流JSON数据"""
        if self._workflow_data is None:
            raise RuntimeError("工作流数据未加载")
        return self._workflow_data.copy()
    
    def validate_parameters(self, params: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证参数"""
        errors = {}
        
        for param_name, param_config in self.parameter_mapping.items():
            value = params.get(param_name)
            
            # 检查必需参数
            if param_config.required and value is None:
                if param_name not in errors:
                    errors[param_name] = []
                errors[param_name].append(f"必需参数 '{param_name}' 缺失")
                continue
            
            # 如果值为None且有默认值，跳过验证
            if value is None and param_config.default is not None:
                continue
            
            if value is not None:
                # 类型验证
                type_errors = self._validate_parameter_type(param_name, value, param_config)
                if type_errors:
                    if param_name not in errors:
                        errors[param_name] = []
                    errors[param_name].extend(type_errors)
        
        return errors
    
    def _validate_parameter_type(self, param_name: str, value: Any, config: ParameterConfig) -> List[str]:
        """验证参数类型和范围"""
        errors = []
        
        try:
            if config.param_type == "integer":
                if not isinstance(value, int):
                    value = int(value)
                if config.min_value is not None and value < config.min_value:
                    errors.append(f"'{param_name}' 值 {value} 小于最小值 {config.min_value}")
                if config.max_value is not None and value > config.max_value:
                    errors.append(f"'{param_name}' 值 {value} 大于最大值 {config.max_value}")
                    
            elif config.param_type == "float":
                if not isinstance(value, (int, float)):
                    value = float(value)
                if config.min_value is not None and value < config.min_value:
                    errors.append(f"'{param_name}' 值 {value} 小于最小值 {config.min_value}")
                if config.max_value is not None and value > config.max_value:
                    errors.append(f"'{param_name}' 值 {value} 大于最大值 {config.max_value}")
                    
            elif config.param_type == "string":
                if not isinstance(value, str):
                    errors.append(f"'{param_name}' 必须是字符串类型")
                    
            # 选项验证
            if config.options and value not in config.options:
                errors.append(f"'{param_name}' 值 '{value}' 不在允许的选项中: {config.options}")
                
        except (ValueError, TypeError) as e:
            errors.append(f"'{param_name}' 类型转换失败: {e}")
        
        return errors
    
    def validate_workflow_structure(self) -> List[str]:
        """验证工作流结构"""
        errors = []
        workflow_data = self.get_workflow_data()
        
        # 检查必需节点
        for node_validation in self.node_validation:
            node_id = node_validation.id
            
            if node_id not in workflow_data:
                errors.append(f"缺少必需节点: {node_id} ({node_validation.description})")
                continue
            
            node = workflow_data[node_id]
            if node.get('class_type') != node_validation.class_type:
                errors.append(
                    f"节点 {node_id} 类型错误: "
                    f"期望 {node_validation.class_type}, "
                    f"实际 {node.get('class_type', 'unknown')}"
                )
        
        # 检查参数映射的节点是否存在
        for param_name, param_config in self.parameter_mapping.items():
            node_id = param_config.node_id
            if node_id not in workflow_data:
                errors.append(f"参数 '{param_name}' 映射的节点 '{node_id}' 不存在")
        
        return errors
    
    def get_parameter_info(self, param_name: str) -> Optional[ParameterConfig]:
        """获取参数配置信息"""
        return self.parameter_mapping.get(param_name)
    
    def get_all_parameters(self) -> Dict[str, ParameterConfig]:
        """获取所有参数配置"""
        return self.parameter_mapping.copy()
    
    def get_default_value(self, param_name: str) -> Any:
        """获取参数默认值"""
        # 优先使用参数配置中的默认值
        param_config = self.parameter_mapping.get(param_name)
        if param_config and param_config.default is not None:
            return param_config.default
        
        # 其次使用全局默认值
        return self.default_params.get(param_name)
    
    def __str__(self) -> str:
        return f"WorkflowConfig({self.workflow_info.name} v{self.workflow_info.version})"