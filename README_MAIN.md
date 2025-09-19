# ComfyUI 自动化系统主程序使用指南

> **一键启动完整系统，支持单体提示词变体生成和批量处理**

## 🚀 快速开始

### 方式1: Windows双击启动 (推荐新手)
```bash
双击 start.bat 文件
```

### 方式2: 快速启动脚本
```bash
python quick_start.py
```

### 方式3: 完整主程序
```bash
python main.py
```

## 📋 主要功能

### 🎯 单体提示词变体生成
从一个简单的主题描述，自动生成多种变体组合：

```bash
# 命令行模式
python main.py --subject "春天的樱花树下，少女在读书" --count 15

# 交互式模式
python main.py
# 然后选择 "1. 单个主题生成变体"
```

**示例**:
- 输入: `"森林中的小木屋"`
- 生成: `"wide shot of 森林中的小木屋, 写实主义 style, natural lighting, masterpiece, highly detailed"`
- 变体数量: 可自定义 (默认10个)

### 📦 批量提示词处理
接受多个不同的提示词进行批量处理：

```bash
# 命令行模式
python main.py --prompts "夜晚的城市" "海边的灯塔" "山顶的寺庙"

# 从文件读取
echo -e "森林小屋\n海边灯塔\n城市夜景" > prompts.txt
python main.py --file prompts.txt

# 交互式模式
python main.py
# 然后选择 "2. 批量提示词处理"
```

### 📊 自动分析功能
处理完成后自动进行数据分析和优化建议：

```bash
# 带自动分析的单主题处理
python main.py --subject "肖像画" --count 20 --analyze

# 带自动分析的批量处理
python main.py --prompts "风景画" "人物肖像" "抽象艺术" --analyze
```

## 🎮 交互式模式

运行 `python main.py` 进入交互式菜单：

```
🎨 ComfyUI 自动化系统 - 交互式模式
======================================

📋 选择操作模式:
1. 单个主题生成变体
2. 批量提示词处理
3. 从文件读取提示词
4. 数据分析
5. 系统状态
6. 配置管理
0. 退出
```

### 详细功能说明

#### 1. 单个主题生成变体
- 输入主题描述
- 设置变体数量
- 选择工作流类型
- 是否自动分析

#### 2. 批量提示词处理
- 逐行输入多个提示词
- 空行结束输入
- 统一处理所有提示词

#### 3. 从文件读取提示词
- 支持文本文件 (.txt)
- 每行一个提示词
- 自动预览文件内容

#### 4. 数据分析
- 完整分析历史数据
- 生成优化提示词
- 元素性能分析
- 仪表板数据
- 分析报告生成

#### 5. 系统状态
- 批量处理器状态
- ComfyUI连接状态
- 数据库统计
- 输出文件统计

#### 6. 配置管理
- 查看当前配置
- 修改处理参数
- 保存配置文件

## ⚙️ 配置系统

### 创建配置文件
```bash
# 创建示例配置
python main.py --create-config

# 使用自定义配置
python main.py --config my_config.json
```

### 配置文件示例
```json
{
  "batch_processing": {
    "max_concurrent_tasks": 1,
    "task_timeout": 300,
    "batch_delay": 2.0
  },
  "prompt_generation": {
    "default_variation_count": 10,
    "max_variations": 50
  },
  "analysis": {
    "auto_analyze": false,
    "generate_reports": true
  }
}
```

## 📝 命令行参数

### 基本用法
```bash
python main.py [选项]

选项:
  -h, --help            显示帮助信息
  -c, --config CONFIG   指定配置文件路径
  -s, --subject SUBJECT 单个主题描述
  -n, --count COUNT     变体数量
  -p, --prompts PROMPT1 PROMPT2...  批量提示词
  -f, --file FILE       提示词文件路径
  -w, --workflow TYPE   工作流类型 (默认: txt2img)
  -a, --analyze         完成后自动分析
  -i, --interactive     交互式模式
  -v, --verbose         详细输出
```

### 使用示例

#### 单主题生成
```bash
# 基础使用
python main.py --subject "春天的樱花"

# 自定义数量
python main.py --subject "森林小屋" --count 20

# 带自动分析
python main.py --subject "海边风景" --count 15 --analyze

# 指定工作流
python main.py --subject "人物肖像" --workflow "txt2img" --count 10
```

