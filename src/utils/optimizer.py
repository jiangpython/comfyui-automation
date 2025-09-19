"""迭代式提示词优化器 - 基于分析结果自动优化提示词"""

import json
import logging
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime, timedelta

from .metadata_schema import TaskMetadata, TaskResult
from .prompt_analyzer import PromptAnalyzer
from .recommendation_engine import RecommendationEngine
from ..prompt_generator.generator import PromptGenerator

logger = logging.getLogger(__name__)

@dataclass
class OptimizationSuggestion:
    """优化建议"""
    type: str  # 'add', 'remove', 'replace', 'adjust_weight'
    target_element: str
    suggestion: str
    confidence: float
    expected_improvement: float
    reasoning: str

@dataclass
class OptimizationResult:
    """优化结果"""
    original_prompt: str
    optimized_prompt: str
    suggestions_applied: List[OptimizationSuggestion]
    predicted_success_rate: float
    predicted_quality_score: float
    optimization_timestamp: datetime

class PromptOptimizer:
    """提示词优化器"""
    
    def __init__(self, analyzer: PromptAnalyzer = None, 
                 recommendation_engine: RecommendationEngine = None,
                 prompt_generator: PromptGenerator = None):
        self.analyzer = analyzer or PromptAnalyzer()
        self.recommendation_engine = recommendation_engine or RecommendationEngine()
        self.prompt_generator = prompt_generator or PromptGenerator()
        
        # 优化策略配置
        self.optimization_config = {
            'min_success_rate_threshold': 0.7,
            'quality_weight': 0.6,
            'success_rate_weight': 0.4,
            'max_suggestions_per_prompt': 5,
            'confidence_threshold': 0.6,
            'conservative_mode': True  # 保守模式：只应用高置信度的建议
        }
    
    def optimize_prompt(self, prompt: str, tasks: List[TaskMetadata], 
                       results: List[TaskResult]) -> OptimizationResult:
        """优化单个提示词"""
        
        logger.info(f"开始优化提示词: {prompt[:50]}...")
        
        # 分析当前提示词的性能
        current_performance = self._analyze_prompt_performance(prompt, tasks, results)
        
        # 生成优化建议
        suggestions = self._generate_optimization_suggestions(
            prompt, current_performance, tasks, results
        )
        
        # 应用优化建议
        optimized_prompt, applied_suggestions = self._apply_suggestions(prompt, suggestions)
        
        # 预测优化效果
        predicted_metrics = self._predict_optimization_effect(
            optimized_prompt, applied_suggestions, tasks, results
        )
        
        result = OptimizationResult(
            original_prompt=prompt,
            optimized_prompt=optimized_prompt,
            suggestions_applied=applied_suggestions,
            predicted_success_rate=predicted_metrics['success_rate'],
            predicted_quality_score=predicted_metrics['quality_score'],
            optimization_timestamp=datetime.now()
        )
        
        logger.info(f"提示词优化完成，应用了 {len(applied_suggestions)} 个建议")
        return result
    
    def batch_optimize_prompts(self, prompts: List[str], tasks: List[TaskMetadata], 
                              results: List[TaskResult]) -> List[OptimizationResult]:
        """批量优化提示词"""
        
        logger.info(f"开始批量优化 {len(prompts)} 个提示词")
        
        optimization_results = []
        
        for i, prompt in enumerate(prompts):
            try:
                result = self.optimize_prompt(prompt, tasks, results)
                optimization_results.append(result)
                
                logger.info(f"优化进度: {i+1}/{len(prompts)}")
                
            except Exception as e:
                logger.error(f"优化提示词失败 '{prompt[:30]}...': {e}")
                # 创建空的优化结果
                optimization_results.append(OptimizationResult(
                    original_prompt=prompt,
                    optimized_prompt=prompt,
                    suggestions_applied=[],
                    predicted_success_rate=0.5,
                    predicted_quality_score=0.5,
                    optimization_timestamp=datetime.now()
                ))
        
        logger.info(f"批量优化完成，共处理 {len(optimization_results)} 个提示词")
        return optimization_results
    
    def generate_next_iteration(self, tasks: List[TaskMetadata], results: List[TaskResult],
                               iteration_count: int = 50) -> List[str]:
        """基于历史数据生成下一轮迭代的提示词"""
        
        logger.info(f"生成下一轮迭代的 {iteration_count} 个提示词")
        
        # 分析最佳表现的元素和模式
        element_analyses = self.analyzer.analyze_prompt_elements(tasks, results)
        top_elements = sorted(element_analyses.values(), 
                            key=lambda x: x.success_rate * x.avg_quality, reverse=True)[:20]
        
        # 获取元素组合推荐
        combinations = self.recommendation_engine.analyze_element_combinations(tasks, results)
        top_combinations = combinations[:10]
        
        # 识别成功模式
        successful_tasks = [t for t in tasks if t.status == 'completed' and 
                           (t.quality_score or 0) > 0.7]
        
        new_prompts = []
        
        # 策略1: 基于最佳元素组合生成 (30%)
        strategy1_count = int(iteration_count * 0.3)
        for _ in range(strategy1_count):
            selected_elements = self._select_high_performance_elements(top_elements, 3, 6)
            prompt = self._create_prompt_from_elements(selected_elements)
            new_prompts.append(prompt)
        
        # 策略2: 基于成功组合变体生成 (40%)
        strategy2_count = int(iteration_count * 0.4)
        for _ in range(strategy2_count):
            if top_combinations:
                base_combo = self._weighted_random_choice(top_combinations)
                variant_prompt = self._create_combination_variant(base_combo, top_elements)
                new_prompts.append(variant_prompt)
        
        # 策略3: 基于成功案例微调 (30%)
        strategy3_count = iteration_count - len(new_prompts)
        for _ in range(strategy3_count):
            if successful_tasks:
                base_task = self._weighted_random_choice(successful_tasks, 
                                                       weight_key='quality_score')
                optimized = self.optimize_prompt(base_task.prompt, tasks, results)
                new_prompts.append(optimized.optimized_prompt)
        
        # 去重并返回
        unique_prompts = list(dict.fromkeys(new_prompts))
        
        logger.info(f"生成了 {len(unique_prompts)} 个独特的下一轮提示词")
        return unique_prompts
    
    def _analyze_prompt_performance(self, prompt: str, tasks: List[TaskMetadata], 
                                   results: List[TaskResult]) -> Dict[str, Any]:
        """分析提示词的当前性能"""
        
        # 查找相似的历史任务
        similar_tasks = []
        prompt_elements = set(self.analyzer._extract_prompt_elements(prompt))
        
        for task in tasks:
            if task.status not in ['completed', 'failed']:
                continue
                
            task_elements = set(self.analyzer._extract_prompt_elements(task.prompt))
            similarity = len(prompt_elements & task_elements) / len(prompt_elements | task_elements)
            
            if similarity > 0.3:  # 30%以上的相似度
                similar_tasks.append((task, similarity))
        
        if not similar_tasks:
            return {
                'success_rate': 0.5,
                'avg_quality': 0.5,
                'avg_time': 30.0,
                'sample_size': 0
            }
        
        # 计算加权平均性能
        total_weight = sum(similarity for _, similarity in similar_tasks)
        weighted_success = 0
        weighted_quality = 0
        weighted_time = 0
        
        for task, similarity in similar_tasks:
            weight = similarity / total_weight
            is_success = 1 if task.status == 'completed' else 0
            quality = task.quality_score or 0
            time_cost = task.actual_time or 30.0
            
            weighted_success += is_success * weight
            weighted_quality += quality * weight
            weighted_time += time_cost * weight
        
        return {
            'success_rate': weighted_success,
            'avg_quality': weighted_quality,
            'avg_time': weighted_time,
            'sample_size': len(similar_tasks)
        }
    
    def _generate_optimization_suggestions(self, prompt: str, performance: Dict[str, Any],
                                          tasks: List[TaskMetadata], 
                                          results: List[TaskResult]) -> List[OptimizationSuggestion]:
        """生成优化建议"""
        
        suggestions = []
        prompt_elements = self.analyzer._extract_prompt_elements(prompt)
        
        # 获取元素分析和推荐
        element_analyses = self.analyzer.analyze_prompt_elements(tasks, results)
        combinations = self.recommendation_engine.analyze_element_combinations(tasks, results)
        anti_patterns = self.recommendation_engine.identify_anti_patterns(tasks, results)
        
        # 建议1: 移除低效元素
        for element in prompt_elements:
            if element in element_analyses:
                analysis = element_analyses[element]
                if analysis.success_rate < 0.5 and analysis.total_count >= 5:
                    suggestions.append(OptimizationSuggestion(
                        type='remove',
                        target_element=element,
                        suggestion=f"移除低效元素 '{element}'",
                        confidence=min(0.9, (0.5 - analysis.success_rate) * 2),
                        expected_improvement=0.1,
                        reasoning=f"该元素成功率仅为 {analysis.success_rate:.1%}，建议移除"
                    ))
        
        # 建议2: 添加高效元素
        top_elements = sorted([a for a in element_analyses.values() 
                             if a.success_rate > 0.8 and a.element not in prompt_elements],
                            key=lambda x: x.success_rate * x.avg_quality, reverse=True)[:5]
        
        for analysis in top_elements:
            suggestions.append(OptimizationSuggestion(
                type='add',
                target_element=analysis.element,
                suggestion=f"添加高效元素 '{analysis.element}'",
                confidence=min(0.8, analysis.success_rate),
                expected_improvement=0.15,
                reasoning=f"该元素成功率为 {analysis.success_rate:.1%}，平均质量 {analysis.avg_quality:.2f}"
            ))
        
        # 建议3: 基于协同效应
        for combo in combinations[:3]:
            if any(elem in prompt_elements for elem in combo.elements):
                missing_elements = [elem for elem in combo.elements 
                                  if elem not in prompt_elements]
                if missing_elements:
                    suggestions.append(OptimizationSuggestion(
                        type='add',
                        target_element=missing_elements[0],
                        suggestion=f"添加协同元素 '{missing_elements[0]}'",
                        confidence=combo.effectiveness_score,
                        expected_improvement=0.12,
                        reasoning=f"与现有元素存在协同效应，效果评分 {combo.effectiveness_score:.2f}"
                    ))
        
        # 建议4: 避免反模式
        for anti_pattern in anti_patterns[:3]:
            pattern_elements = set(anti_pattern.elements)
            prompt_element_set = set(prompt_elements)
            
            if len(pattern_elements & prompt_element_set) >= 2:
                conflict_element = list(pattern_elements & prompt_element_set)[0]
                suggestions.append(OptimizationSuggestion(
                    type='remove',
                    target_element=conflict_element,
                    suggestion=f"移除冲突元素 '{conflict_element}' 以避免反模式",
                    confidence=anti_pattern.confidence,
                    expected_improvement=0.08,
                    reasoning=f"检测到反模式，可能导致质量下降"
                ))
        
        # 按置信度和预期改进排序
        suggestions.sort(key=lambda x: x.confidence * x.expected_improvement, reverse=True)
        
        # 返回最多N个建议
        return suggestions[:self.optimization_config['max_suggestions_per_prompt']]
    
    def _apply_suggestions(self, prompt: str, suggestions: List[OptimizationSuggestion]
                          ) -> Tuple[str, List[OptimizationSuggestion]]:
        """应用优化建议"""
        
        applied_suggestions = []
        modified_prompt = prompt
        prompt_elements = self.analyzer._extract_prompt_elements(prompt)
        
        for suggestion in suggestions:
            # 只应用高置信度的建议
            if suggestion.confidence < self.optimization_config['confidence_threshold']:
                continue
            
            if suggestion.type == 'remove' and suggestion.target_element in prompt_elements:
                # 移除元素
                modified_prompt = self._remove_element_from_prompt(
                    modified_prompt, suggestion.target_element)
                applied_suggestions.append(suggestion)
                
            elif suggestion.type == 'add':
                # 添加元素
                modified_prompt = self._add_element_to_prompt(
                    modified_prompt, suggestion.target_element)
                applied_suggestions.append(suggestion)
        
        return modified_prompt, applied_suggestions
    
    def _remove_element_from_prompt(self, prompt: str, element: str) -> str:
        """从提示词中移除指定元素"""
        # 简单的字符串替换实现
        element_variations = [
            element,
            f", {element}",
            f"{element},",
            f", {element},",
        ]
        
        modified = prompt
        for variation in element_variations:
            modified = modified.replace(variation, "")
        
        # 清理多余的逗号和空格
        modified = ", ".join([part.strip() for part in modified.split(",") if part.strip()])
        
        return modified
    
    def _add_element_to_prompt(self, prompt: str, element: str) -> str:
        """向提示词中添加元素"""
        if not prompt.strip():
            return element
        
        # 在适当的位置插入元素
        if prompt.strip().endswith(','):
            return f"{prompt.strip()} {element}"
        else:
            return f"{prompt.strip()}, {element}"
    
    def _predict_optimization_effect(self, optimized_prompt: str, 
                                   applied_suggestions: List[OptimizationSuggestion],
                                   tasks: List[TaskMetadata], 
                                   results: List[TaskResult]) -> Dict[str, float]:
        """预测优化效果"""
        
        # 基于历史数据预测
        base_performance = self._analyze_prompt_performance(optimized_prompt, tasks, results)
        
        # 计算预期改进
        total_improvement = sum(s.expected_improvement * s.confidence 
                              for s in applied_suggestions)
        
        predicted_success_rate = min(0.95, base_performance['success_rate'] + total_improvement)
        predicted_quality = min(1.0, base_performance['avg_quality'] + total_improvement * 0.5)
        
        return {
            'success_rate': predicted_success_rate,
            'quality_score': predicted_quality
        }
    
    def _select_high_performance_elements(self, top_elements, min_count: int, max_count: int) -> List[str]:
        """选择高性能元素组合"""
        import random
        
        count = random.randint(min_count, min(max_count, len(top_elements)))
        selected = []
        
        # 加权随机选择
        weights = [elem.success_rate * elem.avg_quality for elem in top_elements]
        total_weight = sum(weights)
        
        for _ in range(count):
            if not top_elements:
                break
                
            r = random.random() * total_weight
            cumulative = 0
            
            for i, weight in enumerate(weights):
                cumulative += weight
                if r <= cumulative:
                    selected.append(top_elements[i].element)
                    top_elements.pop(i)
                    weights.pop(i)
                    total_weight -= weight
                    break
        
        return selected
    
    def _create_prompt_from_elements(self, elements: List[str]) -> str:
        """从元素列表创建提示词"""
        return ", ".join(elements)
    
    def _create_combination_variant(self, base_combo, top_elements) -> str:
        """基于组合创建变体"""
        import random
        
        # 使用基础组合的部分元素
        variant_elements = list(base_combo.elements)
        
        # 随机替换1-2个元素
        replace_count = random.randint(1, min(2, len(variant_elements)))
        available_elements = [elem.element for elem in top_elements 
                            if elem.element not in variant_elements]
        
        if available_elements:
            for _ in range(replace_count):
                if variant_elements and available_elements:
                    old_element = random.choice(variant_elements)
                    new_element = random.choice(available_elements)
                    
                    idx = variant_elements.index(old_element)
                    variant_elements[idx] = new_element
                    available_elements.remove(new_element)
        
        return ", ".join(variant_elements)
    
    def _weighted_random_choice(self, items, weight_key: str = None):
        """加权随机选择"""
        import random
        
        if not items:
            return None
        
        if weight_key:
            weights = [getattr(item, weight_key, 0.5) for item in items]
        else:
            weights = [getattr(item, 'effectiveness_score', 0.5) for item in items]
        
        total_weight = sum(weights)
        if total_weight == 0:
            return random.choice(items)
        
        r = random.random() * total_weight
        cumulative = 0
        
        for item, weight in zip(items, weights):
            cumulative += weight
            if r <= cumulative:
                return item
        
        return items[-1]  # 后备选择
    
    def export_optimization_history(self, optimization_results: List[OptimizationResult], 
                                   filename: str) -> str:
        """导出优化历史"""
        
        logger.info(f"导出优化历史到 {filename}")
        
        export_data = {
            'export_timestamp': datetime.now().isoformat(),
            'total_optimizations': len(optimization_results),
            'optimization_config': self.optimization_config,
            'results': []
        }
        
        for result in optimization_results:
            export_data['results'].append({
                'original_prompt': result.original_prompt,
                'optimized_prompt': result.optimized_prompt,
                'suggestions_count': len(result.suggestions_applied),
                'suggestions': [
                    {
                        'type': s.type,
                        'target': s.target_element,
                        'suggestion': s.suggestion,
                        'confidence': s.confidence,
                        'improvement': s.expected_improvement,
                        'reasoning': s.reasoning
                    } for s in result.suggestions_applied
                ],
                'predicted_success_rate': result.predicted_success_rate,
                'predicted_quality_score': result.predicted_quality_score,
                'timestamp': result.optimization_timestamp.isoformat()
            })
        
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(export_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"优化历史导出完成，共 {len(optimization_results)} 条记录")
        return filename