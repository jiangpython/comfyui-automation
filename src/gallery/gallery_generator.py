"""HTML画廊生成器"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import logging
from dataclasses import asdict

from ..utils import ResultManager, TaskDatabase
from ..utils.metadata_schema import TaskMetadata

logger = logging.getLogger(__name__)

class GalleryGenerator:
    """HTML画廊生成器"""
    
    def __init__(self, 
                 result_manager: ResultManager,
                 template_dir: Path,
                 output_dir: Path):
        
        self.result_manager = result_manager
        self.template_dir = Path(template_dir)
        self.output_dir = Path(output_dir)
        self.gallery_data_file = self.output_dir / "gallery_data.json"
        
        logger.info("画廊生成器初始化完成")
    
    def generate_gallery(self, 
                        batch_ids: Optional[List[str]] = None,
                        status_filter: Optional[List[str]] = None,
                        date_from: Optional[datetime] = None,
                        date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """生成HTML画廊
        
        Args:
            batch_ids: 要包含的批次ID列表
            status_filter: 任务状态筛选 ['completed', 'failed']
            date_from: 开始日期
            date_to: 结束日期
            
        Returns:
            生成结果信息
        """
        
        logger.info("开始生成HTML画廊")
        
        try:
            # 1. 获取任务数据
            gallery_data = self._collect_gallery_data(
                batch_ids=batch_ids,
                status_filter=status_filter or ['completed'],
                date_from=date_from,
                date_to=date_to
            )
            
            # 2. 生成画廊JSON数据文件
            self._save_gallery_data(gallery_data)
            
            # 3. 复制静态文件
            self._copy_static_files()
            
            # 4. 生成HTML文件
            html_file = self._generate_html_file(gallery_data)
            
            # 5. 统计信息
            stats = self._calculate_stats(gallery_data)
            
            result = {
                'success': True,
                'html_file': str(html_file),
                'data_file': str(self.gallery_data_file),
                'total_images': len(gallery_data['images']),
                'stats': stats,
                'generated_at': datetime.now().isoformat()
            }
            
            logger.info(f"画廊生成成功: {result['total_images']} 张图片")
            return result
            
        except Exception as e:
            logger.error(f"画廊生成失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'generated_at': datetime.now().isoformat()
            }
    
    def _collect_gallery_data(self, 
                             batch_ids: Optional[List[str]] = None,
                             status_filter: List[str] = None,
                             date_from: Optional[datetime] = None,
                             date_to: Optional[datetime] = None) -> Dict[str, Any]:
        """收集画廊数据"""
        
        logger.debug("开始收集画廊数据")
        
        # 获取所有任务
        if batch_ids:
            # 根据批次ID筛选
            all_tasks = []
            for batch_id in batch_ids:
                batch_tasks = self.result_manager.get_tasks_by_batch(batch_id)
                all_tasks.extend(batch_tasks)
        else:
            # 获取所有任务
            all_tasks = self.result_manager.get_all_tasks()
        
        # 应用筛选条件
        filtered_tasks = self._apply_task_filters(
            all_tasks, status_filter, date_from, date_to
        )
        
        logger.debug(f"筛选后任务数量: {len(filtered_tasks)}")
        
        # 转换为画廊数据格式
        images = []
        tags = set()
        
        for task in filtered_tasks:
            # 获取任务结果
            result = self.result_manager.get_result(task.task_id)
            if not result or not result.output_files:
                continue
            
            # 构建图片数据
            image_data = self._build_image_data(task, result)
            if image_data:
                images.append(image_data)
                # 收集标签
                if hasattr(task, 'user_tags') and task.user_tags:
                    tags.update(task.user_tags)
        
        # 按创建时间降序排序
        images.sort(key=lambda x: x['created_at'], reverse=True)
        
        gallery_data = {
            'images': images,
            'tags': sorted(list(tags)),
            'metadata': {
                'total_images': len(images),
                'generated_at': datetime.now().isoformat(),
                'filters_applied': {
                    'batch_ids': batch_ids,
                    'status_filter': status_filter,
                    'date_from': date_from.isoformat() if date_from else None,
                    'date_to': date_to.isoformat() if date_to else None
                }
            }
        }
        
        logger.debug(f"收集完成: {len(images)} 张图片, {len(tags)} 个标签")
        return gallery_data
    
    def _apply_task_filters(self,
                           tasks: List[TaskMetadata],
                           status_filter: List[str],
                           date_from: Optional[datetime],
                           date_to: Optional[datetime]) -> List[TaskMetadata]:
        """应用任务筛选条件"""
        
        filtered = []
        
        for task in tasks:
            # 状态筛选
            if status_filter and task.status not in status_filter:
                continue
            
            # 日期筛选
            if date_from and task.created_at and task.created_at < date_from:
                continue
            
            if date_to and task.created_at and task.created_at > date_to:
                continue
            
            filtered.append(task)
        
        return filtered
    
    def _build_image_data(self, task: TaskMetadata, result) -> Optional[Dict[str, Any]]:
        """构建单张图片的数据"""
        
        try:
            # 查找主要输出图片
            primary_image = result.primary_image or result.output_files[0]
            image_path = Path(result.storage_path) / primary_image
            
            if not image_path.exists():
                logger.warning(f"图片文件不存在: {image_path}")
                return None
            
            # 获取图片信息
            image_info = self._get_image_info(image_path)
            
            # 构建相对路径（相对于画廊HTML文件）
            relative_path = self._get_relative_image_path(image_path)
            
            image_data = {
                'id': task.task_id,
                'title': f"Task {task.task_id}",
                'src': relative_path,
                'thumbnail': relative_path,  # 简化版本，实际可以生成缩略图
                'prompt': task.prompt,
                'status': task.status,
                'created_at': task.created_at.isoformat() if task.created_at else None,
                'completed_at': task.completed_at.isoformat() if task.completed_at else None,
                'generation_time': result.generation_time if hasattr(result, 'generation_time') else task.actual_time,
                'quality_score': task.quality_score,
                'tags': task.user_tags or [],
                'workflow_type': task.workflow_type,
                'workflow_params': task.workflow_params,
                'file_info': image_info,
                'batch_id': getattr(task, 'batch_id', None),
                'error_message': task.error_message if task.status == 'failed' else None
            }
            
            return image_data
            
        except Exception as e:
            logger.error(f"构建图片数据失败 {task.task_id}: {e}")
            return None
    
    def _get_image_info(self, image_path: Path) -> Dict[str, Any]:
        """获取图片文件信息"""
        
        try:
            stat = image_path.stat()
            
            # 尝试获取图片尺寸
            width, height = 0, 0
            try:
                from PIL import Image
                with Image.open(image_path) as img:
                    width, height = img.size
            except ImportError:
                logger.debug("PIL不可用，无法获取图片尺寸")
            except Exception as e:
                logger.debug(f"获取图片尺寸失败: {e}")
            
            return {
                'filename': image_path.name,
                'size_bytes': stat.st_size,
                'size_mb': round(stat.st_size / (1024 * 1024), 2),
                'width': width,
                'height': height,
                'resolution': f"{width}x{height}" if width > 0 else "未知",
                'modified_at': datetime.fromtimestamp(stat.st_mtime).isoformat()
            }
            
        except Exception as e:
            logger.error(f"获取图片信息失败: {e}")
            return {
                'filename': image_path.name,
                'size_bytes': 0,
                'size_mb': 0,
                'width': 0,
                'height': 0,
                'resolution': "未知"
            }
    
    def _get_relative_image_path(self, image_path: Path) -> str:
        """获取图片相对于HTML文件的路径"""
        
        try:
            # 计算相对路径
            html_dir = self.output_dir
            relative_path = image_path.relative_to(html_dir)
            
            # 转换为URL格式（使用正斜杠）
            return str(relative_path).replace('\\', '/')
            
        except ValueError:
            # 如果不在相对路径中，尝试创建软链接或复制
            logger.warning(f"图片不在输出目录中: {image_path}")
            
            # 创建images子目录
            images_dir = self.output_dir / "images"
            images_dir.mkdir(exist_ok=True)
            
            # 复制图片到画廊目录
            dest_path = images_dir / image_path.name
            if not dest_path.exists():
                shutil.copy2(image_path, dest_path)
                logger.debug(f"复制图片: {image_path} -> {dest_path}")
            
            return f"images/{image_path.name}"
    
    def _save_gallery_data(self, gallery_data: Dict[str, Any]):
        """保存画廊数据到JSON文件"""
        
        # 确保输出目录存在
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存JSON数据
        with open(self.gallery_data_file, 'w', encoding='utf-8') as f:
            json.dump(gallery_data, f, indent=2, ensure_ascii=False)
        
        logger.debug(f"画廊数据已保存: {self.gallery_data_file}")
    
    def _copy_static_files(self):
        """复制静态文件到输出目录"""
        
        try:
            # 创建静态文件目录
            static_dir = self.output_dir / "static"
            static_dir.mkdir(exist_ok=True)
            
            # 复制CSS文件
            src_css = self.template_dir.parent / "static" / "css"
            dest_css = static_dir / "css"
            if src_css.exists():
                if dest_css.exists():
                    shutil.rmtree(dest_css)
                shutil.copytree(src_css, dest_css)
                logger.debug(f"复制CSS文件: {src_css} -> {dest_css}")
            
            # 复制JavaScript文件
            src_js = self.template_dir.parent / "static" / "js"
            dest_js = static_dir / "js"
            if src_js.exists():
                if dest_js.exists():
                    shutil.rmtree(dest_js)
                shutil.copytree(src_js, dest_js)
                logger.debug(f"复制JavaScript文件: {src_js} -> {dest_js}")
            
            logger.debug("静态文件复制完成")
            
        except Exception as e:
            logger.error(f"复制静态文件失败: {e}")
    
    def _generate_html_file(self, gallery_data: Dict[str, Any]) -> Path:
        """生成HTML文件"""
        
        # 读取模板
        template_file = self.template_dir / "gallery.html"
        if not template_file.exists():
            raise FileNotFoundError(f"画廊模板不存在: {template_file}")
        
        with open(template_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        # 替换模板变量
        html_content = html_content.replace(
            '../static/', 'static/'
        )

        # 将画廊数据嵌入HTML
        gallery_data_script = f"""
    <script>
        // 画廊数据直接嵌入
        window.GALLERY_DATA = {json.dumps(gallery_data, ensure_ascii=False, indent=2)};
    </script>"""

        # 在</body>标签前插入数据脚本
        html_content = html_content.replace('</body>', gallery_data_script + '\n</body>')

        # 输出HTML文件
        html_file = self.output_dir / "gallery.html"
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.debug(f"HTML文件已生成: {html_file}")
        return html_file
    
    def _calculate_stats(self, gallery_data: Dict[str, Any]) -> Dict[str, Any]:
        """计算统计信息"""
        
        images = gallery_data['images']
        
        if not images:
            return {
                'total_images': 0,
                'success_rate': 0,
                'average_quality': 0,
                'average_generation_time': 0,
                'total_size_mb': 0,
                'status_distribution': {},
                'quality_distribution': {},
                'high_quality_count': 0
            }
        
        # 基础统计
        completed_count = sum(1 for img in images if img['status'] == 'completed')
        total_count = len(images)
        success_rate = completed_count / total_count if total_count > 0 else 0
        
        # 质量统计
        quality_scores = [img['quality_score'] for img in images if img['quality_score'] is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 时间统计
        generation_times = [img['generation_time'] for img in images if img['generation_time'] is not None]
        avg_time = sum(generation_times) / len(generation_times) if generation_times else 0
        
        # 大小统计
        total_size_mb = sum(img['file_info']['size_mb'] for img in images)
        
        # 状态分布
        status_dist = {}
        for img in images:
            status = img['status']
            status_dist[status] = status_dist.get(status, 0) + 1
        
        # 质量分布
        quality_dist = {'high': 0, 'medium': 0, 'low': 0}
        for score in quality_scores:
            if score >= 0.8:
                quality_dist['high'] += 1
            elif score >= 0.5:
                quality_dist['medium'] += 1
            else:
                quality_dist['low'] += 1
        
        return {
            'total_images': total_count,
            'success_rate': round(success_rate, 3),
            'average_quality': round(avg_quality, 3),
            'average_generation_time': round(avg_time, 1),
            'total_size_mb': round(total_size_mb, 1),
            'status_distribution': status_dist,
            'quality_distribution': quality_dist,
            'high_quality_count': quality_dist['high']
        }
    
    def update_gallery(self) -> Dict[str, Any]:
        """增量更新画廊（添加新生成的图片）"""
        
        logger.info("开始增量更新画廊")
        
        try:
            # 读取现有画廊数据
            existing_data = {}
            if self.gallery_data_file.exists():
                with open(self.gallery_data_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            
            # 获取现有图片ID
            existing_ids = set()
            if 'images' in existing_data:
                existing_ids = {img['id'] for img in existing_data['images']}
            
            # 获取新任务
            last_update = existing_data.get('metadata', {}).get('generated_at')
            date_from = None
            if last_update:
                date_from = datetime.fromisoformat(last_update.replace('Z', ''))
            
            # 收集新数据
            new_gallery_data = self._collect_gallery_data(
                status_filter=['completed'],
                date_from=date_from
            )
            
            # 过滤出真正的新图片
            new_images = [
                img for img in new_gallery_data['images']
                if img['id'] not in existing_ids
            ]
            
            if not new_images:
                logger.info("没有新图片需要更新")
                return {
                    'success': True,
                    'new_images_count': 0,
                    'total_images_count': len(existing_data.get('images', [])),
                    'updated_at': datetime.now().isoformat()
                }
            
            # 合并数据
            all_images = existing_data.get('images', []) + new_images
            all_images.sort(key=lambda x: x['created_at'], reverse=True)
            
            # 更新标签
            all_tags = set(existing_data.get('tags', []))
            for img in new_images:
                all_tags.update(img['tags'])
            
            # 重建画廊数据
            updated_gallery_data = {
                'images': all_images,
                'tags': sorted(list(all_tags)),
                'metadata': {
                    'total_images': len(all_images),
                    'generated_at': datetime.now().isoformat(),
                    'last_incremental_update': datetime.now().isoformat(),
                    'new_images_in_update': len(new_images)
                }
            }
            
            # 保存更新后的数据
            self._save_gallery_data(updated_gallery_data)
            
            # 复制静态文件（以防有更新）
            self._copy_static_files()
            
            # 重新生成HTML
            self._generate_html_file(updated_gallery_data)
            
            logger.info(f"画廊增量更新完成: 新增 {len(new_images)} 张图片")
            
            return {
                'success': True,
                'new_images_count': len(new_images),
                'total_images_count': len(all_images),
                'updated_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"画廊增量更新失败: {e}")
            return {
                'success': False,
                'error': str(e),
                'updated_at': datetime.now().isoformat()
            }
    
    def get_gallery_info(self) -> Dict[str, Any]:
        """获取画廊信息"""
        
        if not self.gallery_data_file.exists():
            return {
                'exists': False,
                'message': '画廊尚未生成'
            }
        
        try:
            with open(self.gallery_data_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            metadata = data.get('metadata', {})
            
            return {
                'exists': True,
                'html_file': str(self.output_dir / "gallery.html"),
                'total_images': metadata.get('total_images', 0),
                'generated_at': metadata.get('generated_at'),
                'last_update': metadata.get('last_incremental_update'),
                'tags_count': len(data.get('tags', [])),
                'file_size_mb': round(self.gallery_data_file.stat().st_size / (1024 * 1024), 2)
            }
            
        except Exception as e:
            logger.error(f"读取画廊信息失败: {e}")
            return {
                'exists': True,
                'error': f"读取失败: {e}"
            }