"""提示词元素管理"""

import yaml
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Set
from dataclasses import dataclass

@dataclass
class PromptElement:
    """单个提示词元素"""
    name: str
    weight: float = 1.0
    aliases: List[str] = None
    enhancers: List[str] = None
    conflicts: List[str] = None
    category: str = ""
    description: str = ""
    
    def __post_init__(self):
        if self.aliases is None:
            self.aliases = []
        if self.enhancers is None:
            self.enhancers = []
        if self.conflicts is None:
            self.conflicts = []

@dataclass
class PromptTemplate:
    """提示词模板"""
    pattern: str
    weight: float = 1.0
    description: str = ""

class PromptElements:
    """提示词元素库管理器"""
    
    def __init__(self, elements_file: Optional[str] = None):
        self.elements_file = elements_file or self._get_default_elements_path()
        self.elements: Dict[str, List[PromptElement]] = {}
        self.templates: List[PromptTemplate] = []
        self.load()
    
    def _get_default_elements_path(self) -> Path:
        """获取默认元素文件路径"""
        return Path(__file__).parent.parent.parent / "data" / "prompt_elements.yaml"
    
    def load(self):
        """加载元素配置文件"""
        try:
            with open(self.elements_file, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
            
            # 加载各类元素
            for element_type, elements_data in data.items():
                if element_type == 'templates':
                    self._load_templates(elements_data)
                else:
                    self._load_elements(element_type, elements_data)
                    
        except Exception as e:
            raise Exception(f"加载元素文件失败: {e}")
    
    def _load_elements(self, element_type: str, elements_data: List[Dict]):
        """加载指定类型的元素"""
        elements = []
        for item in elements_data:
            element = PromptElement(
                name=item['name'],
                weight=item.get('weight', 1.0),
                aliases=item.get('aliases', []),
                enhancers=item.get('enhancers', []),
                conflicts=item.get('conflicts', []),
                category=item.get('category', ''),
                description=item.get('description', '')
            )
            elements.append(element)
        
        self.elements[element_type] = elements
    
    def _load_templates(self, templates_data: List[Dict]):
        """加载模板"""
        for item in templates_data:
            template = PromptTemplate(
                pattern=item['pattern'],
                weight=item.get('weight', 1.0),
                description=item.get('description', '')
            )
            self.templates.append(template)
    
    def get_element_types(self) -> List[str]:
        """获取所有元素类型"""
        return list(self.elements.keys())
    
    def get_elements(self, element_type: str) -> List[PromptElement]:
        """获取指定类型的所有元素"""
        return self.elements.get(element_type, [])
    
    def get_random_element(self, element_type: str, exclude: Optional[Set[str]] = None) -> Optional[PromptElement]:
        """随机获取指定类型的元素"""
        elements = self.get_elements(element_type)
        if not elements:
            return None
        
        # 过滤排除的元素
        if exclude:
            elements = [e for e in elements if e.name not in exclude]
        
        if not elements:
            return None
        
        # 基于权重的随机选择
        weights = [e.weight for e in elements]
        return random.choices(elements, weights=weights)[0]
    
    def get_random_template(self) -> Optional[PromptTemplate]:
        """随机获取模板"""
        if not self.templates:
            return None
        
        weights = [t.weight for t in self.templates]
        return random.choices(self.templates, weights=weights)[0]
    
    def check_conflicts(self, selected_elements: Dict[str, PromptElement]) -> List[str]:
        """检查元素间的冲突"""
        conflicts = []
        
        for element_type, element in selected_elements.items():
            if element.conflicts:
                for other_type, other_element in selected_elements.items():
                    if other_element.name in element.conflicts:
                        conflicts.append(f"{element.name} 与 {other_element.name} 冲突")
        
        return conflicts
    
    def get_element_by_name(self, element_type: str, name: str) -> Optional[PromptElement]:
        """根据名称获取元素"""
        elements = self.get_elements(element_type)
        for element in elements:
            if element.name == name or name in element.aliases:
                return element
        return None
    
    def get_elements_by_category(self, element_type: str, category: str) -> List[PromptElement]:
        """根据分类获取元素"""
        elements = self.get_elements(element_type)
        return [e for e in elements if e.category == category]
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取元素库统计信息"""
        stats = {
            'total_types': len(self.elements),
            'total_elements': sum(len(elements) for elements in self.elements.values()),
            'total_templates': len(self.templates),
            'by_type': {}
        }
        
        for element_type, elements in self.elements.items():
            stats['by_type'][element_type] = {
                'count': len(elements),
                'categories': len(set(e.category for e in elements if e.category))
            }
        
        return stats