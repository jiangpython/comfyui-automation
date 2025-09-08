"""稳健的任务监控系统"""

import time
import logging
from typing import Optional, Dict, Any, List, Callable
from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

@dataclass
class MonitorResult:
    """监控结果"""
    status: str  # completed, failed, running, unknown
    confidence: float  # 0.0 - 1.0
    details: Dict[str, Any]

class TaskDetector(ABC):
    """任务检测器基类"""
    
    def __init__(self, name: str):
        self.name = name
        self.enabled = True
        self.last_error = None
    
    @abstractmethod
    def is_available(self) -> bool:
        """检查检测器是否可用"""
        pass
    
    @abstractmethod
    def check(self, prompt_id: str) -> MonitorResult:
        """检查任务状态"""
        pass

class HistoryDetector(TaskDetector):
    """历史记录检测器（主检测器）"""
    
    def __init__(self, client):
        super().__init__("history")
        self.client = client
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.client.is_connected
    
    def check(self, prompt_id: str) -> MonitorResult:
        """检查历史记录"""
        try:
            history = self.client.get_history(prompt_id)
            if history and prompt_id in history:
                return MonitorResult(
                    status="completed",
                    confidence=1.0,
                    details={"source": "history", "data": history[prompt_id]}
                )
            else:
                return MonitorResult(
                    status="unknown",
                    confidence=0.5,
                    details={"source": "history", "message": "not found in history"}
                )
        except Exception as e:
            logger.debug(f"历史记录检测失败: {e}")
            self.last_error = str(e)
            return MonitorResult(
                status="unknown",
                confidence=0.0,
                details={"source": "history", "error": str(e)}
            )

class QueueDetector(TaskDetector):
    """队列状态检测器"""
    
    def __init__(self, client):
        super().__init__("queue")
        self.client = client
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.client.is_connected
    
    def check(self, prompt_id: str) -> MonitorResult:
        """检查队列状态"""
        try:
            queue_status = self.client.get_queue_status()
            if not queue_status:
                return MonitorResult(
                    status="unknown",
                    confidence=0.0,
                    details={"source": "queue", "error": "no queue data"}
                )
            
            running = queue_status.get("queue_running", [])
            pending = queue_status.get("queue_pending", [])
            
            # 检查是否在运行队列中
            for item in running:
                if len(item) > 1 and item[1] == prompt_id:
                    return MonitorResult(
                        status="running",
                        confidence=0.9,
                        details={"source": "queue", "queue_position": "running"}
                    )
            
            # 检查是否在等待队列中
            for i, item in enumerate(pending):
                if len(item) > 1 and item[1] == prompt_id:
                    return MonitorResult(
                        status="running",
                        confidence=0.8,
                        details={"source": "queue", "queue_position": i}
                    )
            
            # 不在队列中，可能已完成或失败
            return MonitorResult(
                status="unknown",
                confidence=0.3,
                details={"source": "queue", "message": "not in queue"}
            )
            
        except Exception as e:
            logger.debug(f"队列状态检测失败: {e}")
            self.last_error = str(e)
            return MonitorResult(
                status="unknown",
                confidence=0.0,
                details={"source": "queue", "error": str(e)}
            )

class FileDetector(TaskDetector):
    """文件输出检测器（备用检测器）"""
    
    def __init__(self, output_directory: Path):
        super().__init__("file")
        self.output_directory = Path(output_directory)
    
    def is_available(self) -> bool:
        """检查是否可用"""
        return self.output_directory.exists()
    
    def check(self, prompt_id: str) -> MonitorResult:
        """检查输出文件"""
        try:
            # 这是一个简化的文件检查，实际实现需要更复杂的逻辑
            # 因为需要知道任务对应的文件名模式
            return MonitorResult(
                status="unknown",
                confidence=0.1,
                details={"source": "file", "message": "file detection not implemented"}
            )
        except Exception as e:
            logger.debug(f"文件检测失败: {e}")
            self.last_error = str(e)
            return MonitorResult(
                status="unknown",
                confidence=0.0,
                details={"source": "file", "error": str(e)}
            )

