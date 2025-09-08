# ComfyUI 自动化系统用户指南

> **版本**: v2.3  
> **更新日期**: 2025-09-08  
> **状态**: Phase 2.3 完成，批量处理系统已全功能可用

---

## 📖 目录

- [1. 系统概述](#1-系统概述)
- [2. 快速开始](#2-快速开始)
- [3. 系统配置](#3-系统配置)
- [4. 批量处理指南](#4-批量处理指南)
- [5. 提示词管理](#5-提示词管理)
- [6. 工作流配置](#6-工作流配置)
- [7. 结果管理](#7-结果管理)
- [8. 监控与调试](#8-监控与调试)
- [9. 常见问题](#9-常见问题)
- [10. 性能优化](#10-性能优化)

---

## 1. 系统概述

### 🎯 核心功能
ComfyUI 自动化系统是一个完整的批量图像生成解决方案，主要特点：

- **智能提示词生成**: 从简单主题自动生成数百种变体组合
- **批量任务处理**: 支持大规模并发任务执行，实时进度监控
- **稳健的ComfyUI集成**: 自动启动、连接监控、异常恢复
- **双存储系统**: SQLite数据库 + JSON文件，确保数据安全
- **实时监控**: 吞吐量、ETA预估、系统资源监控

### 🏗️ 系统架构
```
BatchProcessor (核心)
├── PromptGenerator      # 提示词生成器
├── WorkflowManager      # 工作流管理器  
├── ComfyUIClient        # ComfyUI客户端
├── TaskQueue            # 任务队列管理
├── ProgressMonitor      # 进度监控器
└── ResultManager        # 结果管理器
```

---

## 2. 快速开始

### 2.1 环境要求
- **Python**: 3.11+
- **ComfyUI**: 已安装并能正常运行
- **内存**: 8GB+ (推荐)
- **存储**: 根据生成图片数量确定

### 2.2 安装与配置

#### Step 1: 激活虚拟环境
```bash
cd D:/项目/comfyui_automation
venv\Scripts\activate  # Windows
# 或 source venv/bin/activate  # Linux/Mac
```

#### Step 2: 验证安装
```bash
python simple_test.py
```
期望输出：`🎉 基础集成测试完全成功!`

#### Step 3: 编辑配置（如需要）
编辑 `src/config/settings.py` 中的默认配置：
```python
ComfyUIConfig:
    path: "D:/LM/ComfyUI"           # ComfyUI路径
    api_url: "http://127.0.0.1:8188" # API地址
    startup_mode: "auto"             # 启动模式
```

### 2.3 第一次使用

#### 快速示例：生成森林小屋变体
```python
from src.batch_processor import BatchProcessor
from pathlib import Path

# 初始化处理器
processor = BatchProcessor(
    output_directory=Path("./output"),
    database_path=Path("./data/database/tasks.db"),
    workflows_directory=Path("./workflows")
)

# 创建批量任务
task_ids = processor.create_batch_from_subject(
    subject="森林中的小木屋，冬天雪景",
    variation_count=10,
    workflow_type="txt2img"
)

print(f"已创建 {len(task_ids)} 个任务")

# 开始批量处理
success = processor.start_batch_processing()
print(f"批量处理结果: {success}")
```

---

## 3. 系统配置

### 3.1 ComfyUI配置

#### 启动模式选择
- **auto**: 自动启动ComfyUI（推荐）
- **manual**: 手动启动，系统等待确认
- **check_only**: 仅检查，不启动

```python
# 在 settings.py 中配置
ComfyUIConfig(
    startup_mode="auto",        # 启动模式
    startup_timeout=120,        # 启动超时(秒)
    venv_python=""             # 自动推导路径
)
```

### 3.2 生成配置
```python
GenerationConfig(
    default_resolution=(1024, 1024),  # 默认分辨率
    default_steps=20,                 # 默认步数
    max_concurrent_tasks=1,           # 最大并发数
    batch_size=1                      # 批次大小
)
```

### 3.3 输出配置
```python
OutputConfig(
    base_directory="./output",    # 输出根目录
    organize_by="date",          # 组织方式: date/subject/style
    save_metadata=True,          # 保存元数据
    generate_gallery=True        # 生成画廊页面
)
```

---

## 4. 批量处理指南

### 4.1 三种批量模式

#### 模式1: 单主题变体生成
```python
# 从一个主题生成多个变体
task_ids = processor.create_batch_from_subject(
    subject="春天的樱花树下，阳光透过花瓣",
    variation_count=20,
    workflow_type="txt2img"
)
```

#### 模式2: 提示词列表批处理
```python
# 批量处理多个不同提示词
prompts = [
    "夜晚的城市街道，霓虹灯闪烁",
    "海边的灯塔，暴风雨前的宁静",
    "山顶的古老寺庙，晨雾缭绕"
]

task_ids = processor.create_batch_from_prompts(
    prompts=prompts,
    workflow_type="txt2img"
)
```

#### 模式3: 穷举式组合生成
```python
# 生成所有可能的主题和风格组合
subjects = ["森林小屋", "城市街道", "海边灯塔"]
styles = ["写实主义", "动漫风格", "水彩画"]

task_ids = processor.create_exhaustive_batch(
    subjects=subjects,
    styles=styles,
    max_combinations=50,
    workflow_type="txt2img"
)
```

### 4.2 批量处理控制

#### 启动处理
```python
# 设置进度回调
def progress_callback(snapshot):
    progress = (snapshot.completed_tasks + snapshot.failed_tasks) / snapshot.total_tasks * 100
    print(f"进度: {progress:.1f}% | 完成: {snapshot.completed_tasks} | 失败: {snapshot.failed_tasks}")

processor.add_progress_callback(progress_callback)

# 开始处理
success = processor.start_batch_processing(
    max_concurrent=1,      # 并发数
    console_output=True    # 控制台输出
)
```

#### 暂停与恢复
```python
processor.pause_processing()   # 暂停处理
processor.resume_processing()  # 恢复处理
processor.stop_processing()    # 停止处理
```

### 4.3 状态监控

#### 获取处理状态
```python
status = processor.get_processing_status()
print(f"运行状态: {status['is_running']}")
print(f"队列状态: {status['queue_status']}")
print(f"性能指标: {status['performance_metrics']}")
```

#### 获取批量结果
```python
results = processor.get_batch_results()
print(f"成功任务: {results['summary']['total_completed']}")
print(f"失败任务: {results['summary']['total_failed']}")
print(f"输出文件: {len(results['output_files'])}")
```

---

## 5. 提示词管理

### 5.1 提示词元素配置

编辑 `data/prompt_elements.yaml` 来自定义元素库：

```yaml
elements:
  subjects:
    - name: "森林小屋"
      weight: 1.0
      tags: ["建筑", "自然"]
    - name: "城市街道"
      weight: 0.8
      tags: ["城市", "现代"]

  styles:
    - name: "写实主义"
      weight: 1.0
      conflicts: ["动漫风格"]
    - name: "动漫风格"
      weight: 0.9
      conflicts: ["写实主义"]

  camera_angles:
    - name: "wide shot"
      weight: 0.8
    - name: "close-up"
      weight: 0.6

templates:
  - pattern: "{camera_angles} of {subjects}, {styles} style, {lighting}"
    weight: 0.3
    description: "完整描述模板"
```

### 5.2 提示词生成策略

#### 智能识别模式
```python
generator = PromptGenerator()

# 短主题 -> 元素组合
prompts1 = generator.generate_variations("森林小屋", variation_count=10)

# 完整描述 -> 增强变体  
prompts2 = generator.generate_variations(
    "春天的樱花树下，一位少女在读书，阳光透过花瓣洒在她身上", 
    variation_count=5
)
```

### 5.3 权重与冲突系统

- **权重**: 控制元素选择概率（0.0-1.0）
- **冲突**: 避免不兼容元素组合
- **标签**: 用于分类和筛选

---

## 6. 工作流配置

### 6.1 工作流结构

每个工作流包含两个文件：
```
workflows/txt2img/
├── config.yaml          # 工作流配置
└── txt2img.json         # ComfyUI工作流JSON
```

### 6.2 配置文件格式

`config.yaml` 示例：
```yaml
name: "txt2img"
version: "1.0.0"
description: "基础文本到图像生成工作流"

parameters:
  prompt:
    node_id: "6"
    field: "text"
    type: "string"
    required: true
    
  steps:
    node_id: "3"
    field: "steps"
    type: "int"
    default: 20
    
  cfg_scale:
    node_id: "3"
    field: "cfg"
    type: "float"
    default: 8.0

validation:
  required_nodes: ["3", "6", "8"]
  output_nodes: ["9"]
```

### 6.3 参数映射

系统会自动将任务参数映射到ComfyUI节点：
```python
# 任务数据
task_data = {
    'prompt': "森林小屋，冬天雪景",
    'steps': 25,
    'cfg_scale': 7.5
}

# 自动映射到工作流
workflow = workflow_manager.create_workflow_from_task("txt2img", task_data)
```

---

## 7. 结果管理

### 7.1 双存储系统

系统使用双存储模式确保数据安全：

#### SQLite数据库
- 高性能查询和统计
- 事务支持和数据完整性
- 位置: `data/database/tasks.db`

#### JSON元数据文件
- 人类可读的备份格式
- 便于数据迁移和外部处理
- 位置: `output/metadata/`

### 7.2 文件组织结构

```
output/
├── 20250908_143022_batch_森林小屋/     # 批次目录
│   ├── task_001_completed.png         # 生成图片
│   ├── task_002_completed.png
│   └── metadata/
│       ├── task_001.json              # 任务元数据
│       └── task_002.json
└── metadata/
    └── batch_20250908_143022.json     # 批次元数据
```

### 7.3 元数据内容

每个任务的元数据包含：
```json
{
  "task_id": "task_20250908_143022_001",
  "prompt": "wide shot of 森林小屋, 写实主义 style, natural lighting",
  "workflow_type": "txt2img",
  "status": "completed",
  "created_at": "2025-09-08T14:30:22",
  "started_at": "2025-09-08T14:30:25",
  "completed_at": "2025-09-08T14:31:45",
  "generation_time": 80.5,
  "quality_score": 0.85,
  "tags": ["森林", "建筑", "写实"],
  "workflow_params": {...},
  "output_files": ["task_001_completed.png"],
  "file_size": 2048576
}
```

### 7.4 结果查询与统计

```python
# 获取统计信息
stats = processor.result_manager.get_statistics()
print(f"总任务数: {stats['total_tasks']}")
print(f"成功率: {stats['success_rate']:.1%}")
print(f"平均生成时间: {stats['avg_generation_time']:.1f}秒")

# 查询特定任务
task = processor.result_manager.get_task("task_001")
result = processor.result_manager.get_result("task_001")

# 批量查询
completed_tasks = processor.result_manager.get_tasks_by_status("completed")
failed_tasks = processor.result_manager.get_tasks_by_status("failed")
```

---

## 8. 监控与调试

### 8.1 实时进度监控

#### 进度快照信息
```python
snapshot = processor.progress_monitor.get_latest_snapshot()
print(f"总任务: {snapshot.total_tasks}")
print(f"完成: {snapshot.completed_tasks}")
print(f"运行中: {snapshot.running_tasks}")
print(f"成功率: {snapshot.success_rate:.1%}")
print(f"吞吐量: {snapshot.throughput_tasks_per_minute:.1f} 任务/分钟")
print(f"预计剩余: {snapshot.estimated_remaining_time/60:.1f} 分钟")
```

#### 自定义进度回调
```python
def detailed_progress_callback(snapshot):
    # 进度条显示
    progress = (snapshot.completed_tasks + snapshot.failed_tasks) / snapshot.total_tasks * 100
    bar = "█" * int(progress / 5) + "░" * (20 - int(progress / 5))
    
    print(f"\r[{bar}] {progress:.1f}% | "
          f"完成: {snapshot.completed_tasks} | "
          f"失败: {snapshot.failed_tasks} | "
          f"速度: {snapshot.throughput_tasks_per_minute:.1f}/min", 
          end="", flush=True)

processor.add_progress_callback(detailed_progress_callback)
```

### 8.2 性能指标

#### 系统资源监控
```python
performance = processor.progress_monitor.get_performance_metrics()
print(f"平均吞吐量: {performance['average_throughput']:.1f} 任务/分钟")
print(f"峰值吞吐量: {performance['peak_throughput']:.1f} 任务/分钟")
print(f"平均内存使用: {performance['average_memory_usage_mb']:.0f} MB")
print(f"峰值内存使用: {performance['peak_memory_usage_mb']:.0f} MB")
```

#### 任务处理统计
```python
task_stats = performance['task_time_statistics']
print(f"最快任务: {task_stats['min_time']:.1f}秒")
print(f"最慢任务: {task_stats['max_time']:.1f}秒")
print(f"平均时间: {task_stats['avg_time']:.1f}秒")
```

### 8.3 日志与调试

#### 日志级别配置
```python
import logging
logging.basicConfig(
    level=logging.DEBUG,  # DEBUG, INFO, WARNING, ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

#### 常用调试信息
```python
# ComfyUI连接状态
health = processor.comfyui_client.health_check()
print(f"服务运行: {health['service_running']}")
print(f"API可访问: {health['api_accessible']}")
print(f"进程存活: {health['process_alive']}")

# 队列状态详情
queue_stats = processor.task_queue.get_queue_statistics()
print(f"优先级分布: {queue_stats['priority_distribution']}")
print(f"重试统计: {queue_stats['retry_statistics']}")
```

---

## 9. 常见问题

### 9.1 启动问题

#### Q: ComfyUI无法自动启动
**A**: 检查配置路径和虚拟环境设置
```python
# 验证路径
comfyui_path = Path("D:/LM/ComfyUI")
print(f"ComfyUI路径存在: {comfyui_path.exists()}")

venv_python = comfyui_path / "venv" / "Scripts" / "python.exe"
print(f"虚拟环境Python存在: {venv_python.exists()}")

# 手动模式测试
settings_obj.comfyui.startup_mode = "manual"
```

#### Q: 依赖包缺失错误
**A**: 激活虚拟环境并安装依赖
```bash
venv\Scripts\activate
pip install -r requirements.txt
```

### 9.2 任务执行问题

#### Q: 任务一直处于运行状态
**A**: 检查ComfyUI工作流和超时设置
```python
# 调整超时时间
processor.task_executor.task_timeout = 600  # 10分钟

# 检查工作流有效性
workflow_data = processor.workflow_manager.validate_workflow("txt2img")
print(f"工作流有效: {workflow_data is not None}")
```

#### Q: 生成图片找不到
**A**: 检查ComfyUI输出目录设置
```python
# 检查默认输出目录
comfyui_output = Path("D:/LM/ComfyUI/output")
print(f"输出目录存在: {comfyui_output.exists()}")
print(f"最近文件: {sorted(comfyui_output.glob('*.png'))[-5:]}")
```

### 9.3 性能问题

#### Q: 处理速度太慢
**A**: 优化并发设置和批次延迟
```python
# 增加并发数（小心显存）
processor.max_concurrent_tasks = 2

# 减少批次延迟
processor.batch_delay = 1.0

# 禁用详细日志
logging.getLogger().setLevel(logging.WARNING)
```

#### Q: 内存占用过高
**A**: 清理历史数据和限制缓存
```python
# 清理进度历史
processor.progress_monitor.clear_history(keep_recent=50)

# 清理已完成任务
processor.task_queue.clear_completed_tasks()

# 手动垃圾回收
import gc
gc.collect()
```

---

## 10. 性能优化

### 10.1 系统配置优化

#### 硬件建议
- **GPU显存**: 8GB+ (推荐12GB+)
- **系统内存**: 16GB+ (大批量任务)
- **SSD存储**: 加速文件IO操作

#### 软件优化
```python
# 优化批处理器设置
processor = BatchProcessor(
    max_concurrent_tasks=2,        # 根据显存调整
    task_timeout=300,              # 5分钟超时
    batch_delay=1.0,               # 减少延迟
    enable_database=True,          # 数据库查询更快
    enable_json_metadata=False     # 大批量时禁用JSON
)
```

### 10.2 提示词优化

#### 减少无效组合
```yaml
# 在 prompt_elements.yaml 中添加冲突规则
elements:
  styles:
    - name: "写实主义"
      conflicts: ["动漫风格", "抽象艺术"]
    - name: "动漫风格" 
      conflicts: ["写实主义", "古典绘画"]
```

#### 提高成功率
```python
# 使用验证过的元素组合
validated_elements = generator.validate_element_combinations()

# 过滤低质量提示词
high_quality_prompts = [p for p in prompts if p.quality_score > 0.7]
```

### 10.3 批处理策略

#### 分批处理
```python
# 大任务分成小批次
large_prompts = ["prompt1", "prompt2", ...] * 100  # 大量提示词

batch_size = 20
for i in range(0, len(large_prompts), batch_size):
    batch = large_prompts[i:i+batch_size]
    
    task_ids = processor.create_batch_from_prompts(batch)
    success = processor.start_batch_processing()
    
    if success:
        print(f"批次 {i//batch_size + 1} 完成")
```

#### 优先级调度
```python
# 重要任务设置高优先级
urgent_tasks = processor.create_batch_from_subject(
    subject="紧急任务：客户展示图",
    priority=10  # 高优先级
)

# 普通任务设置默认优先级
normal_tasks = processor.create_batch_from_subject(
    subject="常规测试图",
    priority=0   # 默认优先级
)
```

### 10.4 监控与诊断

#### 性能基准测试
```python
import time

start_time = time.time()
task_ids = processor.create_batch_from_subject("测试主题", variation_count=10)
creation_time = time.time() - start_time

start_processing = time.time()
success = processor.start_batch_processing()
processing_time = time.time() - start_processing

print(f"任务创建耗时: {creation_time:.2f}秒")
print(f"批量处理耗时: {processing_time:.2f}秒")
print(f"平均单任务时间: {processing_time/len(task_ids):.2f}秒")
```

#### 内存监控
```python
import psutil

def monitor_memory():
    process = psutil.Process()
    memory_mb = process.memory_info().rss / (1024 * 1024)
    cpu_percent = process.cpu_percent()
    return memory_mb, cpu_percent

# 在处理过程中定期监控
def memory_callback(snapshot):
    memory_mb, cpu_percent = monitor_memory()
    if memory_mb > 2000:  # 超过2GB警告
        print(f"⚠️ 内存使用过高: {memory_mb:.0f}MB")

processor.add_progress_callback(memory_callback)
```

---

## 📞 技术支持

如果遇到问题或需要帮助：

1. **查看日志**: 检查控制台输出和错误信息
2. **运行测试**: 执行 `python simple_test.py` 验证系统状态
3. **检查配置**: 确认ComfyUI路径和API设置正确
4. **性能监控**: 观察内存和CPU使用情况

---

**文档版本**: v2.3  
**最后更新**: 2025-09-08  
**系统状态**: Phase 2.3 完成，全功能可用 ✅