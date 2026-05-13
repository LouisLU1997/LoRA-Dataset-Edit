"""
caption_service.py — 全自动 AI 打标后台服务
启动后自动安装依赖、下载模型，然后等待主程序指令
通信协议: stdin/stdout JSON
"""

import sys, json, os, traceback, subprocess
from pathlib import Path

os.environ['TOKENIZERS_PARALLELISM'] = 'false'

# 模型统一存到脚本同目录 models/
BASE_DIR   = Path(__file__).parent.resolve()
MODELS_DIR = BASE_DIR / 'models'
MODELS_DIR.mkdir(exist_ok=True)

HF_DIR = MODELS_DIR / 'huggingface'
HF_DIR.mkdir(exist_ok=True)
os.environ['HF_HOME']               = str(HF_DIR)
os.environ['HUGGINGFACE_HUB_CACHE'] = str(HF_DIR / 'hub')
os.environ['TRANSFORMERS_CACHE']    = str(HF_DIR / 'hub')

# ── 通信 ─────────────────────────────────────────────────────────

def send(obj):
    try:
        print(json.dumps(obj, ensure_ascii=False), flush=True)
    except (UnicodeEncodeError, Exception):
        # fallback: 用 ASCII 安全模式
        print(json.dumps(obj, ensure_ascii=True), flush=True)

def log(msg, level='info'):
    send({'type': 'log', 'msg': str(msg), 'level': level})

def err(msg):
    send({'type': 'error', 'msg': str(msg)})

def progress(pct, msg=''):
    send({'type': 'progress', 'pct': pct, 'msg': msg})

# ── 自动安装依赖 ─────────────────────────────────────────────────

def pip_install(*packages, extra_index=None):
    cmd = [sys.executable, '-m', 'pip', 'install', '--quiet',
           '--disable-pip-version-check', *packages]
    if extra_index:
        cmd += ['--index-url', extra_index]
    log(f'安装: {" ".join(packages)}')
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(result.stderr[-500:] if result.stderr else '安装失败')

def ensure_deps_wd14():
    """确保 WD14 所需依赖已安装"""

    # 先检测 onnxruntime 是否能正常导入（不只是存在）
    def _ort_ok():
        try:
            import onnxruntime as _ort
            # 真正测试能用（触发 _ARRAY_API 错误）
            _ = _ort.get_available_providers()
            return True
        except Exception:
            return False

    if not _ort_ok():
        log('onnxruntime 不可用，尝试修复...')
        progress(5, '修复 onnxruntime...')
        # _ARRAY_API not found = numpy 版本冲突，先修复 numpy 再装 ort
        pip_install('numpy==1.26.4')
        # 卸载旧的 onnxruntime，装 GPU 版
        subprocess.run(
            [sys.executable, '-m', 'pip', 'uninstall', 'onnxruntime',
             'onnxruntime-gpu', '-y', '-q'],
            capture_output=True)
        pip_install('onnxruntime-gpu')
        log('重装完成，验证中...')

        # 用子进程验证（避免当前进程缓存了坏的模块）
        check = subprocess.run(
            [sys.executable, '-c',
             'import onnxruntime; onnxruntime.get_available_providers(); print("OK")'],
            capture_output=True, text=True)
        if check.returncode != 0 or 'OK' not in check.stdout:
            # GPU 版失败，退回 CPU 版
            log('GPU 版失败，改用 CPU 版 onnxruntime...')
            subprocess.run(
                [sys.executable, '-m', 'pip', 'uninstall', 'onnxruntime-gpu', '-y', '-q'],
                capture_output=True)
            pip_install('onnxruntime')
            check2 = subprocess.run(
                [sys.executable, '-c',
                 'import onnxruntime; print("OK")'],
                capture_output=True, text=True)
            if 'OK' not in check2.stdout:
                raise RuntimeError('无法安装 onnxruntime，请手动运行: pip install numpy==1.26.4 onnxruntime-gpu')
        log('onnxruntime 修复完成 OK')

    # 检查其他依赖
    other_missing = []
    try:
        import huggingface_hub
    except ImportError:
        other_missing.append('huggingface_hub')

    if other_missing:
        pip_install(*other_missing)

# ── WD14 ─────────────────────────────────────────────────────────

_wd14_session = None
_wd14_tags    = None
WD14_DIR = MODELS_DIR / 'wd14_v3'

