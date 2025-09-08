"""提示词元素组合器"""

import random
import itertools
from typing import Dict, List, Set, Optional, Tuple, Any
from dataclasses import dataclass

from .elements import PromptElements, PromptElement, PromptTemplate

@dataclass
class ElementSelection:
    """元素选择"""
    elements: Dict[str, PromptElement]
    template: PromptTemplate
    conflicts: List[str]
    quality_score: float = 0.0

class ElementCombinator:
    """元素组合器"""
    
    def __init__(self, prompt_elements: PromptElements):
        self.elements = prompt_elements
        self.required_types = ['subjects']  # 必需的元素类型
        self.optional_types = ['camera_angles', 'styles', 'lighting', 'moods']  # 可选的元素类型
        self.enhancer_types = ['quality_enhancers']  # 增强词类型
    
    def generate_single_combination(self, 
                                  required_elements: Optional[Dict[str, str]] = None,
                                  exclude_elements: Optional[Dict[str, Set[str]]] = None,
                                  min_elements: int = 3,
                                  max_elements: int = 5) -> Optional[ElementSelection]:
        """生成单个元素组合"""
        
        selected_elements = {}
        used_types = set()
        
        # 1. 添加必需元素
        for element_type in self.required_types:
            if required_elements and element_type in required_elements:
                # 使用指定元素
                element = self.elements.get_element_by_name(element_type, required_elements[element_type])
                if not element:
                    continue
            else:
                # 随机选择
                exclude_set = exclude_elements.get(element_type, set()) if exclude_elements else set()
                element = self.elements.get_random_element(element_type, exclude=exclude_set)
                if not element:
                    continue
            
            selected_elements[element_type] = element
            used_types.add(element_type)
        
        # 2. 添加可选元素
        remaining_slots = max_elements - len(selected_elements)
        available_types = [t for t in self.optional_types if t not in used_types]
        
        # 随机选择要使用的可选类型
        num_optional = min(remaining_slots, len(available_types))
        num_optional = max(min_elements - len(selected_elements), num_optional)
        
        if num_optional > 0 and available_types:
            selected_types = random.sample(available_types, min(num_optional, len(available_types)))
            
            for element_type in selected_types:
                exclude_set = exclude_elements.get(element_type, set()) if exclude_elements else set()
                element = self.elements.get_random_element(element_type, exclude=exclude_set)
                if element:
                    selected_elements[element_type] = element
                    used_types.add(element_type)
        
        # 3. 检查冲突
        conflicts = self.elements.check_conflicts(selected_elements)
        if conflicts:
            # 如果有冲突，尝试重新生成
            return None
        
        # 4. 选择模板
        template = self.elements.get_random_template()
        if not template:
            return None
        
        # 5. 计算质量分数
        quality_score = self._calculate_quality_score(selected_elements, template)
        
        return ElementSelection(
            elements=selected_elements,
            template=template,
            conflicts=conflicts,
            quality_score=quality_score
        )
    
    def generate_combinations(self,
                            count: int = 10,
                            required_elements: Optional[Dict[str, str]] = None,
                            exclude_elements: Optional[Dict[str, Set[str]]] = None,
                            min_elements: int = 3,
                            max_elements: int = 5,
                            max_retries: int = 100) -> List[ElementSelection]:
        """生成多个元素组合"""
        
        combinations = []
        retries = 0
        
        while len(combinations) < count and retries < max_retries:
            combination = self.generate_single_combination(
                required_elements=required_elements,
                exclude_elements=exclude_elements,
                min_elements=min_elements,
                max_elements=max_elements
            )
            
            if combination and not self._is_duplicate(combination, combinations):
                combinations.append(combination)
            
            retries += 1
        
        # 按质量分数排序
        combinations.sort(key=lambda x: x.quality_score, reverse=True)
        return combinations
    
    def generate_exhaustive_combinations(self,
                                       subjects: Optional[List[str]] = None,
                                       styles: Optional[List[str]] = None,
                                       max_combinations: int = 100) -> List[ElementSelection]:
        """生成穷举式组合（指定主题和风格的所有组合）"""
        
        combinations = []
        
        # 获取指定的主题列表
        if subjects:
            subject_elements = [self.elements.get_element_by_name('subjects', s) for s in subjects]
            subject_elements = [e for e in subject_elements if e is not None]
        else:
            subject_elements = self.elements.get_elements('subjects')[:5]  # 限制数量
        
        # 获取指定的风格列表
        if styles:
            style_elements = [self.elements.get_element_by_name('styles', s) for s in styles]
            style_elements = [e for e in style_elements if e is not None]
        else:
            style_elements = self.elements.get_elements('styles')[:3]  # 限制数量
        
        # 生成所有主题×风格的组合
        for subject, style in itertools.product(subject_elements, style_elements):
            if len(combinations) >= max_combinations:
                break
            
            # 为每个主题×风格组合添加其他随机元素
            base_elements = {
                'subjects': subject,
                'styles': style
            }
            
            # 添加其他元素
            for _ in range(3):  # 每个基础组合生成3个变体
                selected_elements = base_elements.copy()
                
                # 随机添加其他类型的元素
                for element_type in ['camera_angles', 'lighting', 'moods']:
                    if random.random() > 0.3:  # 70%概率添加
                        element = self.elements.get_random_element(element_type)
                        if element:
                            selected_elements[element_type] = element
                
                # 检查冲突
                conflicts = self.elements.check_conflicts(selected_elements)
                if conflicts:
                    continue
                
                # 选择模板
                template = self.elements.get_random_template()
                if not template:
                    continue
                
                combination = ElementSelection(
                    elements=selected_elements,
                    template=template,
                    conflicts=conflicts,
                    quality_score=self._calculate_quality_score(selected_elements, template)
                )
                
                if not self._is_duplicate(combination, combinations):
                    combinations.append(combination)
        
        return combinations[:max_combinations]
    
    def _calculate_quality_score(self, elements: Dict[str, PromptElement], template: PromptTemplate) -> float:
        """计算组合的质量分数"""
        score = 0.0
        
        # 基础分数：元素权重之和
        score += sum(element.weight for element in elements.values())
        
        # 模板权重
        score += template.weight
        
        # 元素数量奖励
        score += len(elements) * 0.1
        
        # 特殊奖励
        element_names = set(element.name for element in elements.values())
        
        # 高质量组合奖励
        if 'photorealistic' in element_names:
            score += 0.2
        if 'masterpiece' in element_names:
            score += 0.3
        
        return score
    
    def _is_duplicate(self, combination: ElementSelection, existing: List[ElementSelection]) -> bool:
        """检查是否为重复组合"""
        current_elements = set(combination.elements.keys())
        current_names = set(element.name for element in combination.elements.values())
        
        for existing_combo in existing:
            existing_elements = set(existing_combo.elements.keys())
            existing_names = set(element.name for element in existing_combo.elements.values())
            
            # 如果元素类型和元素名称都相同，则认为是重复
            if current_elements == existing_elements and current_names == existing_names:
                return True
        
        return False
    
    def get_combination_statistics(self, combinations: List[ElementSelection]) -> Dict[str, Any]:
        """获取组合统计信息"""
        if not combinations:
            return {}
        
        stats = {
            'total_combinations': len(combinations),
            'average_quality_score': sum(c.quality_score for c in combinations) / len(combinations),
            'element_usage': {},
            'template_usage': {},
            'conflicts_count': sum(len(c.conflicts) for c in combinations)
        }
        
        # 统计元素使用频率
        for combination in combinations:
            for element_type, element in combination.elements.items():
                if element_type not in stats['element_usage']:
                    stats['element_usage'][element_type] = {}
                if element.name not in stats['element_usage'][element_type]:
                    stats['element_usage'][element_type][element.name] = 0
                stats['element_usage'][element_type][element.name] += 1
            
            # 统计模板使用频率
            template_pattern = combination.template.pattern
            if template_pattern not in stats['template_usage']:
                stats['template_usage'][template_pattern] = 0
            stats['template_usage'][template_pattern] += 1
        
        return stats