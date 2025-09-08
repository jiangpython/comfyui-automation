# ComfyUI 自动化项目记录

## 📝 项目信息

**项目名称**: ComfyUI Automation System  
**创建日期**: 2025-09-08  
**项目路径**: `D:/项目/comfyui_automation`  
**开发状态**: 架构设计完成，准备开发

---

## 🎯 项目目标

创建一个智能化的ComfyUI自动化系统，实现：
- 大规模提示词组合生成
- 批量图片生成自动化
- 交互式结果筛选和分析
- 数据驱动的提示词优化

---

## 🏗️ 系统架构

### 核心模块
1. **提示词生成器**: 智能组合各种元素生成大量提示词变体
2. **ComfyUI客户端**: 稳健的任务执行和监控系统
3. **结果管理器**: 任务数据存储和索引
4. **HTML画廊**: 交互式图片预览和筛选界面
5. **分析引擎**: 基于用户反馈的提示词优化

### 技术特点
- **稳健性**: 多重任务检测机制，异常恢复
- **可扩展**: 模块化设计，支持多工作流
- **智能化**: 数据驱动的提示词优化
- **用户友好**: 直观的HTML界面

---

## 🛠️ 已完成工作

### 前期探索 (2025-09-08)
- [x] ComfyUI API连接测试
- [x] 基础工作流执行验证
- [x] 单任务自动化脚本开发
- [x] 5任务批量测试成功 (100%成功率)

### 技术验证
- [x] ComfyUI自动启动机制
- [x] API格式工作流解析
- [x] 任务状态监控
- [x] 参数动态注入

### 测试结果
```
执行统计 (2025-09-08 测试):
- 总任务数: 5个
- 成功完成: 5个 
- 失败: 0个
- 成功率: 100.0%
- 平均耗时: 15.1秒/张 (首张60.2秒含加载)
```

---

## 📁 文件结构状态

### 当前文件
```
comfyui_automation/
├── final_automation.py          # ✅ 最终可用版本
├── txt2img.json                 # ✅ API格式工作流
├── output/                      # ✅ 输出目录
├── test_comfyui_debug.py       # 🗑️ 待清理
├── test_comfyui_simple.py      # 🗑️ 待清理
├── test_fixed.py               # 🗑️ 待清理
├── test_single_task.py         # 🗑️ 待清理
└── workflow_automation.py      # 🗑️ 待清理
```

### 计划结构
```
comfyui_automation/
├── src/
│   ├── prompt_generator/       # 📝 待开发
│   ├── comfyui_client/        # 📝 待开发 (基于final_automation.py)
│   ├── config/                # 📝 待开发
│   └── utils/                 # 📝 待开发
├── data/                      # 📝 待创建
├── output/                    # ✅ 已存在
├── main.py                    # 📝 待开发
└── requirements.txt           # 📝 待创建
```

---

## 🎮 核心功能设计

### 1. 提示词生成器
```python
# 元素组合示例
ELEMENTS = {
    "camera_angles": ["wide shot", "close-up", "medium shot"],
    "styles": ["medieval", "cartoon", "sci-fi", "photorealistic"],
    "subjects": ["forest cabin", "mountain lake", "city street"],
    "lighting": ["soft lighting", "dramatic lighting", "golden hour"]
}

# 从 "forest cabin" 生成变体:
# → "wide shot of forest cabin, medieval style, soft lighting"
# → "close-up of forest cabin, sci-fi style, dramatic lighting" 
# → ... (数百种组合)
```

### 2. 批量执行系统
- 自动启动ComfyUI (可选择手动模式)
- 稳健的任务监控 (多重检测 + 异常恢复)
- 大批量队列处理 (支持数百任务)
- 实时进度跟踪

### 3. 结果筛选分析
- HTML画廊: 网格式图片预览
- 交互筛选: 多选、标签、搜索
- 智能分析: 成功模式识别
- 优化建议: 高效提示词推荐

---

## 📊 用户工作流

```
[配置提示词元素] 
    ↓
[生成N个组合] (如100个变体)
    ↓ 
[批量执行ComfyUI] (自动化运行)
    ↓
[HTML画廊预览] (查看所有结果)
    ↓
[筛选满意图片] (点击选择喜欢的)
    ↓
[分析成功模式] (找出有效组合)
    ↓
[生成优化建议] (下次用什么提示词)
    ↓
[迭代改进] (基于分析结果继续优化)
```

