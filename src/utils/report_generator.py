"""报告生成器 - 生成HTML可视化分析报告"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import asdict
import base64

from .prompt_analyzer import PromptAnalyzer
from .recommendation_engine import RecommendationEngine, RecommendationReport

logger = logging.getLogger(__name__)

class ReportGenerator:
    """报告生成器"""
    
    def __init__(self, output_dir: str = "output/reports"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.template_dir = Path("templates")
        self.static_dir = Path("static")
        
    def generate_analysis_report(self, tasks, results, export_format: str = 'html') -> str:
        """生成完整的分析报告"""
        
        logger.info(f"生成分析报告 ({export_format})")
        
        # 进行分析
        prompt_analyzer = PromptAnalyzer()
        recommendation_engine = RecommendationEngine()
        
        # 生成分析数据
        prompt_analysis = prompt_analyzer.generate_summary_report(tasks, results)
        recommendation_report = recommendation_engine.generate_recommendation_report(tasks, results)
        
        if export_format.lower() == 'html':
            return self._generate_html_report(prompt_analysis, recommendation_report)
        elif export_format.lower() == 'json':
            return self._generate_json_report(prompt_analysis, recommendation_report)
        else:
            raise ValueError(f"不支持的导出格式: {export_format}")
    
    def _generate_html_report(self, prompt_analysis: Dict, recommendation_report: RecommendationReport) -> str:
        """生成HTML格式报告"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"analysis_report_{timestamp}.html"
        
        # 准备图表数据
        charts_data = self._prepare_charts_data(prompt_analysis, recommendation_report)
        
        # 生成HTML内容
        html_content = self._build_html_content(prompt_analysis, recommendation_report, charts_data)
        
        # 写入文件
        with open(report_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        logger.info(f"HTML报告已生成: {report_file}")
        return str(report_file)
    
    def _generate_json_report(self, prompt_analysis: Dict, recommendation_report: RecommendationReport) -> str:
        """生成JSON格式报告"""
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_file = self.output_dir / f"analysis_report_{timestamp}.json"
        
        # 合并数据
        combined_data = {
            'generated_at': datetime.now().isoformat(),
            'report_type': 'comprehensive_analysis',
            'prompt_analysis': prompt_analysis,
            'recommendation_report': {
                'generated_at': recommendation_report.generated_at.isoformat(),
                'analysis_period': recommendation_report.analysis_period,
                'total_combinations_analyzed': recommendation_report.total_combinations_analyzed,
                'best_combinations': [
                    {
                        'elements': list(combo.elements),
                        'total_count': combo.total_count,
                        'success_rate': combo.success_rate,
                        'avg_quality': combo.avg_quality,
                        'effectiveness_score': combo.effectiveness_score
                    }
                    for combo in recommendation_report.best_combinations
                ],
                'optimization_suggestions': [
                    asdict(suggestion) for suggestion in recommendation_report.optimization_suggestions
                ],
                'element_synergies': recommendation_report.element_synergies,
                'anti_patterns': recommendation_report.anti_patterns,
                'performance_insights': recommendation_report.performance_insights
            }
        }
        
        # 写入文件
        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(combined_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"JSON报告已生成: {report_file}")
        return str(report_file)
    
    def _prepare_charts_data(self, prompt_analysis: Dict, recommendation_report: RecommendationReport) -> Dict:
        """准备图表数据"""
        
        charts = {}
        
        # 1. 整体性能趋势图
        if 'temporal_trends' in prompt_analysis and 'success_rate_trend' in prompt_analysis['temporal_trends']:
            charts['performance_trend'] = {
                'type': 'line',
                'title': '成功率和质量趋势',
                'data': {
                    'labels': list(range(len(prompt_analysis['temporal_trends']['success_rate_trend']))),
                    'datasets': [
                        {
                            'label': '成功率',
                            'data': prompt_analysis['temporal_trends']['success_rate_trend'],
                            'borderColor': 'rgb(75, 192, 192)',
                            'backgroundColor': 'rgba(75, 192, 192, 0.2)'
                        },
                        {
                            'label': '质量分数',
                            'data': prompt_analysis['temporal_trends']['quality_trend'],
                            'borderColor': 'rgb(255, 99, 132)',
                            'backgroundColor': 'rgba(255, 99, 132, 0.2)'
                        }
                    ]
                }
            }
        
        # 2. 元素效果对比图
        if 'top_performing_elements' in prompt_analysis:
            elements = prompt_analysis['top_performing_elements'][:10]
            charts['element_performance'] = {
                'type': 'bar',
                'title': '高效元素排行',
                'data': {
                    'labels': [elem['element'] for elem in elements],
                    'datasets': [{
                        'label': '成功率',
                        'data': [elem['success_rate'] for elem in elements],
                        'backgroundColor': 'rgba(54, 162, 235, 0.6)',
                        'borderColor': 'rgba(54, 162, 235, 1)',
                        'borderWidth': 1
                    }]
                }
            }
        
        # 3. 协同效应网络图
        if recommendation_report.element_synergies:
            synergies = recommendation_report.element_synergies[:15]
            nodes = []
            edges = []
            
            # 收集所有元素
            all_elements = set()
            for synergy in synergies:
                all_elements.add(synergy['element1'])
                all_elements.add(synergy['element2'])
            
            # 创建节点
            for i, element in enumerate(all_elements):
                nodes.append({
                    'id': element,
                    'label': element,
                    'color': f'hsl({i * 360 / len(all_elements)}, 70%, 50%)'
                })
            
            # 创建连接
            for synergy in synergies:
                edges.append({
                    'from': synergy['element1'],
                    'to': synergy['element2'],
                    'width': min(10, synergy['synergy_strength'] * 20),
                    'label': f"+{synergy['synergy_strength']:.2f}"
                })
            
            charts['synergy_network'] = {
                'type': 'network',
                'title': '元素协同效应网络',
                'data': {
                    'nodes': nodes,
                    'edges': edges
                }
            }
        
        # 4. 最佳组合雷达图
        if recommendation_report.best_combinations:
            best_combo = recommendation_report.best_combinations[0]
            charts['combination_radar'] = {
                'type': 'radar',
                'title': f'最佳组合分析: {", ".join(best_combo.elements)}',
                'data': {
                    'labels': ['成功率', '平均质量', '稳定性', '兼容性', '效果评分'],
                    'datasets': [{
                        'label': '组合表现',
                        'data': [
                            best_combo.success_rate,
                            best_combo.avg_quality,
                            max(0, 1 - best_combo.quality_variance),
                            best_combo.compatibility_score,
                            best_combo.effectiveness_score
                        ],
                        'backgroundColor': 'rgba(255, 99, 132, 0.2)',
                        'borderColor': 'rgba(255, 99, 132, 1)',
                        'pointBackgroundColor': 'rgba(255, 99, 132, 1)'
                    }]
                }
            }
        
        # 5. 问题模式饼图
        if recommendation_report.anti_patterns:
            conflict_types = {}
            for pattern in recommendation_report.anti_patterns:
                conflict_type = pattern['conflict_type']
                conflict_types[conflict_type] = conflict_types.get(conflict_type, 0) + 1
            
            charts['conflict_types'] = {
                'type': 'doughnut',
                'title': '冲突模式分布',
                'data': {
                    'labels': list(conflict_types.keys()),
                    'datasets': [{
                        'data': list(conflict_types.values()),
                        'backgroundColor': [
                            'rgba(255, 99, 132, 0.8)',
                            'rgba(54, 162, 235, 0.8)',
                            'rgba(255, 205, 86, 0.8)',
                            'rgba(75, 192, 192, 0.8)',
                            'rgba(153, 102, 255, 0.8)'
                        ]
                    }]
                }
            }
        
        return charts
    
    def _build_html_content(self, prompt_analysis: Dict, recommendation_report: RecommendationReport, 
                          charts_data: Dict) -> str:
        """构建HTML内容"""
        
        html_template = '''
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ComfyUI 自动化系统 - 分析报告</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        :root {
            --primary-color: #3498db;
            --secondary-color: #2c3e50;
            --success-color: #27ae60;
            --warning-color: #f39c12;
            --danger-color: #e74c3c;
            --bg-color: #ecf0f1;
            --card-bg: #ffffff;
            --text-color: #2c3e50;
            --border-color: #bdc3c7;
        }
        
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: var(--bg-color);
            color: var(--text-color);
            line-height: 1.6;
        }
        
        .container {
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
        }
        
        .header {
            background: linear-gradient(135deg, var(--primary-color), var(--secondary-color));
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }
        
        .header h1 {
            font-size: 2.5rem;
            margin-bottom: 10px;
        }
        
        .header .subtitle {
            font-size: 1.1rem;
            opacity: 0.9;
        }
        
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        
        .stat-card {
            background: var(--card-bg);
            padding: 25px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            text-align: center;
            transition: transform 0.3s ease;
        }
        
        .stat-card:hover {
            transform: translateY(-5px);
        }
        
        .stat-value {
            font-size: 2rem;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .stat-label {
            font-size: 0.9rem;
            color: #7f8c8d;
        }
        
        .success { color: var(--success-color); }
        .warning { color: var(--warning-color); }
        .info { color: var(--primary-color); }
        .danger { color: var(--danger-color); }
        
        .section {
            background: var(--card-bg);
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 30px;
        }
        
        .section h2 {
            font-size: 1.8rem;
            margin-bottom: 20px;
            color: var(--secondary-color);
            border-bottom: 2px solid var(--primary-color);
            padding-bottom: 10px;
        }
        
        .chart-container {
            position: relative;
            height: 400px;
            margin-bottom: 20px;
        }
        
        .recommendations-list {
            list-style: none;
        }
        
        .recommendation-item {
            background: #f8f9fa;
            padding: 15px;
            border-left: 4px solid var(--primary-color);
            margin-bottom: 10px;
            border-radius: 5px;
        }
        
        .recommendation-item .confidence {
            float: right;
            background: var(--success-color);
            color: white;
            padding: 2px 8px;
            border-radius: 12px;
            font-size: 0.8rem;
        }
        
        .elements-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }
        
        .element-card {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid var(--primary-color);
        }
        
        .element-name {
            font-weight: bold;
            font-size: 1.1rem;
            margin-bottom: 5px;
        }
        
        .element-stats {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            color: #6c757d;
        }
        
        .synergy-item {
            background: linear-gradient(90deg, #e3f2fd, #fff);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid var(--success-color);
        }
        
        .anti-pattern-item {
            background: linear-gradient(90deg, #ffebee, #fff);
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 4px solid var(--danger-color);
        }
        
        .network-container {
            height: 500px;
            border: 1px solid var(--border-color);
            border-radius: 8px;
        }
        
        .footer {
            text-align: center;
            padding: 20px;
            color: #7f8c8d;
            font-size: 0.9rem;
        }
        
        @media (max-width: 768px) {
            .container { padding: 10px; }
            .header h1 { font-size: 2rem; }
            .stats-grid { grid-template-columns: 1fr; }
            .chart-container { height: 300px; }
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <div class="header">
            <h1>🎨 ComfyUI 自动化分析报告</h1>
            <div class="subtitle">生成时间: {generated_at}</div>
            <div class="subtitle">分析周期: {analysis_period}</div>
        </div>
        
        <!-- 核心指标 -->
        <div class="stats-grid">
            <div class="stat-card">
                <div class="stat-value success">{success_rate}</div>
                <div class="stat-label">总体成功率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value info">{avg_quality}</div>
                <div class="stat-label">平均质量分数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value warning">{total_tasks}</div>
                <div class="stat-label">总任务数</div>
            </div>
            <div class="stat-card">
                <div class="stat-value info">{combinations_analyzed}</div>
                <div class="stat-label">分析组合数</div>
            </div>
        </div>
        
        <!-- 性能趋势图 -->
        {performance_chart_section}
        
        <!-- 高效元素分析 -->
        <div class="section">
            <h2>🏆 高效元素排行榜</h2>
            {element_performance_chart}
            <div class="elements-grid">
                {top_elements_html}
            </div>
        </div>
        
        <!-- 最佳组合分析 -->
        <div class="section">
            <h2>💎 最佳元素组合</h2>
            {combination_radar_chart}
            <div class="elements-grid">
                {best_combinations_html}
            </div>
        </div>
        
        <!-- 协同效应分析 -->
        <div class="section">
            <h2>🤝 元素协同效应</h2>
            {synergy_network_chart}
            <div>
                {synergies_html}
            </div>
        </div>
        
        <!-- 反模式分析 -->
        <div class="section">
            <h2>⚠️ 需要避免的组合</h2>
            {conflict_chart}
            <div>
                {anti_patterns_html}
            </div>
        </div>
        
        <!-- 优化建议 -->
        <div class="section">
            <h2>💡 优化建议</h2>
            <ul class="recommendations-list">
                {recommendations_html}
            </ul>
        </div>
    </div>
    
    <div class="footer">
        <p>🤖 由 ComfyUI 自动化系统生成 | 数据分析引擎 v1.0</p>
    </div>
    
    <script>
        // 初始化图表
        {charts_js}
    </script>
</body>
</html>
        '''
        
        # 填充模板数据
        return html_template.format(
            generated_at=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            analysis_period=recommendation_report.analysis_period,
            success_rate=f"{prompt_analysis['overall_performance']['success_rate']:.1%}",
            avg_quality=f"{prompt_analysis['overall_performance']['average_quality']:.2f}",
            total_tasks=prompt_analysis['analysis_period']['total_tasks'],
            combinations_analyzed=recommendation_report.total_combinations_analyzed,
            
            performance_chart_section=self._build_chart_section('performance_trend', charts_data),
            element_performance_chart=self._build_chart_section('element_performance', charts_data),
            combination_radar_chart=self._build_chart_section('combination_radar', charts_data),
            synergy_network_chart=self._build_chart_section('synergy_network', charts_data),
            conflict_chart=self._build_chart_section('conflict_types', charts_data),
            
            top_elements_html=self._build_elements_html(prompt_analysis.get('top_performing_elements', [])),
            best_combinations_html=self._build_combinations_html(recommendation_report.best_combinations),
            synergies_html=self._build_synergies_html(recommendation_report.element_synergies),
            anti_patterns_html=self._build_anti_patterns_html(recommendation_report.anti_patterns),
            recommendations_html=self._build_recommendations_html(prompt_analysis.get('recommendations', [])),
            
            charts_js=self._build_charts_js(charts_data)
        )
    
    def _build_chart_section(self, chart_name: str, charts_data: Dict) -> str:
        """构建图表区域"""
        if chart_name not in charts_data:
            return ''
        
        chart = charts_data[chart_name]
        
        if chart['type'] == 'network':
            return f'''
            <div class="section">
                <h2>{chart['title']}</h2>
                <div id="{chart_name}" class="network-container"></div>
            </div>
            '''
        else:
            return f'''
            <div class="section">
                <h2>{chart['title']}</h2>
                <div class="chart-container">
                    <canvas id="{chart_name}"></canvas>
                </div>
            </div>
            '''
    
    def _build_elements_html(self, elements: List[Dict]) -> str:
        """构建元素HTML"""
        if not elements:
            return '<div class="element-card">暂无数据</div>'
        
        html_parts = []
        for elem in elements[:8]:  # 显示前8个
            html_parts.append(f'''
                <div class="element-card">
                    <div class="element-name">{elem['element']}</div>
                    <div class="element-stats">
                        <span>成功率: {elem['success_rate']:.1%}</span>
                        <span>质量: {elem['avg_quality']:.2f}</span>
                        <span>使用次数: {elem['usage_count']}</span>
                    </div>
                </div>
            ''')
        
        return ''.join(html_parts)
    
    def _build_combinations_html(self, combinations) -> str:
        """构建组合HTML"""
        if not combinations:
            return '<div class="element-card">暂无数据</div>'
        
        html_parts = []
        for combo in combinations[:6]:  # 显示前6个
            elements_str = ' + '.join(combo.elements)
            html_parts.append(f'''
                <div class="element-card">
                    <div class="element-name">{elements_str}</div>
                    <div class="element-stats">
                        <span>成功率: {combo.success_rate:.1%}</span>
                        <span>质量: {combo.avg_quality:.2f}</span>
                        <span>效果评分: {combo.effectiveness_score:.2f}</span>
                    </div>
                </div>
            ''')
        
        return ''.join(html_parts)
    
    def _build_synergies_html(self, synergies: List[Dict]) -> str:
        """构建协同效应HTML"""
        if not synergies:
            return '<div class="synergy-item">暂无协同效应数据</div>'
        
        html_parts = []
        for synergy in synergies[:8]:  # 显示前8个
            html_parts.append(f'''
                <div class="synergy-item">
                    <strong>{synergy['element1']} + {synergy['element2']}</strong>
                    <div style="margin-top: 5px; font-size: 0.9rem;">
                        协同强度: +{synergy['synergy_strength']:.2f} | 
                        成功率提升: +{synergy['success_synergy']:.2f} | 
                        质量提升: +{synergy['quality_synergy']:.2f}
                    </div>
                </div>
            ''')
        
        return ''.join(html_parts)
    
    def _build_anti_patterns_html(self, anti_patterns: List[Dict]) -> str:
        """构建反模式HTML"""
        if not anti_patterns:
            return '<div class="anti-pattern-item">未发现问题组合</div>'
        
        html_parts = []
        for pattern in anti_patterns[:6]:  # 显示前6个
            elements_str = ' + '.join(pattern['elements'])
            html_parts.append(f'''
                <div class="anti-pattern-item">
                    <strong>{elements_str}</strong>
                    <div style="margin-top: 5px; font-size: 0.9rem;">
                        冲突类型: {pattern['conflict_type']} | 
                        严重程度: {pattern['severity']:.2f} | 
                        成功率下降: -{pattern['success_degradation']:.2f}
                    </div>
                </div>
            ''')
        
        return ''.join(html_parts)
    
    def _build_recommendations_html(self, recommendations: List[str]) -> str:
        """构建建议HTML"""
        if not recommendations:
            return '<li class="recommendation-item">暂无优化建议</li>'
        
        html_parts = []
        for i, rec in enumerate(recommendations, 1):
            html_parts.append(f'''
                <li class="recommendation-item">
                    <div class="confidence">建议 {i}</div>
                    {rec}
                </li>
            ''')
        
        return ''.join(html_parts)
    
    def _build_charts_js(self, charts_data: Dict) -> str:
        """构建图表JavaScript"""
        js_parts = []
        
        for chart_name, chart_config in charts_data.items():
            if chart_config['type'] == 'network':
                # 网络图使用vis.js
                js_parts.append(f'''
                    // {chart_config['title']}
                    {{
                        const container = document.getElementById('{chart_name}');
                        const data = {json.dumps(chart_config['data'])};
                        const options = {{
                            nodes: {{
                                shape: 'dot',
                                size: 16,
                                font: {{ size: 12 }}
                            }},
                            edges: {{
                                font: {{ size: 10 }},
                                smooth: true
                            }},
                            physics: {{
                                enabled: true,
                                stabilization: {{ iterations: 100 }}
                            }}
                        }};
                        new vis.Network(container, data, options);
                    }}
                ''')
            else:
                # 其他图表使用Chart.js
                js_parts.append(f'''
                    // {chart_config['title']}
                    {{
                        const ctx = document.getElementById('{chart_name}').getContext('2d');
                        new Chart(ctx, {{
                            type: '{chart_config['type']}',
                            data: {json.dumps(chart_config['data'])},
                            options: {{
                                responsive: true,
                                maintainAspectRatio: false,
                                plugins: {{
                                    title: {{
                                        display: false
                                    }},
                                    legend: {{
                                        position: 'top'
                                    }}
                                }},
                                scales: {self._get_chart_scales(chart_config['type'])}
                            }}
                        }});
                    }}
                ''')
        
        return '\n'.join(js_parts)
    
    def _get_chart_scales(self, chart_type: str) -> str:
        """获取图表坐标轴配置"""
        if chart_type in ['radar', 'doughnut', 'pie']:
            return '{}'
        
        return '''
        {
            y: {
                beginAtZero: true,
                max: 1,
                ticks: {
                    callback: function(value) {
                        return (value * 100).toFixed(0) + '%';
                    }
                }
            }
        }
        '''