def load_wd14():
    global _wd14_session, _wd14_tags
    if _wd14_session is not None:
        return

    ensure_deps_wd14()

    import onnxruntime as ort
    import huggingface_hub, csv

    WD14_DIR.mkdir(exist_ok=True)
    repo = 'SmilingWolf/wd-vit-tagger-v3'

    model_file = WD14_DIR / 'model.onnx'
    tags_file  = WD14_DIR / 'selected_tags.csv'

    if not model_file.exists():
        log('下载 WD14 v3 模型（约 400MB）...')
        progress(20, '下载 WD14 model.onnx...')
        huggingface_hub.hf_hub_download(
            repo, 'model.onnx', local_dir=str(WD14_DIR))
        log('model.onnx 下载完成，下载标签表...')
        progress(70, '下载 WD14 标签表...')
        huggingface_hub.hf_hub_download(
            repo, 'selected_tags.csv', local_dir=str(WD14_DIR))
        log('WD14 下载完成 OK')
    else:
        log('WD14 模型已存在，跳过下载')
    progress(85, '加载 WD14 模型...')

    with open(tags_file, newline='', encoding='utf-8') as f:
        _wd14_tags = [row['name'] for row in csv.DictReader(f)]

    providers = ['CUDAExecutionProvider', 'CPUExecutionProvider']
    _wd14_session = ort.InferenceSession(str(model_file), providers=providers)
    log('WD14 v3 加载完成 OK')

def run_wd14(image_path, threshold=0.35):
    import numpy as np
    from PIL import Image as PILImage

    img = PILImage.open(image_path).convert('RGB')
    img = img.resize((448, 448), PILImage.LANCZOS)
    arr = np.array(img, dtype=np.float32)[:, :, ::-1]
    arr = arr[None]  # batch dim

    inp  = _wd14_session.get_inputs()[0].name
    out  = _wd14_session.get_outputs()[0].name
    probs = _wd14_session.run([out], {inp: arr})[0][0]

    tags = [(t, float(p)) for t, p in zip(_wd14_tags, probs) if float(p) >= threshold]
    tags.sort(key=lambda x: -x[1])
    return ', '.join(t for t, _ in tags)

