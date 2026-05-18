# LoRA 数据集标注查看器

**中文** | [English](#english)

---

<img src="logo.png" alt="Louis LU" height="28">

---

## 简介

用于 LoRA 训练数据集的图片管理、Tag 编辑与 AI 自动打标工具。支持单图 / 双图 / 三图并排浏览，气泡式 Tag 编辑，WD14 与 Qwen3.5 双模型 AI 打标，以及输入图与结果图的自动对齐裁切。

## 更新日志

### v3.0
- **交换参考图**：在三图模式下，可将 A 组与 B 组的参考图一键互换，弹窗同时预览两侧参考图，支持自由缩放，图片后台加载不卡 UI
- **批量重命名**：右侧批量操作区新增「✏ 批量重命名」，支持两种模式：
  - **前缀＋序号**：自定义前缀、起始序号、补零位数（如 `car_001`）
  - **查找／替换**：在文件名中查找并替换指定文字
  - 操作前实时预览新旧名称对比，冲突项自动标红并跳过
- **重命名快捷键**：单张重命名从工具栏按钮改为 **Ctrl+R**
- **窗口图标**：标题栏与任务栏显示自定义 L 图标
- **Bug 修复**：修复刷新后始终跳回第一张的问题（根因：Tag 搜索框防抖回调被意外触发）；修复双图模式下刷新按钮位置错乱；修复 Tag 气泡在窗口缩放时偶发 TclError

### v2.0
- **重命名**：可对单张图片（及所有关联文件）直接改名（Ctrl+R）
- **刷新目录**：一键重新扫描已选文件夹，新增 / 删除的文件即时同步，自动保持当前浏览位置
- **复制组**：支持单选或多选（Shift / Ctrl）图片组，一键复制到指定目录，自动按 `input / result / ref` 子目录结构存放
- **性能优化**：刷新时仅重载变化的缩略图，列表未变时跳过 widget 重建

### v1.0
- 初始版本：双图 / 三图模式、气泡 Tag 编辑、WD14 + Qwen3.5 AI 打标、对齐裁切、批量操作

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
  ├── logo.png              工具栏 Logo
  ├── small_logo.png        窗口图标
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

### 重命名（Ctrl+R）

按 **Ctrl+R** 弹出输入框，输入新文件名（不含扩展名），程序自动将该组的输入图、参考图、结果图、TXT 文件统一改名。

### 刷新目录

在外部对文件夹进行增删改操作后，点击工具栏 **🔄 刷新** 重新扫描，当前浏览位置保持不变。

### 复制图片组

在左侧列表单击选中，或 **Shift+点击** / **Ctrl+点击** 多选，点击工具栏 **📋 复制组**，选择目标目录后按以下结构复制：

```
目标目录/
  ├── input/    输入图
  ├── result/   结果图 + TXT 标注
  └── ref/      参考图（如有）
```

### 交换参考图

在三图模式下，点击工具栏 **⇄ 交换参考图**，弹窗左侧列出所有组，右侧实时预览当前组与目标组的参考图，确认后自动互换文件名。

### 批量重命名

右侧面板 → **✏ 批量重命名**，作用于当前筛选列表：

| 模式 | 说明 |
|------|------|
| 前缀＋序号 | 设前缀和起始序号，如 `car_` + `001` → `car_001`、`car_002`… |
| 查找／替换 | 在文件名中查找并替换指定文字，留空替换框即为删除 |

操作前可实时预览所有改名结果，冲突项红色标注自动跳过。

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
- **批量处理**：右侧批量操作区 → **✂ 批量对齐裁切**

### 批量操作

右侧面板底部，作用范围为当前筛选列表：

- **＋ 添加 Tag**：给所有筛选图片添加指定 Tag
- **－ 删除 Tag**：删除指定 Tag
- **⇄ 替换 Tag**：批量替换 Tag
- **✂ 批量对齐裁切**：批量处理分辨率不一致的图对
- **✏ 批量重命名**：批量修改文件名

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

## Changelog

### v3.0
- **Swap Reference Images**: In triple-panel mode, swap reference images between any two groups with one click. The dialog previews both sides simultaneously with scalable thumbnails; images load in the background without freezing the UI
- **Batch Rename**: New "✏ Batch Rename" in the right panel, with two modes:
  - **Prefix + Number**: Set a prefix, start index, and zero-padding (e.g. `car_001`)
  - **Find / Replace**: Find and replace text in filenames
  - Live preview of all old → new name pairs; conflicting entries are highlighted red and skipped automatically
- **Rename Shortcut**: Single-image rename is now **Ctrl+R** (toolbar button removed)
- **Window Icon**: Custom L icon in the title bar and taskbar
- **Bug Fixes**: Fixed refresh always jumping back to the first image (root cause: tag search debounce callback firing unexpectedly); fixed refresh button position in dual-panel mode; fixed occasional TclError in tag bubble panel during window resize

### v2.0
- **Rename**: Rename any image group (all associated files) in one step — Ctrl+R
- **Refresh**: Re-scan selected folders on demand; preserves current viewing position
- **Copy Groups**: Single or multi-select (Shift / Ctrl) and copy to a destination folder, auto-organized into `input / result / ref` subdirectories
- **Performance**: Thumbnail cache preserved on refresh; widget rebuild skipped when list is unchanged

### v1.0
- Initial release: dual / triple panel mode, bubble tag editor, WD14 + Qwen3.5 AI captioning, align & crop, batch operations

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

```
LoRA_Viewer/
  ├── lora_reviewer.py      Main application
  ├── caption_service.py    AI captioning backend
  ├── run.bat               Launch script
  ├── logo.png              Toolbar logo
  ├── small_logo.png        Window icon
  └── README.md
```

### Step 3: Launch

Double-click `run.bat`. On first launch it installs `pillow` and `send2trash` automatically, then opens the main window.

## Usage

### Basic Operations

1. Click **📂 Input / 📂 Result** in the toolbar to select dataset folders
2. Click items in the left list to switch images; use ↑↓ keyboard navigation
3. Scroll the thumbnail bar at the bottom horizontally; click to jump
4. Click a tag bubble to delete; type in the input box to add tags; Ctrl+S to save

### Display Modes

| Mode | Description |
|------|-------------|
| Single | Result image only |
| Dual | Input + Result side by side |
| Triple | Input + Reference + Result side by side |

### Filtering

- **Missing Input / Result / TXT / Resolution mismatch / Missing Reference**: quickly locate problem files
- **Tag search box**: filter the image list by tag content
- **Global Tags panel** (right side): single-click to add a tag to the current image; double-click to filter by that tag

### Rename (Ctrl+R)

Press **Ctrl+R** to rename the current group. All associated files (input, reference, result, TXT) are renamed together.

### Refresh

After making external changes to the folders, click **🔄 Refresh** to re-scan. Your current viewing position is preserved.

### Copy Groups

Single-click to select, or **Shift+click** / **Ctrl+click** to multi-select. Click **📋 Copy Groups** and choose a destination — files are copied into `input / result / ref` subdirectories automatically.

### Swap Reference Images

In triple-panel mode, click **⇄ Swap Ref** in the toolbar. The dialog lists all groups on the left and shows live previews on the right. Confirm to swap filenames between the two groups.

### Batch Rename

Right panel → **✏ Batch Rename** (operates on the current filtered list):

| Mode | Description |
|------|-------------|
| Prefix + Number | Custom prefix and start index, e.g. `car_` + `001` → `car_001`, `car_002`… |
| Find / Replace | Find and replace text in filenames; leave the replacement blank to delete |

A live preview shows all old → new name pairs before you confirm. Conflicting names are highlighted red and skipped.

### AI Captioning

1. Click **🤖 AI Caption** (top-right) to open the panel
2. Click **🔧 Install All Dependencies** (requires internet; PyTorch ~2.5 GB)
3. Reopen the panel, select a model, and start captioning

| Model | Output | Size | Use Case |
|-------|--------|------|----------|
| WD14 v3 | Tags | ~400 MB | Fast tagging, Danbooru-style |
| Qwen3.5-4B | Natural language | ~8 GB | Detailed descriptions, custom prompts |

### Align & Crop

When input and result resolutions differ, an **✂ Align & Crop** button appears:

- **Near-equal sizes**: scale down proportionally, then center-crop
- **Integer scale** (e.g. 4K vs 1080p): scale by integer factor, then center-crop
- **Batch**: right panel → **✂ Batch Align & Crop**

### Batch Operations

Right panel (operates on the current filtered list):

- **＋ Add Tag** / **－ Remove Tag** / **⇄ Replace Tag**
- **✂ Batch Align & Crop**
- **✏ Batch Rename**

---

## FAQ

**Q: run.bat closes immediately?**
Python is not installed or "Add Python to PATH" was not checked. Run `python --version` in a terminal to verify.

**Q: AI captioning times out?**
The app automatically switches to hf-mirror.com for users in China. If it keeps failing, try a proxy.

**Q: WD14 onnxruntime error?**
Click **🔧 Install All Dependencies** to reinstall.

**Q: Qwen ImportError or missing model class?**
Click **🔧 Install All Dependencies** to upgrade transformers.

**Q: Qwen is extremely slow?**
Qwen3.5-4B requires an NVIDIA GPU. Use WD14 on CPU-only machines.

---

## License

MIT
