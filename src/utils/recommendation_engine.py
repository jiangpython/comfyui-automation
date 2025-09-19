"""推荐引擎 - 识别高效元素组合并生成优化建议"""

import json
import logging
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any, Set
from dataclasses import dataclass, asdict
from statistics import mean, stdev, median
from itertools import combinations
import math

from .metadata_schema import TaskMetadata, TaskResult
from .prompt_analyzer import PromptAnalyzer, PromptAnalysis

logger = logging.getLogger(__name__)

@dataclass
class ElementCombination:
    """元素组合"""
    elements: Tuple[str, ...]
    total_count: int
    success_count: int
    success_rate: float
    avg_quality: float
    quality_variance: float
    avg_generation_time: float
    effectiveness_score: float
    compatibility_score: float

@dataclass
class OptimizationSuggestion:
    """优化建议"""
    suggestion_type: str  # 'add_element', 'remove_element', 'replace_element', 'reorder_elements'
    current_elements: List[str]
    suggested_elements: List[str]
    expected_improvement: float
    confidence: float
    reasoning: str

@dataclass
class RecommendationReport:
    """推荐报告"""
    generated_at: datetime
    analysis_period: str
    total_combinations_analyzed: int
    best_combinations: List[ElementCombination]
    optimization_suggestions: List[OptimizationSuggestion]
    element_synergies: List[Dict[str, Any]]
    anti_patterns: List[Dict[str, Any]]
    performance_insights: Dict[str, Any]