def _hf_download_with_progress(repo_id, cache_dir, desc='', target_gb=8.0):
    """
    下载模型，把 stdout/stderr 的 tqdm 进度实时转发到日志区。
    用子进程隔离，stdout 逐行读取。
    """
    import subprocess as _sp, threading, time, re

    log(f'开始下载 {desc}（约 {target_gb:.0f} GB）...')
    log(f'保存位置: {cache_dir}')
    log('提示：如果长时间卡在 0%，可能需要科学上网访问 HuggingFace')
    progress(20, '正在连接 HuggingFace...')

    # 用独立 Python 进程下载，这样 tqdm 输出到 stderr 我们能读到
    dl_script = f"""
import os, sys
os.environ['HF_HOME'] = r'{cache_dir.parent}'
os.environ['HUGGINGFACE_HUB_CACHE'] = r'{cache_dir}'
os.environ['TRANSFORMERS_CACHE'] = r'{cache_dir}'
os.environ['HF_ENDPOINT'] = 'https://hf-mirror.com'
# 禁用 xet 传输协议（与镜像站不兼容）
os.environ['HF_HUB_DISABLE_XET'] = '1'
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id='{repo_id}',
    cache_dir=r'{cache_dir}',
    ignore_patterns=['*.pt','flax_model*','tf_model*','rust_model*','onnx*','*.gguf'],
)
print('__DOWNLOAD_DONE__', flush=True)
"""

    proc = _sp.Popen(
        [sys.executable, '-c', dl_script],
        stdout=_sp.PIPE, stderr=_sp.PIPE,
        text=True, bufsize=1,
        creationflags=_sp.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
    )

    done = [False]
    success = [False]

    def _read_stderr():
        """读 stderr（tqdm进度条在这里）"""
        buf = ''
        for chunk in iter(lambda: proc.stderr.read(1), ''):
            if chunk in ('\r', '\n'):
                line = buf.strip()
                buf = ''
                if not line: continue
                # 解析 tqdm 进度行
                # 例: Fetching 17 files:  18%|██ | 3/17 [00:20<01:30, ...]
                m = re.search(r'(\d+)/(\d+)\s*\[(\d+:\d+)<', line)
                if m:
                    done_n, total_n = int(m.group(1)), int(m.group(2))
                    elapsed = m.group(3)
                    pct_files = done_n / total_n if total_n else 0
                    overall = int(20 + pct_files * 65)
                    msg = f'下载文件 {done_n}/{total_n}  已用时 {elapsed}'
                    progress(min(overall, 87), msg)
                    log(f'  {msg}')
                elif 'Downloading' in line or 'downloading' in line:
                    # 单文件下载进度: model.safetensors:  45%|... 1.2G/2.7G
                    m2 = re.search(r'([\d.]+[GMK]?)/([\d.]+[GMK]?)', line)
                    if m2:
                        log(f'  {line.split(":")[0].strip()}: {m2.group(1)}/{m2.group(2)}')
            else:
                buf += chunk

    def _read_stdout():
        for line in proc.stdout:
            line = line.strip()
            if line == '__DOWNLOAD_DONE__':
                success[0] = True
            elif line:
                log(f'  {line}')
        done[0] = True

    t_err = threading.Thread(target=_read_stderr, daemon=True)
    t_out = threading.Thread(target=_read_stdout, daemon=True)
    t_err.start()
    t_out.start()

    # 同时轮询目录大小作备用显示
    last_size = -1
    while not done[0]:
        time.sleep(4)
        try:
            total_bytes = sum(
                f.stat().st_size for f in Path(cache_dir).rglob('*') if f.is_file()
            )
            gb = total_bytes / 1024**3
            if total_bytes != last_size and total_bytes > 0:
                last_size = total_bytes
                log(f'  磁盘已写入: {gb:.2f} GB')
        except Exception:
            pass

    proc.wait()
    t_out.join(timeout=5)
    t_err.join(timeout=5)

    if proc.returncode != 0 or not success[0]:
        # 读取剩余 stderr
        try:
            remaining_err = proc.stderr.read() if proc.stderr else ''
            if remaining_err:
                log(f'子进程错误信息: {remaining_err[-800:]}')
        except Exception:
            pass
        # 检查是否是断点续传问题（文件已有部分）
        total_bytes = sum(f.stat().st_size for f in Path(cache_dir).rglob('*') if f.is_file())
        gb = total_bytes / 1024**3
        log(f'当前已下载: {gb:.2f} GB，尝试断点续传...')
        # 再试一次（snapshot_download 支持断点续传）
        try:
            from huggingface_hub import snapshot_download
            snapshot_download(
                repo_id=repo_id,
                cache_dir=str(cache_dir),
                ignore_patterns=['*.pt','flax_model*','tf_model*','rust_model*','onnx*','*.gguf'],
                resume_download=True,
                local_files_only=False,
            )
            log('断点续传完成 OK')
        except Exception as e2:
            raise RuntimeError(f'下载失败: {e2}')

    total_bytes = sum(f.stat().st_size for f in Path(cache_dir).rglob('*') if f.is_file())
    gb = total_bytes / 1024**3
    log(f'{desc} 下载完成 OK  共 {gb:.2f} GB')
    progress(88, f'下载完成 {gb:.2f} GB OK')


# ── Qwen2.5-VL ───────────────────────────────────────────────────

_qwen_model     = None
_qwen_processor = None
QWEN_MODEL_ID   = 'Qwen/Qwen3.5-4B'

QWEN_SYSTEM_PROMPT = (
    'You are an image captioning assistant. '
    'Always reply with ONLY the final caption — one short paragraph, plain English, no markdown, '
    'no bullet points, no analysis, no preamble like "The image shows" or "The user wants". '
    'Start the reply directly with the description.'
)

