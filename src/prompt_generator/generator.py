"""提示词生成器主类"""

import random
import re
from typing import List, Dict, Optional, Set, Any, Tuple
from dataclasses import dataclass

from .elements import PromptElements, PromptElement
from .combinator import ElementCombinator, ElementSelection

@dataclass
class GeneratedPrompt:
    """生成的提示词"""
    text: str
    elements: Dict[str, PromptElement]
    template_pattern: str
    quality_score: float
    metadata: Dict[str, Any]

class PromptGenerator:
    """提示词生成器"""
    
    def __init__(self, elements_file: Optional[str] = None):
        self.elements = PromptElements(elements_file)
        self.combinator = ElementCombinator(self.elements)
    
    def generate_prompts(self,
                        count: int = 10,
                        subjects: Optional[List[str]] = None,
                        styles: Optional[List[str]] = None,
                        required_elements: Optional[Dict[str, str]] = None,
                        exclude_elements: Optional[Dict[str, Set[str]]] = None,
                        min_elements: int = 3,
                        max_elements: int = 5,
                        add_quality_enhancers: bool = True) -> List[GeneratedPrompt]:
        """生成提示词列表"""
        
        # 生成元素组合
        combinations = self.combinator.generate_combinations(
            count=count,
            required_elements=required_elements,
            exclude_elements=exclude_elements,
            min_elements=min_elements,
            max_elements=max_elements
        )
        
        # 转换为提示词文本
        prompts = []
        for combination in combinations:
            prompt_text = self._render_prompt(combination, add_quality_enhancers)
            if prompt_text:
                prompt = GeneratedPrompt(
                    text=prompt_text,
                    elements=combination.elements,
                    template_pattern=combination.template.pattern,
                    quality_score=combination.quality_score,
                    metadata=self._create_metadata(combination)
                )
                prompts.append(prompt)
        
        return prompts
    
    def generate_exhaustive_prompts(self,
                                  subjects: List[str],
                                  styles: Optional[List[str]] = None,
                                  max_combinations: int = 100,
                                  add_quality_enhancers: bool = True) -> List[GeneratedPrompt]:
        """生成穷举式提示词（所有指定主题和风格的组合）"""
        
        combinations = self.combinator.generate_exhaustive_combinations(
            subjects=subjects,
            styles=styles,
            max_combinations=max_combinations
        )
        
        prompts = []
        for combination in combinations:
            prompt_text = self._render_prompt(combination, add_quality_enhancers)
            if prompt_text:
                prompt = GeneratedPrompt(
                    text=prompt_text,
                    elements=combination.elements,
                    template_pattern=combination.template.pattern,
                    quality_score=combination.quality_score,
                    metadata=self._create_metadata(combination)
                )
                prompts.append(prompt)
        
        return prompts
    
    def generate_variations(self,
                          base_subject: str,
                          variation_count: int = 20,
                          add_quality_enhancers: bool = True) -> List[GeneratedPrompt]:
        """基于单个主题生成多种变体"""
        
        # 检查是否为完整提示词（包含逗号或长度>20字符）
        if ',' in base_subject or len(base_subject) > 20:
            # 这是完整的提示词，直接作为基础进行变体生成
            return self.generate_complete_prompt_variations(
                base_prompt=base_subject,
                variation_count=variation_count,
                add_quality_enhancers=add_quality_enhancers
            )
        else:
            # 传统方式：在元素库中查找匹配的主题
            subject_element = self.elements.get_element_by_name('subjects', base_subject)
            if not subject_element:
                # 如果找不到匹配的主题，创建一个临时主题元素
                subject_element = PromptElement(name=base_subject, weight=1.0)
                
            required_elements = {'subjects': base_subject}
            
            return self.generate_prompts(
                count=variation_count,
                required_elements=required_elements,
                add_quality_enhancers=add_quality_enhancers
            )
    
    def generate_complete_prompt_variations(self,
                                          base_prompt: str,
                                          variation_count: int = 20,
                                          add_quality_enhancers: bool = True) -> List[GeneratedPrompt]:
        """为完整提示词生成变体（添加光照、风格、镜头角度等元素）"""
        
        variations = []
        variation_templates = [
            # 不同的增强模式
            "{base_prompt}, {lighting}",
            "{base_prompt}, {camera_angles}, {lighting}",
            "{base_prompt}, {styles} style",
            "{base_prompt}, {styles} style, {lighting}",
            "{base_prompt}, {moods} atmosphere",
            "{base_prompt}, {camera_angles}, {moods} atmosphere",
            "{base_prompt}, {styles} style, {lighting}, {moods} atmosphere",
            "{base_prompt}, {camera_angles}",
            "{base_prompt}, {lighting}, {quality_enhancers}",
            "{base_prompt}, {styles} rendering"
        ]
        
        for i in range(variation_count):
            # 随机选择模板
            template_pattern = random.choice(variation_templates)
            
            # 随机选择元素
            selected_elements = {}
            
            # 根据模板需要的元素类型添加元素
            if '{lighting}' in template_pattern:
                lighting = self.elements.get_random_element('lighting')
                if lighting:
                    selected_elements['lighting'] = lighting
            
            if '{camera_angles}' in template_pattern:
                angle = self.elements.get_random_element('camera_angles')
                if angle:
                    selected_elements['camera_angles'] = angle
                    
            if '{styles}' in template_pattern:
                style = self.elements.get_random_element('styles')
                if style:
                    selected_elements['styles'] = style
                    
            if '{moods}' in template_pattern:
                mood = self.elements.get_random_element('moods')
                if mood:
                    selected_elements['moods'] = mood
                    
            if '{quality_enhancers}' in template_pattern and add_quality_enhancers:
                enhancer = self.elements.get_random_element('quality_enhancers')
                if enhancer:
                    selected_elements['quality_enhancers'] = enhancer
            
            # 渲染提示词
            rendered_text = template_pattern.replace('{base_prompt}', base_prompt)
            
            for element_type, element in selected_elements.items():
                placeholder = f"{{{element_type}}}"
                if placeholder in rendered_text:
                    rendered_text = rendered_text.replace(placeholder, element.name)
            
            # 清理未使用的占位符
            rendered_text = re.sub(r'\{[^}]+\}', '', rendered_text)
            
            # 清理多余的逗号和空格
            rendered_text = re.sub(r',\s*,', ',', rendered_text)
            rendered_text = re.sub(r',\s*$', '', rendered_text)
            rendered_text = re.sub(r'^\s*,', '', rendered_text)
            rendered_text = re.sub(r'\s+', ' ', rendered_text).strip()
            
            # 计算质量分数
            quality_score = sum(element.weight for element in selected_elements.values()) + 1.0  # 基础分数1.0
            
            # 创建变体对象
            variation = GeneratedPrompt(
                text=rendered_text,
                elements=selected_elements,
                template_pattern=template_pattern,
                quality_score=quality_score,
                metadata={
                    'base_prompt': base_prompt,
                    'variation_type': 'complete_prompt_enhancement',
                    'elements_added': list(selected_elements.keys())
                }
            )
            
            variations.append(variation)
        
        # 按质量分数排序
        variations.sort(key=lambda x: x.quality_score, reverse=True)
        return variations
    
    def _render_prompt(self, combination: ElementSelection, add_quality_enhancers: bool = True) -> str:
        """将元素组合渲染为提示词文本"""
        
        template_pattern = combination.template.pattern
        elements = combination.elements.copy()
        
        # 添加质量增强词
        if add_quality_enhancers:
            enhancer_element = self.elements.get_random_element('quality_enhancers')
            if enhancer_element:
                elements['quality_enhancers'] = enhancer_element
        
        # 替换模板中的占位符
        rendered_text = template_pattern
        
        for element_type, element in elements.items():
            placeholder = f"{{{element_type}}}"
            if placeholder in rendered_text:
                rendered_text = rendered_text.replace(placeholder, element.name)
        
        # 清理未使用的占位符和相关文本
        rendered_text = re.sub(r'\{[^}]+\}[^,]*', '', rendered_text)  # 移除占位符及其前后文字
        rendered_text = re.sub(r'of\s*,', '', rendered_text)  # 移除 "of ," 
        rendered_text = re.sub(r'in\s*,', '', rendered_text)  # 移除 "in ,"
        rendered_text = re.sub(r'style\s*,\s*style', 'style', rendered_text)  # 重复的style
        
        # 清理多余的逗号和空格
        rendered_text = re.sub(r',\s*,', ',', rendered_text)  # 连续逗号
        rendered_text = re.sub(r',\s*$', '', rendered_text)   # 末尾逗号
        rendered_text = re.sub(r'^\s*,', '', rendered_text)   # 开头逗号
        rendered_text = re.sub(r'\s+', ' ', rendered_text).strip()  # 多余空格
        
        # 添加元素的增强词
        enhancers = []
        for element in elements.values():
            if element.enhancers:
                # 随机选择一些增强词
                selected_enhancers = random.sample(
                    element.enhancers, 
                    min(len(element.enhancers), 2)  # 最多选择2个增强词
                )
                enhancers.extend(selected_enhancers)
        
        # 去重并添加增强词
        if enhancers:
            unique_enhancers = list(set(enhancers))
            rendered_text += ", " + ", ".join(unique_enhancers)
        
        return rendered_text
    
    def _create_metadata(self, combination: ElementSelection) -> Dict[str, Any]:
        """创建元数据"""
        metadata = {
            'elements_used': {
                element_type: {
                    'name': element.name,
                    'weight': element.weight,
                    'category': element.category,
                    'aliases': element.aliases
                }
                for element_type, element in combination.elements.items()
            },
            'template': {
                'pattern': combination.template.pattern,
                'weight': combination.template.weight,
                'description': combination.template.description
            },
            'quality_score': combination.quality_score,
            'conflicts': combination.conflicts
        }
        
        return metadata
    
    def analyze_prompts(self, prompts: List[GeneratedPrompt]) -> Dict[str, Any]:
        """分析生成的提示词"""
        if not prompts:
            return {}
        
        analysis = {
            'total_prompts': len(prompts),
            'average_quality_score': sum(p.quality_score for p in prompts) / len(prompts),
            'quality_distribution': self._analyze_quality_distribution(prompts),
            'element_frequency': self._analyze_element_frequency(prompts),
            'template_usage': self._analyze_template_usage(prompts),
            'prompt_length_stats': self._analyze_prompt_lengths(prompts)
        }
        
        return analysis
    
    def _analyze_quality_distribution(self, prompts: List[GeneratedPrompt]) -> Dict[str, int]:
        """分析质量分数分布"""
        distribution = {'low': 0, 'medium': 0, 'high': 0}
        
        for prompt in prompts:
            score = prompt.quality_score
            if score < 2.0:
                distribution['low'] += 1
            elif score < 4.0:
                distribution['medium'] += 1
            else:
                distribution['high'] += 1
        
        return distribution
    
    def _analyze_element_frequency(self, prompts: List[GeneratedPrompt]) -> Dict[str, Dict[str, int]]:
        """分析元素使用频率"""
        frequency = {}
        
        for prompt in prompts:
            for element_type, element in prompt.elements.items():
                if element_type not in frequency:
                    frequency[element_type] = {}
                
                element_name = element.name
                if element_name not in frequency[element_type]:
                    frequency[element_type][element_name] = 0
                frequency[element_type][element_name] += 1
        
        return frequency
    
    def _analyze_template_usage(self, prompts: List[GeneratedPrompt]) -> Dict[str, int]:
        """分析模板使用频率"""
        usage = {}
        
        for prompt in prompts:
            pattern = prompt.template_pattern
            if pattern not in usage:
                usage[pattern] = 0
            usage[pattern] += 1
        
        return usage
    
    def _analyze_prompt_lengths(self, prompts: List[GeneratedPrompt]) -> Dict[str, float]:
        """分析提示词长度统计"""
        lengths = [len(prompt.text) for prompt in prompts]
        word_counts = [len(prompt.text.split()) for prompt in prompts]
        
        if not lengths:
            return {}
        
        return {
            'avg_characters': sum(lengths) / len(lengths),
            'min_characters': min(lengths),
            'max_characters': max(lengths),
            'avg_words': sum(word_counts) / len(word_counts),
            'min_words': min(word_counts),
            'max_words': max(word_counts)
        }
    
    def export_prompts(self, prompts: List[GeneratedPrompt], format: str = 'txt') -> str:
        """导出提示词"""
        if format == 'txt':
            return '\n'.join(prompt.text for prompt in prompts)
        elif format == 'json':
            import json
            data = [
                {
                    'text': prompt.text,
                    'quality_score': prompt.quality_score,
                    'metadata': prompt.metadata
                }
                for prompt in prompts
            ]
            return json.dumps(data, indent=2, ensure_ascii=False)
        else:
            raise ValueError(f"不支持的格式: {format}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取生成器统计信息"""
        return {
            'elements_stats': self.elements.get_statistics(),
            'generator_info': {
                'version': '1.0.0',
                'supported_formats': ['txt', 'json'],
                'max_elements_per_prompt': 5,
                'min_elements_per_prompt': 3
            }
        }