class RecommendationEngine:
    """推荐引擎"""
    
    def __init__(self):
        self.prompt_analyzer = PromptAnalyzer()
        self.min_combination_occurrence = 3
        self.max_combination_size = 4
        
    def analyze_element_combinations(self, tasks: List[TaskMetadata], results: List[TaskResult]) -> List[ElementCombination]:
        """分析元素组合的效果"""
        
        logger.info("开始分析元素组合效果")
        
        # 收集所有组合的数据
        combination_stats = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'quality_scores': [],
            'generation_times': [],
            'task_ids': []
        })
        
        result_map = {r.task_id: r for r in results}
        
        for task in tasks:
            if task.status not in ['completed', 'failed']:
                continue
                
            elements = self.prompt_analyzer._extract_prompt_elements(task.prompt)
            if len(elements) < 2:
                continue
            
            is_success = task.status == 'completed'
            quality_score = task.quality_score or 0
            generation_time = task.actual_time or 0
            
            # 生成所有可能的组合（2到max_size个元素）
            for size in range(2, min(len(elements) + 1, self.max_combination_size + 1)):
                for combo in combinations(sorted(elements), size):
                    combo_key = tuple(combo)
                    combination_stats[combo_key]['total'] += 1
                    combination_stats[combo_key]['task_ids'].append(task.task_id)
                    
                    if is_success:
                        combination_stats[combo_key]['success'] += 1
                        combination_stats[combo_key]['quality_scores'].append(quality_score)
                        combination_stats[combo_key]['generation_times'].append(generation_time)
        
        # 计算组合效果
        combinations = []
        for combo, stats in combination_stats.items():
            if stats['total'] < self.min_combination_occurrence:
                continue
            
            success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            avg_quality = mean(stats['quality_scores']) if stats['quality_scores'] else 0
            quality_variance = stdev(stats['quality_scores']) if len(stats['quality_scores']) > 1 else 0
            avg_time = mean(stats['generation_times']) if stats['generation_times'] else 0
            
            # 计算效果评分
            effectiveness_score = self._calculate_combination_effectiveness(
                success_rate, avg_quality, quality_variance, stats['total']
            )
            
            # 计算兼容性评分
            compatibility_score = self._calculate_compatibility_score(combo)
            
            combinations.append(ElementCombination(
                elements=combo,
                total_count=stats['total'],
                success_count=stats['success'],
                success_rate=success_rate,
                avg_quality=avg_quality,
                quality_variance=quality_variance,
                avg_generation_time=avg_time,
                effectiveness_score=effectiveness_score,
                compatibility_score=compatibility_score
            ))
        
        # 按效果评分排序
        combinations.sort(key=lambda x: x.effectiveness_score, reverse=True)
        
        logger.info(f"分析了 {len(combinations)} 个有效元素组合")
        return combinations
    
    def identify_element_synergies(self, tasks: List[TaskMetadata], results: List[TaskResult]) -> List[Dict[str, Any]]:
        """识别元素之间的协同效应"""
        
        logger.info("识别元素协同效应")
        
        # 获取单个元素的基线性能
        element_analyses = self.prompt_analyzer.analyze_prompt_elements(tasks, results)
        
        # 分析组合效果
        combinations = self.analyze_element_combinations(tasks, results)
        
        synergies = []
        
        for combo in combinations:
            if len(combo.elements) != 2:  # 只分析两元素组合的协同效应
                continue
            
            elem1, elem2 = combo.elements
            
            # 获取单个元素的性能
            elem1_perf = element_analyses.get(elem1)
            elem2_perf = element_analyses.get(elem2)
            
            if not elem1_perf or not elem2_perf:
                continue
            
            # 计算预期性能（假设独立）
            expected_success_rate = (elem1_perf.success_rate + elem2_perf.success_rate) / 2
            expected_quality = (elem1_perf.avg_quality + elem2_perf.avg_quality) / 2
            
            # 计算协同效应强度
            success_synergy = combo.success_rate - expected_success_rate
            quality_synergy = combo.avg_quality - expected_quality
            
            # 只保留显著的协同效应
            if success_synergy > 0.1 or quality_synergy > 0.1:
                synergies.append({
                    'element1': elem1,
                    'element2': elem2,
                    'combination_success_rate': combo.success_rate,
                    'expected_success_rate': expected_success_rate,
                    'success_synergy': success_synergy,
                    'combination_quality': combo.avg_quality,
                    'expected_quality': expected_quality,
                    'quality_synergy': quality_synergy,
                    'total_occurrences': combo.total_count,
                    'synergy_strength': success_synergy + quality_synergy
                })
        
        # 按协同强度排序
        synergies.sort(key=lambda x: x['synergy_strength'], reverse=True)
        
        logger.info(f"识别出 {len(synergies)} 个协同效应")
        return synergies[:15]  # 返回top15
    
    def identify_anti_patterns(self, tasks: List[TaskMetadata], results: List[TaskResult]) -> List[Dict[str, Any]]:
        """识别反模式（相互冲突的元素组合）"""
        
        logger.info("识别反模式")
        
        # 获取单个元素的基线性能
        element_analyses = self.prompt_analyzer.analyze_prompt_elements(tasks, results)
        
        # 分析组合效果
        combinations = self.analyze_element_combinations(tasks, results)
        
        anti_patterns = []
        
        for combo in combinations:
            if len(combo.elements) < 2:
                continue
            
            # 计算组合中元素的平均单独性能
            individual_performances = []
            for elem in combo.elements:
                elem_perf = element_analyses.get(elem)
                if elem_perf:
                    individual_performances.append({
                        'success_rate': elem_perf.success_rate,
                        'quality': elem_perf.avg_quality
                    })
            
            if not individual_performances:
                continue
            
            avg_individual_success = mean([p['success_rate'] for p in individual_performances])
            avg_individual_quality = mean([p['quality'] for p in individual_performances])
            
            # 检测负面影响
            success_degradation = avg_individual_success - combo.success_rate
            quality_degradation = avg_individual_quality - combo.avg_quality
            
            # 如果组合性能明显低于单独性能，则为反模式
            if (success_degradation > 0.2 or quality_degradation > 0.2) and combo.total_count >= 3:
                anti_patterns.append({
                    'elements': list(combo.elements),
                    'combination_success_rate': combo.success_rate,
                    'expected_success_rate': avg_individual_success,
                    'success_degradation': success_degradation,
                    'combination_quality': combo.avg_quality,
                    'expected_quality': avg_individual_quality,
                    'quality_degradation': quality_degradation,
                    'total_occurrences': combo.total_count,
                    'severity': success_degradation + quality_degradation,
                    'conflict_type': self._identify_conflict_type(combo.elements)
                })
        
        # 按严重程度排序
        anti_patterns.sort(key=lambda x: x['severity'], reverse=True)
        
        logger.info(f"识别出 {len(anti_patterns)} 个反模式")
        return anti_patterns[:10]  # 返回top10
    
    def generate_optimization_suggestions(self, current_prompt: str, tasks: List[TaskMetadata], 
                                       results: List[TaskResult]) -> List[OptimizationSuggestion]:
        """为给定提示词生成优化建议"""
        
        logger.info(f"为提示词生成优化建议: {current_prompt[:50]}...")
        
        current_elements = self.prompt_analyzer._extract_prompt_elements(current_prompt)
        if not current_elements:
            return []
        
        suggestions = []
        
        # 获取元素分析和组合分析
        element_analyses = self.prompt_analyzer.analyze_prompt_elements(tasks, results)
        combinations = self.analyze_element_combinations(tasks, results)
        synergies = self.identify_element_synergies(tasks, results)
        anti_patterns = self.identify_anti_patterns(tasks, results)
        
        # 1. 添加高效元素的建议
        high_performing_elements = [
            elem for elem, analysis in element_analyses.items()
            if analysis.success_rate > 0.8 and analysis.avg_quality > 0.7
            and elem not in current_elements
        ]
        
        for elem in high_performing_elements[:3]:  # 推荐top3
            analysis = element_analyses[elem]
            suggestions.append(OptimizationSuggestion(
                suggestion_type='add_element',
                current_elements=current_elements.copy(),
                suggested_elements=current_elements + [elem],
                expected_improvement=analysis.success_rate - 0.5,  # 假设基线为0.5
                confidence=min(0.9, analysis.total_count / 10),
                reasoning=f"添加高效元素 '{elem}' (成功率: {analysis.success_rate:.1%}, 平均质量: {analysis.avg_quality:.2f})"
            ))
        
        # 2. 移除低效元素的建议
        low_performing_elements = [
            elem for elem in current_elements
            if elem in element_analyses and element_analyses[elem].success_rate < 0.5
        ]
        
        for elem in low_performing_elements:
            analysis = element_analyses[elem]
            new_elements = [e for e in current_elements if e != elem]
            suggestions.append(OptimizationSuggestion(
                suggestion_type='remove_element',
                current_elements=current_elements.copy(),
                suggested_elements=new_elements,
                expected_improvement=0.5 - analysis.success_rate,
                confidence=min(0.8, analysis.total_count / 10),
                reasoning=f"移除低效元素 '{elem}' (成功率仅: {analysis.success_rate:.1%})"
            ))
        
        # 3. 基于协同效应的建议
        for synergy in synergies[:5]:
            elem1, elem2 = synergy['element1'], synergy['element2']
            
            # 如果当前只有其中一个元素，建议添加另一个
            if elem1 in current_elements and elem2 not in current_elements:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type='add_element',
                    current_elements=current_elements.copy(),
                    suggested_elements=current_elements + [elem2],
                    expected_improvement=synergy['quality_synergy'],
                    confidence=0.7,
                    reasoning=f"添加 '{elem2}' 与 '{elem1}' 形成协同效应 (质量提升: +{synergy['quality_synergy']:.2f})"
                ))
            elif elem2 in current_elements and elem1 not in current_elements:
                suggestions.append(OptimizationSuggestion(
                    suggestion_type='add_element',
                    current_elements=current_elements.copy(),
                    suggested_elements=current_elements + [elem1],
                    expected_improvement=synergy['quality_synergy'],
                    confidence=0.7,
                    reasoning=f"添加 '{elem1}' 与 '{elem2}' 形成协同效应 (质量提升: +{synergy['quality_synergy']:.2f})"
                ))
        
        # 4. 避免反模式的建议
        for anti_pattern in anti_patterns:
            conflicting_elements = [e for e in anti_pattern['elements'] if e in current_elements]
            if len(conflicting_elements) >= 2:
                # 建议移除效果较差的元素
                worst_element = min(conflicting_elements, 
                                  key=lambda e: element_analyses.get(e, PromptAnalysis('', 0, 0, 0, 0, 0, 0)).success_rate)
                new_elements = [e for e in current_elements if e != worst_element]
                
                suggestions.append(OptimizationSuggestion(
                    suggestion_type='remove_element',
                    current_elements=current_elements.copy(),
                    suggested_elements=new_elements,
                    expected_improvement=anti_pattern['success_degradation'],
                    confidence=0.6,
                    reasoning=f"移除 '{worst_element}' 以避免与其他元素冲突 (冲突类型: {anti_pattern['conflict_type']})"
                ))
        
        # 5. 基于最佳组合的替换建议
        best_combinations = [c for c in combinations if c.effectiveness_score > 0.8][:5]
        for combo in best_combinations:
            combo_elements = list(combo.elements)
            overlap = set(current_elements) & set(combo_elements)
            
            # 如果有部分重叠，建议完成整个组合
            if len(overlap) > 0 and len(overlap) < len(combo_elements):
                missing_elements = [e for e in combo_elements if e not in current_elements]
                if len(missing_elements) <= 2:  # 不建议添加太多元素
                    suggestions.append(OptimizationSuggestion(
                        suggestion_type='add_element',
                        current_elements=current_elements.copy(),
                        suggested_elements=current_elements + missing_elements,
                        expected_improvement=combo.effectiveness_score - 0.5,
                        confidence=0.8,
                        reasoning=f"完成高效组合 {combo_elements} (效果评分: {combo.effectiveness_score:.2f})"
                    ))
        
        # 按预期改进排序
        suggestions.sort(key=lambda x: x.expected_improvement * x.confidence, reverse=True)
        
        logger.info(f"生成了 {len(suggestions)} 个优化建议")
        return suggestions[:10]  # 返回top10
    
    def generate_recommendation_report(self, tasks: List[TaskMetadata], 
                                     results: List[TaskResult]) -> RecommendationReport:
        """生成完整的推荐报告"""
        
        logger.info("生成推荐引擎报告")
        
        if not tasks:
            raise ValueError("没有足够的数据生成报告")
        
        # 分析数据
        combinations = self.analyze_element_combinations(tasks, results)
        synergies = self.identify_element_synergies(tasks, results)
        anti_patterns = self.identify_anti_patterns(tasks, results)
        
        # 获取最佳组合
        best_combinations = combinations[:20] if combinations else []
        
        # 计算性能洞察
        performance_insights = self._calculate_performance_insights(combinations, synergies, anti_patterns)
        
        # 生成通用优化建议（基于数据整体趋势）
        general_suggestions = self._generate_general_suggestions(combinations, synergies, anti_patterns)
        
        return RecommendationReport(
            generated_at=datetime.now(),
            analysis_period=self._get_analysis_period(tasks),
            total_combinations_analyzed=len(combinations),
            best_combinations=best_combinations,
            optimization_suggestions=general_suggestions,
            element_synergies=synergies,
            anti_patterns=anti_patterns,
            performance_insights=performance_insights
        )
    
    def export_recommendation_report(self, report: RecommendationReport, output_path: str):
        """导出推荐报告"""
        
        logger.info(f"导出推荐报告到: {output_path}")
        
        # 转换为可序列化的格式
        report_dict = {
            'generated_at': report.generated_at.isoformat(),
            'analysis_period': report.analysis_period,
            'total_combinations_analyzed': report.total_combinations_analyzed,
            'best_combinations': [
                {
                    'elements': list(combo.elements),
                    'total_count': combo.total_count,
                    'success_rate': combo.success_rate,
                    'avg_quality': combo.avg_quality,
                    'effectiveness_score': combo.effectiveness_score,
                    'compatibility_score': combo.compatibility_score
                }
                for combo in report.best_combinations
            ],
            'optimization_suggestions': [
                asdict(suggestion) for suggestion in report.optimization_suggestions
            ],
            'element_synergies': report.element_synergies,
            'anti_patterns': report.anti_patterns,
            'performance_insights': report.performance_insights
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(report_dict, f, indent=2, ensure_ascii=False)
        
        logger.info("推荐报告导出完成")
    
    def _calculate_combination_effectiveness(self, success_rate: float, avg_quality: float,
                                           quality_variance: float, occurrence_count: int) -> float:
        """计算组合效果评分"""
        # 基础效果 = 成功率 * 质量
        base_effectiveness = success_rate * avg_quality
        
        # 稳定性加成（方差越小越稳定）
        stability_bonus = max(0, 0.2 - quality_variance) * 0.5
        
        # 样本量加成（更多样本更可信）
        sample_bonus = min(0.1, occurrence_count / 50)
        
        effectiveness = base_effectiveness + stability_bonus + sample_bonus
        return min(1.0, max(0.0, effectiveness))
    
    def _calculate_compatibility_score(self, elements: Tuple[str, ...]) -> float:
        """计算兼容性评分"""
        # 简化的兼容性检测逻辑
        score = 1.0
        elements_list = list(elements)
        
        # 检测样式冲突
        style_conflicts = [
            (['realistic', 'photorealistic'], ['anime', 'cartoon', 'manga']),
            (['high quality', 'masterpiece'], ['low quality', 'worst quality']),
            (['detailed', 'ultra detailed'], ['simple', 'minimalist'])
        ]
        
        for group1, group2 in style_conflicts:
            has_group1 = any(any(word in elem for word in group1) for elem in elements_list)
            has_group2 = any(any(word in elem for word in group2) for elem in elements_list)
            
            if has_group1 and has_group2:
                score -= 0.3  # 冲突惩罚
        
        # 检测过度修饰（太多形容词）
        quality_modifiers = ['high quality', 'best quality', 'masterpiece', 'detailed', 'perfect']
        modifier_count = sum(1 for elem in elements_list 
                           for modifier in quality_modifiers 
                           if modifier in elem)
        
        if modifier_count > 2:
            score -= 0.1 * (modifier_count - 2)
        
        return max(0.0, min(1.0, score))
    
    def _identify_conflict_type(self, elements: Tuple[str, ...]) -> str:
        """识别冲突类型"""
        elements_str = ' '.join(elements).lower()
        
        if any(style in elements_str for style in ['realistic', 'photo']) and \
           any(style in elements_str for style in ['anime', 'cartoon']):
            return 'style_conflict'
        
        if any(quality in elements_str for quality in ['high quality', 'masterpiece']) and \
           any(quality in elements_str for quality in ['low quality', 'worst']):
            return 'quality_conflict'
        
        if any(detail in elements_str for detail in ['detailed', 'complex']) and \
           any(detail in elements_str for detail in ['simple', 'minimal']):
            return 'complexity_conflict'
        
        return 'semantic_conflict'
    
    def _calculate_performance_insights(self, combinations: List[ElementCombination],
                                      synergies: List[Dict[str, Any]],
                                      anti_patterns: List[Dict[str, Any]]) -> Dict[str, Any]:
        """计算性能洞察"""
        insights = {}
        
        if combinations:
            # 组合大小效果分析
            size_performance = defaultdict(list)
            for combo in combinations:
                size_performance[len(combo.elements)].append(combo.effectiveness_score)
            
            insights['optimal_combination_size'] = max(
                size_performance.keys(),
                key=lambda size: mean(size_performance[size]) if size_performance[size] else 0
            ) if size_performance else 2
            
            # 成功率分布
            success_rates = [combo.success_rate for combo in combinations]
            insights['success_rate_distribution'] = {
                'mean': mean(success_rates),
                'median': median(success_rates),
                'std': stdev(success_rates) if len(success_rates) > 1 else 0
            }
            
            # 质量分布
            quality_scores = [combo.avg_quality for combo in combinations]
            insights['quality_distribution'] = {
                'mean': mean(quality_scores),
                'median': median(quality_scores),
                'std': stdev(quality_scores) if len(quality_scores) > 1 else 0
            }
        
        # 协同效应统计
        if synergies:
            insights['synergy_strength'] = {
                'max': max(s['synergy_strength'] for s in synergies),
                'avg': mean(s['synergy_strength'] for s in synergies),
                'count': len(synergies)
            }
        
        # 反模式统计
        if anti_patterns:
            insights['anti_pattern_severity'] = {
                'max': max(ap['severity'] for ap in anti_patterns),
                'avg': mean(ap['severity'] for ap in anti_patterns),
                'count': len(anti_patterns)
            }
        
        return insights
    
    def _generate_general_suggestions(self, combinations: List[ElementCombination],
                                    synergies: List[Dict[str, Any]],
                                    anti_patterns: List[Dict[str, Any]]) -> List[OptimizationSuggestion]:
        """生成通用优化建议"""
        suggestions = []
        
        # 基于最佳组合的建议
        if combinations:
            best_combo = combinations[0]
            suggestions.append(OptimizationSuggestion(
                suggestion_type='add_element',
                current_elements=[],
                suggested_elements=list(best_combo.elements),
                expected_improvement=best_combo.effectiveness_score,
                confidence=0.9,
                reasoning=f"使用最佳元素组合，效果评分: {best_combo.effectiveness_score:.2f}"
            ))
        
        # 基于协同效应的建议
        if synergies:
            top_synergy = synergies[0]
            suggestions.append(OptimizationSuggestion(
                suggestion_type='add_element',
                current_elements=[top_synergy['element1']],
                suggested_elements=[top_synergy['element1'], top_synergy['element2']],
                expected_improvement=top_synergy['synergy_strength'],
                confidence=0.8,
                reasoning=f"利用最强协同效应: {top_synergy['element1']} + {top_synergy['element2']}"
            ))
        
        return suggestions
    
    def _get_analysis_period(self, tasks: List[TaskMetadata]) -> str:
        """获取分析时间段"""
        if not tasks:
            return "No data"
        
        dates = [t.created_at for t in tasks if t.created_at]
        if not dates:
            return "Unknown period"
        
        start_date = min(dates).strftime('%Y-%m-%d')
        end_date = max(dates).strftime('%Y-%m-%d')
        return f"{start_date} to {end_date}"