# 用户提供自定义 Prompt 时使用此 System Prompt，不强制语言和格式，让用户指令优先
QWEN_CUSTOM_SYSTEM_PROMPT = (
    'You are an image captioning assistant. '
    'The user specifies exactly what to describe. Treat it as a whitelist: '
    'ONLY describe what is explicitly requested. Everything not listed is excluded automatically. '
    'OUTPUT FORMAT: plain continuous text only. No markdown, no bold (**), no headers, '
    'no bullet points, no section labels of any kind. '
    'PRIORITY ALLOCATION (apply silently — never print these labels in output):\n'
    '  "主要" = ~65% of total length\n'
    '  "次要" = ~25% of total length\n'
    '  "简单提及"/"略提" = 1 sentence\n'
    'TERM DEFINITIONS:\n'
    '  "外貌" = face, hair, skin, clothing, accessories, body build — NOT actions or poses\n'
    '  "动作"/"姿态" = movements, gestures, limb positions\n'
    '  "站位" = position relative to objects or frame\n'
    '  "互动" = physical or visual relationship between person and object\n'
    'NEVER write:\n'
    '  - Anything not in the user\'s request (background, lighting, atmosphere, composition)\n'
    '  - Self-references: "根据要求", "所有描述均", "不涉及", "as instructed"\n'
    '  - Inference/symbolism: "仿佛", "好像", "暗示", "象征", "似乎", "体现", "营造", "呼应", "统一性"\n'
    '  - Closing summaries: "整幅图像", "整个场景", "总体来看", "综上"\n'
    '  - What you chose NOT to describe\n'
    'Stop immediately when all requested content is covered.'
)

QWEN_DEFAULT_PROMPT = (
    'Write a short caption for this image suitable for Stable Diffusion LoRA training. '
    'Describe the texture, material, lighting, and color in plain English. '
    'One paragraph, under 60 words.'
)

def ensure_deps_qwen():
    missing = []
    try:
        import torch
    except ImportError:
        missing.append('torch')
    if 'torch' in missing:
        log('安装 PyTorch CUDA 12.4...')
        pip_install('torch', 'torchvision',
                    extra_index='https://download.pytorch.org/whl/cu124')
    other = []
    for pkg, name in [('accelerate', 'accelerate'),
                      ('PIL', 'pillow')]:
        try:
            __import__(pkg)
        except ImportError:
            other.append(name)
    if other:
        pip_install(*other)
    # Qwen3.5 需要最新版 transformers + huggingface_hub
    try:
        from transformers import Qwen3_5ForConditionalGeneration  # noqa
    except (ImportError, Exception):
        log('升级 huggingface_hub 和 transformers（Qwen3.5 需要）...')
        pip_install('huggingface_hub', '--upgrade')
        pip_install('git+https://github.com/huggingface/transformers.git@main')
        log('✓ 依赖安装完成，请重新点击加载（首次安装需重启服务生效）')

def load_qwen():
    global _qwen_model, _qwen_processor
    if _qwen_model is not None:
        return

    ensure_deps_qwen()

    import torch
    from transformers import Qwen3_5ForConditionalGeneration, AutoProcessor

    qwen_cache = HF_DIR / 'hub'

    def _snap_has_config(cache_dir):
        model_slug = QWEN_MODEL_ID.replace('/', '--')
        snap_root = cache_dir / f'models--{model_slug}' / 'snapshots'
        if snap_root.exists():
            for snap in snap_root.iterdir():
                if snap.is_dir() and (snap / 'config.json').exists():
                    return True
        return False

    if not _snap_has_config(qwen_cache):
        log('下载 Qwen3.5-4B（约 8GB）...')
        _hf_download_with_progress(QWEN_MODEL_ID, qwen_cache, 'Qwen3.5-4B', target_gb=8.0)
    else:
        log('Qwen3.5-4B 已缓存，直接加载...')

    progress(88, '加载 Qwen Processor...')
    _qwen_processor = AutoProcessor.from_pretrained(
        QWEN_MODEL_ID,
        cache_dir=str(qwen_cache),
        use_fast=False,
        local_files_only=True,
    )

    progress(92, '加载 Qwen 模型权重...')
    import threading, time
    _loading_done = [False]
    def _heartbeat():
        secs = 0
        while not _loading_done[0]:
            time.sleep(5); secs += 5
            if not _loading_done[0]:
                log(f'  仍在加载中... 已等待 {secs} 秒')
    threading.Thread(target=_heartbeat, daemon=True).start()

    _qwen_model = Qwen3_5ForConditionalGeneration.from_pretrained(
        QWEN_MODEL_ID,
        torch_dtype=torch.bfloat16,
        device_map='auto',
        cache_dir=str(qwen_cache),
        local_files_only=True,
    )
    _loading_done[0] = True
    _qwen_model.eval()
    progress(100, 'Qwen3.5-4B 加载完成 OK')
    log('Qwen3.5-4B 加载完成 OK')

