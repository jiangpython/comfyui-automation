"""分析系统集成模块 - 统一管理所有分析功能"""

import os
import json
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime
from pathlib import Path

from .utils.metadata_schema import TaskMetadata, TaskResult
from .utils.prompt_analyzer import PromptAnalyzer
from .utils.recommendation_engine import RecommendationEngine
from .utils.report_generator import ReportGenerator
from .utils.optimizer import PromptOptimizer
from .utils.result_manager import ResultManager

logger = logging.getLogger(__name__)

class AnalysisManager:
    """分析系统管理器"""
    
    def __init__(self, output_dir: str = "output/analysis"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # 初始化所有分析组件
        self.prompt_analyzer = PromptAnalyzer()
        self.recommendation_engine = RecommendationEngine()
        self.report_generator = ReportGenerator()
        self.optimizer = PromptOptimizer(
            analyzer=self.prompt_analyzer,
            recommendation_engine=self.recommendation_engine
        )
        self.result_manager = ResultManager(
            database_path=Path("data/database/tasks.db"),
            output_directory=Path("output")
        )
        
        logger.info("分析系统管理器初始化完成")
    
    def run_complete_analysis(self, data_source: str = "database") -> Dict[str, Any]:
        """运行完整分析流程"""
        
        logger.info("开始运行完整分析流程")
        
        try:
            # 1. 加载数据
            tasks, results = self._load_analysis_data(data_source)
            
            if not tasks:
                logger.warning("没有找到可分析的任务数据")
                return {'error': '没有找到可分析的任务数据'}
            
            logger.info(f"加载了 {len(tasks)} 个任务和 {len(results)} 个结果")
            
            # 2. 基础统计分析
            basic_stats = self._generate_basic_statistics(tasks, results)
            
            # 3. 提示词元素分析
            element_analysis = self.prompt_analyzer.analyze_prompt_elements(tasks, results)
            
            # 4. 失败模式识别
            failing_patterns = self.prompt_analyzer.identify_failing_patterns(tasks)
            
            # 5. 时间趋势分析
            temporal_trends = self.prompt_analyzer.analyze_temporal_trends(tasks)
            
            # 6. 元素相关性分析
            correlations = self.prompt_analyzer.get_element_correlations(tasks)
            
            # 7. 元素组合分析
            combinations = self.recommendation_engine.analyze_element_combinations(tasks, results)
            
            # 8. 协同效应识别
            synergies = self.recommendation_engine.identify_element_synergies(tasks, results)
            
            # 9. 反模式识别
            anti_patterns = self.recommendation_engine.identify_anti_patterns(tasks, results)
            
            # 10. 生成优化建议
            optimization_suggestions = self._generate_optimization_suggestions(
                element_analysis, combinations, synergies, anti_patterns
            )
            
            # 11. 编译完整报告
            analysis_results = {
                'analysis_timestamp': datetime.now().isoformat(),
                'data_summary': {
                    'total_tasks': len(tasks),
                    'total_results': len(results),
                    'analysis_period': self._get_analysis_period(tasks)
                },
                'basic_statistics': basic_stats,
                'element_analysis': self._format_element_analysis(element_analysis),
                'failing_patterns': self._format_failing_patterns(failing_patterns),
                'temporal_trends': temporal_trends,
                'element_correlations': correlations,
                'element_combinations': self._format_combinations(combinations),
                'element_synergies': self._format_synergies(synergies),
                'anti_patterns': self._format_anti_patterns(anti_patterns),
                'optimization_suggestions': optimization_suggestions
            }
            
            # 12. 生成和保存报告
            report_files = self._save_analysis_reports(analysis_results, tasks, results)
            analysis_results['report_files'] = report_files
            
            logger.info("完整分析流程执行完成")
            return analysis_results
            
        except Exception as e:
            logger.error(f"分析流程执行失败: {e}")
            return {'error': f'分析执行失败: {str(e)}'}
    
    def generate_optimization_iteration(self, base_prompts: List[str] = None, 
                                      iteration_size: int = 50) -> Dict[str, Any]:
        """生成优化迭代"""
        
        logger.info(f"生成优化迭代，目标数量: {iteration_size}")
        
        # 加载历史数据
        tasks, results = self._load_analysis_data()
        
        if base_prompts:
            # 优化现有提示词
            optimization_results = self.optimizer.batch_optimize_prompts(base_prompts, tasks, results)
            optimized_prompts = [r.optimized_prompt for r in optimization_results]
        else:
            # 生成全新的迭代提示词
            optimized_prompts = self.optimizer.generate_next_iteration(tasks, results, iteration_size)
            optimization_results = []
        
        # 保存迭代结果
        iteration_data = {
            'iteration_timestamp': datetime.now().isoformat(),
            'base_prompts': base_prompts or [],
            'optimized_prompts': optimized_prompts,
            'optimization_results': [
                {
                    'original': r.original_prompt,
                    'optimized': r.optimized_prompt,
                    'suggestions_count': len(r.suggestions_applied),
                    'predicted_success_rate': r.predicted_success_rate,
                    'predicted_quality': r.predicted_quality_score
                } for r in optimization_results
            ],
            'total_prompts': len(optimized_prompts)
        }
        
        # 保存到文件
        iteration_file = self.output_dir / f"iteration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(iteration_file, 'w', encoding='utf-8') as f:
            json.dump(iteration_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"优化迭代生成完成，共 {len(optimized_prompts)} 个提示词")
        
        return {
            'iteration_file': str(iteration_file),
            'prompts': optimized_prompts,
            'optimization_summary': {
                'total_optimized': len(optimization_results),
                'avg_predicted_success_rate': 
                    sum(r.predicted_success_rate for r in optimization_results) / max(1, len(optimization_results)),
                'avg_predicted_quality': 
                    sum(r.predicted_quality_score for r in optimization_results) / max(1, len(optimization_results))
            } if optimization_results else None
        }
    
    def analyze_element_performance(self, element: str) -> Dict[str, Any]:
        """分析特定元素的性能"""
        
        logger.info(f"分析元素 '{element}' 的性能")
        
        tasks, results = self._load_analysis_data()
        
        # 找到包含该元素的任务
        element_tasks = []
        for task in tasks:
            if task.status not in ['completed', 'failed']:
                continue
            
            task_elements = self.prompt_analyzer._extract_prompt_elements(task.prompt)
            if element in task_elements:
                element_tasks.append(task)
        
        if not element_tasks:
            return {'error': f"未找到包含元素 '{element}' 的任务"}
        
        # 计算性能指标
        total_tasks = len(element_tasks)
        completed_tasks = len([t for t in element_tasks if t.status == 'completed'])
        success_rate = completed_tasks / total_tasks
        
        quality_scores = [t.quality_score for t in element_tasks if t.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        generation_times = [t.actual_time for t in element_tasks if t.actual_time is not None]
        avg_time = sum(generation_times) / len(generation_times) if generation_times else 0
        
        return {
            'element': element,
            'total_usage': total_tasks,
            'success_rate': success_rate,
            'average_quality': avg_quality,
            'average_generation_time': avg_time,
            'usage_frequency': total_tasks / len(tasks),
            'recent_usage': len([t for t in element_tasks 
                               if t.created_at and 
                               (datetime.now() - t.created_at).days <= 7])
        }
    
    def get_analysis_dashboard_data(self) -> Dict[str, Any]:
        """获取分析仪表板数据"""
        
        logger.info("生成分析仪表板数据")
        
        tasks, results = self._load_analysis_data()
        
        if not tasks:
            return {'error': '没有数据可显示'}
        
        # 基础指标
        basic_metrics = self._generate_basic_statistics(tasks, results)
        
        # 近期趋势（最近7天）
        recent_trends = self.prompt_analyzer.analyze_temporal_trends(tasks, days=7)
        
        # 顶级元素
        element_analysis = self.prompt_analyzer.analyze_prompt_elements(tasks, results)
        top_elements = sorted(element_analysis.values(), 
                            key=lambda x: x.success_rate, reverse=True)[:10]
        
        # 问题模式
        failing_patterns = self.prompt_analyzer.identify_failing_patterns(tasks, min_occurrence=3)[:5]
        
        return {
            'last_updated': datetime.now().isoformat(),
            'basic_metrics': basic_metrics,
            'recent_trends': recent_trends,
            'top_performing_elements': [
                {
                    'element': elem.element,
                    'success_rate': elem.success_rate,
                    'usage_count': elem.total_count,
                    'avg_quality': elem.avg_quality
                } for elem in top_elements
            ],
            'problematic_patterns': [
                {
                    'pattern': pattern.pattern,
                    'failure_rate': 1 - pattern.success_rate,
                    'occurrence_count': pattern.total_count
                } for pattern in failing_patterns
            ]
        }
    
    def _load_analysis_data(self, source: str = "database") -> tuple:
        """加载分析数据"""

        # 获取所有任务
        tasks = self.result_manager.get_all_tasks()

        # 获取对应的结果
        results = []
        for task in tasks:
            result = self.result_manager.get_result(task.task_id)
            if result:
                results.append(result)

        return tasks, results
    
    def _generate_basic_statistics(self, tasks: List[TaskMetadata], 
                                  results: List[TaskResult]) -> Dict[str, Any]:
        """生成基础统计信息"""
        
        total_tasks = len(tasks)
        completed_tasks = len([t for t in tasks if t.status == 'completed'])
        failed_tasks = len([t for t in tasks if t.status == 'failed'])
        pending_tasks = total_tasks - completed_tasks - failed_tasks
        
        success_rate = completed_tasks / total_tasks if total_tasks > 0 else 0
        
        # 质量统计
        quality_scores = [t.quality_score for t in tasks if t.quality_score is not None]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0
        
        # 时间统计
        generation_times = [t.actual_time for t in tasks if t.actual_time is not None]
        avg_generation_time = sum(generation_times) / len(generation_times) if generation_times else 0
        
        return {
            'total_tasks': total_tasks,
            'completed_tasks': completed_tasks,
            'failed_tasks': failed_tasks,
            'pending_tasks': pending_tasks,
            'overall_success_rate': success_rate,
            'average_quality_score': avg_quality,
            'average_generation_time': avg_generation_time,
            'high_quality_count': len([s for s in quality_scores if s >= 0.8])
        }
    
    def _get_analysis_period(self, tasks: List[TaskMetadata]) -> str:
        """获取分析时间段"""
        dates = [t.created_at for t in tasks if t.created_at]
        if not dates:
            return "Unknown"
        
        min_date = min(dates).strftime('%Y-%m-%d')
        max_date = max(dates).strftime('%Y-%m-%d')
        return f"{min_date} to {max_date}"
    
    def _format_element_analysis(self, element_analysis) -> List[Dict[str, Any]]:
        """格式化元素分析结果"""
        return [
            {
                'element': analysis.element,
                'total_count': analysis.total_count,
                'success_count': analysis.success_count,
                'success_rate': analysis.success_rate,
                'avg_quality': analysis.avg_quality,
                'avg_generation_time': analysis.avg_generation_time,
                'usage_frequency': analysis.usage_frequency
            } for analysis in element_analysis.values()
        ]
    
    def _format_failing_patterns(self, failing_patterns) -> List[Dict[str, Any]]:
        """格式化失败模式"""
        return [
            {
                'pattern': pattern.pattern,
                'elements': pattern.elements,
                'total_count': pattern.total_count,
                'success_count': pattern.success_count,
                'success_rate': pattern.success_rate,
                'avg_quality': pattern.avg_quality,
                'quality_variance': pattern.quality_variance
            } for pattern in failing_patterns
        ]
    
    def _format_combinations(self, combinations) -> List[Dict[str, Any]]:
        """格式化元素组合"""
        return [
            {
                'elements': combo.elements,
                'occurrence_count': combo.occurrence_count,
                'success_count': combo.success_count,
                'success_rate': combo.success_rate,
                'avg_quality': combo.avg_quality,
                'effectiveness_score': combo.effectiveness_score
            } for combo in combinations
        ]
    
    def _format_synergies(self, synergies) -> List[Dict[str, Any]]:
        """格式化协同效应"""
        return [
            {
                'primary_element': synergy.primary_element,
                'synergy_elements': synergy.synergy_elements,
                'synergy_strength': synergy.synergy_strength,
                'quality_boost': synergy.quality_boost,
                'success_rate_boost': synergy.success_rate_boost,
                'confidence': synergy.confidence
            } for synergy in synergies
        ]
    
    def _format_anti_patterns(self, anti_patterns) -> List[Dict[str, Any]]:
        """格式化反模式"""
        return [
            {
                'elements': pattern.elements,
                'conflict_type': pattern.conflict_type,
                'negative_impact': pattern.negative_impact,
                'occurrence_count': pattern.occurrence_count,
                'confidence': pattern.confidence
            } for pattern in anti_patterns
        ]
    
    def _generate_optimization_suggestions(self, element_analysis, combinations, 
                                          synergies, anti_patterns) -> List[Dict[str, Any]]:
        """生成优化建议"""
        
        suggestions = []
        
        # 基于高效元素的建议
        top_elements = sorted(element_analysis.values(), 
                            key=lambda x: x.success_rate * x.avg_quality, reverse=True)[:5]
        
        for elem in top_elements:
            suggestions.append({
                'type': 'element_recommendation',
                'suggestion': f"推荐使用高效元素 '{elem.element}'",
                'reason': f"成功率 {elem.success_rate:.1%}，平均质量 {elem.avg_quality:.2f}",
                'priority': 'high',
                'impact': 'positive'
            })
        
        # 基于协同效应的建议
        for synergy in synergies[:3]:
            suggestions.append({
                'type': 'synergy_recommendation',
                'suggestion': f"组合使用 '{synergy.primary_element}' 与 {', '.join(synergy.synergy_elements)}",
                'reason': f"协同效应强度 {synergy.synergy_strength:.2f}，质量提升 {synergy.quality_boost:.2f}",
                'priority': 'medium',
                'impact': 'positive'
            })
        
        # 基于反模式的建议
        for anti_pattern in anti_patterns[:3]:
            suggestions.append({
                'type': 'anti_pattern_warning',
                'suggestion': f"避免同时使用 {', '.join(anti_pattern.elements)}",
                'reason': f"检测到冲突模式，负面影响 {anti_pattern.negative_impact:.2f}",
                'priority': 'high',
                'impact': 'negative'
            })
        
        # 基于失败模式的建议
        if hasattr(self, '_last_failing_patterns'):
            for pattern in self._last_failing_patterns[:2]:
                suggestions.append({
                    'type': 'pattern_warning',
                    'suggestion': f"谨慎使用 '{pattern.pattern}' 模式",
                    'reason': f"该模式成功率仅为 {pattern.success_rate:.1%}",
                    'priority': 'medium',
                    'impact': 'negative'
                })
        
        return suggestions
    
    def _save_analysis_reports(self, analysis_results: Dict[str, Any], 
                              tasks: List[TaskMetadata], results: List[TaskResult]) -> Dict[str, str]:
        """保存分析报告"""
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        report_files = {}
        
        try:
            # 生成HTML报告
            html_report = self.report_generator.generate_analysis_report(tasks, results, 'html')
            html_file = self.output_dir / f"analysis_report_{timestamp}.html"
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(html_report)
            report_files['html'] = str(html_file)
            
            # 生成JSON报告
            json_report = self.report_generator.generate_analysis_report(tasks, results, 'json')
            json_file = self.output_dir / f"analysis_data_{timestamp}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                f.write(json_report)
            report_files['json'] = str(json_file)
            
            # 保存完整分析结果
            full_analysis_file = self.output_dir / f"full_analysis_{timestamp}.json"
            with open(full_analysis_file, 'w', encoding='utf-8') as f:
                json.dump(analysis_results, f, indent=2, ensure_ascii=False)
            report_files['full_analysis'] = str(full_analysis_file)
            
            logger.info(f"分析报告保存完成，文件: {list(report_files.keys())}")
            
        except Exception as e:
            logger.error(f"保存分析报告失败: {e}")
        
        return report_files