#!/usr/bin/env python3
"""
ComfyUI 自动化系统主程序
一键启动整个系统，支持多种运行模式
"""

import sys
import argparse
import logging
import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime

# 添加src目录到Python路径
sys.path.append(str(Path(__file__).parent / 'src'))

from src.batch_processor import BatchProcessor
from src.analysis_integration import AnalysisManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComfyUIAutomationSystem:
    """ComfyUI自动化系统主类"""
    
    def __init__(self, config_file: Optional[str] = None):
        """初始化系统"""
        self.config = self._load_config(config_file)
        self.batch_processor = None
        self.analysis_manager = None
        
        # 初始化组件
        self._initialize_components()
    
    def _load_config(self, config_file: Optional[str] = None) -> dict:
        """加载配置文件"""
        default_config = {
            # 基础配置
            "output_directory": "./output",
            "database_path": "./data/database/tasks.db",
            "workflows_directory": "./workflows",
            
            # 批量处理配置
            "batch_processing": {
                "max_concurrent_tasks": 1,
                "task_timeout": 300,
                "batch_delay": 2.0,
                "enable_progress_monitor": True
            },
            
            # 提示词生成配置
            "prompt_generation": {
                "default_variation_count": 10,
                "max_variations": 100,
                "enable_template_system": True,
                "quality_threshold": 0.7
            },
            
            # 工作流配置
            "workflow": {
                "default_type": "txt2img",
                "default_resolution": [1024, 1024],
                "default_steps": 20,
                "default_cfg_scale": 7.5
            },
            
            # 输出配置
            "output": {
                "generate_gallery": True,
                "save_metadata": True,
                "organize_by_date": True,
                "enable_json_backup": True
            },
            
            # 分析系统配置
            "analysis": {
                "auto_analyze": False,
                "generate_reports": True,
                "optimization_enabled": True
            }
        }
        
        if config_file and Path(config_file).exists():
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    user_config = json.load(f)
                    # 合并配置
                    self._merge_config(default_config, user_config)
            except Exception as e:
                logger.warning(f"配置文件加载失败，使用默认配置: {e}")
        
        return default_config
    
    def _merge_config(self, default: dict, user: dict):
        """递归合并配置"""
        for key, value in user.items():
            if key in default and isinstance(default[key], dict) and isinstance(value, dict):
                self._merge_config(default[key], value)
            else:
                default[key] = value
    
    def _initialize_components(self):
        """初始化系统组件"""
        logger.info("🚀 初始化ComfyUI自动化系统...")
        
        # 初始化批量处理器
        self.batch_processor = BatchProcessor(
            output_directory=Path(self.config["output_directory"]),
            database_path=Path(self.config["database_path"]),
            workflows_directory=Path(self.config["workflows_directory"]),
            max_concurrent_tasks=self.config["batch_processing"]["max_concurrent_tasks"],
            task_timeout=self.config["batch_processing"]["task_timeout"],
            batch_delay=self.config["batch_processing"]["batch_delay"]
        )
        
        # 初始化分析管理器
        analysis_output = Path(self.config["output_directory"]) / "analysis"
        self.analysis_manager = AnalysisManager(str(analysis_output))
        
        logger.info("✅ 系统组件初始化完成")
    
    def run_single_subject(self, subject: str, variation_count: int = None, 
                          workflow_type: str = None, auto_analyze: bool = None) -> bool:
        """处理单个主题，生成变体"""
        logger.info(f"🎯 开始处理单个主题: {subject}")
        
        # 使用配置或参数值
        variation_count = variation_count or self.config["prompt_generation"]["default_variation_count"]
        workflow_type = workflow_type or self.config["workflow"]["default_type"]
        auto_analyze = auto_analyze if auto_analyze is not None else self.config["analysis"]["auto_analyze"]
        
        try:
            # 创建批次任务
            logger.info(f"📝 生成 {variation_count} 个提示词变体...")
            task_ids = self.batch_processor.create_batch_from_subject(
                subject=subject,
                variation_count=variation_count,
                workflow_type=workflow_type
            )
            
            logger.info(f"✅ 成功创建 {len(task_ids)} 个任务")
            
            # 设置进度回调
            if self.config["batch_processing"]["enable_progress_monitor"]:
                self._setup_progress_monitor()
            
            # 开始批量处理
            logger.info("🔄 开始批量处理...")
            success = self.batch_processor.start_batch_processing()
            
            if success:
                # 获取处理结果
                results = self.batch_processor.get_batch_results()
                self._print_batch_summary(results)
                
                # 生成画廊
                if self.config["output"]["generate_gallery"]:
                    logger.info("🖼️ 生成HTML画廊...")
                    # 画廊在批量处理完成后自动生成
                
                # 自动分析
                if auto_analyze:
                    logger.info("📊 开始自动分析...")
                    self._run_auto_analysis()
                
                logger.info("🎉 单个主题处理完成!")
                return True
            else:
                logger.error("❌ 批量处理失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 处理失败: {e}")
            return False
    
    def run_batch_prompts(self, prompts: List[str], workflow_type: str = None, 
                         auto_analyze: bool = None) -> bool:
        """批量处理多个提示词"""
        logger.info(f"📦 开始批量处理 {len(prompts)} 个提示词")
        
        workflow_type = workflow_type or self.config["workflow"]["default_type"]
        auto_analyze = auto_analyze if auto_analyze is not None else self.config["analysis"]["auto_analyze"]
        
        try:
            # 创建批次任务
            logger.info("📝 创建批次任务...")
            task_ids = self.batch_processor.create_batch_from_prompts(
                prompts=prompts,
                workflow_type=workflow_type
            )
            
            logger.info(f"✅ 成功创建 {len(task_ids)} 个任务")
            
            # 设置进度回调
            if self.config["batch_processing"]["enable_progress_monitor"]:
                self._setup_progress_monitor()
            
            # 开始批量处理
            logger.info("🔄 开始批量处理...")
            success = self.batch_processor.start_batch_processing()
            
            if success:
                # 获取处理结果
                results = self.batch_processor.get_batch_results()
                self._print_batch_summary(results)
                
                # 生成画廊
                if self.config["output"]["generate_gallery"]:
                    logger.info("🖼️ 生成HTML画廊...")
                
                # 自动分析
                if auto_analyze:
                    logger.info("📊 开始自动分析...")
                    self._run_auto_analysis()
                
                logger.info("🎉 批量提示词处理完成!")
                return True
            else:
                logger.error("❌ 批量处理失败")
                return False
                
        except Exception as e:
            logger.error(f"❌ 处理失败: {e}")
            return False
    
    def run_from_file(self, file_path: str, workflow_type: str = None, 
                     auto_analyze: bool = None) -> bool:
        """从文件读取提示词进行处理"""
        logger.info(f"📁 从文件读取提示词: {file_path}")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                prompts = [line.strip() for line in f if line.strip()]
            
            if not prompts:
                logger.error("❌ 文件中没有有效的提示词")
                return False
            
            return self.run_batch_prompts(prompts, workflow_type, auto_analyze)
            
        except Exception as e:
            logger.error(f"❌ 读取文件失败: {e}")
            return False
    
    def run_interactive(self):
        """交互式模式"""
        logger.info("🎮 进入交互式模式")
        print("\n" + "="*60)
        print("🎨 ComfyUI 自动化系统 - 交互式模式")
        print("="*60)
        
        while True:
            try:
                print("\n📋 选择操作模式:")
                print("1. 单个主题生成变体")
                print("2. 批量提示词处理")
                print("3. 从文件读取提示词")
                print("4. 数据分析")
                print("5. 系统状态")
                print("6. 配置管理")
                print("0. 退出")
                
                choice = input("\n请选择 (0-6): ").strip()
                
                if choice == '0':
                    print("👋 再见!")
                    break
                elif choice == '1':
                    self._interactive_single_subject()
                elif choice == '2':
                    self._interactive_batch_prompts()
                elif choice == '3':
                    self._interactive_file_input()
                elif choice == '4':
                    self._interactive_analysis()
                elif choice == '5':
                    self._show_system_status()
                elif choice == '6':
                    self._interactive_config()
                else:
                    print("❌ 无效选择，请重试")
                    
            except KeyboardInterrupt:
                print("\n👋 用户取消，退出程序")
                break
            except Exception as e:
                logger.error(f"交互式模式错误: {e}")
                print(f"❌ 发生错误: {e}")
    
    def _interactive_single_subject(self):
        """交互式单主题处理"""
        print("\n🎯 单个主题生成变体")
        print("-" * 30)
        
        subject = input("请输入主题描述: ").strip()
        if not subject:
            print("❌ 主题不能为空")
            return
        
        try:
            count_input = input(f"变体数量 (默认{self.config['prompt_generation']['default_variation_count']}): ").strip()
            variation_count = int(count_input) if count_input else self.config['prompt_generation']['default_variation_count']
        except ValueError:
            variation_count = self.config['prompt_generation']['default_variation_count']
        
        workflow_type = input(f"工作流类型 (默认{self.config['workflow']['default_type']}): ").strip()
        workflow_type = workflow_type if workflow_type else self.config['workflow']['default_type']
        
        analyze_input = input("完成后自动分析? (y/N): ").strip().lower()
        auto_analyze = analyze_input == 'y'
        
        print(f"\n📝 配置确认:")
        print(f"  主题: {subject}")
        print(f"  变体数量: {variation_count}")
        print(f"  工作流: {workflow_type}")
        print(f"  自动分析: {'是' if auto_analyze else '否'}")
        
        confirm = input("\n确认执行? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            self.run_single_subject(subject, variation_count, workflow_type, auto_analyze)
        else:
            print("❌ 已取消")
    
    def _interactive_batch_prompts(self):
        """交互式批量提示词处理"""
        print("\n📦 批量提示词处理")
        print("-" * 30)
        
        prompts = []
        print("请输入提示词，每行一个，空行结束:")
        
        while True:
            prompt = input(f"提示词 #{len(prompts) + 1}: ").strip()
            if not prompt:
                break
            prompts.append(prompt)
        
        if not prompts:
            print("❌ 没有输入任何提示词")
            return
        
        workflow_type = input(f"工作流类型 (默认{self.config['workflow']['default_type']}): ").strip()
        workflow_type = workflow_type if workflow_type else self.config['workflow']['default_type']
        
        analyze_input = input("完成后自动分析? (y/N): ").strip().lower()
        auto_analyze = analyze_input == 'y'
        
        print(f"\n📝 配置确认:")
        print(f"  提示词数量: {len(prompts)}")
        print(f"  工作流: {workflow_type}")
        print(f"  自动分析: {'是' if auto_analyze else '否'}")
        
        for i, prompt in enumerate(prompts, 1):
            print(f"  {i}. {prompt[:50]}{'...' if len(prompt) > 50 else ''}")
        
        confirm = input("\n确认执行? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            self.run_batch_prompts(prompts, workflow_type, auto_analyze)
        else:
            print("❌ 已取消")
    
    def _interactive_file_input(self):
        """交互式文件输入处理"""
        print("\n📁 从文件读取提示词")
        print("-" * 30)
        
        file_path = input("请输入文件路径: ").strip()
        if not file_path:
            print("❌ 文件路径不能为空")
            return
        
        if not Path(file_path).exists():
            print(f"❌ 文件不存在: {file_path}")
            return
        
        # 预览文件内容
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = [line.strip() for line in f if line.strip()]
            
            print(f"\n📄 文件预览 (共{len(lines)}行):")
            for i, line in enumerate(lines[:5], 1):
                print(f"  {i}. {line[:50]}{'...' if len(line) > 50 else ''}")
            if len(lines) > 5:
                print(f"  ... 还有 {len(lines) - 5} 行")
                
        except Exception as e:
            print(f"❌ 读取文件失败: {e}")
            return
        
        workflow_type = input(f"工作流类型 (默认{self.config['workflow']['default_type']}): ").strip()
        workflow_type = workflow_type if workflow_type else self.config['workflow']['default_type']
        
        analyze_input = input("完成后自动分析? (y/N): ").strip().lower()
        auto_analyze = analyze_input == 'y'
        
        print(f"\n📝 配置确认:")
        print(f"  文件: {file_path}")
        print(f"  提示词数量: {len(lines)}")
        print(f"  工作流: {workflow_type}")
        print(f"  自动分析: {'是' if auto_analyze else '否'}")
        
        confirm = input("\n确认执行? (Y/n): ").strip().lower()
        if confirm in ['', 'y', 'yes']:
            self.run_from_file(file_path, workflow_type, auto_analyze)
        else:
            print("❌ 已取消")
    
    def _interactive_analysis(self):
        """交互式分析"""
        print("\n📊 数据分析")
        print("-" * 30)
        print("1. 完整分析")
        print("2. 生成优化提示词")
        print("3. 元素性能分析")
        print("4. 仪表板数据")
        print("5. 生成分析报告")
        
        choice = input("\n请选择 (1-5): ").strip()
        
        try:
            if choice == '1':
                logger.info("开始完整分析...")
                results = self.analysis_manager.run_complete_analysis()
                if 'error' not in results:
                    print("✅ 分析完成!")
                    print(f"📊 总任务数: {results['data_summary']['total_tasks']}")
                    print(f"📈 成功率: {results['basic_statistics']['overall_success_rate']:.1%}")
                else:
                    print(f"❌ 分析失败: {results['error']}")
                    
            elif choice == '2':
                count_input = input("生成数量 (默认50): ").strip()
                count = int(count_input) if count_input else 50
                
                results = self.analysis_manager.generate_optimization_iteration(iteration_size=count)
                print(f"✅ 生成了 {len(results['prompts'])} 个优化提示词")
                print(f"📁 保存位置: {results['iteration_file']}")
                
            elif choice == '3':
                element = input("请输入要分析的元素: ").strip()
                if element:
                    results = self.analysis_manager.analyze_element_performance(element)
                    if 'error' not in results:
                        print(f"✅ 元素 '{element}' 分析完成:")
                        print(f"  使用次数: {results['total_usage']}")
                        print(f"  成功率: {results['success_rate']:.1%}")
                        print(f"  平均质量: {results['average_quality']:.2f}")
                    else:
                        print(f"❌ {results['error']}")
                        
            elif choice == '4':
                results = self.analysis_manager.get_analysis_dashboard_data()
                if 'error' not in results:
                    print("✅ 仪表板数据:")
                    metrics = results['basic_metrics']
                    print(f"  总任务数: {metrics['total_tasks']}")
                    print(f"  成功率: {metrics['overall_success_rate']:.1%}")
                    print(f"  平均质量: {metrics['average_quality_score']:.2f}")
                else:
                    print(f"❌ {results['error']}")
                    
            elif choice == '5':
                format_choice = input("报告格式 (html/json, 默认html): ").strip()
                format_type = format_choice if format_choice in ['html', 'json'] else 'html'
                
                from src.utils.result_manager import ResultManager
                from src.utils.report_generator import ReportGenerator

                # 使用系统现有的结果管理器
                result_manager = self.batch_processor.result_manager
                report_generator = ReportGenerator()
                
                tasks = result_manager.get_all_tasks()
                results = []
                for task in tasks:
                    result = result_manager.get_result(task.task_id)
                    if result:
                        results.append(result)
                if tasks:
                    report_content = report_generator.generate_analysis_report(tasks, results, format_type)
                    
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    output_file = f"output/analysis_report_{timestamp}.{format_type}"
                    
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(report_content)
                    
                    print(f"✅ 报告生成完成: {output_file}")
                else:
                    print("❌ 没有数据可生成报告")
                    
        except Exception as e:
            print(f"❌ 分析失败: {e}")
    
    def _show_system_status(self):
        """显示系统状态"""
        print("\n🔍 系统状态")
        print("-" * 30)
        
        try:
            # 批量处理器状态
            if self.batch_processor:
                status = self.batch_processor.get_processing_status()
                print(f"📦 批量处理器:")
                print(f"  运行状态: {'运行中' if status['is_running'] else '空闲'}")
                print(f"  队列状态: {status['queue_status']}")
                
                # ComfyUI连接状态
                health = self.batch_processor.comfyui_client.health_check()
                print(f"🖥️  ComfyUI状态:")
                print(f"  服务运行: {'✅' if health['service_running'] else '❌'}")
                print(f"  API可访问: {'✅' if health['api_accessible'] else '❌'}")
                
            # 数据库统计
            stats = self.batch_processor.result_manager.get_statistics()
            print(f"💾 数据统计:")
            print(f"  总任务数: {stats['total_tasks']}")
            print(f"  成功率: {stats['success_rate']:.1%}")
            print(f"  平均生成时间: {stats['avg_generation_time']:.1f}秒")
            
            # 输出目录状态
            output_dir = Path(self.config["output_directory"])
            if output_dir.exists():
                image_files = list(output_dir.glob("**/*.png"))
                metadata_files = list(output_dir.glob("**/metadata/*.json"))
                print(f"📁 输出文件:")
                print(f"  图片文件: {len(image_files)}")
                print(f"  元数据文件: {len(metadata_files)}")
                
                # 画廊文件
                gallery_file = output_dir / "gallery.html"
                print(f"  HTML画廊: {'✅' if gallery_file.exists() else '❌'}")
            
        except Exception as e:
            print(f"❌ 获取状态失败: {e}")
    
    def _interactive_config(self):
        """交互式配置管理"""
        print("\n⚙️ 配置管理")
        print("-" * 30)
        print("1. 显示当前配置")
        print("2. 修改批量处理配置")
        print("3. 修改提示词生成配置")
        print("4. 保存配置到文件")
        
        choice = input("\n请选择 (1-4): ").strip()
        
        if choice == '1':
            print("\n📋 当前配置:")
            self._print_config(self.config)
        elif choice == '2':
            self._modify_batch_config()
        elif choice == '3':
            self._modify_prompt_config()
        elif choice == '4':
            self._save_config()
    
    def _modify_batch_config(self):
        """修改批量处理配置"""
        print("\n🔧 批量处理配置")
        batch_config = self.config["batch_processing"]
        
        try:
            print(f"当前最大并发数: {batch_config['max_concurrent_tasks']}")
            new_concurrent = input("新的并发数 (回车跳过): ").strip()
            if new_concurrent:
                batch_config['max_concurrent_tasks'] = int(new_concurrent)
            
            print(f"当前任务超时: {batch_config['task_timeout']}秒")
            new_timeout = input("新的超时时间 (秒, 回车跳过): ").strip()
            if new_timeout:
                batch_config['task_timeout'] = int(new_timeout)
            
            print(f"当前批次延迟: {batch_config['batch_delay']}秒")
            new_delay = input("新的批次延迟 (秒, 回车跳过): ").strip()
            if new_delay:
                batch_config['batch_delay'] = float(new_delay)
                
            print("✅ 配置已更新")
            
        except ValueError as e:
            print(f"❌ 输入无效: {e}")
    
    def _modify_prompt_config(self):
        """修改提示词生成配置"""
        print("\n📝 提示词生成配置")
        prompt_config = self.config["prompt_generation"]
        
        try:
            print(f"当前默认变体数: {prompt_config['default_variation_count']}")
            new_count = input("新的默认变体数 (回车跳过): ").strip()
            if new_count:
                prompt_config['default_variation_count'] = int(new_count)
            
            print(f"当前最大变体数: {prompt_config['max_variations']}")
            new_max = input("新的最大变体数 (回车跳过): ").strip()
            if new_max:
                prompt_config['max_variations'] = int(new_max)
                
            print("✅ 配置已更新")
            
        except ValueError as e:
            print(f"❌ 输入无效: {e}")
    
    def _save_config(self):
        """保存配置到文件"""
        file_path = input("配置文件路径 (默认config.json): ").strip()
        file_path = file_path if file_path else "config.json"
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(self.config, f, indent=2, ensure_ascii=False)
            print(f"✅ 配置已保存到: {file_path}")
        except Exception as e:
            print(f"❌ 保存失败: {e}")
    
    def _print_config(self, config: dict, indent: int = 0):
        """递归打印配置"""
        for key, value in config.items():
            if isinstance(value, dict):
                print("  " * indent + f"{key}:")
                self._print_config(value, indent + 1)
            else:
                print("  " * indent + f"{key}: {value}")
    
    def _setup_progress_monitor(self):
        """设置进度监控回调"""
        def progress_callback(snapshot):
            total = snapshot.total_tasks
            completed = snapshot.completed_tasks + snapshot.failed_tasks
            progress = completed / total * 100 if total > 0 else 0
            
            # 进度条
            bar_length = 30
            filled_length = int(bar_length * completed / total) if total > 0 else 0
            bar = "█" * filled_length + "░" * (bar_length - filled_length)
            
            print(f"\r[{bar}] {progress:.1f}% | "
                  f"完成:{snapshot.completed_tasks} | "
                  f"失败:{snapshot.failed_tasks} | "
                  f"速度:{snapshot.throughput_tasks_per_minute:.1f}/min", 
                  end="", flush=True)
        
        self.batch_processor.add_progress_callback(progress_callback)
    
    def _print_batch_summary(self, results: dict):
        """打印批次处理结果摘要"""
        print("\n" + "="*50)
        print("📊 批次处理结果摘要")
        print("="*50)
        
        summary = results.get('summary', {})
        print(f"✅ 成功任务: {summary.get('total_completed', 0)}")
        print(f"❌ 失败任务: {summary.get('total_failed', 0)}")
        print(f"⏱️  总耗时: {summary.get('total_time', 0):.1f}秒")
        print(f"📈 成功率: {summary.get('success_rate', 0):.1%}")
        
        if summary.get('avg_quality_score'):
            print(f"⭐ 平均质量: {summary['avg_quality_score']:.2f}")
        
        print(f"🖼️ 生成文件: {len(results.get('output_files', []))}")
        
        # 输出文件路径提示
        if results.get('output_files'):
            first_file = results['output_files'][0]
            output_dir = Path(first_file).parent
            print(f"📁 输出目录: {output_dir}")
            
            # 画廊链接
            gallery_file = output_dir.parent / "gallery.html"
            if gallery_file.exists():
                print(f"🌐 HTML画廊: {gallery_file}")
    
    def _run_auto_analysis(self):
        """运行自动分析"""
        try:
            if self.config["analysis"]["generate_reports"]:
                results = self.analysis_manager.run_complete_analysis()
                if 'error' not in results:
                    logger.info("📊 分析完成")
                    if 'report_files' in results:
                        for report_type, file_path in results['report_files'].items():
                            logger.info(f"📄 {report_type.upper()}报告: {file_path}")
                else:
                    logger.warning(f"分析失败: {results['error']}")
                    
        except Exception as e:
            logger.warning(f"自动分析失败: {e}")

def create_sample_config():
    """创建示例配置文件"""
    sample_config = {
        "output_directory": "./output",
        "database_path": "./data/database/tasks.db", 
        "workflows_directory": "./workflows",
        "batch_processing": {
            "max_concurrent_tasks": 1,
            "task_timeout": 300,
            "batch_delay": 2.0,
            "enable_progress_monitor": True
        },
        "prompt_generation": {
            "default_variation_count": 10,
            "max_variations": 50,
            "enable_template_system": True,
            "quality_threshold": 0.7
        },
        "workflow": {
            "default_type": "txt2img",
            "default_resolution": [1024, 1024],
            "default_steps": 20,
            "default_cfg_scale": 7.5
        },
        "output": {
            "generate_gallery": True,
            "save_metadata": True,
            "organize_by_date": True,
            "enable_json_backup": True
        },
        "analysis": {
            "auto_analyze": False,
            "generate_reports": True,
            "optimization_enabled": True
        }
    }
    
    with open("config.json", 'w', encoding='utf-8') as f:
        json.dump(sample_config, f, indent=2, ensure_ascii=False)
    
    print("示例配置文件已创建: config.json")

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="ComfyUI 自动化系统 v3.3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例:
  # 交互式模式
  python main.py
  
  # 单个主题生成变体
  python main.py --subject "春天的樱花" --count 15
  
  # 批量提示词处理  
  python main.py --prompts "森林小屋" "海边灯塔" "城市夜景"
  
  # 从文件读取提示词
  python main.py --file prompts.txt
  
  # 带自动分析
  python main.py --subject "肖像画" --count 20 --analyze
  
  # 创建示例配置
  python main.py --create-config
        """
    )
    
    # 主要参数
    parser.add_argument('--config', '-c', help='配置文件路径')
    parser.add_argument('--subject', '-s', help='单个主题描述')
    parser.add_argument('--count', '-n', type=int, help='变体数量')
    parser.add_argument('--prompts', '-p', nargs='*', help='批量提示词列表')
    parser.add_argument('--file', '-f', help='提示词文件路径')
    parser.add_argument('--plan', help='YAML计划文件路径（按分类多选做笛卡尔积）')
    parser.add_argument('--workflow', '-w', default='txt2img', help='工作流类型')
    parser.add_argument('--analyze', '-a', action='store_true', help='完成后自动分析')
    
    # 特殊功能
    parser.add_argument('--interactive', '-i', action='store_true', help='交互式模式')
    parser.add_argument('--create-config', action='store_true', help='创建示例配置文件')
    parser.add_argument('--verbose', '-v', action='store_true', help='详细输出')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # 创建配置文件
    if args.create_config:
        create_sample_config()
        return 0
    
    try:
        # 初始化系统
        system = ComfyUIAutomationSystem(args.config)
        
        # 交互式模式或无参数时进入交互模式
        if args.interactive or len(sys.argv) == 1:
            system.run_interactive()
            return 0
        
        # 命令行模式处理
        success = False
        
        if args.subject:
            # 单个主题模式
            success = system.run_single_subject(
                subject=args.subject,
                variation_count=args.count,
                workflow_type=args.workflow,
                auto_analyze=args.analyze
            )
            
        elif args.prompts:
            # 批量提示词模式
            success = system.run_batch_prompts(
                prompts=args.prompts,
                workflow_type=args.workflow,
                auto_analyze=args.analyze
            )
            
        elif args.file:
            # 文件输入模式
            success = system.run_from_file(
                file_path=args.file,
                workflow_type=args.workflow,
                auto_analyze=args.analyze
            )
        elif args.plan:
            # YAML 计划模式
            bp = system.batch_processor
            task_ids = bp.create_batch_from_yaml_plan(Path(args.plan), workflow_type=args.workflow)
            if task_ids:
                if system.config["batch_processing"]["enable_progress_monitor"]:
                    system._setup_progress_monitor()
                success = bp.start_batch_processing()
            else:
                success = False
            
        else:
            # 没有指定操作，显示帮助
            parser.print_help()
            return 1
        
        return 0 if success else 1
        
    except KeyboardInterrupt:
        print("\n👋 用户取消操作")
        return 1
    except Exception as e:
        logger.error(f"系统错误: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())