#### 批量处理
```bash
# 多个提示词
python main.py --prompts "夜晚城市" "森林小径" "山顶寺庙"

# 从文件读取
python main.py --file my_prompts.txt --analyze

# 自定义工作流
python main.py --file batch_prompts.txt --workflow "img2img"
```

#### 配置和调试
```bash
# 使用自定义配置
python main.py --config custom.json --subject "测试主题"

# 详细输出模式
python main.py --verbose --subject "调试测试"

# 纯交互模式
python main.py --interactive
```

## 🔄 典型工作流程

### 新用户首次使用
1. **双击启动**: `start.bat`
2. **选择快速模式**: 选择1
3. **单主题测试**: 输入 "春天的樱花"
4. **查看结果**: 自动打开画廊页面
5. **数据分析**: 运行分析查看效果

### 日常批量处理
1. **准备提示词**: 编辑 `prompts.txt` 文件
2. **批量处理**: `python main.py --file prompts.txt --analyze`
3. **查看画廊**: 打开 `output/gallery.html`
4. **筛选结果**: 使用画廊的筛选和收藏功能
5. **优化迭代**: 基于分析结果优化提示词

### 高级用户工作流
1. **创建配置**: `python main.py --create-config`
2. **自定义参数**: 编辑 `config.json`
3. **批量生成**: `python main.py --config config.json --subject "主题" --count 50`
4. **深度分析**: `python analysis_cli.py analyze`
5. **迭代优化**: `python analysis_cli.py optimize --count 30`

## 📊 输出结果

### 文件结构
```
output/
├── 20250909_143022_batch_春天的樱花/    # 批次目录
│   ├── task_001_completed.png          # 生成图片
│   ├── task_002_completed.png
│   └── metadata/                        # 元数据
│       ├── task_001.json
│       └── task_002.json
├── gallery.html                         # HTML画廊
├── static/                              # 画廊资源
└── analysis/                            # 分析报告
    ├── analysis_report_*.html
    └── dashboard_data_*.json
```

### 查看结果
- **HTML画廊**: `output/gallery.html` - 响应式图片浏览界面
- **原始图片**: `output/批次目录/` - 生成的PNG文件
- **分析报告**: `output/analysis/` - 数据分析结果
- **元数据**: `output/metadata/` - JSON格式的任务信息

## 🛠️ 故障排除

### 常见问题

#### Q: 无法启动ComfyUI
```bash
# 检查路径配置
python -c "from pathlib import Path; print('ComfyUI存在:', Path('D:/LM/ComfyUI').exists())"

# 手动启动ComfyUI
cd D:\LM\ComfyUI
venv\Scripts\activate
python main.py
```

#### Q: 任务处理失败
```bash
# 运行系统测试
python simple_test.py

# 检查工作流配置
ls workflows/txt2img/
```

#### Q: 内存不足
```bash
# 修改配置减少并发
python main.py --create-config
# 编辑 config.json: "max_concurrent_tasks": 1
```

### 日志调试
```bash
# 启用详细日志
python main.py --verbose --subject "测试"

# 查看系统状态
python main.py --interactive
# 选择 "5. 系统状态"
```

## 🎯 最佳实践

### 提示词编写建议
- **具体描述**: "春天的樱花树下，穿白裙的少女在读书" 比 "少女" 更好
- **风格指定**: 添加 "写实主义", "动漫风格", "水彩画" 等风格描述
- **质量词汇**: 使用 "masterpiece", "highly detailed", "best quality"
- **避免冲突**: 不要同时使用 "写实" 和 "动漫" 等冲突词汇

### 批量处理策略
- **分批执行**: 大量任务分成20-50个一批
- **质量优先**: 使用 `--analyze` 参数了解效果
- **迭代改进**: 基于分析结果优化下一批提示词

### 性能优化
- **并发设置**: 根据显卡显存调整 `max_concurrent_tasks`
- **超时控制**: 复杂任务增加 `task_timeout`
- **定期清理**: 删除不需要的输出文件节省空间

## 📞 技术支持

### 自助诊断
```bash
# 系统自检
python simple_test.py

# 分析系统测试
python test_analysis_system.py

# 查看系统状态
python main.py --interactive  # 选择 "5. 系统状态"
```

### 获取帮助
```bash
# 查看帮助
python main.py --help

# 查看完整文档
start USER_GUIDE.md
```

---

**🎉 立即开始使用**:
1. 双击 `start.bat` (Windows)
2. 或运行 `python quick_start.py`
3. 或执行 `python main.py --subject "你的主题"`

**享受AI艺术创作的乐趣！** ✨