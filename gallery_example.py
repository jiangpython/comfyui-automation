"""HTML画廊生成示例"""

import sys
from pathlib import Path
import logging

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from src.batch_processor import BatchProcessor
from src.config.settings import Settings

# 设置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def gallery_demo():
    """画廊生成演示"""
    
    logger.info("开始HTML画廊生成演示")
    
    try:
        # 1. 初始化批量处理器
        settings_obj = Settings()
        
        output_dir = Path("./output")
        database_path = Path("./data/database/tasks.db") 
        workflows_dir = Path("./workflows")
        
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
        
        # 2. 检查现有画廊
        gallery_info = processor.get_gallery_info()
        logger.info(f"画廊信息: {gallery_info}")
        
        if gallery_info['exists']:
            logger.info(f"发现现有画廊，包含 {gallery_info.get('total_images', 0)} 张图片")
            
            # 增量更新画廊
            logger.info("执行增量更新...")
            update_result = processor.update_gallery()
            
            if update_result['success']:
                logger.info(f"✅ 画廊更新成功")
                logger.info(f"新增图片: {update_result['new_images_count']}")
                logger.info(f"总图片数: {update_result['total_images_count']}")
            else:
                logger.error(f"❌ 画廊更新失败: {update_result.get('error')}")
        
        else:
            logger.info("未找到现有画廊，生成新画廊...")
            
            # 生成新画廊
            gallery_result = processor.generate_gallery(
                status_filter=['completed', 'failed'],  # 包含已完成和失败的任务
                batch_ids=None,  # 包含所有批次
                date_from=None,  # 不限制日期
                date_to=None
            )
            
            if gallery_result['success']:
                logger.info(f"✅ 画廊生成成功")
                logger.info(f"HTML文件: {gallery_result['html_file']}")
                logger.info(f"数据文件: {gallery_result['data_file']}")
                logger.info(f"图片总数: {gallery_result['total_images']}")
                
                # 显示统计信息
                stats = gallery_result['stats']
                logger.info(f"统计信息:")
                logger.info(f"  - 成功率: {stats['success_rate']:.1%}")
                logger.info(f"  - 平均质量: {stats['average_quality']:.2f}")
                logger.info(f"  - 平均生成时间: {stats['average_generation_time']:.1f}s")
                logger.info(f"  - 高质量图片数: {stats['high_quality_count']}")
                logger.info(f"  - 总文件大小: {stats['total_size_mb']:.1f}MB")
            else:
                logger.error(f"❌ 画廊生成失败: {gallery_result.get('error')}")
        
        # 3. 显示最终画廊信息
        final_info = processor.get_gallery_info()
        if final_info['exists']:
            logger.info(f"\n🎨 画廊已就绪!")
            logger.info(f"📁 HTML文件: {final_info['html_file']}")
            logger.info(f"📊 图片总数: {final_info['total_images']}")
            logger.info(f"🏷️ 标签数量: {final_info.get('tags_count', 0)}")
            logger.info(f"⏰ 生成时间: {final_info.get('generated_at', '未知')}")
            
            # 打开画廊提示
            html_file = Path(final_info['html_file'])
            if html_file.exists():
                logger.info(f"\n🌐 在浏览器中打开画廊:")
                logger.info(f"   {html_file.resolve()}")
            else:
                logger.warning("HTML文件不存在")
        
        logger.info("✅ 画廊演示完成")
        
        return True
        
    except Exception as e:
        logger.error(f"画廊演示失败: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    logger.info("启动HTML画廊生成演示")
    success = gallery_demo()
    
    if success:
        logger.info("演示成功完成!")
    else:
        logger.error("演示失败!")
        sys.exit(1)