#!/usr/bin/env python3
"""
ComfyUI 自动化系统 - 第三阶段集成测试
功能：验证画廊功能、数据分析功能和推荐引擎的完整性和正确性
"""

import os
import sys
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import shutil

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.utils.prompt_analyzer import PromptAnalyzer, AnalysisReport
from src.utils.recommendation_engine import RecommendationEngine
from src.utils.metadata_schema import TaskMetadata


class Phase3IntegrationTest:
    """第三阶段集成测试类"""
    
    def __init__(self):
        self.test_dir = Path("test_output")
        self.test_dir.mkdir(exist_ok=True)
        
        # 创建测试数据库
        self.test_db_path = self.test_dir / "test_tasks.db"
        self._setup_test_database()
        
        # 创建测试元数据目录
        self.test_metadata_dir = self.test_dir / "metadata"
        self.test_metadata_dir.mkdir(exist_ok=True)
        
        # 初始化测试数据
        self._create_test_data()
        
        print("🧪 第三阶段集成测试初始化完成")
        print(f"📁 测试目录: {self.test_dir}")
        print(f"🗄️ 测试数据库: {self.test_db_path}")
        print(f"📄 测试元数据目录: {self.test_metadata_dir}")
    
    def _setup_test_database(self):
        """设置测试数据库"""
        # 创建测试数据库
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            # 创建任务表
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    prompt TEXT NOT NULL,
                    status TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    quality_score REAL,
                    generation_time REAL,
                    error_message TEXT,
                    workflow_params TEXT
                )
            """)
            
            conn.commit()
    
    def _create_test_data(self):
        """创建测试数据"""
        print("📊 创建测试数据...")
        
        # 测试提示词
        test_prompts = [
            "a beautiful landscape with mountains and lakes, masterpiece, best quality",
            "portrait of a young woman, anime style, high quality",
            "futuristic cityscape at sunset, oil painting, ultra detailed",
            "cute cat sitting on a windowsill, cartoon style, professional",
            "abstract art with vibrant colors, digital art, award winning",
            "steampunk mechanical device, realistic, high resolution",
            "fantasy castle in the clouds, concept art, detailed",
            "minimalist geometric design, clean, sharp focus"
        ]
        
        # 生成测试任务数据
        tasks = []
        for i, prompt in enumerate(test_prompts):
            # 生成多个变体
            for j in range(3):
                task_id = f"test_task_{i}_{j}"
                status = "completed" if j < 2 else "failed"
                quality_score = 0.6 + (i * 0.05) + (j * 0.1) + (0.1 if status == "completed" else 0)
                quality_score = min(1.0, max(0.0, quality_score))
                
                task = TaskMetadata(
                    task_id=task_id,
                    prompt=prompt,
                    workflow_type="txt2img",
                    status=status,
                    created_at=datetime.now() - timedelta(days=i*2, hours=j*3),
                    quality_score=quality_score if status == "completed" else None,
                    actual_time=10 + i * 2 + j * 3,
                    error_message="timeout error" if status == "failed" else None
                )
                tasks.append(task)
        
        # 保存到数据库
        with sqlite3.connect(self.test_db_path) as conn:
            cursor = conn.cursor()
            
            for task in tasks:
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks 
                    (task_id, prompt, status, created_at, quality_score, generation_time, error_message)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    task.task_id,
                    task.prompt,
                    task.status,
                    task.created_at.isoformat(),
                    task.quality_score,
                    task.actual_time,
                    task.error_message
                ))
            
            conn.commit()
        
        # 保存到JSON文件
        for i, task in enumerate(tasks):
            json_file = self.test_metadata_dir / f"task_{i:03d}.json"
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump({
                    'task_id': task.task_id,
                    'prompt': task.prompt,
                    'status': task.status,
                    'created_at': task.created_at.isoformat(),
                    'quality_score': task.quality_score,
                    'generation_time': task.actual_time,
                    'error_message': task.error_message
                }, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 创建了 {len(tasks)} 个测试任务")
    
    def test_prompt_analyzer(self):
        """测试提示词分析器"""
        print("\n🔍 测试提示词分析器...")
        
        try:
            # 初始化分析器
            analyzer = PromptAnalyzer(str(self.test_db_path))
            
            # 测试单个提示词分析
            test_prompt = "a beautiful landscape with mountains and lakes, masterpiece, best quality"
            analysis = analyzer.analyze_prompt_performance(test_prompt, days_back=30)
            
            print(f"  📝 测试提示词: {test_prompt}")
            print(f"  📊 成功率: {analysis.success_rate:.2%}")
            print(f"  ⭐ 平均质量: {analysis.avg_quality:.2f}")
            print(f"  ⏱️ 平均生成时间: {analysis.avg_generation_time:.1f}s")
            print(f"  🎯 效果评分: {analysis.effectiveness_score:.2f}")
            
            # 测试元素效果分析
            element_analysis = analyzer.analyze_element_effectiveness(days_back=30)
            print(f"  🧩 分析元素数量: {len(element_analysis)}")
            
            if element_analysis:
                best_element = element_analysis[0]
                print(f"  🏆 最佳元素: {best_element.element} (成功率: {best_element.success_rate:.2%})")
            
            # 测试完整分析报告
            report = analyzer.generate_analysis_report(days_back=30)
            print(f"  📈 总任务数: {report.total_tasks}")
            print(f"  ✅ 成功率: {report.overall_success_rate:.2%}")
            print(f"  💡 建议数量: {len(report.recommendations)}")
            
            # 导出报告
            report_path = self.test_dir / "analysis_report.json"
            analyzer.export_analysis_report(report, str(report_path))
            print(f"  💾 报告已导出: {report_path}")
            
            print("  ✅ 提示词分析器测试通过")
            return True
            
        except Exception as e:
            print(f"  ❌ 提示词分析器测试失败: {e}")
            return False
    
    def test_recommendation_engine(self):
        """测试推荐引擎"""
        print("\n🤖 测试推荐引擎...")
        
        try:
            # 初始化推荐引擎
            engine = RecommendationEngine(str(self.test_db_path))
            
            # 测试提示词优化推荐
            test_prompt = "a beautiful landscape with mountains"
            optimization = engine.recommend_prompt_optimization(test_prompt)
            
            print(f"  📝 原始提示词: {optimization.original_prompt}")
            print(f"  ✨ 推荐提示词: {optimization.recommended_prompt}")
            print(f"  🎯 置信度: {optimization.confidence_score:.2f}")
            print(f"  📈 预期质量提升: {optimization.expected_quality_boost:.2f}")
            print(f"  💭 推理: {optimization.reasoning}")
            
            # 测试元素推荐
            element_recommendations = engine.recommend_element_combinations(test_prompt, max_elements=3)
            print(f"  🧩 元素推荐数量: {len(element_recommendations)}")
            
            for i, rec in enumerate(element_recommendations[:3]):
                print(f"    {i+1}. {rec.element} ({rec.recommendation_type}) - 置信度: {rec.confidence:.2f}")
            
            # 测试工作流参数推荐
            test_params = {'cfg_scale': 7.0, 'steps': 20}
            param_recommendations = engine.recommend_workflow_parameters(test_params, 'quality')
            print(f"  ⚙️ 参数推荐数量: {len(param_recommendations)}")
            
            for rec in param_recommendations:
                print(f"    - {rec.parameter_name}: {rec.current_value} → {rec.recommended_value}")
            
            # 测试批量策略推荐
            test_prompts = ["a beautiful landscape", "portrait of a woman", "abstract art"]
            batch_recommendations = engine.recommend_batch_strategies(test_prompts, 'optimization')
            print(f"  📦 批量策略推荐数量: {len(batch_recommendations)}")
            
            # 测试智能建议
            context = {'low_success_rate': True, 'quality_issues': True}
            suggestions = engine.generate_smart_suggestions(context)
            print(f"  💡 智能建议数量: {len(suggestions)}")
            
            print("  ✅ 推荐引擎测试通过")
            return True
            
        except Exception as e:
            print(f"  ❌ 推荐引擎测试失败: {e}")
            return False
    
    def test_gallery_files(self):
        """测试画廊文件"""
        print("\n🖼️ 测试画廊文件...")
        
        try:
            # 检查HTML文件
            html_file = Path("templates/gallery.html")
            if html_file.exists():
                with open(html_file, 'r', encoding='utf-8') as f:
                    html_content = f.read()
                
                # 检查关键元素
                required_elements = [
                    'gallery-grid', 'searchInput', 'imageModal', 'starRating',
                    'selectAllBtn', 'exportSelectedBtn', 'gallery.js'
                ]
                
                missing_elements = []
                for element in required_elements:
                    if element not in html_content:
                        missing_elements.append(element)
                
                if missing_elements:
                    print(f"  ⚠️ HTML文件缺少元素: {missing_elements}")
                else:
                    print("  ✅ HTML文件结构完整")
            else:
                print("  ❌ HTML文件不存在")
                return False
            
            # 检查CSS文件
            css_file = Path("static/css/gallery.css")
            if css_file.exists():
                with open(css_file, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                
                # 检查关键样式
                required_styles = [
                    'gallery-grid', 'image-card', 'modal', 'sidebar',
                    'btn-primary', 'star-rating', 'quality-badge'
                ]
                
                missing_styles = []
                for style in required_styles:
                    if style not in css_content:
                        missing_styles.append(style)
                
                if missing_styles:
                    print(f"  ⚠️ CSS文件缺少样式: {missing_styles}")
                else:
                    print("  ✅ CSS文件样式完整")
            else:
                print("  ❌ CSS文件不存在")
                return False
            
            # 检查JavaScript文件
            js_file = Path("static/js/gallery.js")
            if js_file.exists():
                with open(js_file, 'r', encoding='utf-8') as f:
                    js_content = f.read()
                
                # 检查关键功能
                required_functions = [
                    'GalleryManager', 'loadImages', 'applyFilters',
                    'openModal', 'toggleSelection', 'exportSelected'
                ]
                
                missing_functions = []
                for func in required_functions:
                    if func not in js_content:
                        missing_functions.append(func)
                
                if missing_functions:
                    print(f"  ⚠️ JavaScript文件缺少功能: {missing_functions}")
                else:
                    print("  ✅ JavaScript文件功能完整")
            else:
                print("  ❌ JavaScript文件不存在")
                return False
            
            print("  ✅ 画廊文件测试通过")
            return True
            
        except Exception as e:
            print(f"  ❌ 画廊文件测试失败: {e}")
            return False
    
    def test_data_integration(self):
        """测试数据集成"""
        print("\n🔗 测试数据集成...")
        
        try:
            # 测试数据库连接
            with sqlite3.connect(self.test_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM tasks")
                task_count = cursor.fetchone()[0]
                print(f"  📊 数据库任务数量: {task_count}")
            
            # 测试JSON文件
            json_files = list(self.test_metadata_dir.glob("*.json"))
            print(f"  📄 JSON文件数量: {len(json_files)}")
            
            # 测试数据一致性
            db_tasks = []
            with sqlite3.connect(self.test_db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT task_id, prompt, status FROM tasks")
                db_tasks = cursor.fetchall()
            
            json_tasks = []
            for json_file in json_files:
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    json_tasks.append((data['task_id'], data['prompt'], data['status']))
            
            print(f"  🔄 数据一致性检查: 数据库 {len(db_tasks)} 条，JSON {len(json_tasks)} 条")
            
            # 测试分析器和推荐引擎的数据访问
            analyzer = PromptAnalyzer(str(self.test_db_path))
            engine = RecommendationEngine(str(self.test_db_path))
            
            # 测试数据查询
            recent_tasks = analyzer._get_recent_tasks(30)
            print(f"  📈 分析器可访问任务数: {len(recent_tasks)}")
            
            print("  ✅ 数据集成测试通过")
            return True
            
        except Exception as e:
            print(f"  ❌ 数据集成测试失败: {e}")
            return False
    
    def test_end_to_end_workflow(self):
        """测试端到端工作流"""
        print("\n🔄 测试端到端工作流...")
        
        try:
            # 1. 数据分析
            analyzer = PromptAnalyzer(str(self.test_db_path))
            report = analyzer.generate_analysis_report(days_back=30)
            
            # 2. 基于分析结果生成推荐
            engine = RecommendationEngine(str(self.test_db_path))
            
            # 选择效果最好的提示词进行优化
            if report.top_performing_prompts:
                best_prompt = report.top_performing_prompts[0]
                optimization = engine.recommend_prompt_optimization(best_prompt.prompt)
                
                print(f"  🏆 最佳提示词: {best_prompt.prompt}")
                print(f"  ✨ 优化建议: {optimization.recommended_prompt}")
                print(f"  📈 预期提升: {optimization.expected_quality_boost:.2f}")
            
            # 3. 生成批量策略
            test_prompts = [p.prompt for p in report.top_performing_prompts[:3]]
            batch_strategies = engine.recommend_batch_strategies(test_prompts, 'optimization')
            
            print(f"  📦 批量策略数量: {len(batch_strategies)}")
            
            # 4. 生成智能建议
            context = {
                'low_success_rate': report.overall_success_rate < 0.8,
                'quality_issues': report.avg_quality_score < 0.7
            }
            suggestions = engine.generate_smart_suggestions(context)
            
            print(f"  💡 智能建议: {len(suggestions)} 条")
            for i, suggestion in enumerate(suggestions[:3]):
                print(f"    {i+1}. {suggestion}")
            
            print("  ✅ 端到端工作流测试通过")
            return True
            
        except Exception as e:
            print(f"  ❌ 端到端工作流测试失败: {e}")
            return False
    
    def run_all_tests(self):
        """运行所有测试"""
        print("🚀 开始第三阶段集成测试")
        print("=" * 50)
        
        test_results = []
        
        # 运行各项测试
        test_results.append(("画廊文件测试", self.test_gallery_files()))
        test_results.append(("数据集成测试", self.test_data_integration()))
        test_results.append(("提示词分析器测试", self.test_prompt_analyzer()))
        test_results.append(("推荐引擎测试", self.test_recommendation_engine()))
        test_results.append(("端到端工作流测试", self.test_end_to_end_workflow()))
        
        # 输出测试结果
        print("\n" + "=" * 50)
        print("📊 测试结果汇总")
        print("=" * 50)
        
        passed = 0
        total = len(test_results)
        
        for test_name, result in test_results:
            status = "✅ 通过" if result else "❌ 失败"
            print(f"{test_name}: {status}")
            if result:
                passed += 1
        
        print(f"\n🎯 总体结果: {passed}/{total} 项测试通过")
        
        if passed == total:
            print("🎉 所有测试通过！第三阶段功能完整可用")
        else:
            print("⚠️ 部分测试失败，请检查相关功能")
        
        return passed == total
    
    def cleanup(self):
        """清理测试文件"""
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
            print(f"🧹 清理测试文件: {self.test_dir}")


def main():
    """主函数"""
    test = Phase3IntegrationTest()
    
    try:
        success = test.run_all_tests()
        return 0 if success else 1
    finally:
        # 询问是否清理测试文件
        response = input("\n是否清理测试文件？(y/N): ").strip().lower()
        if response in ['y', 'yes']:
            test.cleanup()
        else:
            print(f"测试文件保留在: {test.test_dir}")


if __name__ == "__main__":
    exit(main())