---

## ⚡ 关键技术方案

### ComfyUI任务检测机制
```python
# 多重检测策略
detectors = [
    HistoryDetector(),      # 主检测: 历史记录
    QueueDetector(),        # 辅助: 队列状态  
    FileDetector(),         # 备用: 文件检查
    WebSocketDetector(),    # 实时: 事件推送
]

# 稳健性保障
- 连续失败 → 紧急模式
- 检测异常 → 自动重试
- API超时 → 多重回退
- 进程崩溃 → 自动恢复
```

### 工作流配置管理
```yaml
# workflows/txt2img/config.yaml
parameters:
  prompt:
    node_id: "6"
    input_key: "text"
    type: "string"
  
  resolution:
    width:
      node_id: "5" 
      input_key: "width"
      default: 1024
```

### 图片-提示词关联
```json
{
  "task_id": "abc123",
  "prompt": "wide shot of forest cabin, medieval style",
  "output_files": ["task_abc123_1234567890.png"],
  "prompt_elements": {
    "camera_angle": "wide shot",
    "subject": "forest cabin", 
    "style": "medieval"
  }
}
```

---

## 📈 开发优先级

### Phase 1: 核心功能 (第1周)
- 清理现有测试文件
- 重构ComfyUI客户端 (基于final_automation.py)
- 开发提示词生成器
- 集成基础批量处理

### Phase 2: 高级功能 (第2周)  
- 工作流配置系统
- 结果数据管理
- 任务监控增强

### Phase 3: 用户界面 (第3周)
- HTML画廊开发
- 图片筛选功能
- 数据分析引擎

---

## 🎯 成功指标

### 功能指标
- [x] 单批次处理 100+ 任务
- [ ] 任务成功率 > 95%
- [ ] 支持 3+ 工作流类型
- [ ] HTML画廊响应速度 < 2秒

### 用户体验
- [ ] 一键批量生成
- [ ] 直观的结果筛选
- [ ] 有效的优化建议
- [ ] 详细的进度反馈

---

## 🔄 迭代记录

### v0.1 - 概念验证 (2025-09-08)
- ComfyUI API连接成功
- 5任务批量测试通过
- 基础自动化流程验证

### v0.2 - 架构设计 (2025-09-08)
- 完整系统架构设计
- 开发计划制定
- 技术方案确定

### v1.0 - 计划发布 (预计 3周后)
- 完整功能实现
- 用户界面完成
- 文档和测试完善

---

## 🧠 设计决策记录

### ComfyUI启动策略
**问题**: 是否需要每次自动启动ComfyUI？  
**决策**: 提供多种模式 (auto/manual/check_only)  
**理由**: 灵活性，避免重复启动开销

### 任务完成检测
**问题**: 如何可靠检测慢速任务完成？  
**决策**: 多重检测 + 动态间隔 + 异常恢复  
**理由**: 稳健性优先，避免程序崩溃

### 工作流配置
**问题**: 新工作流如何快速集成？  
**决策**: 独立配置文件 + 参数映射  
**理由**: 可扩展性，便于维护

### 图片提示词关联
**问题**: 如何追踪图片对应的提示词？  
**决策**: 数据库 + JSON元数据 + HTML画廊  
**理由**: 多重保障，便于分析和查看

---

## 📞 备注信息

### 环境信息
- **ComfyUI路径**: D:/LM/ComfyUI
- **Python环境**: ComfyUI专用venv
- **显卡**: NVIDIA GeForce RTX 5090 (32GB VRAM)
- **系统**: Windows + MINGW64

### 重要文件
- `final_automation.py`: 当前最稳定可用版本
- `txt2img.json`: 验证可用的API工作流  
- API URL: http://127.0.0.1:8188

### 下次开发重点
1. 清理测试文件，建立规范目录结构
2. 基于final_automation.py重构客户端模块
3. 开发提示词组合生成器
4. 建立配置管理系统

---

*文档最后更新: 2025-09-08*  
*下次更新时间: 开发Phase 1完成后*