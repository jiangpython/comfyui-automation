"""提示词分析器 - 分析提示词成功率和效果"""

import re
import json
import logging
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from statistics import mean, stdev

from .metadata_schema import TaskMetadata, TaskResult

logger = logging.getLogger(__name__)

@dataclass
class PromptAnalysis:
    """提示词分析结果"""
    element: str
    total_count: int
    success_count: int
    success_rate: float
    avg_quality: float
    avg_generation_time: float
    usage_frequency: float

@dataclass
class PromptPattern:
    """提示词模式"""
    pattern: str
    elements: List[str]
    total_count: int
    success_count: int
    success_rate: float
    avg_quality: float
    quality_variance: float

class PromptAnalyzer:
    """提示词分析器"""
    
    def __init__(self):
        self.common_separators = [',', ';', '|', '\n']
        self.stop_words = {'and', 'the', 'a', 'an', 'with', 'by', 'in', 'on', 'at', 'to'}
        
    def analyze_prompt_elements(self, tasks: List[TaskMetadata], results: List[TaskResult]) -> Dict[str, PromptAnalysis]:
        """分析提示词元素的成功率和质量"""
        
        logger.info("开始分析提示词元素")
        
        # 创建任务结果映射
        result_map = {r.task_id: r for r in results}
        
        # 存储每个元素的统计数据
        element_stats = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'quality_scores': [],
            'generation_times': []
        })
        
        total_tasks = len(tasks)
        
        for task in tasks:
            if task.status not in ['completed', 'failed']:
                continue
                
            # 解析提示词元素
            elements = self._extract_prompt_elements(task.prompt)
            task_result = result_map.get(task.task_id)
            
            is_success = task.status == 'completed'
            quality_score = task.quality_score or 0
            generation_time = task.actual_time or 0
            
            for element in elements:
                element_stats[element]['total'] += 1
                
                if is_success:
                    element_stats[element]['success'] += 1
                    element_stats[element]['quality_scores'].append(quality_score)
                    element_stats[element]['generation_times'].append(generation_time)
        
        # 生成分析结果
        analyses = {}
        for element, stats in element_stats.items():
            if stats['total'] < 3:  # 过滤出现次数太少的元素
                continue
                
            success_rate = stats['success'] / stats['total'] if stats['total'] > 0 else 0
            avg_quality = mean(stats['quality_scores']) if stats['quality_scores'] else 0
            avg_time = mean(stats['generation_times']) if stats['generation_times'] else 0
            usage_frequency = stats['total'] / total_tasks
            
            analyses[element] = PromptAnalysis(
                element=element,
                total_count=stats['total'],
                success_count=stats['success'],
                success_rate=success_rate,
                avg_quality=avg_quality,
                avg_generation_time=avg_time,
                usage_frequency=usage_frequency
            )
        
        logger.info(f"完成提示词元素分析，共分析 {len(analyses)} 个元素")
        return analyses
    
    def identify_failing_patterns(self, tasks: List[TaskMetadata], min_occurrence: int = 5) -> List[PromptPattern]:
        """识别容易失败的提示词模式"""
        
        logger.info("识别失败率较高的提示词模式")
        
        pattern_stats = defaultdict(lambda: {
            'total': 0,
            'success': 0,
            'quality_scores': [],
            'elements': set()
        })
        
        for task in tasks:
            if task.status not in ['completed', 'failed']:
                continue
                
            # 提取关键模式
            patterns = self._extract_patterns(task.prompt)
            elements = self._extract_prompt_elements(task.prompt)
            
            is_success = task.status == 'completed'
            quality_score = task.quality_score or 0
            
            for pattern in patterns:
                pattern_stats[pattern]['total'] += 1
                pattern_stats[pattern]['elements'].update(elements[:3])  # 取前3个主要元素
                
                if is_success:
                    pattern_stats[pattern]['success'] += 1
                    pattern_stats[pattern]['quality_scores'].append(quality_score)
        
        # 生成失败模式列表
        failing_patterns = []
        for pattern, stats in pattern_stats.items():
            if stats['total'] < min_occurrence:
                continue
                
            success_rate = stats['success'] / stats['total']
            if success_rate < 0.7:  # 成功率低于70%的模式
                avg_quality = mean(stats['quality_scores']) if stats['quality_scores'] else 0
                quality_var = stdev(stats['quality_scores']) if len(stats['quality_scores']) > 1 else 0
                
                failing_patterns.append(PromptPattern(
                    pattern=pattern,
                    elements=list(stats['elements']),
                    total_count=stats['total'],
                    success_count=stats['success'],
                    success_rate=success_rate,
                    avg_quality=avg_quality,
                    quality_variance=quality_var
                ))
        
        # 按成功率排序
        failing_patterns.sort(key=lambda x: x.success_rate)
        
        logger.info(f"识别出 {len(failing_patterns)} 个问题模式")
        return failing_patterns
    
    def analyze_temporal_trends(self, tasks: List[TaskMetadata], days: int = 30) -> Dict[str, Any]:
        """分析时间趋势"""
        
        logger.info(f"分析最近 {days} 天的趋势")
        
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_tasks = [t for t in tasks if t.created_at and t.created_at >= cutoff_date]
        
        if not recent_tasks:
            return {'error': '没有足够的近期数据'}
        
        # 按日期分组
        daily_stats = defaultdict(lambda: {
            'total': 0,
            'completed': 0,
            'failed': 0,
            'quality_scores': []
        })
        
        for task in recent_tasks:
            date_key = task.created_at.strftime('%Y-%m-%d')
            daily_stats[date_key]['total'] += 1
            
            if task.status == 'completed':
                daily_stats[date_key]['completed'] += 1
                if task.quality_score:
                    daily_stats[date_key]['quality_scores'].append(task.quality_score)
            elif task.status == 'failed':
                daily_stats[date_key]['failed'] += 1
        
        # 计算趋势
        dates = sorted(daily_stats.keys())
        success_rates = []
        quality_trends = []
        
        for date in dates:
            stats = daily_stats[date]
            success_rate = stats['completed'] / stats['total'] if stats['total'] > 0 else 0
            success_rates.append(success_rate)
            
            avg_quality = mean(stats['quality_scores']) if stats['quality_scores'] else 0
            quality_trends.append(avg_quality)
        
        return {
            'period': f"{dates[0]} to {dates[-1]}" if dates else "No data",
            'total_tasks': len(recent_tasks),
            'daily_data': dict(daily_stats),
            'success_rate_trend': success_rates,
            'quality_trend': quality_trends,
            'avg_success_rate': mean(success_rates) if success_rates else 0,
            'avg_quality': mean(quality_trends) if quality_trends else 0
        }
    
    def get_element_correlations(self, tasks: List[TaskMetadata], min_cooccurrence: int = 5) -> List[Dict[str, Any]]:
        """分析元素之间的相关性"""
        
        logger.info("分析提示词元素相关性")
        
        # 统计元素共现
        cooccurrence = defaultdict(lambda: defaultdict(int))
        element_success = defaultdict(lambda: {'total': 0, 'success': 0})
        
        for task in tasks:
            if task.status not in ['completed', 'failed']:
                continue
                
            elements = self._extract_prompt_elements(task.prompt)
            is_success = task.status == 'completed'
            
            # 记录单个元素统计
            for element in elements:
                element_success[element]['total'] += 1
                if is_success:
                    element_success[element]['success'] += 1
            
            # 记录元素共现
            for i, elem1 in enumerate(elements):
                for elem2 in elements[i+1:]:
                    cooccurrence[elem1][elem2] += 1
                    cooccurrence[elem2][elem1] += 1
        
        # 计算相关性
        correlations = []
        for elem1, co_dict in cooccurrence.items():
            for elem2, count in co_dict.items():
                if count < min_cooccurrence:
                    continue
                
                # 计算提升度 (lift)
                elem1_prob = element_success[elem1]['total'] / len(tasks)
                elem2_prob = element_success[elem2]['total'] / len(tasks)
                joint_prob = count / len(tasks)
                
                lift = joint_prob / (elem1_prob * elem2_prob) if elem1_prob * elem2_prob > 0 else 0
                
                if lift > 1.2:  # 只保留有正相关的组合
                    correlations.append({
                        'element1': elem1,
                        'element2': elem2,
                        'cooccurrence_count': count,
                        'lift': lift,
                        'confidence': count / element_success[elem1]['total']
                    })
        
        # 按提升度排序
        correlations.sort(key=lambda x: x['lift'], reverse=True)
        
        logger.info(f"发现 {len(correlations)} 个显著相关性")
        return correlations[:20]  # 返回top20
    
    def _extract_prompt_elements(self, prompt: str) -> List[str]:
        """从提示词中提取元素"""
        if not prompt:
            return []
        
        # 清理和标准化
        prompt = prompt.lower().strip()
        
        # 按分隔符分割
        elements = []
        for sep in self.common_separators:
            prompt = prompt.replace(sep, ',')
        
        parts = [part.strip() for part in prompt.split(',') if part.strip()]
        
        # 清理元素
        for part in parts:
            # 移除特殊字符
            cleaned = re.sub(r'[^\w\s-]', '', part)
            cleaned = re.sub(r'\s+', ' ', cleaned).strip()
            
            # 过滤停用词和过短的词
            if cleaned and len(cleaned) > 2 and cleaned not in self.stop_words:
                elements.append(cleaned)
        
        return elements[:10]  # 限制元素数量
    
    def _extract_patterns(self, prompt: str) -> List[str]:
        """提取提示词模式"""
        patterns = []
        
        # 长度模式
        word_count = len(prompt.split())
        if word_count <= 5:
            patterns.append("short_prompt")
        elif word_count <= 15:
            patterns.append("medium_prompt")
        else:
            patterns.append("long_prompt")
        
        # 内容模式
        prompt_lower = prompt.lower()
        
        if any(word in prompt_lower for word in ['portrait', 'face', 'person', 'man', 'woman']):
            patterns.append("portrait_content")
        
        if any(word in prompt_lower for word in ['landscape', 'nature', 'mountain', 'ocean', 'forest']):
            patterns.append("landscape_content")
        
        if any(word in prompt_lower for word in ['anime', 'manga', 'cartoon']):
            patterns.append("anime_style")
        
        if any(word in prompt_lower for word in ['realistic', 'photorealistic', 'photo']):
            patterns.append("realistic_style")
        
        if any(word in prompt_lower for word in ['art', 'painting', 'digital art']):
            patterns.append("artistic_style")
        
        # 修饰词模式
        if any(word in prompt_lower for word in ['highly detailed', 'ultra detailed', '4k', '8k', 'hd']):
            patterns.append("high_detail_request")
        
        if any(word in prompt_lower for word in ['masterpiece', 'best quality', 'perfect']):
            patterns.append("quality_emphasis")
        
        return patterns
    
    def generate_summary_report(self, tasks: List[TaskMetadata], results: List[TaskResult]) -> Dict[str, Any]:
        """生成综合分析报告"""
        
        logger.info("生成提示词分析总结报告")
        
        if not tasks:
            return {'error': '没有数据可分析'}
        
        # 基础统计
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'completed'])
        failed_tasks = len([t for t in tasks if t.status == 'failed'])
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # 质量统计
        quality_scores = [t.quality_score for t in tasks if t.quality_score is not None]
        avg_quality = mean(quality_scores) if quality_scores else 0
        
        # 时间统计
        generation_times = [t.actual_time for t in tasks if t.actual_time is not None]
        avg_time = mean(generation_times) if generation_times else 0
        
        # 元素分析
        element_analyses = self.analyze_prompt_elements(tasks, results)
        top_elements = sorted(element_analyses.values(), key=lambda x: x.success_rate, reverse=True)[:10]
        worst_elements = sorted(element_analyses.values(), key=lambda x: x.success_rate)[:5]
        
        # 失败模式
        failing_patterns = self.identify_failing_patterns(tasks)
        
        # 时间趋势
        temporal_trends = self.analyze_temporal_trends(tasks)
        
        # 相关性分析
        correlations = self.get_element_correlations(tasks)
        
        return {
            'generated_at': datetime.now().isoformat(),
            'analysis_period': {
                'total_tasks': total_tasks,
                'date_range': self._get_date_range(tasks)
            },
            'overall_performance': {
                'success_rate': success_rate,
                'completed_tasks': completed_tasks,
                'failed_tasks': failed_tasks,
                'average_quality': avg_quality,
                'average_generation_time': avg_time
            },
            'top_performing_elements': [
                {
                    'element': elem.element,
                    'success_rate': elem.success_rate,
                    'avg_quality': elem.avg_quality,
                    'usage_count': elem.total_count
                } for elem in top_elements
            ],
            'problematic_elements': [
                {
                    'element': elem.element,
                    'success_rate': elem.success_rate,
                    'avg_quality': elem.avg_quality,
                    'usage_count': elem.total_count
                } for elem in worst_elements
            ],
            'failing_patterns': [
                {
                    'pattern': pattern.pattern,
                    'success_rate': pattern.success_rate,
                    'count': pattern.total_count,
                    'key_elements': pattern.elements
                } for pattern in failing_patterns[:5]
            ],
            'temporal_trends': temporal_trends,
            'element_correlations': correlations[:10],
            'recommendations': self._generate_recommendations(
                top_elements, worst_elements, failing_patterns
            )
        }
    
    def _get_date_range(self, tasks: List[TaskMetadata]) -> str:
        """获取任务的日期范围"""
        dates = [t.created_at for t in tasks if t.created_at]
        if not dates:
            return "Unknown"
        
        min_date = min(dates).strftime('%Y-%m-%d')
        max_date = max(dates).strftime('%Y-%m-%d')
        return f"{min_date} to {max_date}"
    
    def _generate_recommendations(self, top_elements, worst_elements, failing_patterns) -> List[str]:
        """生成优化建议"""
        recommendations = []
        
        if top_elements:
            top_element = top_elements[0]
            recommendations.append(
                f"建议多使用高效元素 '{top_element.element}'，其成功率达 {top_element.success_rate:.1%}"
            )
        
        if worst_elements:
            worst_element = worst_elements[0]
            recommendations.append(
                f"避免或谨慎使用 '{worst_element.element}'，其成功率仅为 {worst_element.success_rate:.1%}"
            )
        
        if failing_patterns:
            pattern = failing_patterns[0]
            recommendations.append(
                f"注意 '{pattern.pattern}' 模式，容易导致生成失败"
            )
        
        recommendations.extend([
            "保持提示词简洁明确，避免过于复杂的描述",
            "使用具体而非抽象的词汇描述想要的效果",
            "定期检查生成质量，及时调整提示词策略"
        ])
        
        return recommendations