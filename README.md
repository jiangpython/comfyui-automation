# ComfyUI 自动化系统

> **版本**: v2.3  
> **状态**: Phase 2.3 完成，批量处理系统全功能可用  
> **开发周期**: 2025-09-08 完成核心功能开发

---

## 🌟 项目概述

ComfyUI 自动化系统是一个完整的批量图像生成解决方案，支持智能提示词生成、大规模并发任务处理和实时进度监控。

### ✨ 核心特性

- **🎨 智能提示词生成** - 从简单主题自动生成数百种变体组合
- **⚡ 批量任务处理** - 支持大规模并发任务执行，实时进度监控  
- **🔗 稳健ComfyUI集成** - 自动启动、连接监控、异常恢复
- **📊 双存储系统** - SQLite数据库 + JSON文件，确保数据安全
- **📈 实时监控** - 吞吐量、ETA预估、系统资源监控

---

## 🚀 快速开始

### 环境要求
- **Python**: 3.11+
- **ComfyUI**: 已安装并能正常运行
- **内存**: 8GB+ (推荐)
- **存储**: 根据生成图片数量确定

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repo-url>
   cd comfyui_automation
   ```

2. **激活虚拟环境**
   ```bash
   # Windows
   venv\Scripts\activate
   
   # Linux/Mac
   source venv/bin/activate
   ```

3. **验证安装**
   ```bash
   python system_verification.py
   ```
   期望输出：`🎉 基础集成测试完全成功!`

### 第一次使用

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

# 开始批量处理
success = processor.start_batch_processing()
print(f"批量处理结果: {success}")
```

---

## 📚 文档

- **[用户指南](USER_GUIDE.md)** - 完整的使用说明和最佳实践
- **[开发计划](DEVELOPMENT_PLAN.md)** - 项目开发进度和技术细节
- **[系统验证](system_verification.py)** - 系统健康检查脚本

---

## 🏗️ 系统架构

```
BatchProcessor (核心)
├── PromptGenerator      # 提示词生成器
├── WorkflowManager      # 工作流管理器  
├── ComfyUIClient        # ComfyUI客户端
├── TaskQueue            # 任务队列管理
├── ProgressMonitor      # 进度监控器
└── ResultManager        # 结果管理器
```

### 项目结构
```
comfyui_automation/
├── src/
│   ├── batch_processor/           # 批量处理核心
│   │   ├── batch_processor.py     # 主处理器
│   │   ├── task_queue.py          # 任务队列
│   │   └── progress_monitor.py    # 进度监控
│   ├── prompt_generator/          # 提示词生成
│   ├── workflow_manager/          # 工作流管理
│   ├── comfyui_client/           # ComfyUI集成
│   ├── utils/                    # 工具模块
│   └── config/                   # 配置管理
├── workflows/                    # 工作流配置
├── data/                        # 数据文件
├── output/                      # 输出目录
├── system_verification.py      # 系统验证
├── USER_GUIDE.md               # 用户指南
└── DEVELOPMENT_PLAN.md         # 开发计划
```

---

## 🎯 主要功能

### 批量处理模式

1. **单主题变体生成**
   ```python
   task_ids = processor.create_batch_from_subject(
       subject="春天的樱花树下，阳光透过花瓣",
       variation_count=20
   )
   ```

2. **提示词列表批处理**
   ```python
   prompts = ["夜晚的城市街道", "海边的灯塔", "山顶的寺庙"]
   task_ids = processor.create_batch_from_prompts(prompts)
   ```

3. **穷举式组合生成**
   ```python
   task_ids = processor.create_exhaustive_batch(
       subjects=["森林小屋", "城市街道"],
       styles=["写实主义", "动漫风格"],
       max_combinations=50
   )
   ```

### 实时监控

- **进度跟踪**: 实时显示完成进度和任务状态
- **性能指标**: 吞吐量、平均处理时间、ETA预估
- **资源监控**: 内存使用、CPU占用率
- **任务统计**: 成功率、失败原因分析

---

## 🔧 配置说明

### ComfyUI配置
```python
ComfyUIConfig(
    path="D:/LM/ComfyUI",              # ComfyUI路径
    api_url="http://127.0.0.1:8188",   # API地址
    startup_mode="auto",               # 启动模式: auto/manual/check_only
    startup_timeout=120                # 启动超时(秒)
)
```

### 提示词元素配置
编辑 `data/prompt_elements.yaml` 自定义元素库：
```yaml
elements:
  subjects:
    - name: "森林小屋"
      weight: 1.0
      tags: ["建筑", "自然"]
  
  styles:
    - name: "写实主义"  
      weight: 1.0
      conflicts: ["动漫风格"]
```

---

## 📊 开发里程碑

### ✅ Milestone 1: 基础功能完成
- 智能提示词生成器 (支持100+组合)
- 稳健的ComfyUI客户端 (100%成功率)
- 完整的测试验证

### ✅ Milestone 2: 系统集成完成  
- 多工作流配置支持
- 端到端批量处理流程
- 双存储结果管理系统
- 实时进度监控
- 任务队列管理

### 🚧 Milestone 3: 产品化完成 (规划中)
- HTML画廊界面
- 图片筛选与反馈
- 数据分析与优化建议

---

## 🤝 贡献指南

1. Fork 本项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

---

## 📄 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情

---

## 🆘 支持与反馈

- **文档**: 查看 [USER_GUIDE.md](USER_GUIDE.md) 获取详细使用说明
- **问题**: 在 [Issues](../../issues) 中报告问题或建议
- **验证**: 运行 `python system_verification.py` 检查系统状态

---

**开发者**: Claude  
**最后更新**: 2025-09-08  
**项目状态**: Phase 2.3 完成，全功能可用 🎉