class TaskMonitor:
    """稳健的任务监控器"""
    
    def __init__(self, client, output_directory: Optional[Path] = None):
        self.client = client
        self.detectors: List[TaskDetector] = []
        
        # 初始化检测器
        self.detectors.append(HistoryDetector(client))
        self.detectors.append(QueueDetector(client))
        
        if output_directory:
            self.detectors.append(FileDetector(output_directory))
        
        # 监控参数
        self.max_retries = 3
        self.base_check_interval = 2  # 基础检查间隔（秒）
        self.max_check_interval = 10  # 最大检查间隔（秒）
        self.emergency_timeout = 1800  # 紧急超时（30分钟）
    
    def wait_for_completion(self, 
                          prompt_id: str, 
                          timeout: int = 600,
                          progress_callback: Optional[Callable] = None) -> bool:
        """等待任务完成"""
        start_time = time.time()
        consecutive_failures = 0
        last_known_status = None
        check_interval = self.base_check_interval
        
        logger.info(f"开始监控任务 {prompt_id}")
        
        while time.time() - start_time < timeout:
            try:
                # 执行检查
                current_status = self._check_all_detectors(prompt_id)
                
                # 处理检查结果
                if current_status == "completed":
                    logger.info(f"任务 {prompt_id} 完成")
                    return True
                elif current_status == "failed":
                    logger.warning(f"任务 {prompt_id} 失败")
                    return False
                elif current_status == "running":
                    last_known_status = "running"
                    consecutive_failures = 0
                    if progress_callback:
                        progress_callback(prompt_id, "running")
                
                # 健康检查和错误处理
                if current_status == "unknown":
                    consecutive_failures += 1
                    if consecutive_failures >= 5:
                        logger.warning(f"连续检测失败，启用紧急模式")
                        if self._emergency_mode_check(prompt_id):
                            return True
                        consecutive_failures = 0  # 重置计数器
                else:
                    consecutive_failures = 0
                
                # 动态调整检查间隔
                check_interval = self._calculate_check_interval(
                    time.time() - start_time, 
                    consecutive_failures
                )
                
                # 绝对超时检查
                if time.time() - start_time > self.emergency_timeout:
                    logger.error(f"任务 {prompt_id} 达到绝对超时限制")
                    return False
                
                time.sleep(check_interval)
                
            except KeyboardInterrupt:
                logger.info("用户中断任务监控")
                raise
            except Exception as e:
                logger.error(f"任务监控异常: {e}")
                consecutive_failures += 1
                time.sleep(5)  # 异常后等待较长时间
        
        # 超时处理
        logger.warning(f"任务 {prompt_id} 监控超时")
        return self._timeout_fallback(prompt_id, last_known_status)
    
    def _check_all_detectors(self, prompt_id: str) -> str:
        """使用所有检测器检查任务状态"""
        results = []
        
        for detector in self.detectors:
            if not detector.enabled:
                continue
            
            try:
                if detector.is_available():
                    result = detector.check(prompt_id)
                    results.append(result)
                    
                    logger.debug(f"检测器 {detector.name}: {result.status} (置信度: {result.confidence})")
                else:
                    logger.debug(f"检测器 {detector.name} 不可用")
            except Exception as e:
                logger.debug(f"检测器 {detector.name} 异常: {e}")
        
        # 聚合结果
        return self._aggregate_results(results)
    
    def _aggregate_results(self, results: List[MonitorResult]) -> str:
        """聚合多个检测结果"""
        if not results:
            return "unknown"
        
        # 按置信度排序
        results.sort(key=lambda x: x.confidence, reverse=True)
        
        # 优先级：completed > failed > running > unknown
        for result in results:
            if result.status == "completed" and result.confidence > 0.8:
                return "completed"
        
        for result in results:
            if result.status == "failed" and result.confidence > 0.8:
                return "failed"
        
        for result in results:
            if result.status == "running" and result.confidence > 0.5:
                return "running"
        
        return "unknown"
    
    def _emergency_mode_check(self, prompt_id: str) -> bool:
        """紧急模式检查"""
        logger.info("执行紧急模式检查")
        
        # 尝试最简单的检查方法
        for _ in range(3):
            try:
                history = self.client.get_history(prompt_id)
                if history and prompt_id in history:
                    logger.info("紧急模式检查：任务已完成")
                    return True
                time.sleep(5)
            except:
                pass
        
        logger.warning("紧急模式检查失败")
        return False
    
    def _calculate_check_interval(self, elapsed_time: float, consecutive_failures: int) -> float:
        """动态计算检查间隔"""
        # 基础间隔 + 失败惩罚 + 时间衰减
        interval = self.base_check_interval + consecutive_failures * 0.5
        
        # 运行时间越长，检查间隔越大
        if elapsed_time > 120:  # 2分钟后
            interval += min(elapsed_time / 60, 5)  # 最多增加5秒
        
        return min(interval, self.max_check_interval)
    
    def _timeout_fallback(self, prompt_id: str, last_known_status: Optional[str]) -> bool:
        """超时回退处理"""
        logger.warning(f"任务 {prompt_id} 超时，最后状态: {last_known_status}")
        
        # 最后一次尝试
        try:
            history = self.client.get_history(prompt_id)
            if history and prompt_id in history:
                logger.info("超时回退：发现任务已完成")
                return True
        except:
            pass
        
        return False
    
    def get_detector_status(self) -> Dict[str, Any]:
        """获取检测器状态"""
        status = {}
        for detector in self.detectors:
            status[detector.name] = {
                'enabled': detector.enabled,
                'available': detector.is_available(),
                'last_error': detector.last_error
            }
        return status