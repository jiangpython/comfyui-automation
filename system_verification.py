"""简化的批量处理器测试脚本"""

import sys
from pathlib import Path
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_basic_integration():
    """基础集成测试"""
    
    logger.info("开始基础集成测试")
    
    try:
        # 1. 测试配置加载
        logger.info("=== 测试配置加载 ===")
        from src.config.settings import load_settings
        settings = load_settings()
        logger.info("✅ 配置加载成功")
        
        # 2. 测试提示词生成器
        logger.info("=== 测试提示词生成器 ===")
        from src.prompt_generator import PromptGenerator
        generator = PromptGenerator()
        
        prompts = generator.generate_variations("森林小屋", variation_count=3)
        logger.info(f"✅ 生成了 {len(prompts)} 个提示词变体")
        for i, prompt in enumerate(prompts):
            logger.info(f"  {i+1}. {prompt.text}")
        
        # 3. 测试工作流管理器
        logger.info("=== 测试工作流管理器 ===")
        from src.workflow_manager import WorkflowManager
        workflows_dir = Path(settings['workflows']['directory'])
        workflow_manager = WorkflowManager(workflows_dir)
        logger.info(f"✅ 工作流管理器加载了 {len(workflow_manager)} 个工作流")
        
        # 4. 测试任务队列
        logger.info("=== 测试任务队列 ===")
        from src.batch_processor.task_queue import TaskQueue
        queue = TaskQueue()
        
        task_ids = queue.add_tasks_from_generated_prompts(
            generated_prompts=prompts,
            workflow_type="txt2img"
        )
        logger.info(f"✅ 任务队列添加了 {len(task_ids)} 个任务")
        
        # 5. 测试进度监控器
        logger.info("=== 测试进度监控器 ===")
        from src.batch_processor.progress_monitor import ProgressMonitor
        monitor = ProgressMonitor()
        monitor.start_monitoring(len(task_ids))
        
        # 模拟进度更新
        monitor.update_progress(queue.get_queue_status())
        latest = monitor.get_latest_snapshot()
        if latest:
            logger.info(f"✅ 进度监控正常，总任务: {latest.total_tasks}")
        
        monitor.stop_monitoring()
        
        # 6. 测试结果管理器
        logger.info("=== 测试结果管理器 ===")
        from src.utils import ResultManager
        
        output_dir = Path(settings['output']['base_directory'])
        database_path = Path(settings['database']['file_path'])
        output_dir.mkdir(parents=True, exist_ok=True)
        database_path.parent.mkdir(parents=True, exist_ok=True)
        
        result_manager = ResultManager(
            database_path=database_path,
            output_directory=output_dir,
            enable_database=True,
            enable_json_metadata=True
        )
        logger.info("✅ 结果管理器初始化成功")
        
        # 7. 测试ComfyUI客户端连接检查
        logger.info("=== 测试ComfyUI客户端 ===")
        from src.comfyui_client import ComfyUIClient
        from src.config.settings import Settings
        
        settings_obj = Settings()
        client = ComfyUIClient(settings_obj)
        
        is_running = client.is_service_running()
        logger.info(f"ComfyUI服务状态: {'✅ 运行中' if is_running else '❌ 未运行'}")
        
        # 8. 测试批量处理器初始化
        logger.info("=== 测试批量处理器初始化 ===")
        from src.batch_processor import BatchProcessor
        
        processor = BatchProcessor(
            output_directory=output_dir,
            database_path=database_path,
            workflows_directory=workflows_dir,
            comfyui_settings=settings_obj,
            max_concurrent_tasks=1,
            task_timeout=300,
            batch_delay=2.0
        )
        logger.info("✅ 批量处理器初始化成功")
        
        # 9. 测试批量任务创建
        logger.info("=== 测试批量任务创建 ===")
        task_ids = processor.create_batch_from_subject(
            subject="测试主题：春天的花园",
            variation_count=2,
            workflow_type="txt2img"
        )
        logger.info(f"✅ 批量任务创建成功: {len(task_ids)} 个任务")
        
        # 展示生成的任务
        pending_tasks = processor.task_queue.get_pending_tasks()
        logger.info("生成的任务:")
        for i, task in enumerate(pending_tasks[:3]):
            logger.info(f"  {i+1}. {task.prompt[:100]}...")
        
        # 10. 获取状态信息
        logger.info("=== 获取系统状态 ===")
        processing_status = processor.get_processing_status()
        logger.info(f"处理状态: {processing_status['is_running']}")
        logger.info(f"队列状态: {processing_status['queue_status']}")
        
        logger.info("\n🎉 基础集成测试完全成功!")
        logger.info("所有核心模块都能正常工作，系统集成完成!")
        
        return True
        
    except Exception as e:
        logger.error(f"集成测试失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("启动简化集成测试")
    success = test_basic_integration()
    
    if success:
        logger.info("集成测试成功完成!")
        sys.exit(0)
    else:
        logger.error("集成测试失败!")
        sys.exit(1)