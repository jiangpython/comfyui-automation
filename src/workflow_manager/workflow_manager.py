"""工作流管理器 - 管理多个工作流配置"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

from .workflow_config import WorkflowConfig
from .parameter_mapper import ParameterMapper

logger = logging.getLogger(__name__)

class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self, workflows_directory: Path):
        self.workflows_dir = Path(workflows_directory)
        self.loaded_workflows: Dict[str, WorkflowConfig] = {}
        self.parameter_mappers: Dict[str, ParameterMapper] = {}
        
        # 自动发现和加载工作流
        self.discover_workflows()
    
    def discover_workflows(self):
        """自动发现工作流配置"""
        if not self.workflows_dir.exists():
            logger.warning(f"工作流目录不存在: {self.workflows_dir}")
            return
        
        # 扫描子目录
        for workflow_dir in self.workflows_dir.iterdir():
            if not workflow_dir.is_dir():
                continue
            
            config_file = workflow_dir / "config.yaml"
            if config_file.exists():
                try:
                    self.load_workflow(workflow_dir.name, config_file)
                except Exception as e:
                    logger.error(f"加载工作流 {workflow_dir.name} 失败: {e}")
    
    def load_workflow(self, workflow_name: str, config_file: Path) -> WorkflowConfig:
        """加载指定工作流"""
        try:
            config = WorkflowConfig(config_file)
            mapper = ParameterMapper(config)
            
            self.loaded_workflows[workflow_name] = config
            self.parameter_mappers[workflow_name] = mapper
            
            logger.info(f"工作流 '{workflow_name}' 加载成功")
            return config
            
        except Exception as e:
            logger.error(f"加载工作流 '{workflow_name}' 失败: {e}")
            raise
    
    def get_workflow_config(self, workflow_name: str) -> Optional[WorkflowConfig]:
        """获取工作流配置"""
        return self.loaded_workflows.get(workflow_name)
    
    def get_parameter_mapper(self, workflow_name: str) -> Optional[ParameterMapper]:
        """获取参数映射器"""
        return self.parameter_mappers.get(workflow_name)
    
    def list_workflows(self) -> List[str]:
        """列出所有已加载的工作流"""
        return list(self.loaded_workflows.keys())
    
    def get_workflow_info(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """获取工作流信息"""
        config = self.loaded_workflows.get(workflow_name)
        if not config:
            return None
        
        return {
            'name': config.workflow_info.name,
            'version': config.workflow_info.version,
            'description': config.workflow_info.description,
            'author': config.workflow_info.author,
            'created_date': config.workflow_info.created_date,
            'parameter_count': len(config.parameter_mapping),
            'required_parameters': [
                name for name, param in config.parameter_mapping.items()
                if param.required
            ]
        }
    
    def create_workflow(self, workflow_name: str, params: Dict[str, Any], 
                       task_id: Optional[str] = None) -> Dict[str, Any]:
        """创建工作流实例"""
        mapper = self.parameter_mappers.get(workflow_name)
        if not mapper:
            raise ValueError(f"未找到工作流: {workflow_name}")
        
        return mapper.apply_parameters(params, task_id)
    
    def create_workflow_from_task(self, workflow_name: str, 
                                task_data: Dict[str, Any]) -> Dict[str, Any]:
        """从任务数据创建工作流"""
        mapper = self.parameter_mappers.get(workflow_name)
        if not mapper:
            raise ValueError(f"未找到工作流: {workflow_name}")
        
        return mapper.create_workflow_from_task(task_data)
    
    def validate_workflow(self, workflow_name: str) -> Dict[str, Any]:
        """验证工作流配置"""
        mapper = self.parameter_mappers.get(workflow_name)
        if not mapper:
            return {
                'valid': False,
                'error': f"未找到工作流: {workflow_name}"
            }
        
        return mapper.validate_workflow_compatibility()
    
    def validate_parameters(self, workflow_name: str, 
                          params: Dict[str, Any]) -> Dict[str, List[str]]:
        """验证参数"""
        config = self.loaded_workflows.get(workflow_name)
        if not config:
            return {'workflow': [f"未找到工作流: {workflow_name}"]}
        
        return config.validate_parameters(params)
    
    def get_parameter_info(self, workflow_name: str, 
                         param_name: Optional[str] = None) -> Dict[str, Any]:
        """获取参数信息"""
        config = self.loaded_workflows.get(workflow_name)
        if not config:
            return {}
        
        if param_name:
            param_config = config.get_parameter_info(param_name)
            if not param_config:
                return {}
            
            return {
                'name': param_name,
                'description': param_config.description,
                'type': param_config.param_type,
                'required': param_config.required,
                'default': param_config.default,
                'min_value': param_config.min_value,
                'max_value': param_config.max_value,
                'step': param_config.step,
                'options': param_config.options,
                'node_mapping': {
                    'node_id': param_config.node_id,
                    'input_name': param_config.input_name
                }
            }
        else:
            # 返回所有参数信息
            all_params = config.get_all_parameters()
            return {
                name: {
                    'description': param.description,
                    'type': param.param_type,
                    'required': param.required,
                    'default': param.default,
                    'min_value': param.min_value,
                    'max_value': param.max_value,
                    'step': param.step,
                    'options': param.options,
                    'node_mapping': {
                        'node_id': param.node_id,
                        'input_name': param.input_name
                    }
                }
                for name, param in all_params.items()
            }
    
    def get_default_parameters(self, workflow_name: str) -> Dict[str, Any]:
        """获取默认参数"""
        config = self.loaded_workflows.get(workflow_name)
        if not config:
            return {}
        
        defaults = {}
        for param_name in config.parameter_mapping:
            default_value = config.get_default_value(param_name)
            if default_value is not None:
                defaults[param_name] = default_value
        
        return defaults
    
    def export_workflow_config(self, workflow_name: str, 
                             output_file: Path) -> bool:
        """导出工作流配置"""
        config = self.loaded_workflows.get(workflow_name)
        if not config:
            logger.error(f"未找到工作流: {workflow_name}")
            return False
        
        try:
            export_data = {
                'workflow_info': {
                    'name': config.workflow_info.name,
                    'version': config.workflow_info.version,
                    'description': config.workflow_info.description,
                    'author': config.workflow_info.author,
                    'created_date': config.workflow_info.created_date
                },
                'parameters': self.get_parameter_info(workflow_name),
                'default_parameters': self.get_default_parameters(workflow_name),
                'validation_result': self.validate_workflow(workflow_name)
            }
            
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"工作流配置已导出到: {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出工作流配置失败: {e}")
            return False
    
    def get_workflow_statistics(self) -> Dict[str, Any]:
        """获取工作流统计信息"""
        total_workflows = len(self.loaded_workflows)
        total_parameters = sum(
            len(config.parameter_mapping) 
            for config in self.loaded_workflows.values()
        )
        
        workflow_details = []
        for name, config in self.loaded_workflows.items():
            validation = self.validate_workflow(name)
            workflow_details.append({
                'name': name,
                'version': config.workflow_info.version,
                'parameter_count': len(config.parameter_mapping),
                'required_parameter_count': len([
                    p for p in config.parameter_mapping.values() if p.required
                ]),
                'valid': validation.get('summary', {}).get('overall_valid', False)
            })
        
        return {
            'total_workflows': total_workflows,
            'total_parameters': total_parameters,
            'valid_workflows': len([w for w in workflow_details if w['valid']]),
            'workflow_details': workflow_details
        }
    
    def reload_workflow(self, workflow_name: str) -> bool:
        """重新加载工作流"""
        if workflow_name not in self.loaded_workflows:
            logger.error(f"工作流 '{workflow_name}' 未加载")
            return False
        
        try:
            # 获取原配置文件路径
            config = self.loaded_workflows[workflow_name]
            config_file = config.config_file
            
            # 重新加载
            self.load_workflow(workflow_name, config_file)
            
            logger.info(f"工作流 '{workflow_name}' 重新加载成功")
            return True
            
        except Exception as e:
            logger.error(f"重新加载工作流 '{workflow_name}' 失败: {e}")
            return False
    
    def __len__(self) -> int:
        return len(self.loaded_workflows)
    
    def __contains__(self, workflow_name: str) -> bool:
        return workflow_name in self.loaded_workflows
    
    def __iter__(self):
        return iter(self.loaded_workflows.keys())