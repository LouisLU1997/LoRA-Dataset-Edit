# DataTag Studio

**中文** | [English](#english)

---

<img src="static/logo.png" alt="DataTag Studio" height="28">

---

## 简介

DataTag Studio 是一款本地运行的图像数据集管理与 Tag 标注工具，专为 AI 训练数据整理而设计。支持**标注模式**与**配对模式**双主界面，单图 / 双图 / 三图并排浏览，气泡式 Tag 编辑，WD14 与 Qwen3.5 双模型 AI 自动打标，以及完整的项目管理系统。

---

## 更新日志

### v5.0

**配对模式（全新功能）**
- 工具栏新增「✏ 标注 / 🔗 配对」主模式切换，整体 UI 随之切换
- 配对模式界面：选择 A、B 两个来源文件夹，图片以缩略图网格展示
- 点击 A 侧图片选中（蓝框高亮）→ 点击 B 侧图片完成配对，已配对图片显示角标
- 双击缩略图全屏放大预览（按 Esc 关闭）
- 中间配对列表显示所有已配对组，可单独删除
- 「▶ 执行配对」一键将所有配对图片转换为 PNG，写入项目输入图 / 结果图目录；执行后自动切回标注模式并刷新
- 支持读取任意图片格式（jpg / png / webp / bmp / tiff / avif / gif 等）

**反向 Tag 筛选**
- 左侧 Tag 搜索栏新增「非」切换按钮
- 正向（默认）：前缀匹配，显示含该 Tag 的图片
- 反向（「非」激活，红色）：精确匹配，显示**不含**该 Tag 的图片
- 右侧全局 Tags 面板状态栏区分显示「筛选：xxx」（蓝）与「排除：xxx」（红）

**多选批量加 Tag**
- 多选图片后，右侧全局 Tags 面板的「＋」按钮直接将该 Tag 写入所有选中项
- 同时，多选状态下输入框回车也会批量写入所有选中项

**AI 标注修复**
- 「已有TXT」选项（跳过 / 追加 / 覆盖）现在真正生效
- 跳过：已有内容的 txt 直接跳过，日志显示 ⏭
- 追加：新 tag 合并到已有 tag，不重复
- 覆盖：完全替换旧内容

### v4.0
- **项目管理系统**：保存目录、模式与标签分类配置，启动自动恢复上次项目
- **应用更名**：DataTag Studio
- **界面重组**：模式切换移至左侧文件列表顶部；筛选按钮按需显示；全局 Tag 交互优化（单击筛选，悬停 ＋ 添加）
- **Toast 提示**：轻量操作反馈

### v3.1
- **数据标签系统**：自定义分类标签，环形图统计，数字键 1–9 快速打标，`_labels.json` 持久化

### v3.0
- **交换参考图**、**批量重命名**（前缀序号 / 查找替换）、Ctrl+R 快捷键

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

安装时必须勾选 **"Add Python to PATH"**。

### 第二步：下载并解压

```
DataTag_Studio/
  ├── main_web.py           主程序
  ├── caption_service.py    AI 打标后台服务
  ├── run.bat               启动脚本
  ├── static/
  │   ├── index.html        前端界面
  │   ├── app_icon.ico      网页图标
  │   └── logo.png          Logo
  └── README.md
```

### 第三步：启动

双击 `run.bat`，首次自动安装依赖，浏览器自动打开 `http://localhost:7788`。

---

## 使用方法

### 标注模式（默认）

#### 基本操作

1. 点击工具栏 **📂 输入图 / 📂 结果图** 选择数据集目录
2. 左侧列表点击切换图片，↑↓ 键盘导航
3. 底部缩略图栏横向滚动预览，点击跳转
4. Tag 区域点击气泡删除，输入框添加新 Tag，Ctrl+S 保存

#### 显示模式

| 模式 | 说明 |
|------|------|
| 单图 | 仅显示结果图 |
| 双图 | 输入图 + 结果图并排 |
| 三图 | 输入图 + 参考图 + 结果图并排 |

#### 项目管理

1. 点击标题旁 **📂 打开项目** 进入项目管理弹窗
2. 输入名称，点击 **＋ 创建项目** 保存当前目录配置
3. 启动时自动恢复上次打开的项目

#### Tag 筛选

- 左侧 Tag 搜索框输入前缀 → 正向筛选（含该 Tag 的图）
- 点「**非**」按钮（变红）→ 反向筛选（不含该 Tag 的图）
- 右侧全局 Tags 面板：单击行筛选，悬停点「＋」添加到当前图

#### 多选批量操作

- **Shift+点击** / **Ctrl+点击** 多选图片
- 多选状态下点右侧全局 Tags 的「＋」→ 该 Tag 写入所有选中项
- 多选状态下输入框回车 → 批量写入所有选中项

#### AI 打标

1. 点击 **🤖 AI 标注** 打开面板
2. 选择「已有TXT」处理方式：**跳过 / 追加 / 覆盖**
3. 点 **🔧 启动服务**，选择模型，**▶ 标注当前图** 或 **⚡ 批量标注**

| 模型 | 输出 | 大小 | 适用场景 |
|------|------|------|----------|
| WD14 v3 | Tag | ~400MB | 快速打标，Danbooru 风格 |
| Qwen3.5-4B | 自然语言 | ~8GB | 详细描述，支持自定义 Prompt |

#### 对齐裁切

输入图与结果图分辨率不一致时出现 **✂ 对齐裁切** 按钮，自动等比缩放后中心裁切。批量处理见右侧面板。

#### 数据标签与统计

1. **⚙ 管理** → 新建分类标签（如"规则"/"不规则"），设置颜色
2. 点击标签按钮打标，数字键 1–9 快速操作
3. **📊 统计** → 查看环形分布图，点击图例按分类筛选

### 配对模式

点击工具栏 **🔗 配对** 切换到配对界面：

1. 选择 **A 来源**文件夹和 **B 来源**文件夹
2. 设置输出**组名前缀**和**起始序号**（如 `group_001`）
3. 点击左侧（A）图片选中（蓝框）→ 点击右侧（B）图片完成配对
4. 双击任意缩略图可全屏预览，点击已配对图片可取消配对
5. 左侧配对列表实时显示所有已配对组，可单独删除
6. 点击 **▶ 执行配对** → 所有图片转 PNG，写入项目目录

---

## 快捷键

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

**Q：Qwen 打标速度极慢？**
Qwen3.5-4B 需要 NVIDIA 显卡（CUDA），CPU 运行极慢，建议改用 WD14。

**Q：配对执行后图片在哪里？**
默认写入当前项目的输入图 / 结果图目录；未设置项目目录时写入来源文件夹的上级目录（`paired_input` / `paired_result`）。

---

## License

MIT

---

<a name="english"></a>

[中文](#datatag-studio) | **English**

---

## Introduction

DataTag Studio is a local image dataset management and tag annotation tool designed for AI training data preparation. It features two main UI modes — **Annotation Mode** and **Pairing Mode** — along with single/dual/triple panel browsing, bubble-style tag editing, WD14 and Qwen3.5 AI auto-captioning, and a full project management system.

---

## Changelog

### v5.0

**Pairing Mode (New)**
- New toolbar toggle: **✏ Annotate / 🔗 Pair** switches the entire UI
- Select folder A and folder B; images shown as thumbnail grids
- Click an A-side image to select (blue border) → click a B-side image to pair; paired images show a badge
- Double-click any thumbnail to view full-size (Esc to close)
- Left panel shows the pair list in real time; individual pairs can be removed
- **▶ Execute** converts all paired images to PNG and writes them to the project's input/result directories; auto-refreshes and returns to Annotation Mode
- Supports any image format (jpg / png / webp / bmp / tiff / avif / gif, etc.)

**Negative Tag Filter**
- New **"非" (NOT)** toggle button in the tag search bar
- Normal mode: prefix match — shows images that contain the tag
- Negative mode (red): exact match — shows images that **do not** contain the tag
- Right panel filter chip shows blue "筛选" (filter) or red "排除" (exclude) accordingly

**Multi-select Batch Tag Add**
- With multiple images selected, clicking **＋** in the global tags panel adds the tag to all selected items instantly
- Pressing Enter in the tag input box also batch-writes to all selected items

**AI Captioning Fix**
- "Existing TXT" options (Skip / Append / Overwrite) now actually work
- Skip: images with existing content are skipped (⏭ in log)
- Append: new tags are merged without duplicates
- Overwrite: existing content is fully replaced

### v4.0
- **Project Management**: save directory configs and auto-restore on startup; renamed to DataTag Studio
- **UI Reorganization**: mode toggle moved to left panel; filter buttons shown only when issues exist; global tag interaction redesigned
- **Toast Notifications**: lightweight operation feedback

### v3.1
- **Data Label System**: custom image classification labels, ring chart statistics, number key shortcuts, `_labels.json` persistence

### v3.0
- **Swap Reference Images**, **Batch Rename** (prefix+number / find-replace), **Ctrl+R shortcut**

### v2.0
- **Rename**, **Refresh**, **Copy Groups**, thumbnail performance

### v1.0
- Initial release: dual/triple panel, bubble tag editor, WD14 + Qwen3.5 AI captioning, align & crop, batch operations

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

Download Python 3.11 from https://www.python.org/downloads/ — check **"Add Python to PATH"**.

### Step 2: Extract

```
DataTag_Studio/
  ├── main_web.py
  ├── caption_service.py
  ├── run.bat
  ├── static/
  │   ├── index.html
  │   ├── app_icon.ico
  │   └── logo.png
  └── README.md
```

### Step 3: Launch

Double-click `run.bat`. Dependencies install automatically on first run, then `http://localhost:7788` opens in your browser.

---

## Usage

### Annotation Mode (Default)

1. Click **📂 Input / 📂 Result** to select dataset folders
2. Click items in the left list; use ↑↓ to navigate
3. Scroll the thumbnail strip horizontally; click to jump
4. Click a tag bubble to delete; type in the input box to add; Ctrl+S to save

#### Tag Filtering

- Type in the left search box → positive prefix filter
- Click **"非"** (turns red) → negative exact filter (images without the tag)
- Right panel global tags: single-click to filter; hover and click **＋** to add

#### Multi-select

- **Shift+click** / **Ctrl+click** to select multiple images
- With multiple selected: click **＋** in global tags panel → adds tag to all selected
- With multiple selected: press Enter in tag input → batch-writes to all selected

#### AI Captioning

1. Click **🤖 AI Caption**, choose **Skip / Append / Overwrite** for existing TXT files
2. Click **🔧 Start Service**, select a model, then caption current or batch

### Pairing Mode

Click **🔗 配对** in the toolbar:

1. Select **Folder A** and **Folder B**
2. Set output **prefix** and **start number**
3. Click an A-side image (blue border) → click a B-side image to pair
4. Double-click any thumbnail for full-size preview
5. Click a paired image to unpair; remove items from the pair list on the left
6. Click **▶ Execute** to convert all pairs to PNG and write to project directories

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| ↑ / ↓ or ← / → | Previous / Next image |
| Ctrl+S | Save tags |
| Ctrl+R | Rename current group |
| Del | Delete current group |
| 1–9 | Quick-assign label |
| Esc | Close zoom / modal |

---

## FAQ

**Q: run.bat closes immediately?**
Python not installed or PATH not set. Run `python --version` in a terminal.

**Q: AI captioning times out?**
App auto-switches to hf-mirror.com. Use a proxy if it keeps failing.

**Q: Qwen is extremely slow?**
Qwen3.5-4B requires an NVIDIA GPU. Use WD14 on CPU-only machines.

**Q: Where do paired images go?**
By default, into the current project's input/result directories. If no project directories are set, they go to `paired_input` / `paired_result` folders next to the source folders.

---

## License

MIT
