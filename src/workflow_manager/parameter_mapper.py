"""参数映射器 - 将用户参数映射到工作流节点"""

import copy
import time
import hashlib
from typing import Dict, Any, Optional
import logging
from datetime import datetime

from .workflow_config import WorkflowConfig

logger = logging.getLogger(__name__)

class ParameterMapper:
    """参数映射器"""
    
    def __init__(self, workflow_config: WorkflowConfig):
        self.config = workflow_config
    
    def apply_parameters(self, params: Dict[str, Any], task_id: Optional[str] = None) -> Dict[str, Any]:
        """将参数应用到工作流"""
        
        # 验证参数
        validation_errors = self.config.validate_parameters(params)
        if validation_errors:
            error_msg = self._format_validation_errors(validation_errors)
            raise ValueError(f"参数验证失败:\n{error_msg}")
        
        # 获取工作流数据副本
        workflow_data = self.config.get_workflow_data()
        
        # 应用参数映射
        for param_name, value in params.items():
            if param_name not in self.config.parameter_mapping:
                logger.warning(f"未知参数: {param_name}, 将被忽略")
                continue
                
            param_config = self.config.parameter_mapping[param_name]
            
            # 如果值为None，使用默认值
            if value is None:
                value = self.config.get_default_value(param_name)
                if value is None:
                    continue
            
            # 应用到工作流节点
            self._apply_parameter_to_node(workflow_data, param_config, value)
        
        # 应用默认参数（如果没有被覆盖）
        self._apply_default_parameters(workflow_data, params)
        
        # 应用特殊参数（如任务ID、时间戳等）
        self._apply_special_parameters(workflow_data, task_id, params)
        
        return workflow_data
    
    def _apply_parameter_to_node(self, workflow_data: Dict[str, Any], param_config, value: Any):
        """将参数应用到指定节点"""
        node_id = param_config.node_id
        input_name = param_config.input_name
        
        if node_id not in workflow_data:
            logger.warning(f"节点 {node_id} 不存在，跳过参数 {input_name}")
            return
        
        node = workflow_data[node_id]
        if 'inputs' not in node:
            node['inputs'] = {}
        
        # 类型转换
        converted_value = self._convert_parameter_type(value, param_config)
        
        node['inputs'][input_name] = converted_value
        
        logger.debug(f"应用参数: {node_id}.{input_name} = {converted_value}")
    
    def _convert_parameter_type(self, value: Any, param_config) -> Any:
        """转换参数类型"""
        try:
            if param_config.param_type == "integer":
                return int(value)
            elif param_config.param_type == "float":
                return float(value)
            elif param_config.param_type == "string":
                return str(value)
            elif param_config.param_type == "boolean":
                if isinstance(value, str):
                    return value.lower() in ('true', '1', 'yes', 'on')
                return bool(value)
            else:
                return value
        except (ValueError, TypeError) as e:
            logger.warning(f"参数类型转换失败: {value} -> {param_config.param_type}, 使用原值")
            return value
    
    def _apply_default_parameters(self, workflow_data: Dict[str, Any], user_params: Dict[str, Any]):
        """应用默认参数（仅当用户未提供时）"""
        for param_name, default_value in self.config.default_params.items():
            # 如果用户已提供此参数，跳过
            if param_name in user_params:
                continue
            
            # 如果参数有映射配置，应用它
            if param_name in self.config.parameter_mapping:
                param_config = self.config.parameter_mapping[param_name]
                self._apply_parameter_to_node(workflow_data, param_config, default_value)
    
    def _apply_special_parameters(self, workflow_data: Dict[str, Any], 
                                task_id: Optional[str], user_params: Dict[str, Any]):
        """应用特殊参数（任务ID、时间戳等）"""
        
        # 生成随机种子（如果seed为-1）
        if 'seed' in self.config.parameter_mapping:
            seed_config = self.config.parameter_mapping['seed']
            node_id = seed_config.node_id
            
            if node_id in workflow_data:
                current_seed = workflow_data[node_id]['inputs'].get(seed_config.input_name, -1)
                if current_seed == -1:
                    # 生成基于时间的随机种子
                    random_seed = int(time.time() * 1000) % 2147483647
                    workflow_data[node_id]['inputs'][seed_config.input_name] = random_seed
                    logger.debug(f"生成随机种子: {random_seed}")
        
        # 生成文件名前缀
        if 'filename_prefix' in self.config.parameter_mapping:
            prefix_config = self.config.parameter_mapping['filename_prefix']
            node_id = prefix_config.node_id
            
            if node_id in workflow_data:
                # 生成包含任务信息的文件名前缀
                prefix_parts = []
                
                if task_id:
                    prefix_parts.append(f"task_{task_id}")
                
                # 添加时间戳
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                prefix_parts.append(timestamp)
                
                # 添加提示词哈希（如果有）
                if 'prompt' in user_params:
                    prompt_hash = hashlib.md5(
                        str(user_params['prompt']).encode('utf-8')
                    ).hexdigest()[:8]
                    prefix_parts.append(f"p{prompt_hash}")
                
                filename_prefix = "_".join(prefix_parts)
                workflow_data[node_id]['inputs'][prefix_config.input_name] = filename_prefix
                logger.debug(f"生成文件名前缀: {filename_prefix}")
    
    def _format_validation_errors(self, errors: Dict[str, list]) -> str:
        """格式化验证错误信息"""
        error_lines = []
        for param_name, param_errors in errors.items():
            for error in param_errors:
                error_lines.append(f"  - {error}")
        return "\n".join(error_lines)
    
    def get_parameter_summary(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取参数应用摘要"""
        summary = {
            'total_parameters': len(params),
            'mapped_parameters': 0,
            'default_parameters': 0,
            'ignored_parameters': 0,
            'parameter_details': {}
        }
        
        for param_name, value in params.items():
            param_info = {
                'value': value,
                'mapped': param_name in self.config.parameter_mapping,
                'has_default': param_name in self.config.default_params
            }
            
            if param_info['mapped']:
                summary['mapped_parameters'] += 1
                param_config = self.config.parameter_mapping[param_name]
                param_info.update({
                    'node_id': param_config.node_id,
                    'input_name': param_config.input_name,
                    'type': param_config.param_type,
                    'description': param_config.description
                })
            else:
                summary['ignored_parameters'] += 1
            
            summary['parameter_details'][param_name] = param_info
        
        # 统计默认参数
        for param_name in self.config.default_params:
            if param_name not in params:
                summary['default_parameters'] += 1
        
        return summary
    
    def create_workflow_from_task(self, task_data: Dict[str, Any]) -> Dict[str, Any]:
        """从任务数据创建工作流"""
        
        task_id = task_data.get('task_id', task_data.get('id'))
        prompt = task_data.get('prompt', '')
        
        # 构建参数字典
        params = {
            'prompt': prompt
        }
        
        # 添加任务中的其他参数
        workflow_params = task_data.get('workflow_params', {})
        params.update(workflow_params)
        
        # 应用参数并返回工作流
        return self.apply_parameters(params, task_id)
    
    def validate_workflow_compatibility(self) -> Dict[str, Any]:
        """验证工作流兼容性"""
        result = {
            'structure_valid': True,
            'structure_errors': [],
            'parameter_mapping_valid': True,
            'mapping_errors': [],
            'summary': {}
        }
        
        # 验证工作流结构
        structure_errors = self.config.validate_workflow_structure()
        if structure_errors:
            result['structure_valid'] = False
            result['structure_errors'] = structure_errors
        
        # 验证参数映射
        workflow_data = self.config.get_workflow_data()
        mapping_errors = []
        
        for param_name, param_config in self.config.parameter_mapping.items():
            node_id = param_config.node_id
            input_name = param_config.input_name
            
            if node_id not in workflow_data:
                mapping_errors.append(f"参数 '{param_name}' 映射的节点 '{node_id}' 不存在")
                continue
            
            node = workflow_data[node_id]
            if 'inputs' not in node:
                mapping_errors.append(f"节点 '{node_id}' 缺少 inputs 字段")
        
        if mapping_errors:
            result['parameter_mapping_valid'] = False
            result['mapping_errors'] = mapping_errors
        
        # 生成摘要
        result['summary'] = {
            'workflow_name': self.config.workflow_info.name,
            'workflow_version': self.config.workflow_info.version,
            'total_nodes': len(workflow_data),
            'total_parameters': len(self.config.parameter_mapping),
            'required_parameters': len([p for p in self.config.parameter_mapping.values() if p.required]),
            'overall_valid': result['structure_valid'] and result['parameter_mapping_valid']
        }
        
        return result