def run_qwen(image_path, prompt=None, max_new_tokens=512, thinking=False):
    import torch, re as _re
    from PIL import Image as PILImage

    is_custom = bool(prompt)
    if not prompt:
        prompt = QWEN_DEFAULT_PROMPT

    # 大图缩半后再送入模型，原文件不动
    pil_img = PILImage.open(image_path).convert('RGB')
    w, h = pil_img.size
    if w > 1920 or h > 1920:
        pil_img = pil_img.resize((w // 2, h // 2), PILImage.LANCZOS)
        log(f'大图缩半: {w}×{h} → {w//2}×{h//2}')
    image_input = pil_img

    # 将 system 指令拼入 user text（transformers 多模态不支持 system role + image 混用）
    # 用户自定义 Prompt 时使用中立 system prompt，避免 "plain English" 覆盖用户指令
    sys_prompt = QWEN_CUSTOM_SYSTEM_PROMPT if is_custom else QWEN_SYSTEM_PROMPT
    full_prompt = f'{sys_prompt}\n\n{prompt}'
    messages = [
        {'role': 'user', 'content': [
            {'type': 'image', 'image': image_input},
            {'type': 'text',  'text': full_prompt},
        ]}
    ]

    inputs = _qwen_processor.apply_chat_template(
        messages,
        tokenize=True,
        add_generation_prompt=True,
        return_dict=True,
        return_tensors='pt',
        enable_thinking=bool(thinking),
    )
    inputs = {k: v.to(_qwen_model.device) for k, v in inputs.items()}

    with torch.no_grad():
        out = _qwen_model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,
            repetition_penalty=1.1,
        )

    trimmed = [o[len(i):] for i, o in zip(inputs['input_ids'], out)]
    text = _qwen_processor.batch_decode(
        trimmed, skip_special_tokens=True,
        clean_up_tokenization_spaces=False)[0].strip()

    # 无论是否开启思考，<think>...</think> 内容不写入结果
    text = _re.sub(r'<think>.*?</think>', '', text, flags=_re.DOTALL).strip()
    return text


# ── 主循环 ────────────────────────────────────────────────────────

def handle_caption(req):
    path   = req.get('path', '')
    model  = req.get('model', 'wd14')
    mode   = req.get('mode', 'natural')
    req_id = req.get('id', '')

    if not path or not os.path.exists(path):
        send({'type': 'caption_done', 'id': req_id,
              'result': '', 'error': '文件不存在: ' + path})
        return

    try:
        parts = []

        if model == 'wd14':
            if _wd14_session is None:
                log('加载 WD14...')
                load_wd14()
            progress(50, f'WD14 打标中...')
            parts.append(run_wd14(path))

        if model == 'qwen':
            if _qwen_model is None:
                log('加载 Qwen2.5-VL...')
                load_qwen()
            progress(50, 'Qwen 生成描述...')
            custom_prompt = req.get('prompt', '')
            max_tokens    = int(req.get('max_tokens', 512))
            thinking      = req.get('thinking', True)
            parts.append(run_qwen(path, prompt=custom_prompt or None,
                                  max_new_tokens=max_tokens, thinking=thinking))

        result = ', '.join(p for p in parts if p)
        progress(100, '完成')
        send({'type': 'caption_done', 'id': req_id, 'result': result, 'error': ''})

    except Exception as e:
        send({'type': 'caption_done', 'id': req_id, 'result': '',
              'error': str(e) + '\n' + traceback.format_exc()})

def handle_load(req):
    model = req.get('model', 'wd14')
    try:
        progress(0, f'准备加载 {model}...')
        if model == 'wd14':
            load_wd14()
        if model == 'qwen':
            load_qwen()
        progress(100, '加载完成')
        send({'type': 'load_done', 'model': model, 'ok': True})
    except Exception as e:
        err(f'加载失败: {e}\n{traceback.format_exc()}')
        send({'type': 'load_done', 'model': model, 'ok': False})

def main():
    send({'type': 'ready'})
    log(f'服务启动，模型目录: {MODELS_DIR}')

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except Exception:
            continue

        cmd = req.get('cmd')
        if   cmd == 'ping':    send({'type': 'pong'})
        elif cmd == 'load':    handle_load(req)
        elif cmd == 'caption': handle_caption(req)
        elif cmd == 'quit':    break

if __name__ == '__main__':
    main()
