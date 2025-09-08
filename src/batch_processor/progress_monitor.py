"""进度监控器"""

import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)

@dataclass
class ProgressSnapshot:
    """进度快照"""
    timestamp: datetime = field(default_factory=datetime.now)
    total_tasks: int = 0
    pending_tasks: int = 0
    running_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    average_time_per_task: float = 0.0
    estimated_remaining_time: float = 0.0
    current_task_id: Optional[str] = None
    current_task_progress: float = 0.0
    throughput_tasks_per_minute: float = 0.0
    memory_usage_mb: Optional[float] = None
    cpu_usage_percent: Optional[float] = None

@dataclass
class ProgressEvent:
    """进度事件"""
    event_type: str  # task_started, task_completed, task_failed, batch_started, batch_completed
    timestamp: datetime = field(default_factory=datetime.now)
    task_id: Optional[str] = None
    message: str = ""
    details: Dict[str, Any] = field(default_factory=dict)

class ProgressMonitor:
    """进度监控器"""
    
    def __init__(self, update_interval: float = 1.0):
        self.update_interval = update_interval
        self.snapshots: List[ProgressSnapshot] = []
        self.events: List[ProgressEvent] = []
        self.callbacks: List[Callable[[ProgressSnapshot], None]] = []
        
        # 监控状态
        self.start_time: Optional[datetime] = None
        self.last_update_time: Optional[datetime] = None
        self.is_monitoring = False
        
        # 性能统计
        self._task_start_times: Dict[str, datetime] = {}
        self._completed_task_times: List[float] = []
        
        logger.info(f"进度监控器初始化完成 (更新间隔: {update_interval}s)")
    
    def start_monitoring(self, total_tasks: int):
        """开始监控"""
        self.start_time = datetime.now()
        self.last_update_time = self.start_time
        self.is_monitoring = True
        
        # 记录开始事件
        self.add_event(ProgressEvent(
            event_type="batch_started",
            message=f"开始批量处理 {total_tasks} 个任务"
        ))
        
        logger.info(f"开始监控批量任务进度: {total_tasks} 个任务")
    
    def stop_monitoring(self):
        """停止监控"""
        if not self.is_monitoring:
            return
        
        self.is_monitoring = False
        end_time = datetime.now()
        total_duration = (end_time - self.start_time).total_seconds() if self.start_time else 0
        
        # 记录结束事件
        self.add_event(ProgressEvent(
            event_type="batch_completed",
            message=f"批量处理完成，总耗时: {total_duration:.1f}秒"
        ))
        
        logger.info(f"监控结束，总耗时: {total_duration:.1f}秒")
    
    def update_progress(self, queue_status: Dict[str, Any], 
                       current_task_id: Optional[str] = None,
                       current_task_progress: float = 0.0):
        """更新进度"""
        
        if not self.is_monitoring:
            return
        
        now = datetime.now()
        
        # 计算性能指标
        total_tasks = queue_status.get('total_added', 0)
        completed_tasks = queue_status.get('completed_count', 0)
        failed_tasks = queue_status.get('failed_count', 0)
        processed_tasks = completed_tasks + failed_tasks
        
        # 计算平均处理时间
        avg_time_per_task = self._calculate_average_task_time()
        
        # 计算吞吐量（任务/分钟）
        throughput = self._calculate_throughput(now)
        
        # 预估剩余时间
        remaining_tasks = queue_status.get('pending_count', 0) + queue_status.get('running_count', 0)
        estimated_remaining_time = (
            remaining_tasks * avg_time_per_task if avg_time_per_task > 0 else 0
        )
        
        # 创建进度快照
        snapshot = ProgressSnapshot(
            timestamp=now,
            total_tasks=total_tasks,
            pending_tasks=queue_status.get('pending_count', 0),
            running_tasks=queue_status.get('running_count', 0),
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks,
            success_rate=queue_status.get('success_rate', 0.0),
            average_time_per_task=avg_time_per_task,
            estimated_remaining_time=estimated_remaining_time,
            current_task_id=current_task_id,
            current_task_progress=current_task_progress,
            throughput_tasks_per_minute=throughput
        )
        
        # 添加系统资源信息
        try:
            import psutil
            process = psutil.Process()
            snapshot.memory_usage_mb = process.memory_info().rss / (1024 * 1024)
            snapshot.cpu_usage_percent = process.cpu_percent()
        except ImportError:
            pass  # psutil不可用时跳过
        except Exception as e:
            logger.debug(f"获取系统资源信息失败: {e}")
        
        # 保存快照
        self.snapshots.append(snapshot)
        
        # 限制快照数量
        max_snapshots = 1000
        if len(self.snapshots) > max_snapshots:
            self.snapshots = self.snapshots[-max_snapshots:]
        
        # 触发回调
        self._trigger_callbacks(snapshot)
        
        self.last_update_time = now
    
    def add_callback(self, callback: Callable[[ProgressSnapshot], None]):
        """添加进度回调函数"""
        self.callbacks.append(callback)
    
    def remove_callback(self, callback: Callable[[ProgressSnapshot], None]):
        """移除进度回调函数"""
        if callback in self.callbacks:
            self.callbacks.remove(callback)
    
    def add_event(self, event: ProgressEvent):
        """添加进度事件"""
        self.events.append(event)
        
        # 限制事件数量
        max_events = 500
        if len(self.events) > max_events:
            self.events = self.events[-max_events:]
        
        logger.debug(f"进度事件: {event.event_type} - {event.message}")
    
    def task_started(self, task_id: str, message: str = ""):
        """记录任务开始"""
        self._task_start_times[task_id] = datetime.now()
        self.add_event(ProgressEvent(
            event_type="task_started",
            task_id=task_id,
            message=message or f"任务开始: {task_id}"
        ))
    
    def task_completed(self, task_id: str, message: str = ""):
        """记录任务完成"""
        if task_id in self._task_start_times:
            start_time = self._task_start_times.pop(task_id)
            duration = (datetime.now() - start_time).total_seconds()
            self._completed_task_times.append(duration)
            
            # 限制记录数量
            if len(self._completed_task_times) > 100:
                self._completed_task_times = self._completed_task_times[-100:]
        
        self.add_event(ProgressEvent(
            event_type="task_completed",
            task_id=task_id,
            message=message or f"任务完成: {task_id}"
        ))
    
    def task_failed(self, task_id: str, error_message: str = ""):
        """记录任务失败"""
        # 清理开始时间记录
        self._task_start_times.pop(task_id, None)
        
        self.add_event(ProgressEvent(
            event_type="task_failed",
            task_id=task_id,
            message=error_message or f"任务失败: {task_id}",
            details={"error": error_message}
        ))
    
    def get_latest_snapshot(self) -> Optional[ProgressSnapshot]:
        """获取最新的进度快照"""
        return self.snapshots[-1] if self.snapshots else None
    
    def get_snapshots_in_range(self, start_time: datetime, 
                             end_time: datetime) -> List[ProgressSnapshot]:
        """获取指定时间范围内的快照"""
        return [
            snapshot for snapshot in self.snapshots
            if start_time <= snapshot.timestamp <= end_time
        ]
    
    def get_recent_events(self, count: int = 10) -> List[ProgressEvent]:
        """获取最近的事件"""
        return self.events[-count:] if self.events else []
    
    def get_events_by_type(self, event_type: str) -> List[ProgressEvent]:
        """根据类型获取事件"""
        return [event for event in self.events if event.event_type == event_type]
    
    def get_progress_summary(self) -> Dict[str, Any]:
        """获取进度摘要"""
        latest = self.get_latest_snapshot()
        if not latest:
            return {}
        
        total_duration = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        
        return {
            'total_tasks': latest.total_tasks,
            'completed_tasks': latest.completed_tasks,
            'failed_tasks': latest.failed_tasks,
            'pending_tasks': latest.pending_tasks,
            'running_tasks': latest.running_tasks,
            'success_rate_percent': latest.success_rate * 100,
            'progress_percent': (
                (latest.completed_tasks + latest.failed_tasks) / max(latest.total_tasks, 1) * 100
            ),
            'average_time_per_task_seconds': latest.average_time_per_task,
            'estimated_remaining_time_seconds': latest.estimated_remaining_time,
            'throughput_tasks_per_minute': latest.throughput_tasks_per_minute,
            'total_elapsed_time_seconds': total_duration,
            'current_task': {
                'task_id': latest.current_task_id,
                'progress_percent': latest.current_task_progress
            },
            'system_resources': {
                'memory_usage_mb': latest.memory_usage_mb,
                'cpu_usage_percent': latest.cpu_usage_percent
            }
        }
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """获取性能指标"""
        if not self.snapshots:
            return {}
        
        # 计算吞吐量趋势
        recent_snapshots = self.snapshots[-10:] if len(self.snapshots) >= 10 else self.snapshots
        throughputs = [s.throughput_tasks_per_minute for s in recent_snapshots if s.throughput_tasks_per_minute > 0]
        
        # 计算内存使用趋势
        memory_usages = [s.memory_usage_mb for s in recent_snapshots if s.memory_usage_mb is not None]
        
        return {
            'average_throughput': sum(throughputs) / len(throughputs) if throughputs else 0,
            'peak_throughput': max(throughputs) if throughputs else 0,
            'average_memory_usage_mb': sum(memory_usages) / len(memory_usages) if memory_usages else 0,
            'peak_memory_usage_mb': max(memory_usages) if memory_usages else 0,
            'task_time_statistics': {
                'min_time': min(self._completed_task_times) if self._completed_task_times else 0,
                'max_time': max(self._completed_task_times) if self._completed_task_times else 0,
                'avg_time': (
                    sum(self._completed_task_times) / len(self._completed_task_times)
                    if self._completed_task_times else 0
                )
            }
        }
    
    def export_progress_data(self) -> Dict[str, Any]:
        """导出进度数据"""
        return {
            'monitoring_session': {
                'start_time': self.start_time.isoformat() if self.start_time else None,
                'end_time': datetime.now().isoformat(),
                'is_monitoring': self.is_monitoring,
                'update_interval': self.update_interval
            },
            'summary': self.get_progress_summary(),
            'performance_metrics': self.get_performance_metrics(),
            'recent_events': [
                {
                    'event_type': event.event_type,
                    'timestamp': event.timestamp.isoformat(),
                    'task_id': event.task_id,
                    'message': event.message,
                    'details': event.details
                }
                for event in self.get_recent_events(20)
            ],
            'snapshots_count': len(self.snapshots),
            'events_count': len(self.events)
        }
    
    def _calculate_average_task_time(self) -> float:
        """计算平均任务处理时间"""
        if not self._completed_task_times:
            return 0.0
        return sum(self._completed_task_times) / len(self._completed_task_times)
    
    def _calculate_throughput(self, current_time: datetime) -> float:
        """计算吞吐量（任务/分钟）"""
        if not self.start_time or not self._completed_task_times:
            return 0.0
        
        elapsed_minutes = (current_time - self.start_time).total_seconds() / 60
        if elapsed_minutes <= 0:
            return 0.0
        
        return len(self._completed_task_times) / elapsed_minutes
    
    def _trigger_callbacks(self, snapshot: ProgressSnapshot):
        """触发所有进度回调"""
        for callback in self.callbacks:
            try:
                callback(snapshot)
            except Exception as e:
                logger.error(f"进度回调执行失败: {e}")
    
    def create_console_callback(self, detailed: bool = False) -> Callable[[ProgressSnapshot], None]:
        """创建控制台输出回调"""
        last_print_time = [0.0]  # 使用列表以便在闭包中修改
        
        def console_callback(snapshot: ProgressSnapshot):
            # 限制输出频率
            if time.time() - last_print_time[0] < 2.0:  # 每2秒最多输出一次
                return
            
            progress_percent = (
                (snapshot.completed_tasks + snapshot.failed_tasks) / 
                max(snapshot.total_tasks, 1) * 100
            )
            
            if detailed:
                print(f"[{snapshot.timestamp.strftime('%H:%M:%S')}] "
                     f"进度: {progress_percent:.1f}% "
                     f"({snapshot.completed_tasks + snapshot.failed_tasks}/{snapshot.total_tasks}) "
                     f"| 成功率: {snapshot.success_rate:.1%} "
                     f"| 平均时间: {snapshot.average_time_per_task:.1f}s "
                     f"| 吞吐量: {snapshot.throughput_tasks_per_minute:.1f}/min "
                     f"| 预计剩余: {snapshot.estimated_remaining_time/60:.1f}min")
            else:
                print(f"进度: {progress_percent:.1f}% "
                     f"({snapshot.completed_tasks + snapshot.failed_tasks}/{snapshot.total_tasks})")
            
            last_print_time[0] = time.time()
        
        return console_callback
    
    def clear_history(self, keep_recent: int = 100):
        """清理历史数据"""
        if len(self.snapshots) > keep_recent:
            self.snapshots = self.snapshots[-keep_recent:]
        
        if len(self.events) > keep_recent:
            self.events = self.events[-keep_recent:]
        
        if len(self._completed_task_times) > keep_recent:
            self._completed_task_times = self._completed_task_times[-keep_recent:]
        
        logger.info(f"清理历史数据，保留最近 {keep_recent} 条记录")