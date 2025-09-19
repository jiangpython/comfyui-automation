"""任务执行器"""

import time
import logging
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass, asdict
from datetime import datetime
import uuid

from .client import ComfyUIClient
from .task_monitor import TaskMonitor

logger = logging.getLogger(__name__)

@dataclass
class Task:
    """任务数据类"""
    id: str
    prompt: str
    workflow_params: Dict[str, Any]
    workflow_type: str = "txt2img"  # 工作流类型
    status: str = "pending"  # pending, running, completed, failed
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    prompt_id: Optional[str] = None
    output_files: List[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now()
        if self.output_files is None:
            self.output_files = []
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        data = asdict(self)
        # 转换datetime为ISO格式字符串
        for key in ['created_at', 'started_at', 'completed_at']:
            if data[key]:
                data[key] = data[key].isoformat()
        return data

class TaskExecutor:
    """任务执行器"""
    
    def __init__(self, client: ComfyUIClient, workflow_manager=None):
        self.client = client
        self.workflow_manager = workflow_manager
        self.monitor = TaskMonitor(client)
        
        # 执行参数
        self.max_retries = 3
        self.task_timeout = 600  # 10分钟
        self.batch_delay = 2  # 批次间延迟（秒）
        
        # 状态追踪
        self.current_task: Optional[Task] = None
        self.completed_tasks: List[Task] = []
        self.failed_tasks: List[Task] = []
    
    def execute_single_task(self, 
                          task: Task,
                          progress_callback: Optional[Callable] = None) -> bool:
        """执行单个任务"""
        logger.info(f"开始执行任务: {task.id}")
        
        task.status = "running"
        task.started_at = datetime.now()
        self.current_task = task
        
        try:
            # 准备工作流
            workflow = self._prepare_workflow(task)
            if not workflow:
                task.status = "failed"
                task.error = "工作流准备失败"
                return False
            
            # 提交任务
            prompt_id = self.client.submit_workflow(workflow)
            if not prompt_id:
                task.status = "failed"
                task.error = "任务提交失败"
                return False
            
            task.prompt_id = prompt_id
            logger.info(f"任务 {task.id} 提交成功，Prompt ID: {prompt_id}")
            
            # 等待完成
            success = self.monitor.wait_for_completion(
                prompt_id, 
                timeout=self.task_timeout,
                progress_callback=progress_callback
            )
            
            if success:
                task.status = "completed"
                task.completed_at = datetime.now()
                task.metadata['duration'] = (task.completed_at - task.started_at).total_seconds()
                self.completed_tasks.append(task)
                logger.info(f"任务 {task.id} 完成，耗时: {task.metadata['duration']:.1f}秒")
                return True
            else:
                task.status = "failed"
                task.error = "任务执行超时或失败"
                self.failed_tasks.append(task)
                logger.error(f"任务 {task.id} 失败: {task.error}")
                return False
                
        except Exception as e:
            task.status = "failed"
            task.error = f"任务执行异常: {str(e)}"
            self.failed_tasks.append(task)
            logger.error(f"任务 {task.id} 异常: {e}")
            return False
        finally:
            self.current_task = None
    
    def execute_batch(self, 
                     tasks: List[Task],
                     progress_callback: Optional[Callable] = None,
                     stop_on_error: bool = False) -> Dict[str, Any]:
        """执行任务批次"""
        logger.info(f"开始执行批次任务，共 {len(tasks)} 个")
        
        start_time = datetime.now()
        results = {
            'total_tasks': len(tasks),
            'completed': 0,
            'failed': 0,
            'skipped': 0,
            'start_time': start_time,
            'tasks': []
        }
        
        for i, task in enumerate(tasks):
            try:
                logger.info(f"执行任务 {i+1}/{len(tasks)}: {task.id}")
                
                # 进度回调
                if progress_callback:
                    progress_callback({
                        'current_task': i + 1,
                        'total_tasks': len(tasks),
                        'task_id': task.id,
                        'status': 'starting'
                    })
                
                # 执行任务
                success = self.execute_single_task(
                    task, 
                    lambda tid, status: progress_callback({
                        'current_task': i + 1,
                        'total_tasks': len(tasks),
                        'task_id': tid,
                        'status': status
                    }) if progress_callback else None
                )
                
                if success:
                    results['completed'] += 1
                else:
                    results['failed'] += 1
                    if stop_on_error:
                        logger.warning("遇到错误，停止批次执行")
                        break
                
                results['tasks'].append(task.to_dict())
                
                # 批次间延迟
                if i < len(tasks) - 1:  # 不是最后一个任务
                    time.sleep(self.batch_delay)
                
                # 健康检查
                if not self._health_check():
                    logger.error("健康检查失败，停止批次执行")
                    break
                    
            except KeyboardInterrupt:
                logger.info("用户中断批次执行")
                # 标记剩余任务为跳过
                for remaining_task in tasks[i+1:]:
                    remaining_task.status = "skipped"
                    results['skipped'] += len(tasks) - i - 1
                break
            except Exception as e:
                logger.error(f"批次执行异常: {e}")
                task.status = "failed"
                task.error = f"批次执行异常: {str(e)}"
                results['failed'] += 1
        
        # 计算总耗时
        end_time = datetime.now()
        results['end_time'] = end_time
        results['total_duration'] = (end_time - start_time).total_seconds()
        results['success_rate'] = results['completed'] / results['total_tasks'] if results['total_tasks'] > 0 else 0
        
        logger.info(f"批次执行完成: {results['completed']}/{results['total_tasks']} 成功")
        return results
    
    def execute_with_retry(self, 
                         task: Task, 
                         max_retries: Optional[int] = None) -> bool:
        """带重试的任务执行"""
        max_retries = max_retries or self.max_retries
        
        for attempt in range(max_retries):
            logger.info(f"任务 {task.id} 第 {attempt + 1} 次尝试")
            
            if self.execute_single_task(task):
                return True
            
            if attempt < max_retries - 1:
                # 重试前等待
                retry_delay = 2 ** attempt  # 指数退避
                logger.info(f"任务 {task.id} 失败，{retry_delay}秒后重试")
                time.sleep(retry_delay)
                
                # 重置任务状态
                task.status = "pending"
                task.started_at = None
                task.error = None
                task.prompt_id = None
        
        logger.error(f"任务 {task.id} 重试 {max_retries} 次后仍然失败")
        return False
    
    def _prepare_workflow(self, task: Task) -> Optional[Dict[str, Any]]:
        """准备工作流"""
        try:
            # 检查workflow_params是否已经是完整的工作流JSON
            # 完整的工作流JSON应该包含数字键（节点ID）
            if isinstance(task.workflow_params, dict) and any(isinstance(k, str) and k.isdigit() for k in task.workflow_params.keys()):
                # 已经是完整的工作流JSON，直接返回
                logger.debug("使用预处理的工作流JSON")
                return task.workflow_params
            
            # 否则，这是参数字典，需要通过工作流管理器处理
            if self.workflow_manager:
                # 构建完整的参数字典，确保包含prompt
                workflow_params = task.workflow_params.copy()
                workflow_params['prompt'] = task.prompt
                
                # 使用工作流管理器
                logger.debug("通过工作流管理器创建工作流")
                return self.workflow_manager.create_workflow(
                    task.workflow_type,
                    workflow_params,
                    task_id=task.id
                )
            else:
                # 简化处理：直接返回工作流参数
                return task.workflow_params
        except Exception as e:
            logger.error(f"准备工作流失败: {e}")
            return None
    
    def _health_check(self) -> bool:
        """健康检查"""
        try:
            health_status = self.client.health_check()
            return health_status.get('service_running', False)
        except Exception as e:
            logger.error(f"健康检查异常: {e}")
            return False
    
    def create_task_from_prompt(self, 
                              prompt: str,
                              workflow_type: str = "txt2img",
                              custom_params: Optional[Dict[str, Any]] = None) -> Task:
        """从提示词创建任务"""
        task_id = str(uuid.uuid4())[:8]
        
        # 基础工作流参数
        workflow_params = {
            'workflow_type': workflow_type,
            'prompt': prompt,
            'task_id': task_id
        }
        
        # 添加自定义参数
        if custom_params:
            workflow_params.update(custom_params)
        
        task = Task(
            id=task_id,
            prompt=prompt,
            workflow_params=workflow_params,
            workflow_type=workflow_type,
            metadata={
                'workflow_type': workflow_type,
                'created_from': 'prompt'
            }
        )
        
        return task
    
    def get_execution_statistics(self) -> Dict[str, Any]:
        """获取执行统计"""
        total_tasks = len(self.completed_tasks) + len(self.failed_tasks)
        
        if total_tasks == 0:
            return {
                'total_tasks': 0,
                'completed': 0,
                'failed': 0,
                'success_rate': 0.0,
                'average_duration': 0.0
            }
        
        # 计算平均耗时
        durations = [
            task.metadata.get('duration', 0) 
            for task in self.completed_tasks 
            if 'duration' in task.metadata
        ]
        average_duration = sum(durations) / len(durations) if durations else 0
        
        return {
            'total_tasks': total_tasks,
            'completed': len(self.completed_tasks),
            'failed': len(self.failed_tasks),
            'success_rate': len(self.completed_tasks) / total_tasks,
            'average_duration': average_duration,
            'total_duration': sum(durations)
        }
    
    def reset_statistics(self):
        """重置统计信息"""
        self.completed_tasks.clear()
        self.failed_tasks.clear()
        self.current_task = None