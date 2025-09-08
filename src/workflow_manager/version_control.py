"""工作流版本控制系统"""

import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging
import hashlib

logger = logging.getLogger(__name__)

class WorkflowVersion:
    """工作流版本信息"""
    
    def __init__(self, version: str, description: str = "", 
                 created_at: Optional[datetime] = None, author: str = ""):
        self.version = version
        self.description = description
        self.created_at = created_at or datetime.now()
        self.author = author
        self.hash: Optional[str] = None
        
    def to_dict(self) -> Dict[str, Any]:
        return {
            'version': self.version,
            'description': self.description,
            'created_at': self.created_at.isoformat(),
            'author': self.author,
            'hash': self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'WorkflowVersion':
        version_obj = cls(
            version=data['version'],
            description=data.get('description', ''),
            created_at=datetime.fromisoformat(data['created_at']),
            author=data.get('author', '')
        )
        version_obj.hash = data.get('hash')
        return version_obj

class WorkflowVersionControl:
    """工作流版本控制"""
    
    def __init__(self, workflow_dir: Path):
        self.workflow_dir = Path(workflow_dir)
        self.versions_dir = self.workflow_dir / "versions"
        self.history_file = self.workflow_dir / "version_history.json"
        
        # 创建版本目录
        self.versions_dir.mkdir(exist_ok=True)
        
        # 加载版本历史
        self.version_history: List[WorkflowVersion] = []
        self.load_version_history()
    
    def load_version_history(self):
        """加载版本历史"""
        if not self.history_file.exists():
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                history_data = json.load(f)
            
            self.version_history = [
                WorkflowVersion.from_dict(version_data)
                for version_data in history_data
            ]
            
            logger.debug(f"加载版本历史: {len(self.version_history)} 个版本")
            
        except Exception as e:
            logger.error(f"加载版本历史失败: {e}")
    
    def save_version_history(self):
        """保存版本历史"""
        try:
            history_data = [version.to_dict() for version in self.version_history]
            
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(history_data, f, indent=2, ensure_ascii=False)
                
            logger.debug("版本历史已保存")
            
        except Exception as e:
            logger.error(f"保存版本历史失败: {e}")
    
    def create_version(self, version: str, description: str = "", 
                      author: str = "") -> bool:
        """创建新版本"""
        
        # 检查版本是否已存在
        if self.version_exists(version):
            logger.error(f"版本 {version} 已存在")
            return False
        
        try:
            # 创建版本对象
            version_obj = WorkflowVersion(version, description, datetime.now(), author)
            
            # 创建版本目录
            version_dir = self.versions_dir / version
            version_dir.mkdir(exist_ok=True)
            
            # 复制当前文件到版本目录
            self._backup_current_files(version_dir)
            
            # 计算版本哈希
            version_obj.hash = self._calculate_version_hash(version_dir)
            
            # 添加到历史记录
            self.version_history.append(version_obj)
            self.version_history.sort(key=lambda v: v.created_at, reverse=True)
            
            # 保存历史记录
            self.save_version_history()
            
            logger.info(f"创建版本 {version} 成功")
            return True
            
        except Exception as e:
            logger.error(f"创建版本失败: {e}")
            return False
    
    def _backup_current_files(self, version_dir: Path):
        """备份当前文件到版本目录"""
        files_to_backup = [
            "config.yaml",
            "txt2img.json",  # 工作流文件
        ]
        
        for filename in files_to_backup:
            source_file = self.workflow_dir / filename
            if source_file.exists():
                dest_file = version_dir / filename
                shutil.copy2(source_file, dest_file)
                logger.debug(f"备份文件: {filename}")
    
    def _calculate_version_hash(self, version_dir: Path) -> str:
        """计算版本哈希值"""
        hash_md5 = hashlib.md5()
        
        # 对版本目录中的所有文件计算哈希
        for file_path in sorted(version_dir.rglob("*")):
            if file_path.is_file():
                with open(file_path, 'rb') as f:
                    for chunk in iter(lambda: f.read(4096), b""):
                        hash_md5.update(chunk)
        
        return hash_md5.hexdigest()
    
    def restore_version(self, version: str) -> bool:
        """恢复指定版本"""
        
        if not self.version_exists(version):
            logger.error(f"版本 {version} 不存在")
            return False
        
        try:
            version_dir = self.versions_dir / version
            
            # 备份当前版本（如果不是最新版本）
            if not self._is_latest_version(version):
                backup_version = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
                self.create_version(backup_version, f"恢复 {version} 前的自动备份")
            
            # 恢复文件
            files_to_restore = list(version_dir.glob("*"))
            for file_path in files_to_restore:
                if file_path.is_file():
                    dest_file = self.workflow_dir / file_path.name
                    shutil.copy2(file_path, dest_file)
                    logger.debug(f"恢复文件: {file_path.name}")
            
            logger.info(f"恢复版本 {version} 成功")
            return True
            
        except Exception as e:
            logger.error(f"恢复版本失败: {e}")
            return False
    
    def delete_version(self, version: str) -> bool:
        """删除版本"""
        
        if not self.version_exists(version):
            logger.error(f"版本 {version} 不存在")
            return False
        
        try:
            # 删除版本目录
            version_dir = self.versions_dir / version
            if version_dir.exists():
                shutil.rmtree(version_dir)
            
            # 从历史记录中删除
            self.version_history = [
                v for v in self.version_history if v.version != version
            ]
            
            # 保存历史记录
            self.save_version_history()
            
            logger.info(f"删除版本 {version} 成功")
            return True
            
        except Exception as e:
            logger.error(f"删除版本失败: {e}")
            return False
    
    def list_versions(self) -> List[Dict[str, Any]]:
        """列出所有版本"""
        return [version.to_dict() for version in self.version_history]
    
    def get_version_info(self, version: str) -> Optional[Dict[str, Any]]:
        """获取版本信息"""
        for version_obj in self.version_history:
            if version_obj.version == version:
                return version_obj.to_dict()
        return None
    
    def version_exists(self, version: str) -> bool:
        """检查版本是否存在"""
        return any(v.version == version for v in self.version_history)
    
    def get_latest_version(self) -> Optional[str]:
        """获取最新版本"""
        if not self.version_history:
            return None
        return self.version_history[0].version
    
    def _is_latest_version(self, version: str) -> bool:
        """检查是否为最新版本"""
        latest = self.get_latest_version()
        return latest == version if latest else False
    
    def compare_versions(self, version1: str, version2: str) -> Dict[str, Any]:
        """比较两个版本"""
        
        version1_info = self.get_version_info(version1)
        version2_info = self.get_version_info(version2)
        
        if not version1_info or not version2_info:
            return {'error': '版本不存在'}
        
        # 比较哈希值
        hash_different = version1_info['hash'] != version2_info['hash']
        
        # 比较文件
        version1_dir = self.versions_dir / version1
        version2_dir = self.versions_dir / version2
        
        file_differences = self._compare_version_files(version1_dir, version2_dir)
        
        return {
            'version1': version1_info,
            'version2': version2_info,
            'hash_different': hash_different,
            'file_differences': file_differences
        }
    
    def _compare_version_files(self, dir1: Path, dir2: Path) -> List[Dict[str, Any]]:
        """比较版本文件差异"""
        differences = []
        
        # 获取所有文件
        files1 = set(f.name for f in dir1.glob("*") if f.is_file())
        files2 = set(f.name for f in dir2.glob("*") if f.is_file())
        
        # 检查新增和删除的文件
        added_files = files2 - files1
        removed_files = files1 - files2
        common_files = files1 & files2
        
        for filename in added_files:
            differences.append({
                'file': filename,
                'type': 'added',
                'description': f'文件 {filename} 在新版本中添加'
            })
        
        for filename in removed_files:
            differences.append({
                'file': filename,
                'type': 'removed',
                'description': f'文件 {filename} 在新版本中删除'
            })
        
        # 检查修改的文件
        for filename in common_files:
            file1 = dir1 / filename
            file2 = dir2 / filename
            
            if not self._files_identical(file1, file2):
                differences.append({
                    'file': filename,
                    'type': 'modified',
                    'description': f'文件 {filename} 内容已修改'
                })
        
        return differences
    
    def _files_identical(self, file1: Path, file2: Path) -> bool:
        """检查两个文件是否相同"""
        try:
            with open(file1, 'rb') as f1, open(file2, 'rb') as f2:
                return f1.read() == f2.read()
        except Exception:
            return False
    
    def export_version(self, version: str, output_dir: Path) -> bool:
        """导出版本到指定目录"""
        
        if not self.version_exists(version):
            logger.error(f"版本 {version} 不存在")
            return False
        
        try:
            version_dir = self.versions_dir / version
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 复制版本文件
            for file_path in version_dir.glob("*"):
                if file_path.is_file():
                    dest_file = output_dir / file_path.name
                    shutil.copy2(file_path, dest_file)
            
            # 创建版本信息文件
            version_info = self.get_version_info(version)
            info_file = output_dir / "version_info.json"
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(version_info, f, indent=2, ensure_ascii=False)
            
            logger.info(f"版本 {version} 已导出到: {output_dir}")
            return True
            
        except Exception as e:
            logger.error(f"导出版本失败: {e}")
            return False
    
    def cleanup_old_versions(self, keep_count: int = 10) -> int:
        """清理旧版本，只保留指定数量的最新版本"""
        
        if len(self.version_history) <= keep_count:
            return 0
        
        # 按时间排序，保留最新的版本
        sorted_versions = sorted(
            self.version_history, 
            key=lambda v: v.created_at, 
            reverse=True
        )
        
        versions_to_delete = sorted_versions[keep_count:]
        deleted_count = 0
        
        for version_obj in versions_to_delete:
            if self.delete_version(version_obj.version):
                deleted_count += 1
        
        logger.info(f"清理了 {deleted_count} 个旧版本")
        return deleted_count
    
    def get_version_statistics(self) -> Dict[str, Any]:
        """获取版本统计信息"""
        if not self.version_history:
            return {
                'total_versions': 0,
                'latest_version': None,
                'oldest_version': None,
                'storage_size_mb': 0
            }
        
        # 计算存储大小
        total_size = 0
        if self.versions_dir.exists():
            for file_path in self.versions_dir.rglob("*"):
                if file_path.is_file():
                    total_size += file_path.stat().st_size
        
        sorted_versions = sorted(self.version_history, key=lambda v: v.created_at)
        
        return {
            'total_versions': len(self.version_history),
            'latest_version': self.version_history[0].version,
            'oldest_version': sorted_versions[0].version,
            'storage_size_mb': round(total_size / (1024 * 1024), 2),
            'versions_by_author': self._get_versions_by_author()
        }
    
    def _get_versions_by_author(self) -> Dict[str, int]:
        """统计各作者的版本数量"""
        author_counts = {}
        for version in self.version_history:
            author = version.author or 'Unknown'
            author_counts[author] = author_counts.get(author, 0) + 1
        return author_counts