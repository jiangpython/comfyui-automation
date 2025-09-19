"""任务结果管理器 - 统一管理数据库和JSON文件"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
import logging
import os

from .metadata_schema import TaskMetadata, TaskResult, GenerationStats, create_result_from_comfyui_output
from .task_database import TaskDatabase

logger = logging.getLogger(__name__)

class ResultManager:
    """任务结果管理器"""
    
    def __init__(self, 
                 database_path: Path,
                 output_directory: Path,
                 enable_json_metadata: bool = True,
                 enable_database: bool = True):
        
        self.database_path = Path(database_path)
        self.output_dir = Path(output_directory)
        self.enable_json = enable_json_metadata
        self.enable_db = enable_database
        
        # 创建输出目录
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.metadata_dir = self.output_dir / "metadata"
        if self.enable_json:
            self.metadata_dir.mkdir(exist_ok=True)
        
        # 初始化数据库
        self.db: Optional[TaskDatabase] = None
        if self.enable_db:
            self.db = TaskDatabase(database_path)
        
        logger.info(f"结果管理器初始化完成 - DB: {enable_database}, JSON: {enable_json_metadata}")
    
    def save_task(self, task: TaskMetadata) -> bool:
        """保存任务元数据"""
        success = True
        
        # 保存到数据库
        if self.enable_db and self.db:
            success &= self.db.save_task(task)
        
        # 保存JSON文件
        if self.enable_json:
            success &= self._save_task_json(task)
        
        return success
    
    def save_result(self, result: TaskResult) -> bool:
        """保存任务结果"""
        success = True
        
        # 保存到数据库
        if self.enable_db and self.db:
            success &= self.db.save_result(result)
        
        # 保存JSON文件
        if self.enable_json:
            success &= self._save_result_json(result)
        
        return success
    
    def save_task_complete(self, task: TaskMetadata, result: TaskResult) -> bool:
        """完整保存任务和结果"""
        # 更新任务状态
        task.status = "completed"
        task.completed_at = datetime.now()
        task.actual_time = result.generation_time
        
        # 保存任务和结果
        success = self.save_task(task) and self.save_result(result)
        
        # 创建组合的JSON文件（包含任务和结果）
        if self.enable_json and success:
            self._save_combined_json(task, result)
        
        return success
    
    def get_task(self, task_id: str) -> Optional[TaskMetadata]:
        """获取任务元数据"""
        # 优先从数据库获取
        if self.enable_db and self.db:
            task = self.db.get_task(task_id)
            if task:
                return task
        
        # 从JSON文件获取
        if self.enable_json:
            return self._load_task_json(task_id)
        
        return None
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        # 优先从数据库获取
        if self.enable_db and self.db:
            result = self.db.get_result(task_id)
            if result:
                return result
        
        # 从JSON文件获取
        if self.enable_json:
            return self._load_result_json(task_id)
        
        return None
    
    def get_task_with_result(self, task_id: str) -> Tuple[Optional[TaskMetadata], Optional[TaskResult]]:
        """同时获取任务和结果"""
        task = self.get_task(task_id)
        result = self.get_result(task_id)
        return task, result
    
    def list_tasks(self, **kwargs) -> List[TaskMetadata]:
        """列出任务"""
        if self.enable_db and self.db:
            return self.db.list_tasks(**kwargs)
        
        # JSON fallback
        if self.enable_json:
            return self._list_tasks_from_json(**kwargs)
        
        return []
    
    def search_tasks(self, **kwargs) -> List[TaskMetadata]:
        """搜索任务"""
        if self.enable_db and self.db:
            return self.db.search_tasks(**kwargs)
        
        # JSON fallback - 简化搜索
        if self.enable_json:
            return self._search_tasks_from_json(**kwargs)
        
        return []
    
    def update_task_status(self, task_id: str, status: str, **kwargs) -> bool:
        """更新任务状态"""
        success = True
        
        if self.enable_db and self.db:
            success &= self.db.update_task_status(task_id, status, **kwargs)
        
        if self.enable_json:
            # 更新JSON文件中的状态
            task = self._load_task_json(task_id)
            if task:
                task.status = status
                if 'error_message' in kwargs:
                    task.error_message = kwargs['error_message']
                if 'prompt_id' in kwargs:
                    task.prompt_id = kwargs['prompt_id']
                
                if status == "running":
                    task.started_at = datetime.now()
                elif status in ["completed", "failed", "cancelled"]:
                    task.completed_at = datetime.now()
                
                success &= self._save_task_json(task)
        
        return success
    
    def update_user_feedback(self, task_id: str, **kwargs) -> bool:
        """更新用户反馈"""
        success = True
        
        if self.enable_db and self.db:
            success &= self.db.update_user_feedback(task_id, **kwargs)
        
        if self.enable_json:
            task = self._load_task_json(task_id)
            if task:
                if 'rating' in kwargs:
                    task.user_rating = kwargs['rating']
                if 'tags' in kwargs:
                    task.user_tags = kwargs['tags']
                if 'notes' in kwargs:
                    task.user_notes = kwargs['notes']
                if 'is_favorite' in kwargs:
                    task.is_favorite = kwargs['is_favorite']
                
                success &= self._save_task_json(task)
        
        return success
    
    def delete_task(self, task_id: str, delete_files: bool = False) -> bool:
        """删除任务"""
        success = True
        
        # 获取文件信息用于删除
        if delete_files:
            result = self.get_result(task_id)
            if result:
                self._delete_task_files(result)
        
        # 从数据库删除
        if self.enable_db and self.db:
            success &= self.db.delete_task(task_id, False)  # 文件已经处理
        
        # 删除JSON文件
        if self.enable_json:
            success &= self._delete_task_json(task_id)
        
        return success
    
    def get_statistics(self, **kwargs) -> GenerationStats:
        """获取统计信息"""
        if self.enable_db and self.db:
            return self.db.get_statistics(**kwargs)
        
        # JSON fallback - 基础统计
        if self.enable_json:
            return self._calculate_json_statistics(**kwargs)
        
        return GenerationStats(
            start_date=datetime.now(),
            end_date=datetime.now()
        )
    
    def export_tasks(self, 
                    output_file: Path, 
                    format: str = "json",
                    task_ids: Optional[List[str]] = None,
                    include_results: bool = True) -> bool:
        """导出任务数据"""
        try:
            if task_ids:
                tasks_data = []
                for task_id in task_ids:
                    task, result = self.get_task_with_result(task_id)
                    if task:
                        data = task.to_dict()
                        if include_results and result:
                            data['result'] = result.to_dict()
                        tasks_data.append(data)
            else:
                # 导出所有任务
                tasks = self.list_tasks(limit=10000)  # 大数量限制
                tasks_data = []
                for task in tasks:
                    data = task.to_dict()
                    if include_results:
                        result = self.get_result(task.task_id)
                        if result:
                            data['result'] = result.to_dict()
                    tasks_data.append(data)
            
            # 保存文件
            if format.lower() == "json":
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump({
                        'export_date': datetime.now().isoformat(),
                        'total_tasks': len(tasks_data),
                        'include_results': include_results,
                        'tasks': tasks_data
                    }, f, indent=2, ensure_ascii=False)
            else:
                raise ValueError(f"不支持的导出格式: {format}")
            
            logger.info(f"导出完成: {len(tasks_data)} 个任务 -> {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"导出任务失败: {e}")
            return False
    
    def import_tasks(self, input_file: Path) -> Tuple[int, int]:
        """导入任务数据"""
        try:
            with open(input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            tasks_data = data.get('tasks', [])
            imported_count = 0
            error_count = 0
            
            for task_data in tasks_data:
                try:
                    # 导入任务
                    result_data = task_data.pop('result', None)
                    task = TaskMetadata.from_dict(task_data)
                    
                    if self.save_task(task):
                        imported_count += 1
                        
                        # 导入结果（如果有）
                        if result_data:
                            result = TaskResult.from_dict(result_data)
                            self.save_result(result)
                    else:
                        error_count += 1
                        
                except Exception as e:
                    logger.error(f"导入单个任务失败: {e}")
                    error_count += 1
            
            logger.info(f"导入完成: {imported_count} 成功, {error_count} 失败")
            return imported_count, error_count
            
        except Exception as e:
            logger.error(f"导入任务失败: {e}")
            return 0, 0
    
    def organize_output_files(self, task_id: str, 
                            source_files: List[Path],
                            create_subdirectory: bool = True,
                            batch_id: Optional[str] = None) -> TaskResult:
        """整理输出文件到管理目录（支持按批次目录归档）。"""
        
        # 目录策略：若提供 batch_id，则优先使用 batch_<id> 作为目录；否则回退 task_<task_id>
        if create_subdirectory:
            if batch_id:
                task_dir = self.output_dir / f"{batch_id}"
            else:
                task_dir = self.output_dir / f"task_{task_id}"
            task_dir.mkdir(exist_ok=True)
            storage_path = str(task_dir)
        else:
            task_dir = self.output_dir
            storage_path = str(self.output_dir)
        
        # 复制文件并收集信息
        output_files = []
        file_sizes = {}
        image_dimensions = {}
        
        for source_file in source_files:
            if not source_file.exists():
                continue
            
            # 生成目标文件名
            dest_file = task_dir / source_file.name
            
            # 复制文件
            shutil.copy2(source_file, dest_file)
            
            # 收集信息
            relative_path = str(dest_file.relative_to(task_dir))
            output_files.append(relative_path)
            file_sizes[relative_path] = dest_file.stat().st_size
            
            # 如果是图片，获取尺寸
            if dest_file.suffix.lower() in ['.png', '.jpg', '.jpeg', '.webp']:
                try:
                    from PIL import Image
                    with Image.open(dest_file) as img:
                        image_dimensions[relative_path] = img.size
                except ImportError:
                    logger.warning("PIL不可用，无法获取图片尺寸")
                except Exception as e:
                    logger.warning(f"获取图片尺寸失败: {e}")
        
        # 创建结果对象
        result = TaskResult(
            task_id=task_id,
            output_files=output_files,
            primary_image=output_files[0] if output_files else None,
            file_sizes_bytes=file_sizes,
            image_dimensions=image_dimensions,
            storage_path=storage_path,
            relative_paths=output_files
        )
        
        return result
    
    def cleanup_orphaned_files(self) -> int:
        """清理孤儿文件"""
        cleaned_count = 0
        
        try:
            # 获取所有任务ID
            tasks = self.list_tasks(limit=10000)
            valid_task_ids = {task.task_id for task in tasks}
            
            # 扫描输出目录
            for item in self.output_dir.iterdir():
                if item.is_dir() and item.name.startswith("task_"):
                    task_id = item.name[5:]  # 移除 "task_" 前缀
                    
                    if task_id not in valid_task_ids:
                        # 删除孤儿目录
                        shutil.rmtree(item)
                        cleaned_count += 1
                        logger.info(f"删除孤儿目录: {item}")
            
            # 清理元数据目录中的孤儿文件
            if self.metadata_dir.exists():
                for json_file in self.metadata_dir.glob("task_*.json"):
                    task_id = json_file.stem[5:]  # 移除 "task_" 前缀
                    
                    if task_id not in valid_task_ids:
                        json_file.unlink()
                        cleaned_count += 1
                        logger.info(f"删除孤儿元数据: {json_file}")
            
            return cleaned_count
            
        except Exception as e:
            logger.error(f"清理孤儿文件失败: {e}")
            return 0
    
    # JSON文件操作方法
    def _save_task_json(self, task: TaskMetadata) -> bool:
        """保存任务JSON文件"""
        try:
            task_file = self.metadata_dir / f"task_{task.task_id}.json"
            with open(task_file, 'w', encoding='utf-8') as f:
                json.dump(task.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存任务JSON失败: {e}")
            return False
    
    def _save_result_json(self, result: TaskResult) -> bool:
        """保存结果JSON文件"""
        try:
            result_file = self.metadata_dir / f"result_{result.task_id}.json"
            with open(result_file, 'w', encoding='utf-8') as f:
                json.dump(result.to_dict(), f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存结果JSON失败: {e}")
            return False
    
    def _save_combined_json(self, task: TaskMetadata, result: TaskResult) -> bool:
        """保存组合JSON文件"""
        try:
            combined_file = self.metadata_dir / f"complete_{task.task_id}.json"
            combined_data = {
                'task': task.to_dict(),
                'result': result.to_dict(),
                'created_at': datetime.now().isoformat()
            }
            with open(combined_file, 'w', encoding='utf-8') as f:
                json.dump(combined_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            logger.error(f"保存组合JSON失败: {e}")
            return False
    
    def _load_task_json(self, task_id: str) -> Optional[TaskMetadata]:
        """从JSON文件加载任务"""
        try:
            task_file = self.metadata_dir / f"task_{task_id}.json"
            if task_file.exists():
                with open(task_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return TaskMetadata.from_dict(data)
        except Exception as e:
            logger.error(f"加载任务JSON失败: {e}")
        return None
    
    def _load_result_json(self, task_id: str) -> Optional[TaskResult]:
        """从JSON文件加载结果"""
        try:
            result_file = self.metadata_dir / f"result_{task_id}.json"
            if result_file.exists():
                with open(result_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return TaskResult.from_dict(data)
        except Exception as e:
            logger.error(f"加载结果JSON失败: {e}")
        return None
    
    def _delete_task_json(self, task_id: str) -> bool:
        """删除任务JSON文件"""
        try:
            files_to_delete = [
                self.metadata_dir / f"task_{task_id}.json",
                self.metadata_dir / f"result_{task_id}.json",
                self.metadata_dir / f"complete_{task_id}.json"
            ]
            
            for file_path in files_to_delete:
                if file_path.exists():
                    file_path.unlink()
            
            return True
        except Exception as e:
            logger.error(f"删除任务JSON失败: {e}")
            return False
    
    def _delete_task_files(self, result: TaskResult):
        """删除任务相关文件"""
        try:
            task_dir = Path(result.storage_path)
            if task_dir.exists() and task_dir.is_dir():
                shutil.rmtree(task_dir)
                logger.info(f"删除任务文件目录: {task_dir}")
        except Exception as e:
            logger.error(f"删除任务文件失败: {e}")
    
    def _list_tasks_from_json(self, **kwargs) -> List[TaskMetadata]:
        """从JSON文件列出任务（简化版）"""
        tasks = []
        try:
            for json_file in self.metadata_dir.glob("task_*.json"):
                task = self._load_task_json(json_file.stem[5:])
                if task:
                    tasks.append(task)
            
            # 简单排序
            tasks.sort(key=lambda t: t.created_at, reverse=True)
            
            # 应用限制
            limit = kwargs.get('limit', 100)
            return tasks[:limit]
            
        except Exception as e:
            logger.error(f"从JSON列出任务失败: {e}")
            return []
    
    def _search_tasks_from_json(self, **kwargs) -> List[TaskMetadata]:
        """从JSON文件搜索任务（简化版）"""
        # 简化实现：先获取所有任务，然后过滤
        all_tasks = self._list_tasks_from_json()
        
        search_text = kwargs.get('search_text', '').lower()
        if not search_text:
            return all_tasks
        
        # 简单文本搜索
        filtered_tasks = []
        for task in all_tasks:
            if (search_text in task.prompt.lower() or 
                search_text in task.user_notes.lower()):
                filtered_tasks.append(task)
        
        return filtered_tasks[:kwargs.get('limit', 100)]
    
    def _calculate_json_statistics(self, **kwargs) -> GenerationStats:
        """从JSON文件计算统计（简化版）"""
        tasks = self._list_tasks_from_json(limit=10000)
        
        start_date = kwargs.get('start_date', datetime.now() - timedelta(days=30))
        end_date = kwargs.get('end_date', datetime.now())
        
        # 过滤日期范围
        filtered_tasks = [
            task for task in tasks 
            if start_date <= task.created_at <= end_date
        ]
        
        # 计算基础统计
        total_tasks = len(filtered_tasks)
        completed_tasks = len([t for t in filtered_tasks if t.status == 'completed'])
        failed_tasks = len([t for t in filtered_tasks if t.status == 'failed'])
        
        stats = GenerationStats(
            start_date=start_date,
            end_date=end_date,
            total_tasks=total_tasks,
            completed_tasks=completed_tasks,
            failed_tasks=failed_tasks
        )
        
        if total_tasks > 0:
            stats.success_rate = completed_tasks / total_tasks
        
        return stats
    
    def get_storage_info(self) -> Dict[str, Any]:
        """获取存储信息"""
        info = {
            'output_directory': str(self.output_dir),
            'metadata_directory': str(self.metadata_dir) if self.enable_json else None,
            'database_file': str(self.database_path) if self.enable_db else None,
            'storage_enabled': {
                'database': self.enable_db,
                'json_metadata': self.enable_json
            }
        }
        
        # 计算存储大小
        try:
            total_size = 0
            file_count = 0
            
            for file_path in self.output_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
                    file_count += 1
            
            info.update({
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'total_files': file_count,
                'subdirectories': len([d for d in self.output_dir.iterdir() if d.is_dir()])
            })
            
        except Exception as e:
            logger.error(f"计算存储大小失败: {e}")
            info.update({
                'total_size_mb': 0,
                'total_files': 0,
                'subdirectories': 0
            })
        
        return info
    
    def get_all_tasks(self) -> List[TaskMetadata]:
        """获取所有任务"""
        if self.enable_db and self.db:
            return self.db.get_all_tasks()
        elif self.enable_json:
            return self._list_tasks_from_json()
        else:
            logger.warning("没有启用任何存储后端")
            return []
    
    def get_tasks_by_status(self, status: str) -> List[TaskMetadata]:
        """根据状态获取任务"""
        if self.enable_db and self.db:
            return self.db.get_tasks_by_status(status)
        elif self.enable_json:
            all_tasks = self._list_tasks_from_json()
            return [task for task in all_tasks if task.status == status]
        else:
            return []
    
    def get_tasks_by_batch(self, batch_id: str) -> List[TaskMetadata]:
        """根据批次ID获取任务"""
        if self.enable_db and self.db:
            return self.db.get_tasks_by_batch(batch_id)
        elif self.enable_json:
            all_tasks = self._list_tasks_from_json()
            return [task for task in all_tasks if getattr(task, 'batch_id', None) == batch_id]
        else:
            return []