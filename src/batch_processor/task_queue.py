"""任务队列管理器"""

import uuid
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from dataclasses import dataclass
import logging
from enum import Enum

from ..utils.metadata_schema import TaskMetadata, create_task_from_prompt_data

logger = logging.getLogger(__name__)

class TaskStatus(Enum):
    """任务状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRY = "retry"

@dataclass
class QueuedTask:
    """队列中的任务"""
    task_metadata: TaskMetadata
    priority: int = 0
    max_retries: int = 3
    retry_delay: float = 2.0
    workflow_params: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.workflow_params is None:
            self.workflow_params = {}

class TaskQueue:
    """任务队列管理器"""
    
    def __init__(self):
        self._queue: List[QueuedTask] = []
        self._running_tasks: Dict[str, QueuedTask] = {}
        self._completed_tasks: List[QueuedTask] = []
        self._failed_tasks: List[QueuedTask] = []
        
        # 统计信息
        self._total_added = 0
        self._total_processed = 0
        
        logger.info("任务队列管理器初始化完成")
    
    def add_task(self, task: TaskMetadata, priority: int = 0, 
                max_retries: int = 3, workflow_params: Optional[Dict[str, Any]] = None) -> str:
        """添加任务到队列"""
        
        queued_task = QueuedTask(
            task_metadata=task,
            priority=priority,
            max_retries=max_retries,
            workflow_params=workflow_params or {}
        )
        
        self._queue.append(queued_task)
        self._total_added += 1
        
        # 按优先级排序（高优先级在前）
        self._queue.sort(key=lambda t: t.priority, reverse=True)
        
        logger.debug(f"任务添加到队列: {task.task_id} (优先级: {priority})")
        return task.task_id
    
    def add_tasks_from_prompts(self, prompts: List[str], 
                             workflow_type: str = "txt2img",
                             base_params: Optional[Dict[str, Any]] = None) -> List[str]:
        """从提示词列表批量添加任务"""
        
        base_params = base_params or {}
        task_ids = []
        
        for i, prompt in enumerate(prompts):
            task_id = f"batch_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:04d}"
            
            # 创建任务元数据
            task_data = {
                'task_id': task_id,
                'prompt': prompt,
                'workflow_params': base_params.copy(),
                **base_params
            }
            
            task = create_task_from_prompt_data(task_data, workflow_type)
            task_id_added = self.add_task(task, workflow_params=base_params)
            task_ids.append(task_id_added)
        
        logger.info(f"批量添加 {len(prompts)} 个任务到队列")
        return task_ids
    
    def add_tasks_from_generated_prompts(self, generated_prompts, 
                                       workflow_type: str = "txt2img",
                                       base_params: Optional[Dict[str, Any]] = None) -> List[str]:
        """从生成的提示词对象列表添加任务"""
        
        base_params = base_params or {}
        task_ids = []
        
        for i, generated_prompt in enumerate(generated_prompts):
            task_id = f"gen_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{i:04d}"
            
            # 创建任务元数据，包含生成的提示词信息
            task_data = {
                'task_id': task_id,
                'prompt': generated_prompt.text,
                'quality_score': generated_prompt.quality_score,
                'workflow_params': base_params.copy(),
                **base_params
            }
            
            # 添加元素信息到用户标签
            if hasattr(generated_prompt, 'elements') and generated_prompt.elements:
                element_names = [elem.name for elem in generated_prompt.elements.values()]
                task_data['tags'] = element_names[:5]  # 限制标签数量
            
            task = create_task_from_prompt_data(task_data, workflow_type)
            task_id_added = self.add_task(task, workflow_params=base_params)
            task_ids.append(task_id_added)
        
        logger.info(f"从生成的提示词添加 {len(generated_prompts)} 个任务到队列")
        return task_ids
    
    def get_next_task(self) -> Optional[QueuedTask]:
        """获取下一个待处理任务"""
        if not self._queue:
            return None
        
        # 获取优先级最高的任务
        task = self._queue.pop(0)
        self._running_tasks[task.task_metadata.task_id] = task
        
        # 更新任务状态
        task.task_metadata.status = TaskStatus.RUNNING.value
        task.task_metadata.started_at = datetime.now()
        
        logger.debug(f"获取下一个任务: {task.task_metadata.task_id}")
        return task
    
    def complete_task(self, task_id: str, success: bool = True, 
                     error_message: Optional[str] = None):
        """完成任务"""
        
        if task_id not in self._running_tasks:
            logger.warning(f"尝试完成不存在的运行中任务: {task_id}")
            return
        
        task = self._running_tasks.pop(task_id)
        task.task_metadata.completed_at = datetime.now()
        self._total_processed += 1
        
        if success:
            task.task_metadata.status = TaskStatus.COMPLETED.value
            self._completed_tasks.append(task)
            logger.debug(f"任务完成: {task_id}")
        else:
            task.task_metadata.status = TaskStatus.FAILED.value
            task.task_metadata.error_message = error_message
            task.task_metadata.retry_count += 1
            
            # 检查是否需要重试
            if task.task_metadata.retry_count < task.max_retries:
                task.task_metadata.status = TaskStatus.RETRY.value
                self._queue.insert(0, task)  # 插入到队列前面优先重试
                logger.info(f"任务失败，安排重试: {task_id} (第{task.task_metadata.retry_count}次)")
            else:
                self._failed_tasks.append(task)
                logger.error(f"任务最终失败: {task_id} - {error_message}")
    
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        
        # 从待处理队列中查找并移除
        for i, task in enumerate(self._queue):
            if task.task_metadata.task_id == task_id:
                task.task_metadata.status = TaskStatus.CANCELLED.value
                cancelled_task = self._queue.pop(i)
                logger.info(f"任务已取消: {task_id}")
                return True
        
        # 从运行中任务查找
        if task_id in self._running_tasks:
            task = self._running_tasks.pop(task_id)
            task.task_metadata.status = TaskStatus.CANCELLED.value
            logger.info(f"运行中任务已取消: {task_id}")
            return True
        
        return False
    
    def cancel_all_tasks(self):
        """取消所有待处理任务"""
        cancelled_count = 0
        
        # 取消队列中的任务
        for task in self._queue:
            task.task_metadata.status = TaskStatus.CANCELLED.value
            cancelled_count += 1
        
        self._queue.clear()
        logger.info(f"已取消 {cancelled_count} 个待处理任务")
    
    def pause_queue(self):
        """暂停队列（标记，实际暂停由处理器控制）"""
        logger.info("队列已标记为暂停")
    
    def resume_queue(self):
        """恢复队列"""
        logger.info("队列已恢复")
    
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return {
            'pending_count': len(self._queue),
            'running_count': len(self._running_tasks),
            'completed_count': len(self._completed_tasks),
            'failed_count': len(self._failed_tasks),
            'total_added': self._total_added,
            'total_processed': self._total_processed,
            'success_rate': (
                len(self._completed_tasks) / max(self._total_processed, 1)
            ) if self._total_processed > 0 else 0.0
        }
    
    def get_pending_tasks(self) -> List[TaskMetadata]:
        """获取待处理任务列表"""
        return [task.task_metadata for task in self._queue]
    
    def get_running_tasks(self) -> List[TaskMetadata]:
        """获取运行中任务列表"""
        return [task.task_metadata for task in self._running_tasks.values()]
    
    def get_completed_tasks(self) -> List[TaskMetadata]:
        """获取已完成任务列表"""
        return [task.task_metadata for task in self._completed_tasks]
    
    def get_failed_tasks(self) -> List[TaskMetadata]:
        """获取失败任务列表"""
        return [task.task_metadata for task in self._failed_tasks]
    
    def get_task_by_id(self, task_id: str) -> Optional[QueuedTask]:
        """根据ID获取任务"""
        
        # 在各个列表中查找
        all_tasks = (self._queue + list(self._running_tasks.values()) + 
                    self._completed_tasks + self._failed_tasks)
        
        for task in all_tasks:
            if task.task_metadata.task_id == task_id:
                return task
        
        return None
    
    def clear_completed_tasks(self):
        """清理已完成的任务"""
        cleared_count = len(self._completed_tasks)
        self._completed_tasks.clear()
        logger.info(f"清理了 {cleared_count} 个已完成任务")
    
    def clear_failed_tasks(self):
        """清理失败的任务"""
        cleared_count = len(self._failed_tasks)
        self._failed_tasks.clear()
        logger.info(f"清理了 {cleared_count} 个失败任务")
    
    def requeue_failed_tasks(self, max_retries: Optional[int] = None):
        """重新排队失败的任务"""
        
        requeued_count = 0
        failed_tasks_copy = self._failed_tasks.copy()
        self._failed_tasks.clear()
        
        for task in failed_tasks_copy:
            # 重置重试计数和状态
            task.task_metadata.retry_count = 0
            task.task_metadata.status = TaskStatus.PENDING.value
            task.task_metadata.error_message = None
            task.task_metadata.started_at = None
            task.task_metadata.completed_at = None
            
            if max_retries is not None:
                task.max_retries = max_retries
            
            self._queue.append(task)
            requeued_count += 1
        
        # 重新排序
        self._queue.sort(key=lambda t: t.priority, reverse=True)
        
        logger.info(f"重新排队 {requeued_count} 个失败任务")
    
    def get_queue_statistics(self) -> Dict[str, Any]:
        """获取队列统计信息"""
        status = self.get_queue_status()
        
        # 计算平均处理时间
        completed_tasks = self.get_completed_tasks()
        processing_times = []
        
        for task in completed_tasks:
            if task.started_at and task.completed_at:
                duration = (task.completed_at - task.started_at).total_seconds()
                processing_times.append(duration)
        
        avg_processing_time = (
            sum(processing_times) / len(processing_times)
            if processing_times else 0.0
        )
        
        # 优先级分布
        priority_distribution = {}
        for task in self._queue:
            priority = task.priority
            priority_distribution[priority] = priority_distribution.get(priority, 0) + 1
        
        return {
            **status,
            'average_processing_time_seconds': avg_processing_time,
            'priority_distribution': priority_distribution,
            'retry_statistics': {
                'total_retries': sum(task.task_metadata.retry_count for task in 
                                   self._completed_tasks + self._failed_tasks),
                'tasks_with_retries': len([task for task in 
                                         self._completed_tasks + self._failed_tasks 
                                         if task.task_metadata.retry_count > 0])
            }
        }
    
    def export_queue_state(self) -> Dict[str, Any]:
        """导出队列状态（用于保存和恢复）"""
        return {
            'timestamp': datetime.now().isoformat(),
            'pending_tasks': [task.task_metadata.to_dict() for task in self._queue],
            'running_tasks': [task.task_metadata.to_dict() for task in self._running_tasks.values()],
            'completed_tasks': [task.task_metadata.to_dict() for task in self._completed_tasks],
            'failed_tasks': [task.task_metadata.to_dict() for task in self._failed_tasks],
            'statistics': self.get_queue_statistics()
        }
    
    def __len__(self) -> int:
        """队列长度"""
        return len(self._queue)
    
    def __bool__(self) -> bool:
        """队列是否为空"""
        return len(self._queue) > 0