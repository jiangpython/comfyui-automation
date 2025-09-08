"""SQLite任务数据库管理"""

import sqlite3
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
import logging

from .metadata_schema import TaskMetadata, TaskResult, GenerationStats

logger = logging.getLogger(__name__)

class TaskDatabase:
    """任务数据库管理器"""
    
    def __init__(self, database_path: Path):
        self.db_path = Path(database_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 创建数据库连接
        self.init_database()
    
    def init_database(self):
        """初始化数据库表结构"""
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript('''
                -- 任务表
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    prompt TEXT NOT NULL,
                    workflow_type TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    workflow_params TEXT,  -- JSON
                    prompt_id TEXT,
                    error_message TEXT,
                    retry_count INTEGER DEFAULT 0,
                    negative_prompt TEXT DEFAULT '',
                    prompt_hash TEXT,
                    width INTEGER DEFAULT 1024,
                    height INTEGER DEFAULT 1024,
                    steps INTEGER DEFAULT 20,
                    cfg_scale REAL DEFAULT 7.0,
                    sampler TEXT DEFAULT 'euler',
                    scheduler TEXT DEFAULT 'normal',
                    seed INTEGER DEFAULT -1,
                    model_name TEXT DEFAULT '',
                    model_hash TEXT,
                    quality_score REAL,
                    estimated_time REAL,
                    actual_time REAL,
                    user_rating INTEGER,
                    user_tags TEXT,  -- JSON array
                    user_notes TEXT DEFAULT '',
                    is_favorite BOOLEAN DEFAULT 0,
                    comfyui_version TEXT DEFAULT '',
                    system_memory_mb INTEGER,
                    gpu_memory_mb INTEGER
                );
                
                -- 任务结果表
                CREATE TABLE IF NOT EXISTS task_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT NOT NULL,
                    output_files TEXT,  -- JSON array
                    primary_image TEXT,
                    file_sizes_bytes TEXT,  -- JSON dict
                    image_dimensions TEXT,  -- JSON dict
                    comfyui_output TEXT,  -- JSON
                    generation_log TEXT,  -- JSON array
                    generation_time REAL,
                    memory_usage TEXT,  -- JSON
                    gpu_utilization REAL,
                    image_analysis TEXT,  -- JSON
                    storage_path TEXT,
                    relative_paths TEXT,  -- JSON array
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks (task_id) ON DELETE CASCADE
                );
                
                -- 用户标签表
                CREATE TABLE IF NOT EXISTS user_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag_name TEXT UNIQUE NOT NULL,
                    usage_count INTEGER DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
                
                -- 性能统计表
                CREATE TABLE IF NOT EXISTS performance_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date DATE NOT NULL,
                    workflow_type TEXT,
                    total_tasks INTEGER DEFAULT 0,
                    completed_tasks INTEGER DEFAULT 0,
                    failed_tasks INTEGER DEFAULT 0,
                    average_time REAL,
                    total_storage_mb REAL DEFAULT 0,
                    stats_data TEXT,  -- JSON
                    UNIQUE(date, workflow_type)
                );
                
                -- 创建索引
                CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status);
                CREATE INDEX IF NOT EXISTS idx_tasks_created_at ON tasks(created_at);
                CREATE INDEX IF NOT EXISTS idx_tasks_workflow_type ON tasks(workflow_type);
                CREATE INDEX IF NOT EXISTS idx_tasks_prompt_hash ON tasks(prompt_hash);
                CREATE INDEX IF NOT EXISTS idx_tasks_quality_score ON tasks(quality_score);
                CREATE INDEX IF NOT EXISTS idx_tasks_user_rating ON tasks(user_rating);
                CREATE INDEX IF NOT EXISTS idx_tasks_is_favorite ON tasks(is_favorite);
                CREATE INDEX IF NOT EXISTS idx_results_task_id ON task_results(task_id);
                CREATE INDEX IF NOT EXISTS idx_results_created_at ON task_results(created_at);
            ''')
        
        logger.info(f"数据库初始化完成: {self.db_path}")
    
    def save_task(self, task: TaskMetadata) -> bool:
        """保存任务元数据"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT OR REPLACE INTO tasks (
                        task_id, prompt, workflow_type, status, created_at, started_at, completed_at,
                        workflow_params, prompt_id, error_message, retry_count, negative_prompt,
                        prompt_hash, width, height, steps, cfg_scale, sampler, scheduler, seed,
                        model_name, model_hash, quality_score, estimated_time, actual_time,
                        user_rating, user_tags, user_notes, is_favorite, comfyui_version,
                        system_memory_mb, gpu_memory_mb
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    task.task_id, task.prompt, task.workflow_type, task.status,
                    task.created_at, task.started_at, task.completed_at,
                    json.dumps(task.workflow_params), task.prompt_id, task.error_message,
                    task.retry_count, task.negative_prompt, task.prompt_hash,
                    task.width, task.height, task.steps, task.cfg_scale,
                    task.sampler, task.scheduler, task.seed, task.model_name, task.model_hash,
                    task.quality_score, task.estimated_time, task.actual_time,
                    task.user_rating, json.dumps(task.user_tags), task.user_notes,
                    task.is_favorite, task.comfyui_version, task.system_memory_mb, task.gpu_memory_mb
                ))
            
            # 更新用户标签统计
            self._update_tag_statistics(task.user_tags)
            
            logger.debug(f"任务保存成功: {task.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存任务失败: {e}")
            return False
    
    def save_result(self, result: TaskResult) -> bool:
        """保存任务结果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('''
                    INSERT INTO task_results (
                        task_id, output_files, primary_image, file_sizes_bytes,
                        image_dimensions, comfyui_output, generation_log, generation_time,
                        memory_usage, gpu_utilization, image_analysis, storage_path, relative_paths
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    result.task_id, json.dumps(result.output_files), result.primary_image,
                    json.dumps(result.file_sizes_bytes), json.dumps(result.image_dimensions),
                    json.dumps(result.comfyui_output), json.dumps(result.generation_log),
                    result.generation_time, json.dumps(result.memory_usage),
                    result.gpu_utilization, json.dumps(result.image_analysis),
                    result.storage_path, json.dumps(result.relative_paths)
                ))
            
            logger.debug(f"任务结果保存成功: {result.task_id}")
            return True
            
        except Exception as e:
            logger.error(f"保存任务结果失败: {e}")
            return False
    
    def get_task(self, task_id: str) -> Optional[TaskMetadata]:
        """获取单个任务"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('SELECT * FROM tasks WHERE task_id = ?', (task_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_task_metadata(row)
                return None
                
        except Exception as e:
            logger.error(f"获取任务失败: {e}")
            return None
    
    def get_result(self, task_id: str) -> Optional[TaskResult]:
        """获取任务结果"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute('SELECT * FROM task_results WHERE task_id = ? ORDER BY created_at DESC LIMIT 1', (task_id,))
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_task_result(row)
                return None
                
        except Exception as e:
            logger.error(f"获取任务结果失败: {e}")
            return None
    
    def list_tasks(self, 
                  status: Optional[str] = None,
                  workflow_type: Optional[str] = None,
                  limit: int = 100,
                  offset: int = 0,
                  order_by: str = "created_at",
                  order_desc: bool = True) -> List[TaskMetadata]:
        """列出任务"""
        try:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            
            if status:
                query += " AND status = ?"
                params.append(status)
            
            if workflow_type:
                query += " AND workflow_type = ?"
                params.append(workflow_type)
            
            order_direction = "DESC" if order_desc else "ASC"
            query += f" ORDER BY {order_by} {order_direction} LIMIT ? OFFSET ?"
            params.extend([limit, offset])
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_task_metadata(row) for row in rows]
                
        except Exception as e:
            logger.error(f"列出任务失败: {e}")
            return []
    
    def search_tasks(self, 
                    search_text: str = "",
                    tags: List[str] = None,
                    min_rating: Optional[int] = None,
                    date_range: Optional[Tuple[datetime, datetime]] = None,
                    only_favorites: bool = False,
                    limit: int = 100) -> List[TaskMetadata]:
        """搜索任务"""
        try:
            query = "SELECT * FROM tasks WHERE 1=1"
            params = []
            
            if search_text:
                query += " AND (prompt LIKE ? OR user_notes LIKE ?)"
                search_pattern = f"%{search_text}%"
                params.extend([search_pattern, search_pattern])
            
            if tags:
                # 搜索包含任一标签的任务
                tag_conditions = []
                for tag in tags:
                    tag_conditions.append("user_tags LIKE ?")
                    params.append(f'%"{tag}"%')
                query += " AND (" + " OR ".join(tag_conditions) + ")"
            
            if min_rating is not None:
                query += " AND user_rating >= ?"
                params.append(min_rating)
            
            if date_range:
                query += " AND created_at BETWEEN ? AND ?"
                params.extend([date_range[0], date_range[1]])
            
            if only_favorites:
                query += " AND is_favorite = 1"
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(query, params)
                rows = cursor.fetchall()
                
                return [self._row_to_task_metadata(row) for row in rows]
                
        except Exception as e:
            logger.error(f"搜索任务失败: {e}")
            return []
    
    def update_task_status(self, task_id: str, status: str, 
                          error_message: Optional[str] = None,
                          prompt_id: Optional[str] = None) -> bool:
        """更新任务状态"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                now = datetime.now()
                
                if status == "running":
                    conn.execute('''
                        UPDATE tasks SET status = ?, started_at = ?, prompt_id = ?
                        WHERE task_id = ?
                    ''', (status, now, prompt_id, task_id))
                elif status in ["completed", "failed", "cancelled"]:
                    conn.execute('''
                        UPDATE tasks SET status = ?, completed_at = ?, error_message = ?
                        WHERE task_id = ?
                    ''', (status, now, error_message, task_id))
                else:
                    conn.execute('''
                        UPDATE tasks SET status = ?, error_message = ?
                        WHERE task_id = ?
                    ''', (status, error_message, task_id))
            
            logger.debug(f"任务状态更新成功: {task_id} -> {status}")
            return True
            
        except Exception as e:
            logger.error(f"更新任务状态失败: {e}")
            return False
    
    def update_user_feedback(self, task_id: str, 
                           rating: Optional[int] = None,
                           tags: Optional[List[str]] = None,
                           notes: Optional[str] = None,
                           is_favorite: Optional[bool] = None) -> bool:
        """更新用户反馈"""
        try:
            updates = []
            params = []
            
            if rating is not None:
                updates.append("user_rating = ?")
                params.append(rating)
            
            if tags is not None:
                updates.append("user_tags = ?")
                params.append(json.dumps(tags))
                self._update_tag_statistics(tags)
            
            if notes is not None:
                updates.append("user_notes = ?")
                params.append(notes)
            
            if is_favorite is not None:
                updates.append("is_favorite = ?")
                params.append(is_favorite)
            
            if not updates:
                return True
            
            params.append(task_id)
            query = f"UPDATE tasks SET {', '.join(updates)} WHERE task_id = ?"
            
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(query, params)
            
            logger.debug(f"用户反馈更新成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"更新用户反馈失败: {e}")
            return False
    
    def delete_task(self, task_id: str, delete_files: bool = False) -> bool:
        """删除任务（级联删除结果）"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 如果需要删除文件，先获取文件列表
                if delete_files:
                    result = self.get_result(task_id)
                    if result:
                        # TODO: 删除实际文件
                        pass
                
                # 删除数据库记录（级联删除）
                conn.execute('DELETE FROM tasks WHERE task_id = ?', (task_id,))
            
            logger.info(f"任务删除成功: {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"删除任务失败: {e}")
            return False
    
    def get_statistics(self, 
                      start_date: Optional[datetime] = None,
                      end_date: Optional[datetime] = None,
                      workflow_type: Optional[str] = None) -> GenerationStats:
        """获取生成统计"""
        if not start_date:
            start_date = datetime.now() - timedelta(days=30)
        if not end_date:
            end_date = datetime.now()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                # 基础查询条件
                where_conditions = ["created_at BETWEEN ? AND ?"]
                params = [start_date, end_date]
                
                if workflow_type:
                    where_conditions.append("workflow_type = ?")
                    params.append(workflow_type)
                
                where_clause = " AND ".join(where_conditions)
                
                # 任务统计
                cursor = conn.execute(f'''
                    SELECT 
                        COUNT(*) as total_tasks,
                        SUM(CASE WHEN status = 'completed' THEN 1 ELSE 0 END) as completed_tasks,
                        SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed_tasks,
                        SUM(CASE WHEN status = 'cancelled' THEN 1 ELSE 0 END) as cancelled_tasks,
                        AVG(actual_time) as avg_time,
                        SUM(actual_time) as total_time,
                        AVG(quality_score) as avg_quality,
                        AVG(user_rating) as avg_rating,
                        SUM(CASE WHEN is_favorite = 1 THEN 1 ELSE 0 END) as total_favorites
                    FROM tasks WHERE {where_clause}
                ''', params)
                
                stats_row = cursor.fetchone()
                
                # 工作流分布
                cursor = conn.execute(f'''
                    SELECT workflow_type, COUNT(*) as count
                    FROM tasks WHERE {where_clause}
                    GROUP BY workflow_type
                ''', params)
                
                workflow_dist = dict(cursor.fetchall())
                
                # 创建统计对象
                stats = GenerationStats(
                    start_date=start_date,
                    end_date=end_date,
                    total_tasks=stats_row[0] or 0,
                    completed_tasks=stats_row[1] or 0,
                    failed_tasks=stats_row[2] or 0,
                    cancelled_tasks=stats_row[3] or 0,
                    average_generation_time=stats_row[4] or 0,
                    total_generation_time=stats_row[5] or 0,
                    average_quality_score=stats_row[6],
                    average_user_rating=stats_row[7],
                    total_favorites=stats_row[8] or 0,
                    workflow_distribution=workflow_dist
                )
                
                if stats.total_tasks > 0:
                    stats.success_rate = stats.completed_tasks / stats.total_tasks
                
                return stats
                
        except Exception as e:
            logger.error(f"获取统计失败: {e}")
            return GenerationStats(start_date=start_date, end_date=end_date)
    
    def _row_to_task_metadata(self, row: sqlite3.Row) -> TaskMetadata:
        """将数据库行转换为TaskMetadata对象"""
        return TaskMetadata(
            task_id=row['task_id'],
            prompt=row['prompt'],
            workflow_type=row['workflow_type'],
            status=row['status'],
            created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else datetime.now(),
            started_at=datetime.fromisoformat(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromisoformat(row['completed_at']) if row['completed_at'] else None,
            workflow_params=json.loads(row['workflow_params'] or '{}'),
            prompt_id=row['prompt_id'],
            error_message=row['error_message'],
            retry_count=row['retry_count'] or 0,
            negative_prompt=row['negative_prompt'] or '',
            prompt_hash=row['prompt_hash'],
            width=row['width'] or 1024,
            height=row['height'] or 1024,
            steps=row['steps'] or 20,
            cfg_scale=row['cfg_scale'] or 7.0,
            sampler=row['sampler'] or 'euler',
            scheduler=row['scheduler'] or 'normal',
            seed=row['seed'] or -1,
            model_name=row['model_name'] or '',
            model_hash=row['model_hash'],
            quality_score=row['quality_score'],
            estimated_time=row['estimated_time'],
            actual_time=row['actual_time'],
            user_rating=row['user_rating'],
            user_tags=json.loads(row['user_tags'] or '[]'),
            user_notes=row['user_notes'] or '',
            is_favorite=bool(row['is_favorite']),
            comfyui_version=row['comfyui_version'] or '',
            system_memory_mb=row['system_memory_mb'],
            gpu_memory_mb=row['gpu_memory_mb']
        )
    
    def _row_to_task_result(self, row: sqlite3.Row) -> TaskResult:
        """将数据库行转换为TaskResult对象"""
        return TaskResult(
            task_id=row['task_id'],
            output_files=json.loads(row['output_files'] or '[]'),
            primary_image=row['primary_image'],
            file_sizes_bytes=json.loads(row['file_sizes_bytes'] or '{}'),
            image_dimensions=json.loads(row['image_dimensions'] or '{}'),
            comfyui_output=json.loads(row['comfyui_output'] or '{}'),
            generation_log=json.loads(row['generation_log'] or '[]'),
            generation_time=row['generation_time'],
            memory_usage=json.loads(row['memory_usage'] or '{}') if row['memory_usage'] else None,
            gpu_utilization=row['gpu_utilization'],
            image_analysis=json.loads(row['image_analysis'] or '{}') if row['image_analysis'] else None,
            storage_path=row['storage_path'] or '',
            relative_paths=json.loads(row['relative_paths'] or '[]')
        )
    
    def _update_tag_statistics(self, tags: List[str]):
        """更新标签统计"""
        if not tags:
            return
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                for tag in tags:
                    conn.execute('''
                        INSERT INTO user_tags (tag_name, usage_count)
                        VALUES (?, 1)
                        ON CONFLICT(tag_name) DO UPDATE SET usage_count = usage_count + 1
                    ''', (tag,))
        except Exception as e:
            logger.error(f"更新标签统计失败: {e}")
    
    def get_popular_tags(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取热门标签"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    SELECT tag_name, usage_count FROM user_tags
                    ORDER BY usage_count DESC LIMIT ?
                ''', (limit,))
                
                return [{'tag': row[0], 'count': row[1]} for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"获取热门标签失败: {e}")
            return []
    
    def cleanup_old_data(self, days_to_keep: int = 90) -> int:
        """清理旧数据"""
        cutoff_date = datetime.now() - timedelta(days=days_to_keep)
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute('''
                    DELETE FROM tasks WHERE created_at < ? AND status IN ('failed', 'cancelled')
                ''', (cutoff_date,))
                
                deleted_count = cursor.rowcount
                logger.info(f"清理了 {deleted_count} 条旧数据")
                return deleted_count
                
        except Exception as e:
            logger.error(f"清理旧数据失败: {e}")
            return 0
    
    def vacuum_database(self):
        """压缩数据库"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute('VACUUM')
            logger.info("数据库压缩完成")
        except Exception as e:
            logger.error(f"数据库压缩失败: {e}")