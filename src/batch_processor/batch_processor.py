"""批量处理器 - 集成所有模块的核心系统"""

import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
import logging

from ..prompt_generator import PromptGenerator
from ..workflow_manager import WorkflowManager, ParameterMapper
from ..comfyui_client import ComfyUIClient, TaskExecutor
from ..comfyui_client.task_executor import Task
from ..utils import ResultManager, TaskMetadata, TaskResult
from .task_queue import TaskQueue
from .progress_monitor import ProgressMonitor

logger = logging.getLogger(__name__)

class BatchProcessor:
    """批量处理器 - 系统核心"""
    
    def __init__(self,
                 # 基础配置
                 output_directory: Path,
                 database_path: Path,
                 workflows_directory: Path,
                 
                 # 组件配置
                 comfyui_settings = None,
                 enable_database: bool = True,
                 enable_json_metadata: bool = True,
                 
                 # 性能配置
                 max_concurrent_tasks: int = 1,
                 task_timeout: int = 600,
                 batch_delay: float = 2.0):
        
        self.output_dir = Path(output_directory)
        self.database_path = Path(database_path)
        self.workflows_dir = Path(workflows_directory)
        
        # 性能配置
        self.max_concurrent_tasks = max_concurrent_tasks
        self.task_timeout = task_timeout
        self.batch_delay = batch_delay
        
        # 初始化组件
        self._init_components(comfyui_settings, enable_database, enable_json_metadata)
        
        # 批量处理状态
        self.is_running = False
        self.is_paused = False
        self._stop_requested = False
        self._processing_thread: Optional[threading.Thread] = None
        
        logger.info("批量处理器初始化完成")
    
    def _init_components(self, comfyui_settings, enable_database: bool, enable_json_metadata: bool):
        """初始化所有组件"""
        
        # 提示词生成器
        self.prompt_generator = PromptGenerator()
        logger.debug("提示词生成器初始化完成")
        
        # 工作流管理器
        self.workflow_manager = WorkflowManager(self.workflows_dir)
        logger.debug(f"工作流管理器初始化完成，加载了 {len(self.workflow_manager)} 个工作流")
        
        # ComfyUI客户端
        self.comfyui_client = ComfyUIClient(comfyui_settings)
        logger.debug("ComfyUI客户端初始化完成")
        
        # 任务执行器
        self.task_executor = TaskExecutor(self.comfyui_client, self.workflow_manager)
        self.task_executor.task_timeout = self.task_timeout
        self.task_executor.batch_delay = self.batch_delay
        logger.debug("任务执行器初始化完成")
        
        # 结果管理器
        self.result_manager = ResultManager(
            database_path=self.database_path,
            output_directory=self.output_dir,
            enable_database=enable_database,
            enable_json_metadata=enable_json_metadata
        )
        logger.debug("结果管理器初始化完成")
        
        # 任务队列
        self.task_queue = TaskQueue()
        logger.debug("任务队列初始化完成")
        
        # 进度监控器
        self.progress_monitor = ProgressMonitor()
        logger.debug("进度监控器初始化完成")
    
    def add_progress_callback(self, callback: Callable):
        """添加进度监控回调"""
        self.progress_monitor.add_callback(callback)
    
    def create_batch_from_subject(self, 
                                subject: str,
                                variation_count: int = 20,
                                workflow_type: str = "txt2img",
                                workflow_params: Optional[Dict[str, Any]] = None) -> List[str]:
        """从主题创建批量任务"""
        
        logger.info(f"从主题创建批量任务: '{subject}', {variation_count} 个变体")
        
        # 生成提示词变体
        prompt_variations = self.prompt_generator.generate_variations(
            base_subject=subject,
            variation_count=variation_count
        )
        
        # 添加到任务队列
        task_ids = self.task_queue.add_tasks_from_generated_prompts(
            generated_prompts=prompt_variations,
            workflow_type=workflow_type,
            base_params=workflow_params or {}
        )
        
        logger.info(f"批量任务创建完成: {len(task_ids)} 个任务")
        return task_ids
    
    def create_batch_from_prompts(self,
                                prompts: List[str],
                                workflow_type: str = "txt2img", 
                                workflow_params: Optional[Dict[str, Any]] = None) -> List[str]:
        """从提示词列表创建批量任务"""
        
        logger.info(f"从提示词列表创建批量任务: {len(prompts)} 个提示词")
        
        task_ids = self.task_queue.add_tasks_from_prompts(
            prompts=prompts,
            workflow_type=workflow_type,
            base_params=workflow_params or {}
        )
        
        logger.info(f"批量任务创建完成: {len(task_ids)} 个任务")
        return task_ids
    
    def create_exhaustive_batch(self,
                              subjects: List[str],
                              styles: Optional[List[str]] = None,
                              max_combinations: int = 50,
                              workflow_type: str = "txt2img",
                              workflow_params: Optional[Dict[str, Any]] = None) -> List[str]:
        """创建穷举式批量任务"""
        
        logger.info(f"创建穷举式批量任务: {len(subjects)} 个主题")
        
        # 生成穷举式提示词组合
        exhaustive_prompts = self.prompt_generator.generate_exhaustive_prompts(
            subjects=subjects,
            styles=styles,
            max_combinations=max_combinations
        )
        
        # 添加到任务队列
        task_ids = self.task_queue.add_tasks_from_generated_prompts(
            generated_prompts=exhaustive_prompts,
            workflow_type=workflow_type,
            base_params=workflow_params or {}
        )
        
        logger.info(f"穷举式批量任务创建完成: {len(task_ids)} 个任务")
        return task_ids
    
    def start_batch_processing(self, 
                             max_concurrent: Optional[int] = None,
                             console_output: bool = True) -> bool:
        """开始批量处理"""
        
        if self.is_running:
            logger.warning("批量处理已在运行中")
            return False
        
        if not self.task_queue:
            logger.warning("任务队列为空，无法开始处理")
            return False
        
        # 启动ComfyUI
        logger.info("启动ComfyUI服务...")
        if not self.comfyui_client.start_service():
            logger.error("无法启动ComfyUI服务")
            return False
        
        # 设置并发数
        if max_concurrent:
            self.max_concurrent_tasks = max_concurrent
        
        # 添加控制台输出回调
        if console_output:
            console_callback = self.progress_monitor.create_console_callback(detailed=True)
            self.progress_monitor.add_callback(console_callback)
        
        # 开始监控
        total_tasks = len(self.task_queue._queue) + len(self.task_queue._running_tasks)
        self.progress_monitor.start_monitoring(total_tasks)
        
        # 重置状态
        self.is_running = True
        self.is_paused = False
        self._stop_requested = False
        
        # 启动处理线程
        self._processing_thread = threading.Thread(
            target=self._batch_processing_loop,
            name="BatchProcessor"
        )
        self._processing_thread.start()
        
        logger.info(f"批量处理已开始: {total_tasks} 个任务, 并发数: {self.max_concurrent_tasks}")
        return True
    
    def pause_processing(self):
        """暂停批量处理"""
        if not self.is_running:
            return
        
        self.is_paused = True
        logger.info("批量处理已暂停")
    
    def resume_processing(self):
        """恢复批量处理"""
        if not self.is_running or not self.is_paused:
            return
        
        self.is_paused = False
        logger.info("批量处理已恢复")
    
    def stop_processing(self, wait_for_completion: bool = True) -> bool:
        """停止批量处理"""
        if not self.is_running:
            return True
        
        logger.info("正在停止批量处理...")
        self._stop_requested = True
        
        # 取消待处理任务
        self.task_queue.cancel_all_tasks()
        
        # 等待处理线程结束
        if wait_for_completion and self._processing_thread:
            self._processing_thread.join(timeout=30)  # 最多等待30秒
            if self._processing_thread.is_alive():
                logger.warning("处理线程未能正常结束")
                return False
        
        self.is_running = False
        self.progress_monitor.stop_monitoring()
        
        # 清理ComfyUI连接
        self.comfyui_client.cleanup()
        
        logger.info("批量处理已停止")
        return True
    
    def get_processing_status(self) -> Dict[str, Any]:
        """获取处理状态"""
        queue_status = self.task_queue.get_queue_status()
        progress_summary = self.progress_monitor.get_progress_summary()
        
        return {
            'is_running': self.is_running,
            'is_paused': self.is_paused,
            'comfyui_connected': self.comfyui_client.is_connected,
            'queue_status': queue_status,
            'progress_summary': progress_summary,
            'system_resources': progress_summary.get('system_resources', {}),
            'concurrent_tasks': self.max_concurrent_tasks,
            'performance_metrics': self.progress_monitor.get_performance_metrics()
        }
    
    def get_batch_results(self) -> Dict[str, Any]:
        """获取批量处理结果"""
        completed_tasks = self.task_queue.get_completed_tasks()
        failed_tasks = self.task_queue.get_failed_tasks()
        
        # 收集结果文件
        result_files = []
        for task in completed_tasks:
            result = self.result_manager.get_result(task.task_id)
            if result and result.output_files:
                result_files.extend([
                    str(Path(result.storage_path) / file)
                    for file in result.output_files
                ])
        
        return {
            'summary': {
                'total_completed': len(completed_tasks),
                'total_failed': len(failed_tasks),
                'success_rate': len(completed_tasks) / max(len(completed_tasks) + len(failed_tasks), 1),
                'total_output_files': len(result_files)
            },
            'completed_tasks': [task.to_dict() for task in completed_tasks],
            'failed_tasks': [task.to_dict() for task in failed_tasks],
            'output_files': result_files,
            'statistics': self.result_manager.get_statistics()
        }
    
    def _batch_processing_loop(self):
        """批量处理主循环"""
        try:
            while not self._stop_requested and self.task_queue:
                if self.is_paused:
                    time.sleep(1.0)
                    continue
                
                # 获取下一个任务
                queued_task = self.task_queue.get_next_task()
                if not queued_task:
                    break
                
                task_metadata = queued_task.task_metadata
                
                # 更新进度监控
                self.progress_monitor.task_started(task_metadata.task_id)
                
                # 执行任务
                success = self._process_single_task(queued_task)
                
                # 更新任务完成状态
                if success:
                    self.task_queue.complete_task(task_metadata.task_id, success=True)
                    self.progress_monitor.task_completed(task_metadata.task_id)
                else:
                    error_message = task_metadata.error_message or "未知错误"
                    self.task_queue.complete_task(
                        task_metadata.task_id, 
                        success=False, 
                        error_message=error_message
                    )
                    self.progress_monitor.task_failed(task_metadata.task_id, error_message)
                
                # 更新进度
                self.progress_monitor.update_progress(
                    queue_status=self.task_queue.get_queue_status(),
                    current_task_id=None  # 任务已完成
                )
                
                # 批次间延迟
                if not self._stop_requested:
                    time.sleep(self.batch_delay)
            
        except Exception as e:
            logger.error(f"批量处理循环异常: {e}")
        finally:
            self.is_running = False
            self.progress_monitor.stop_monitoring()
            logger.info("批量处理循环结束")
    
    def _process_single_task(self, queued_task) -> bool:
        """处理单个任务"""
        task_metadata = queued_task.task_metadata
        
        try:
            # 保存任务到数据库
            self.result_manager.update_task_status(
                task_metadata.task_id, 
                "running",
                prompt_id=None
            )
            
            # 创建工作流
            workflow_data = self.workflow_manager.create_workflow_from_task(
                task_metadata.workflow_type,
                {
                    'task_id': task_metadata.task_id,
                    'prompt': task_metadata.prompt,
                    'workflow_params': task_metadata.workflow_params
                }
            )
            
            # 创建ComfyUI任务
            comfyui_task = Task(
                id=task_metadata.task_id,
                prompt=task_metadata.prompt,
                workflow_params=workflow_data,
                metadata=task_metadata.to_dict()
            )
            
            # 执行任务（带超时和重试）
            def progress_callback(tid, status):
                self.progress_monitor.update_progress(
                    queue_status=self.task_queue.get_queue_status(),
                    current_task_id=tid,
                    current_task_progress=0.5 if status == 'running' else 1.0
                )
            
            success = self.task_executor.execute_with_retry(
                task=comfyui_task,
                max_retries=queued_task.max_retries
            )
            
            if success:
                # 处理任务结果
                self._handle_task_success(task_metadata, comfyui_task)
                return True
            else:
                # 处理任务失败
                self._handle_task_failure(task_metadata, comfyui_task.error)
                return False
                
        except Exception as e:
            logger.error(f"处理任务异常 {task_metadata.task_id}: {e}")
            self._handle_task_failure(task_metadata, str(e))
            return False
    
    def _handle_task_success(self, task_metadata: TaskMetadata, comfyui_task: Task):
        """处理任务成功"""
        try:
            # 更新任务状态
            task_metadata.status = "completed"
            task_metadata.completed_at = datetime.now()
            task_metadata.prompt_id = comfyui_task.prompt_id
            
            # 计算执行时间
            if task_metadata.started_at:
                duration = (task_metadata.completed_at - task_metadata.started_at).total_seconds()
                task_metadata.actual_time = duration
            
            # 查找输出文件
            output_files = self._find_output_files(task_metadata.task_id)
            
            # 创建任务结果
            result = TaskResult(
                task_id=task_metadata.task_id,
                output_files=[f.name for f in output_files],
                primary_image=output_files[0].name if output_files else None,
                generation_time=task_metadata.actual_time,
                storage_path=str(self.output_dir)
            )
            
            # 整理输出文件
            if output_files:
                organized_result = self.result_manager.organize_output_files(
                    task_metadata.task_id,
                    output_files,
                    create_subdirectory=True
                )
                result = organized_result
            
            # 保存任务和结果
            self.result_manager.save_task_complete(task_metadata, result)
            
            logger.info(f"任务完成: {task_metadata.task_id}")
            
        except Exception as e:
            logger.error(f"处理任务成功时出错: {e}")
            # 即使处理成功信息时出错，任务仍然是成功的
    
    def _handle_task_failure(self, task_metadata: TaskMetadata, error_message: str):
        """处理任务失败"""
        task_metadata.status = "failed"
        task_metadata.error_message = error_message
        task_metadata.completed_at = datetime.now()
        
        # 保存失败任务
        self.result_manager.save_task(task_metadata)
        
        logger.error(f"任务失败: {task_metadata.task_id} - {error_message}")
    
    def _find_output_files(self, task_id: str) -> List[Path]:
        """查找任务输出文件"""
        output_files = []
        
        # 在ComfyUI的输出目录中查找
        comfyui_output_dir = Path("D:/LM/ComfyUI/output")  # 默认ComfyUI输出目录
        
        if comfyui_output_dir.exists():
            # 查找包含任务ID的文件
            for file_path in comfyui_output_dir.glob(f"*{task_id}*"):
                if file_path.is_file() and file_path.suffix.lower() in ['.png', '.jpg', '.jpeg']:
                    output_files.append(file_path)
        
        # 按修改时间排序
        output_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)
        
        return output_files
    
    def cleanup(self):
        """清理资源"""
        try:
            # 停止处理
            if self.is_running:
                self.stop_processing()
            
            # 清理ComfyUI连接
            self.comfyui_client.cleanup()
            
            logger.info("批量处理器清理完成")
            
        except Exception as e:
            logger.error(f"清理资源时出错: {e}")
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()