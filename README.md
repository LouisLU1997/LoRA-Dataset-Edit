# DataTag Studio

**中文** | [English](#english)

---

<img src="static/logo.png" alt="DataTag Studio" height="28">

---

## 简介

DataTag Studio 是一款本地运行的图像数据集管理与 Tag 标注工具，专为 AI 训练数据整理而设计。支持单图 / 双图 / 三图并排浏览、气泡式 Tag 编辑、WD14 与 Qwen3.5 双模型 AI 自动打标，以及项目管理系统，让多个数据集的切换与配置一键恢复。

---

## 更新日志

### v4.0

- **项目管理系统**：新建项目时保存当前目录、显示模式与标签分类配置，下次启动自动恢复上次项目；支持多项目切换、保存、删除
- **应用更名**：`LoRA 数据集标注查看器` → `DataTag Studio`
- **界面重组**：
  - 模式切换（单图 / 双图 / 三图）从工具栏移至左侧文件列表顶部
  - 项目名称与「打开项目」按钮紧贴标题显示，旁边实时显示总组数
  - 筛选按钮（缺输入 / 缺结果 / 缺TXT 等）改为按需显示，无问题时自动隐藏
- **全局 Tag 交互优化**：单击行 = 按该 Tag 筛选；悬停出现「＋」按钮 = 添加到当前图，避免误操作
- **Tag 数量**：全局 Tag 列表中的数字改为黄色，更易区分
- **Toast 提示**：刷新、未选目录等操作均有底部轻提示反馈
- **移除批量替换 Tag**（功能冗余）
- **底部渐变**：文件列表底部 Logo 区与工具栏渐变风格保持一致

### v3.1
- **数据标签系统**：Tag 编辑区上方新增「🏷 标签」栏，可为每张图片打自定义分类标签，支持颜色自定义
  - **📊 统计**：弹出环形图，实时展示各标签数量与占比
  - **点击图例**：直接按标签筛选图片列表
  - **数字键 1–9**：快速为当前图片打标
  - **⚙ 管理**：增删标签类别，点击色块循环切换颜色
  - 标签数据保存在结果目录的 `_labels.json`，重命名 / 删除时自动同步

### v3.0
- **交换参考图**：三图模式下一键互换两组参考图，弹窗实时预览双侧
- **批量重命名**：前缀＋序号 / 查找替换两种模式，操作前实时预览，冲突自动跳过
- **重命名快捷键 Ctrl+R**

### v2.0
- **重命名**、**刷新目录**、**复制组**、缩略图性能优化

### v1.0
- 初始版本：双图 / 三图模式、气泡 Tag 编辑、WD14 + Qwen3.5 AI 打标、对齐裁切、批量操作

---

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | **3.10 或 3.11**（推荐 3.11，不支持 3.13） |
| 显卡 | NVIDIA（Qwen AI 打标需要 CUDA；WD14 仅 CPU 亦可运行）|

---

## 安装与启动

### 第一步：安装 Python

前往 https://www.python.org/downloads/ 下载 Python 3.11。

安装时必须勾选 **"Add Python to PATH"**，否则程序无法启动。

### 第二步：下载并解压

```
DataTag_Studio/
  ├── main_web.py           主程序（Web 版）
  ├── caption_service.py    AI 打标后台服务
  ├── run.bat               启动脚本
  ├── static/
  │   ├── index.html        前端界面
  │   ├── logo.ico          网页图标
  │   └── logo.png          Logo
  └── README.md
```

### 第三步：启动

双击 `run.bat`，首次启动自动安装基础依赖（`pillow`、`send2trash`、`fastapi`、`uvicorn`），完成后浏览器自动打开 `http://localhost:7788`。

---

## 使用方法

### 基本操作

1. 点击工具栏 **📂 输入图 / 📂 结果图** 选择数据集目录
2. 左侧列表点击切换图片，支持键盘 ↑↓ 导航
3. 底部缩略图栏横向滚动预览，点击跳转
4. Tag 区域点击气泡删除，输入框添加新 Tag，Ctrl+S 保存

### 显示模式

| 模式 | 说明 |
|------|------|
| 单图 | 仅显示结果图 |
| 双图 | 输入图 + 结果图并排 |
| 三图 | 输入图 + 参考图 + 结果图并排 |

### 项目管理

1. 点击标题旁 **📂 打开项目** 进入项目管理弹窗
2. 输入名称和备注，点击 **＋ 创建项目**，将当前目录配置保存为项目
3. 下次启动自动恢复上次打开的项目
4. 支持多项目切换、保存当前配置、删除

### 筛选功能

- 左侧顶部筛选按钮（有问题时自动出现）：缺输入 / 缺结果 / 缺TXT / 分辨率异 / 缺参考图
- **Tag 前缀搜索框**：按 Tag 内容过滤图片列表
- **全局 Tags 面板**（右侧）：单击行 = 按该 Tag 筛选；悬停点 **＋** = 添加到当前图

### 重命名（Ctrl+R）

按 Ctrl+R 弹出输入框，该组的输入图、参考图、结果图、TXT 文件统一改名。

### 复制图片组

Shift+点击 / Ctrl+点击 多选，点击工具栏 **📋 复制组**，文件按以下结构复制：

```
目标目录/
  ├── input/    输入图
  ├── result/   结果图 + TXT 标注
  └── ref/      参考图（如有）
```

### 交换参考图

三图模式下，点击工具栏 **⇄ 交换参考图**，弹窗左侧选目标组，右侧实时预览双侧参考图，确认后互换文件名。

### 批量重命名

右侧面板 → **✏ 批量重命名**，作用于当前筛选列表：

| 模式 | 说明 |
|------|------|
| 前缀＋序号 | 自定义前缀和起始序号，如 `car_` + `001` → `car_001`、`car_002`… |
| 查找／替换 | 在文件名中查找并替换，留空替换框即为删除 |

### AI 打标

1. 点击右上角 **🤖 AI 标注** 打开面板
2. 点击 **🔧 启动服务**
3. 选择模型，点击 **▶ 标注当前图** 或 **⚡ 批量标注**

| 模型 | 输出格式 | 大小 | 适用场景 |
|------|----------|------|----------|
| WD14 v3 | Tag | ~400MB | 快速打标，Danbooru 风格 |
| Qwen3.5-4B | 自然语言 | ~8GB | 详细描述，支持自定义 Prompt |

> 模型首次使用自动下载，国内网络自动切换 hf-mirror.com 镜像

### 对齐裁切

输入图与结果图分辨率不一致时，黄色提示栏出现 **✂ 对齐裁切** 按钮：

- **近似尺寸**：等比缩小后中心裁切
- **整数倍关系**（如 4K vs 1080p）：先按倍数缩小，再中心裁切
- **批量处理**：右侧面板 → **✂ 批量对齐裁切**

### 数据标签与统计

1. 点击 **⚙ 管理** 新建标签分类（如"规则"/"不规则"），点击色块切换颜色
2. 点击标签按钮打标，再次点击取消，**数字键 1–9** 快速打标
3. 点击 **📊 统计** 查看环形图，点击图例按分类筛选列表
4. 标签数据保存在结果目录的 `_labels.json`

### 快捷键

| 快捷键 | 功能 |
|--------|------|
| ↑ / ↓ 或 ← / → | 上一张 / 下一张 |
| Ctrl+S | 保存 Tag |
| Ctrl+R | 重命名当前图 |
| Del | 删除当前图 |
| 1–9 | 快速打标签分类 |
| Esc | 关闭放大图 / 弹窗 |

---

## 常见问题

**Q：双击 run.bat 闪退？**
Python 未安装或未勾选 Add Python to PATH。命令行输入 `python --version` 验证。

**Q：AI 打标连接超时？**
程序自动切换 hf-mirror.com 镜像，等待片刻；持续失败可挂代理。

**Q：WD14 报 onnxruntime 错误？**
重新运行 run.bat，依赖会自动修复。

**Q：Qwen 打标速度极慢？**
Qwen3.5-4B 需要 NVIDIA 显卡（CUDA），CPU 运行极慢，建议改用 WD14。

---

## License

MIT

---

<a name="english"></a>

[中文](#datatag-studio) | **English**

---

## Introduction

DataTag Studio is a local image dataset management and tag annotation tool designed for AI training data preparation. It supports single / dual / triple panel image browsing, bubble-style tag editing, WD14 and Qwen3.5 AI auto-captioning, and a project management system for instantly switching between dataset configurations.

---

## Changelog

### v4.0

- **Project Management**: Save directory settings, display mode, and label configs as a named project; auto-restores the last project on startup; supports multiple project switching, saving, and deletion
- **Renamed**: `LoRA Dataset Viewer` → `DataTag Studio`
- **UI Reorganization**:
  - Mode toggle (Single / Dual / Triple) moved from toolbar to top of the left file list panel
  - Project name and "Open Project" button placed beside the app title, with live total group count
  - Filter buttons (missing input / result / TXT etc.) now hidden when there are no issues
- **Global Tag Interaction**: Single-click row = filter by tag; hover shows "＋" button = add to current image
- **Tag Count Color**: Numbers in the global tag list are now yellow for better readability
- **Toast Notifications**: Lightweight bottom toasts for refresh, warnings, etc.
- **Removed Batch Replace Tag** (redundant)
- **Bottom Panel Gradient**: Matches the toolbar gradient style

### v3.1
- **Data Label System**: Custom image classification labels with color coding, statistics ring chart, number key shortcuts, and `_labels.json` persistence

### v3.0
- **Swap Reference Images**, **Batch Rename** (prefix+number / find-replace with live preview), **Ctrl+R shortcut**

### v2.0
- **Rename**, **Refresh**, **Copy Groups**, thumbnail performance improvements

### v1.0
- Initial release: dual/triple panel, bubble tag editor, WD14 + Qwen3.5 AI captioning, align & crop, batch ops

---

## Requirements

| Item | Requirement |
|------|-------------|
| OS | Windows 10 / 11 |
| Python | **3.10 or 3.11** (3.11 recommended; 3.13 not supported) |
| GPU | NVIDIA (required for Qwen; WD14 works on CPU) |

---

## Installation

### Step 1: Install Python

Download Python 3.11 from https://www.python.org/downloads/

Check **"Add Python to PATH"** during installation.

### Step 2: Extract

```
DataTag_Studio/
  ├── main_web.py           Main application
  ├── caption_service.py    AI captioning backend
  ├── run.bat               Launch script
  ├── static/
  │   ├── index.html        Frontend UI
  │   ├── logo.ico          Favicon
  │   └── logo.png          Logo
  └── README.md
```

### Step 3: Launch

Double-click `run.bat`. On first run it installs `pillow`, `send2trash`, `fastapi`, and `uvicorn` automatically, then opens `http://localhost:7788` in your browser.

---

## Usage

### Basic Operations

1. Click **📂 Input / 📂 Result** in the toolbar to select dataset folders
2. Click items in the left list; use ↑↓ for keyboard navigation
3. Scroll the thumbnail strip horizontally; click to jump
4. Click a tag bubble to delete; type in the input box to add; Ctrl+S to save

### Display Modes

| Mode | Description |
|------|-------------|
| Single | Result image only |
| Dual | Input + Result side by side |
| Triple | Input + Reference + Result side by side |

### Project Management

1. Click **📂 Open Project** beside the app title
2. Enter a name and note, click **＋ Create Project** to save the current directory config
3. The last project is automatically restored on next startup
4. Switch, save, or delete projects from the same dialog

### Filtering

- Filter buttons appear automatically when issues exist: Missing Input / Result / TXT / Resolution Mismatch / Missing Reference
- **Tag prefix search**: filter the image list by tag content
- **Global Tags panel** (right): single-click to filter; hover and click **＋** to add to the current image

### Rename (Ctrl+R)

Renames all files in a group (input, reference, result, TXT) simultaneously.

### AI Captioning

1. Click **🤖 AI Caption** (top-right)
2. Click **🔧 Start Service**
3. Choose a model and click **▶ Caption Current** or **⚡ Batch Caption**

| Model | Output | Size | Use Case |
|-------|--------|------|----------|
| WD14 v3 | Tags | ~400 MB | Fast, Danbooru-style |
| Qwen3.5-4B | Natural language | ~8 GB | Detailed descriptions, custom prompts |

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ↑ / ↓ or ← / → | Previous / Next image |
| Ctrl+S | Save tags |
| Ctrl+R | Rename current group |
| Del | Delete current group |
| 1–9 | Quick-assign label category |
| Esc | Close zoom / modal |

---

## FAQ

**Q: run.bat closes immediately?**
Python not installed or PATH not set. Run `python --version` in a terminal.

**Q: AI captioning times out?**
App auto-switches to hf-mirror.com. If it keeps failing, use a proxy.

**Q: Qwen is extremely slow?**
Qwen3.5-4B requires an NVIDIA GPU. Use WD14 on CPU-only machines.

---

## License

MIT
