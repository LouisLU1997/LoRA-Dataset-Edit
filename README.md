# LoRA 数据集标注查看器

**中文** | [English](#english)

---

<img src="logo.png" alt="Louis LU" height="28">

---

## 简介

用于 LoRA 训练数据集的图片管理、Tag 编辑与 AI 自动打标工具。支持单图 / 双图 / 三图并排浏览，气泡式 Tag 编辑，WD14 与 Qwen3.5 双模型 AI 打标，以及输入图与结果图的自动对齐裁切。

## 系统要求

| 项目 | 要求 |
|------|------|
| 操作系统 | Windows 10 / 11 |
| Python | **3.10 或 3.11**（推荐 3.11，不支持 3.13） |
| 显卡 | NVIDIA（Qwen AI 打标需要 CUDA；WD14 仅 CPU 亦可运行）|

## 安装步骤

### 第一步：安装 Python

前往 https://www.python.org/downloads/ 下载 Python 3.11。

安装时必须勾选 **"Add Python to PATH"**，否则程序无法启动。

### 第二步：下载并解压

将压缩包解压到任意文件夹，目录结构如下：

```
LoRA_Viewer/
  ├── lora_reviewer.py      主程序
  ├── caption_service.py    AI 打标后台服务
  ├── run.bat               启动脚本
  ├── logo.png              Logo 图片
  └── README.md
```

### 第三步：启动程序

双击 `run.bat`，首次启动会自动安装基础依赖（`pillow`、`send2trash`），完成后主界面自动打开。

## 使用方法

### 基本操作

1. 点击工具栏 **📂 输入图 / 📂 结果图** 选择数据集目录
2. 左侧列表点击切换图片，支持键盘 ↑↓ 导航
3. 底部缩略图栏可横向滚动预览，点击跳转
4. 下方 Tag 区域点击气泡删除，输入框添加新 Tag，Ctrl+S 保存

### 显示模式

| 模式 | 说明 |
|------|------|
| 单图 | 仅显示结果图 |
| 双图 | 输入图 + 结果图并排 |
| 三图 | 输入图 + 参考图 + 结果图并排 |

### 筛选功能

- **缺输入 / 缺结果 / 缺TXT / 分辨率异 / 缺参考图**：快速定位问题文件
- **Tag 搜索框**：按 Tag 内容过滤图片列表
- **全局 Tags 面板**（右侧）：单击 Tag 直接添加到当前图，双击按 Tag 筛选图片

### AI 打标

首次使用需要安装 AI 依赖：

1. 点击右上角 **🤖 AI 标注** 打开面板
2. 点击 **🔧 一键安装全部依赖**（需联网，PyTorch 约 2.5GB）
3. 安装完成后重新打开 AI 面板，选择模型开始标注

| 模型 | 输出格式 | 大小 | 适用场景 |
|------|----------|------|----------|
| WD14 v3 | Tag | ~400MB | 快速打标，Danbooru 风格 |
| Qwen3.5-4B | 自然语言 | ~8GB | 详细描述，支持中文自定义 Prompt |

> 模型首次使用自动下载，国内网络自动切换 hf-mirror.com 镜像

### 对齐裁切

当输入图与结果图分辨率不一致时，分辨率提示栏会出现 **✂ 对齐裁切** 按钮：

- **近似尺寸**（如 1930×1130 vs 1920×1080）：等比缩小后中心裁切至较小尺寸
- **整数倍关系**（如 3840×2160 vs 1920×1088）：先按倍数缩小，再中心裁切
- **批量处理**：右侧批量操作区 → **✂ 批量对齐裁切**，自动扫描并处理当前筛选范围内所有不一致的图对

### 批量操作

右侧面板底部，作用范围为当前筛选列表：

- **＋ 添加 Tag**：给所有筛选图片添加指定 Tag
- **－ 删除 Tag**：删除指定 Tag（有筛选 Tag 时直接删除）
- **⇄ 替换 Tag**：批量替换 Tag
- **✂ 批量对齐裁切**：批量处理分辨率不一致的图对

---

## 常见问题

**Q：双击 run.bat 闪退？**

Python 未安装，或安装时未勾选 Add Python to PATH。打开命令行输入 `python --version` 验证。

**Q：AI 打标一直转圈 / 连接超时？**

HuggingFace 国内访问不稳定，程序会自动切换 hf-mirror.com 镜像，等待片刻即可；若持续失败可挂代理。

**Q：WD14 报 onnxruntime 错误？**

点击 AI 面板内 **🔧 一键安装全部依赖** 重新安装。

**Q：Qwen 报 ImportError 或找不到模型类？**

需要最新版 transformers，点击 **🔧 一键安装全部依赖** 升级。

**Q：Qwen 打标速度极慢？**

Qwen3.5-4B 需要 NVIDIA 显卡（CUDA），纯 CPU 运行会非常慢，建议改用 WD14。

---

## License

MIT

---

<a name="english"></a>

[中文](#lora-数据集标注查看器) | **English**

---

## Introduction

A dataset management tool for LoRA training — browse images in single / dual / triple panel mode, edit tags with a bubble UI, run AI auto-captioning with WD14 or Qwen3.5-4B, and automatically align & crop mismatched input/result image pairs.

## Requirements

| Item | Requirement |
|------|-------------|
| OS | Windows 10 / 11 |
| Python | **3.10 or 3.11** (3.11 recommended; 3.13 not supported) |
| GPU | NVIDIA (required for Qwen AI captioning; WD14 works on CPU only) |

## Installation

### Step 1: Install Python

Download Python 3.11 from https://www.python.org/downloads/

During installation, make sure to check **"Add Python to PATH"**.

### Step 2: Download and Extract

Extract the archive to any folder. The structure should look like this:

```
LoRA_Viewer/
  ├── lora_reviewer.py      Main application
  ├── caption_service.py    AI captioning backend
  ├── run.bat               Launch script
  ├── logo.png              Logo image
  └── README.md
```

### Step 3: Launch

Double-click `run.bat`. On first launch, it will automatically install the required base dependencies (`pillow`, `send2trash`), then open the main window.

## Usage

### Basic Operations

1. Click **📂 Input / 📂 Result** in the toolbar to select your dataset folders
2. Click items in the left list to switch images; use ↑↓ keyboard navigation
3. The thumbnail bar at the bottom can be scrolled horizontally; click to jump
4. Click a tag bubble to delete it; type in the input box to add tags; Ctrl+S to save

### Display Modes

| Mode | Description |
|------|-------------|
| Single | Result image only |
| Dual | Input + Result side by side |
| Triple | Input + Reference + Result side by side |

### Filtering

- **Missing Input / Result / TXT / Resolution mismatch / Missing Reference**: quickly locate problem files
- **Tag search box**: filter the image list by tag content
- **Global Tags panel** (right side): single-click a tag to add it to the current image; double-click to filter by that tag

### AI Captioning

First-time setup requires installing AI dependencies:

1. Click **🤖 AI Caption** in the top-right to open the panel
2. Click **🔧 Install All Dependencies** (requires internet; PyTorch ~2.5GB)
3. Reopen the panel after installation, select a model, and start captioning

| Model | Output | Size | Use Case |
|-------|--------|------|----------|
| WD14 v3 | Tags | ~400MB | Fast tagging, Danbooru-style |
| Qwen3.5-4B | Natural language | ~8GB | Detailed descriptions, custom Chinese prompts |

> Models are downloaded automatically on first use. The hf-mirror.com mirror is used automatically for users in China.

### Align & Crop

When the input and result images have mismatched resolutions, an **✂ Align & Crop** button appears in the resolution bar:

- **Near-equal sizes** (e.g. 1930×1130 vs 1920×1080): proportionally scale down, then center-crop to the smaller size
- **Integer scale** (e.g. 3840×2160 vs 1920×1088): scale down by the integer factor first, then center-crop
- **Batch processing**: use **✂ Batch Align & Crop** in the right panel to process all mismatched pairs in the current filtered list

### Batch Operations

The right panel bottom section operates on the current filtered list:

- **＋ Add Tag**: add a tag to all filtered images
- **－ Remove Tag**: remove a specified tag
- **⇄ Replace Tag**: batch find and replace tags
- **✂ Batch Align & Crop**: process all resolution-mismatched image pairs at once

---

## FAQ

**Q: run.bat closes immediately after double-clicking?**

Python is not installed, or "Add Python to PATH" was not checked during installation. Open a terminal and run `python --version` to verify.

**Q: AI captioning keeps spinning / connection timeout?**

HuggingFace can be slow or unreachable in China. The app automatically switches to hf-mirror.com — wait a moment. If it keeps failing, try using a proxy.

**Q: WD14 shows an onnxruntime error?**

Click **🔧 Install All Dependencies** in the AI panel to reinstall.

**Q: Qwen shows ImportError or missing model class?**

The latest version of transformers is required. Click **🔧 Install All Dependencies** to upgrade.

**Q: Qwen captioning is extremely slow?**

Qwen3.5-4B requires an NVIDIA GPU with CUDA. Running on CPU only is very slow — use WD14 instead.

---

## License

MIT
