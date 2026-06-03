"""
DataTag Studio - Web 版 (FastAPI)
启动后在浏览器中打开 http://localhost:7788
功能与 lora_reviewer.py 完全一致，仅 UI 层换为 HTML/CSS/JS
"""

import asyncio
import io
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import webbrowser
from datetime import datetime
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, Response, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from PIL import Image

# ── 常量 ──────────────────────────────────────────────
IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff', '.avif'}
PORT = 7788

# ── 辅助：send2trash ──────────────────────────────────
try:
    import send2trash
    def _trash(path):
        send2trash.send2trash(str(path))
except ImportError:
    send2trash = None
    def _trash(path):
        os.remove(path)


# ══════════════════════════════════════════════════════
# 应用状态（业务逻辑，无 UI）
# ══════════════════════════════════════════════════════

class AppState:
    _LABEL_COLORS = [
        '#3dd68c', '#e05555', '#d4a84b', '#4b9fd4', '#a84bd4',
        '#d44b9f', '#4bd4c4', '#e07840', '#7a9f4b', '#c8a84b',
    ]

    def __init__(self):
        self.lock = threading.Lock()
        self.dirs: Dict[str, Optional[Path]] = {'input': None, 'ref': None, 'result': None}
        self.files: Dict[str, Dict[str, Path]] = {'input': {}, 'ref': {}, 'result': {}}
        self.txt_files: Dict[str, Path] = {}
        self.txt_content: Dict[str, str] = {}
        self.file_names: List[str] = []
        self.filtered: List[str] = []
        self.cur: int = -1
        self.filter_mode: str = 'all'
        self.tag_filter: Optional[str] = None
        self._tag_filter_neg: bool = False
        self._label_defs: List[dict] = []
        self._labels: Dict[str, str] = {}
        self._label_filter: Optional[str] = None
        self.mode: str = 'one'
        self._res_mismatch: set = set()
        self._thumb_cache: Dict[str, bytes] = {}  # "key:name" -> jpeg bytes

        # Pairing mode
        self._pair_folders: Dict[str, Optional[Path]] = {'a': None, 'b': None}

        # AI captioning
        self._cap_proc = None
        self._cap_msg_queue: queue.Queue = queue.Queue()
        self._cap_pending: Dict[str, Any] = {}
        self._cap_id: int = 0
        self._cap_ready: bool = False
        self._cap_model_loaded: bool = False
        self._cap_model: str = 'wd14'
        self._cap_log: List[dict] = []  # {msg, color}
        self._cap_status: str = ''
        self._cap_progress: float = 0.0
        self._cap_pending_task = None
        self._batch_stop: bool = False
        self._batch_queue: List = []
        self._batch_done: int = 0
        self._batch_total: int = 0

        # WebSocket clients for push updates
        self._ws_clients: List[WebSocket] = []
        self._loop = None  # set on first async call

    def load_project(self, proj: dict):
        """Load directories/mode/labels from a project dict. Returns snapshot after loading."""
        with self.lock:
            # Reset
            self.dirs = {'input': None, 'ref': None, 'result': None}
            self.files = {'input': {}, 'ref': {}, 'result': {}}
            self.txt_files = {}
            self.txt_content = {}
            self.file_names = []
            self.filtered = []
            self.cur = -1
            self.filter_mode = 'all'
            self.tag_filter = None
            self._tag_filter_neg = False
            self._label_filter = None
            self._res_mismatch = set()
            self._thumb_cache = {}
            self.mode = proj.get('mode', 'one')
            self._label_defs = proj.get('label_defs', [])
            self._labels = {}

        # Load each directory (outside lock since select_dir acquires lock internally)
        for key in ('input', 'ref', 'result'):
            path_str = (proj.get('dirs') or {}).get(key)
            if path_str:
                try:
                    self.select_dir(key, path_str)
                except Exception:
                    pass
        return self.snapshot()

    def _nkey(self, s: str):
        return [int(c) if c.isdigit() else c.lower() for c in re.split(r'(\d+)', s)]

    # ── 状态快照 ─────────────────────────────────────

    def snapshot(self) -> dict:
        cur_name = self.filtered[self.cur] if 0 <= self.cur < len(self.filtered) else None
        cur_tags = []
        if cur_name:
            content = self.txt_content.get(cur_name, '')
            cur_tags = [t.strip() for t in content.split(',') if t.strip()]

        inp, res, ref = self.files['input'], self.files['result'], self.files['ref']
        m = self.mode

        def item_status(name):
            hi = (name in inp) or (m == 'one')
            hr = name in res
            hf = (name in ref) or (m != 'three')
            ht = name in self.txt_files
            color = 'orange' if not hi or not hr or not hf else (
                'yellow' if name in self._res_mismatch else (
                '' if ht else 'dim_yellow'))
            icon = '⚠' if not hi or not hr or not hf else ('○' if not ht else '●')
            label = self._labels.get(name)
            label_color = None
            if label:
                for d in self._label_defs:
                    if d['name'] == label:
                        label_color = d.get('color')
                        break
            return {'name': name, 'icon': icon, 'color': color,
                    'label': label, 'label_color': label_color,
                    'has_input': name in inp, 'has_result': name in res,
                    'has_ref': name in ref, 'has_txt': name in self.txt_files}

        list_items = [item_status(n) for n in self.filtered]

        # Global tag counter
        tag_counter = Counter()
        for content in self.txt_content.values():
            for t in content.split(','):
                t = t.strip()
                if t:
                    tag_counter[t] += 1
        global_tags = sorted(tag_counter.items(), key=lambda x: -x[1])

        return {
            'mode': self.mode,
            'dirs': {k: str(v) if v else None for k, v in self.dirs.items()},
            'dir_counts': {k: len(v) for k, v in self.files.items()},
            'cur': self.cur,
            'cur_name': cur_name,
            'cur_tags': cur_tags,
            'cur_has_txt': cur_name in self.txt_files if cur_name else False,
            'total': len(self.file_names),
            'filtered_count': len(self.filtered),
            'filter_mode': self.filter_mode,
            'tag_filter': self.tag_filter,
            'tag_filter_neg': self._tag_filter_neg,
            'label_defs': self._label_defs,
            'labels': self._labels,
            'label_filter': self._label_filter,
            'list_items': list_items,
            'global_tags': global_tags[:300],  # limit for perf
            'stats': {
                'total': len(self.file_names),
                'no_input': sum(1 for n in self.file_names if n not in inp),
                'no_result': sum(1 for n in self.file_names if n not in res),
                'no_txt': sum(1 for n in self.file_names if n not in self.txt_files),
                'no_ref': sum(1 for n in self.file_names if n not in ref),
                'res_mismatch': len(self._res_mismatch),
                'displayed': len(self.filtered),
            },
            'res_mismatch_cur': cur_name in self._res_mismatch if cur_name else False,
            'has_ref_dir': bool(self.dirs.get('ref')),
            'has_result_dir': bool(self.dirs.get('result')),
            'cap_ready': self._cap_ready,
            'cap_model_loaded': self._cap_model_loaded,
            'cap_status': self._cap_status,
            'cap_progress': self._cap_progress,
            'cap_log': self._cap_log[-100:],  # last 100 entries
        }

    # ── 目录选择 ─────────────────────────────────────

    def select_dir(self, key: str, path_str: str):
        p = Path(path_str)
        if not p.exists() or not p.is_dir():
            raise ValueError(f'目录不存在：{path_str}')
        self.dirs[key] = p
        self.files[key] = {
            f.stem: f for f in p.iterdir()
            if f.is_file() and f.suffix.lower() in IMAGE_EXTS
        }
        if key == 'result':
            self.txt_files = {
                f.stem: f for f in p.iterdir()
                if f.is_file() and f.suffix.lower() == '.txt'
            }
            self.txt_content = {}
            for nm, fp in self.txt_files.items():
                try:
                    self.txt_content[nm] = fp.read_text(encoding='utf-8')
                except Exception:
                    self.txt_content[nm] = fp.read_text(encoding='gbk', errors='replace')
            self._load_labels_file()
        self._thumb_cache.clear()
        self._rebuild()

    def refresh_dirs(self):
        cur_name = self.filtered[self.cur] if 0 <= self.cur < len(self.filtered) else None
        for key in ('input', 'ref', 'result'):
            p = self.dirs[key]
            if not p or not p.exists():
                continue
            self.files[key] = {
                f.stem: f for f in p.iterdir()
                if f.is_file() and f.suffix.lower() in IMAGE_EXTS
            }
            if key == 'result':
                self.txt_files = {
                    f.stem: f for f in p.iterdir()
                    if f.is_file() and f.suffix.lower() == '.txt'
                }
                self.txt_content = {}
                for nm, fp in self.txt_files.items():
                    try:
                        self.txt_content[nm] = fp.read_text(encoding='utf-8')
                    except Exception:
                        self.txt_content[nm] = fp.read_text(encoding='gbk', errors='replace')
        self._thumb_cache.clear()
        self._load_labels_file()
        self._rebuild()
        if cur_name and cur_name in self.filtered:
            self.cur = self.filtered.index(cur_name)

    def _rebuild(self):
        names = set()
        for k in ('input', 'ref', 'result'):
            names |= set(self.files[k])
        self.file_names = sorted(names, key=self._nkey)
        self._apply(_keep_pos=False)

    def _apply(self, _keep_pos: bool = True):
        inp, res, ref = self.files['input'], self.files['result'], self.files['ref']
        m = self.filter_mode
        if   m == 'all':          base = list(self.file_names)
        elif m == 'no_input':     base = [n for n in self.file_names if n not in inp]
        elif m == 'no_result':    base = [n for n in self.file_names if n not in res]
        elif m == 'no_txt':       base = [n for n in self.file_names if n not in self.txt_files]
        elif m == 'res_mismatch': base = [n for n in self.file_names if n in self._res_mismatch]
        elif m == 'no_ref':       base = [n for n in self.file_names if n not in ref]
        else:                     base = list(self.file_names)

        if self.tag_filter:
            tf = self.tag_filter
            def _has_tag(n):
                tags = [t.strip().lower() for t in self.txt_content.get(n, '').split(',')]
                if self._tag_filter_neg:
                    # 反向：精确匹配，不含该 tag 的才留下
                    return tf not in tags
                else:
                    # 正向：前缀匹配，含该 tag（或以该字符串开头的 tag）的留下
                    return any(t.startswith(tf) for t in tags)
            base = [n for n in base if _has_tag(n)]
        if self._label_filter is not None:
            if self._label_filter == '__unlabeled__':
                base = [n for n in base if not self._labels.get(n)]
            else:
                base = [n for n in base if self._labels.get(n) == self._label_filter]

        old_name = self.filtered[self.cur] if _keep_pos and 0 <= self.cur < len(self.filtered) else None
        self.filtered = base
        if old_name and old_name in self.filtered:
            self.cur = self.filtered.index(old_name)
        elif self.filtered:
            self.cur = 0
        else:
            self.cur = -1

    # ── 标签文件 ─────────────────────────────────────

    def _labels_file(self) -> Optional[Path]:
        d = self.dirs.get('result')
        return (d / '_labels.json') if d else None

    def _load_labels_file(self):
        f = self._labels_file()
        self._labels = {}
        if f and f.exists():
            try:
                data = json.loads(f.read_text(encoding='utf-8'))
                self._label_defs = data.get('defs', self._label_defs)
                self._labels = data.get('labels', {})
            except Exception:
                pass

    def _save_labels_file(self):
        f = self._labels_file()
        if not f:
            return
        f.write_text(
            json.dumps({'defs': self._label_defs, 'labels': self._labels},
                       ensure_ascii=False, indent=2),
            encoding='utf-8')

    # ── Tag 操作 ──────────────────────────────────────

    def save_tags(self, name: str, tags: List[str]):
        save_dir = self.dirs['result'] or self.dirs['input']
        if not save_dir:
            raise ValueError('未选择结果图目录')
        content = ', '.join(tags)
        path = save_dir / (name + '.txt')
        path.write_text(content, encoding='utf-8')
        self.txt_files[name] = path
        self.txt_content[name] = content

    def batch_add_tag(self, tag_str: str) -> int:
        new_tags = [t.strip() for t in tag_str.split(',') if t.strip()]
        count = 0
        for name in self.filtered:
            tags = [t.strip() for t in self.txt_content.get(name, '').split(',') if t.strip()]
            changed = any(nt not in tags and (tags.append(nt) or True) for nt in new_tags)
            if changed:
                self.save_tags(name, tags); count += 1
        return count

    def batch_del_tag(self, tag_str: str) -> int:
        del_tags = [t.strip().lower() for t in tag_str.split(',') if t.strip()]
        count = 0
        for name in self.filtered:
            tags = [t.strip() for t in self.txt_content.get(name, '').split(',') if t.strip()]
            new = [t for t in tags if not any(d in t.lower() for d in del_tags)]
            if len(new) != len(tags):
                self.save_tags(name, new); count += 1
        return count

    def batch_replace_tag(self, old_tag: str, new_tag: str) -> int:
        count = 0
        for name in self.filtered:
            tags = [t.strip() for t in self.txt_content.get(name, '').split(',') if t.strip()]
            nt = [new_tag if t == old_tag else t for t in tags]
            if not new_tag:
                nt = [t for t in nt if t]
            if nt != tags:
                self.save_tags(name, nt); count += 1
        return count

    # ── 标签分类 ──────────────────────────────────────

    def set_label(self, names: List[str], label_name: str):
        all_same = all(self._labels.get(n) == label_name for n in names)
        for n in names:
            if all_same:
                self._labels.pop(n, None)
            else:
                self._labels[n] = label_name
        self._save_labels_file()

    def get_label_stats(self) -> dict:
        total = len(self.file_names)
        counts = {d['name']: 0 for d in self._label_defs}
        counts['__unlabeled__'] = 0
        for name in self.file_names:
            lbl = self._labels.get(name, '')
            if lbl in counts:
                counts[lbl] += 1
            else:
                counts['__unlabeled__'] += 1
        labeled = total - counts['__unlabeled__']
        pct_done = labeled / total * 100 if total else 0
        return {
            'total': total, 'labeled': labeled, 'pct_done': pct_done,
            'counts': counts, 'defs': self._label_defs,
        }

    # ── 文件操作 ──────────────────────────────────────

    def delete_item(self, name: str) -> list:
        to_del = []
        for key in ('input', 'ref', 'result'):
            p = self.files[key].get(name)
            if p and p.exists():
                to_del.append(p)
        if name in self.txt_files:
            tp = self.txt_files[name]
            if tp.exists():
                to_del.append(tp)
        errors = []
        for p in to_del:
            try:
                _trash(p)
            except Exception as e:
                errors.append(f'{p.name}: {e}')
        for key in ('input', 'ref', 'result'):
            self.files[key].pop(name, None)
        self.txt_files.pop(name, None)
        self.txt_content.pop(name, None)
        self._thumb_cache.pop(f'input:{name}', None)
        self._thumb_cache.pop(f'result:{name}', None)
        if name in self.file_names:
            self.file_names.remove(name)
        self._labels.pop(name, None)
        self._save_labels_file()
        self._res_mismatch.discard(name)
        self._apply()
        return errors

    def rename_item(self, old_name: str, new_name: str) -> list:
        if new_name in self.file_names:
            raise ValueError(f'"{new_name}" 已存在')
        errors = []
        for key in ('input', 'ref', 'result'):
            old_path = self.files[key].get(old_name)
            if old_path and old_path.exists():
                new_path = old_path.parent / (new_name + old_path.suffix)
                try:
                    old_path.rename(new_path)
                    self.files[key][new_name] = new_path
                except Exception as e:
                    errors.append(str(e))
                self.files[key].pop(old_name, None)
        old_txt = self.txt_files.get(old_name)
        if old_txt and old_txt.exists():
            new_txt = old_txt.parent / (new_name + '.txt')
            try:
                old_txt.rename(new_txt)
                self.txt_files[new_name] = new_txt
                self.txt_content[new_name] = self.txt_content.pop(old_name, '')
            except Exception as e:
                errors.append(str(e))
            self.txt_files.pop(old_name, None)
        elif old_name in self.txt_content:
            self.txt_content[new_name] = self.txt_content.pop(old_name)
        if old_name in self._labels:
            self._labels[new_name] = self._labels.pop(old_name)
            self._save_labels_file()
        self._thumb_cache.pop(f'input:{old_name}', None)
        self._thumb_cache.pop(f'result:{old_name}', None)
        self._res_mismatch.discard(old_name)
        if old_name in self.file_names:
            idx = self.file_names.index(old_name)
            self.file_names[idx] = new_name
        self._apply()
        return errors

    def batch_rename(self, old_names: List[str], new_names: List[str]) -> dict:
        existing = set(self.file_names)
        errors, skipped, done = [], [], 0
        tmp_map = {}
        for old, new in zip(old_names, new_names):
            if old == new:
                continue
            if new in existing and new != old:
                skipped.append(f'{old} → {new}（名称冲突）')
                continue
            tmp = '__brn_' + old
            for key in ('input', 'ref', 'result'):
                p = self.files[key].get(old)
                if p and p.exists():
                    try:
                        p.rename(p.parent / (tmp + p.suffix))
                    except Exception as e:
                        errors.append(str(e))
            tp = self.txt_files.get(old)
            if tp and tp.exists():
                try:
                    tp.rename(tp.parent / (tmp + '.txt'))
                except Exception as e:
                    errors.append(str(e))
            tmp_map[old] = (tmp, new)

        for old, (tmp, new) in tmp_map.items():
            for key in ('input', 'ref', 'result'):
                p = self.files[key].get(old)
                if p:
                    tmp_p = p.parent / (tmp + p.suffix)
                    new_p = p.parent / (new + p.suffix)
                    if tmp_p.exists():
                        try:
                            tmp_p.rename(new_p)
                            self.files[key][new] = new_p
                        except Exception as e:
                            errors.append(str(e))
                    self.files[key].pop(old, None)
            tp = self.txt_files.get(old)
            if tp:
                tmp_tp = tp.parent / (tmp + '.txt')
                new_tp = tp.parent / (new + '.txt')
                if tmp_tp.exists():
                    try:
                        tmp_tp.rename(new_tp)
                        self.txt_files[new] = new_tp
                        if old in self.txt_content:
                            self.txt_content[new] = self.txt_content.pop(old)
                    except Exception as e:
                        errors.append(str(e))
                self.txt_files.pop(old, None)
            for lst in (self.file_names, self.filtered):
                if old in lst:
                    lst[lst.index(old)] = new
            self._thumb_cache.pop(f'input:{old}', None)
            self._thumb_cache.pop(f'result:{old}', None)
            self._res_mismatch.discard(old)
            if old in self._labels:
                self._labels[new] = self._labels.pop(old)
            existing.add(new)
            done += 1
        if done:
            self._save_labels_file()
        self._apply()
        return {'done': done, 'skipped': skipped, 'errors': errors}

    def copy_groups(self, names: List[str], dst_str: str) -> dict:
        dst = Path(dst_str)
        ok, fail = 0, []
        for name in names:
            copied_any = False
            for key in ('input', 'ref', 'result'):
                src_path = self.files[key].get(name)
                if src_path and src_path.exists():
                    out_dir = dst / key
                    out_dir.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(src_path, out_dir / src_path.name)
                        copied_any = True
                    except Exception as e:
                        fail.append(f'{src_path.name}: {e}')
            txt_path = self.txt_files.get(name)
            if txt_path and txt_path.exists():
                out_dir = dst / 'result'
                out_dir.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(txt_path, out_dir / txt_path.name)
                    copied_any = True
                except Exception as e:
                    fail.append(str(e))
            if copied_any:
                ok += 1
        return {'ok': ok, 'fail': fail, 'dst': str(dst)}

    def swap_ref(self, name_a: str, name_b: str) -> str:
        ref_a = self.files['ref'].get(name_a)
        ref_b = self.files['ref'].get(name_b)
        if ref_a is None and ref_b is None:
            return 'both_none'
        ref_dir = self.dirs['ref']
        if ref_a and ref_b:
            tmp = ref_dir / ('__swap_tmp__' + ref_a.suffix)
            ref_a.rename(tmp)
            ref_b.rename(ref_dir / (name_a + ref_b.suffix))
            tmp.rename(ref_dir / (name_b + ref_a.suffix))
            self.files['ref'][name_a] = ref_dir / (name_a + ref_b.suffix)
            self.files['ref'][name_b] = ref_dir / (name_b + ref_a.suffix)
        elif ref_a:
            new_path = ref_dir / (name_b + ref_a.suffix)
            ref_a.rename(new_path)
            self.files['ref'].pop(name_a, None)
            self.files['ref'][name_b] = new_path
        else:
            new_path = ref_dir / (name_a + ref_b.suffix)
            ref_b.rename(new_path)
            self.files['ref'].pop(name_b, None)
            self.files['ref'][name_a] = new_path
        for n in (name_a, name_b):
            self._thumb_cache.pop(f'ref:{n}', None)
        return 'ok'

    @staticmethod
    def _do_align_crop(inp_path, res_path):
        inp_img = Image.open(inp_path)
        res_img = Image.open(res_path)
        iw, ih = inp_img.size
        rw, rh = res_img.size
        if iw == rw and ih == rh:
            return None

        def _scale_to_cover(big, bw, bh, sml_w, sml_h):
            ratio_w, ratio_h = bw / sml_w, bh / sml_h
            n = round((ratio_w + ratio_h) / 2)
            if n >= 2 and abs(ratio_w - n) / n < 0.06 and abs(ratio_h - n) / n < 0.06:
                return big.resize((bw // n, bh // n), Image.LANCZOS)
            scale = max(sml_w / bw, sml_h / bh)
            return big.resize((max(sml_w, round(bw * scale)), max(sml_h, round(bh * scale))), Image.LANCZOS)

        if iw >= rw and ih >= rh:
            inp_img = _scale_to_cover(inp_img, iw, ih, rw, rh)
        elif rw >= iw and rh >= ih:
            res_img = _scale_to_cover(res_img, rw, rh, iw, ih)
        iw, ih = inp_img.size; rw, rh = res_img.size
        tw, th = min(iw, rw), min(ih, rh)

        def _center_crop(img, tw, th):
            w, h = img.size
            x, y = (w - tw) // 2, (h - th) // 2
            return img.crop((x, y, x + tw, y + th))

        return _center_crop(inp_img, tw, th), _center_crop(res_img, tw, th), tw, th

    @staticmethod
    def _save_img(img, path):
        ext = path.suffix.lower()
        if ext in ('.jpg', '.jpeg'):
            if img.mode != 'RGB':
                img = img.convert('RGB')
            img.save(path, 'JPEG', quality=95, subsampling=0)
        elif ext == '.webp':
            img.save(path, 'WEBP', quality=95)
        else:
            img.save(path)

    def align_crop(self, name: str) -> dict:
        inp_path = self.files['input'].get(name)
        res_path = self.files['result'].get(name)
        if not inp_path or not res_path:
            raise ValueError('需要同时有输入图和结果图')
        result = self._do_align_crop(inp_path, res_path)
        if result is None:
            return {'status': 'already_same'}
        inp_crop, res_crop, tw, th = result
        self._save_img(inp_crop, inp_path)
        self._save_img(res_crop, res_path)
        self._thumb_cache.pop(f'input:{name}', None)
        self._thumb_cache.pop(f'result:{name}', None)
        self._res_mismatch.discard(name)
        return {'status': 'ok', 'w': tw, 'h': th}

    def batch_align_crop(self) -> dict:
        pairs = [(n, self.files['input'][n], self.files['result'][n])
                 for n in self.filtered
                 if n in self.files['input'] and n in self.files['result']]
        ok = err = skipped = 0
        for name, ip, rp in pairs:
            try:
                result = self._do_align_crop(ip, rp)
                if result:
                    ic, rc, tw, th = result
                    self._save_img(ic, ip)
                    self._save_img(rc, rp)
                    self._thumb_cache.pop(f'input:{name}', None)
                    self._thumb_cache.pop(f'result:{name}', None)
                    self._res_mismatch.discard(name)
                    ok += 1
                else:
                    skipped += 1
            except Exception:
                err += 1
        return {'ok': ok, 'err': err, 'skipped': skipped}

    # ── 图片服务 ──────────────────────────────────────

    def get_image_path(self, key: str, name: str) -> Optional[Path]:
        p = self.files[key].get(name)
        if p and p.exists():
            dir_path = self.dirs.get(key)
            if dir_path and p.parent.resolve() == dir_path.resolve():
                return p
        return None

    def get_thumb_bytes(self, key: str, name: str, size=(160, 100)) -> Optional[bytes]:
        cache_key = f'{key}:{name}'
        if cache_key in self._thumb_cache:
            return self._thumb_cache[cache_key]
        p = self.files[key].get(name)
        if not p or not p.exists():
            return None
        try:
            img = Image.open(p)
            img.thumbnail(size, Image.LANCZOS)
            buf = io.BytesIO()
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            img.save(buf, 'JPEG', quality=75)
            data = buf.getvalue()
            self._thumb_cache[cache_key] = data
            return data
        except Exception:
            return None

    # ── AI 标注 ───────────────────────────────────────

    def _cap_log_add(self, msg: str, color: str = ''):
        self._cap_log.append({'msg': msg, 'color': color})
        if len(self._cap_log) > 300:
            self._cap_log = self._cap_log[-200:]
        # Push WS update if loop is available
        if self._loop and not self._loop.is_closed():
            try:
                asyncio.run_coroutine_threadsafe(self._push_update(), self._loop)
            except Exception:
                pass

    def _find_python(self):
        if not getattr(sys, 'frozen', False):
            return sys.executable
        for candidate in ('python', 'python3'):
            import shutil as _sh
            found = _sh.which(candidate)
            if found:
                return found
        return None

    def cap_start_service(self):
        if self._cap_proc and self._cap_proc.poll() is None:
            self._cap_ready = True
            self._cap_status = '● 服务运行中'
            return
        base_dir = Path(__file__).parent
        service_path = base_dir / 'caption_service.py'
        if not service_path.exists():
            self._cap_log_add(f'找不到 caption_service.py，请将其放到：{base_dir}', 'red')
            self._cap_status = '● 找不到服务脚本'
            return
        python_exe = self._find_python()
        if not python_exe:
            self._cap_log_add('找不到 Python 解释器', 'red')
            return
        try:
            self._cap_proc = subprocess.Popen(
                [python_exe, str(service_path)],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT, text=True, bufsize=1,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0,
            )
            self._cap_ready = False
            self._cap_status = '● 正在启动...'
            threading.Thread(target=self._cap_reader_thread, daemon=True).start()
        except Exception as e:
            self._cap_log_add(f'启动失败: {e}', 'red')
            self._cap_status = '● 启动失败'

    def _cap_reader_thread(self):
        SKIP_PATTERNS = ('warnings.warn', 'UserWarning', 'FutureWarning',
                         'DeprecationWarning', 'is deprecated', 'Loading checkpoint')
        for line in self._cap_proc.stdout:
            line = line.strip()
            if not line or any(p in line for p in SKIP_PATTERNS):
                continue
            try:
                obj = json.loads(line)
                self._handle_cap_msg(obj)
            except Exception:
                if not any(p in line for p in SKIP_PATTERNS):
                    self._cap_log_add(line)
        self._handle_cap_msg({'type': 'proc_exit'})

    def _handle_cap_msg(self, obj: dict):
        t = obj.get('type')
        if t == 'ready':
            self._cap_ready = True
            self._cap_status = '● 服务就绪'
            self._cap_log_add('服务就绪 ✓', 'green')
        elif t == 'log':
            self._cap_log_add(obj.get('msg', ''))
        elif t == 'error':
            self._cap_log_add('⚠ ' + obj.get('msg', ''), 'red')
            self._cap_status = '● 出错'
        elif t == 'progress':
            self._cap_progress = obj.get('pct', 0) / 100.0
            self._cap_status = f'● {obj.get("msg", "")}'
        elif t == 'load_done':
            if obj.get('ok'):
                self._cap_model_loaded = True
                model = obj.get('model', '')
                self._cap_log_add(f'✓ {model} 就绪，可直接标注', 'green')
                self._cap_status = f'● {model} 就绪'
                self._cap_progress = 0
                if hasattr(self, '_cap_pending_task') and self._cap_pending_task:
                    name, cb = self._cap_pending_task
                    self._cap_pending_task = None
                    if name == '__batch__':
                        threading.Thread(target=self._caption_batch_real, daemon=True).start()
                    else:
                        self._do_caption_one(name, cb)
            else:
                self._cap_log_add(f'✗ 模型加载失败', 'red')
                self._cap_status = '● 加载失败'
                self._cap_pending_task = None
        elif t == 'caption_done':
            req_id = obj.get('id', '')
            result = obj.get('result', '')
            err_msg = obj.get('error', '')
            cb = self._cap_pending.pop(req_id, None)
            if cb:
                cb(result, err_msg)
        elif t == 'proc_exit':
            self._cap_ready = False
            self._cap_status = '● 服务已退出'
            self._cap_log_add('服务进程已退出')

    def _cap_send(self, obj: dict) -> bool:
        if not self._cap_proc or self._cap_proc.poll() is not None:
            return False
        try:
            self._cap_proc.stdin.write(json.dumps(obj, ensure_ascii=False) + '\n')
            self._cap_proc.stdin.flush()
            return True
        except Exception:
            return False

    def _do_caption_one(self, name: str, callback, img_path=None):
        if img_path is None:
            img_path = self.files['result'].get(name) or self.files['input'].get(name)
        if not img_path or not img_path.exists():
            callback('', '找不到图片文件')
            return
        self._cap_id += 1
        req_id = str(self._cap_id)
        self._cap_pending[req_id] = callback
        req_data = {
            'cmd': 'caption', 'id': req_id, 'path': str(img_path),
            'model': self._cap_model, 'mode': 'natural',
        }
        if not self._cap_send(req_data):
            self._cap_pending.pop(req_id, None)
            callback('', '服务未运行')

    def caption_current(self, name: str, model: str, overwrite: str = 'skip'):
        self._cap_model = model
        # skip：已有 txt 内容则直接跳过
        if overwrite == 'skip' and name in self.txt_files and self.txt_content.get(name, '').strip():
            self._cap_log_add(f'⏭ {name} 已有标注，跳过', 'yellow')
            return {'status': 'skipped'}
        if not self._cap_ready:
            self.cap_start_service()
            return {'status': 'starting'}
        if self._cap_model_loaded:
            result_holder = {'result': '', 'error': ''}
            event = threading.Event()

            def cb(result, err):
                result_holder['result'] = result
                result_holder['error'] = err
                event.set()

            self._do_caption_one(name, cb)
            event.wait(timeout=120)
            if result_holder['result']:
                new_tags = [t.strip() for t in result_holder['result'].split(',') if t.strip()]
                if overwrite == 'append':
                    existing = [t.strip() for t in self.txt_content.get(name, '').split(',') if t.strip()]
                    merged = existing + [t for t in new_tags if t not in existing]
                    self.save_tags(name, merged)
                    self._cap_log_add(f'✓ {name} 追加完成（+{len(new_tags)}）', 'green')
                    return {'status': 'ok', 'tags': merged}
                else:  # overwrite
                    self.save_tags(name, new_tags)
                    self._cap_log_add(f'✓ {name} 标注完成', 'green')
                    return {'status': 'ok', 'tags': new_tags}
            else:
                return {'status': 'error', 'msg': result_holder['error']}
        else:
            self._cap_send({'cmd': 'load', 'model': model})
            self._cap_pending_task = (name, lambda r, e: None)
            return {'status': 'loading'}

    async def _push_update(self):
        """Push state update to all WS clients"""
        dead = []
        for ws in self._ws_clients:
            try:
                await ws.send_json({'type': 'update'})
            except Exception:
                dead.append(ws)
        for ws in dead:
            self._ws_clients.remove(ws)


class ProjectManager:
    FILE = Path(__file__).parent / 'projects.json'

    def __init__(self):
        self._data = self._load()

    def _load(self):
        if self.FILE.exists():
            try:
                return json.loads(self.FILE.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {'last_id': None, 'projects': []}

    def _save_file(self):
        self.FILE.write_text(
            json.dumps(self._data, ensure_ascii=False, indent=2),
            encoding='utf-8'
        )

    def list_projects(self):
        return list(self._data['projects'])

    def get_last_id(self):
        return self._data.get('last_id')

    def create(self, name: str, note: str, dirs: dict, mode: str, label_defs: list):
        pid = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat(timespec='seconds')
        proj = {
            'id': pid, 'name': name, 'note': note,
            'dirs': dirs, 'mode': mode, 'label_defs': label_defs,
            'created_at': now, 'last_opened': now,
        }
        self._data['projects'].append(proj)
        self._data['last_id'] = pid
        self._save_file()
        return proj

    def open_project(self, pid: str):
        proj = self._find(pid)
        if not proj:
            raise ValueError(f'Project {pid} not found')
        proj['last_opened'] = datetime.now().isoformat(timespec='seconds')
        self._data['last_id'] = pid
        self._save_file()
        return proj

    def save_to_project(self, pid: str, dirs: dict, mode: str, label_defs: list):
        proj = self._find(pid)
        if not proj:
            raise ValueError(f'Project {pid} not found')
        proj['dirs'] = dirs
        proj['mode'] = mode
        proj['label_defs'] = label_defs
        proj['last_opened'] = datetime.now().isoformat(timespec='seconds')
        self._save_file()
        return proj

    def update_meta(self, pid: str, name: str = None, note: str = None):
        proj = self._find(pid)
        if not proj:
            raise ValueError(f'Project {pid} not found')
        if name is not None:
            proj['name'] = name
        if note is not None:
            proj['note'] = note
        self._save_file()
        return proj

    def delete(self, pid: str):
        projs = self._data['projects']
        idx = next((i for i, p in enumerate(projs) if p['id'] == pid), None)
        if idx is None:
            raise ValueError(f'Project {pid} not found')
        projs.pop(idx)
        if self._data.get('last_id') == pid:
            self._data['last_id'] = projs[-1]['id'] if projs else None
        self._save_file()

    def _find(self, pid: str):
        return next((p for p in self._data['projects'] if p['id'] == pid), None)


# ══════════════════════════════════════════════════════
# FastAPI 应用
# ══════════════════════════════════════════════════════

state = AppState()
proj_mgr = ProjectManager()
app = FastAPI(title='DataTag Studio')

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'], allow_methods=['*'], allow_headers=['*'],
)

# Static files
_static_dir = Path(__file__).parent / 'static'
_static_dir.mkdir(exist_ok=True)
app.mount('/static', StaticFiles(directory=str(_static_dir)), name='static')


# ── Pydantic 模型 ─────────────────────────────────────

class SelectDirReq(BaseModel):
    key: str
    path: str

class NavigateReq(BaseModel):
    to: Optional[int] = None
    delta: Optional[int] = None

class SaveTagsReq(BaseModel):
    name: str
    tags: List[str]

class FilterReq(BaseModel):
    mode: str

class TagFilterReq(BaseModel):
    tag: Optional[str] = None
    negative: bool = False

class LabelFilterReq(BaseModel):
    label: Optional[str] = None

class SetLabelReq(BaseModel):
    names: List[str]
    label: str

class LabelDefsReq(BaseModel):
    defs: List[dict]

class DeleteReq(BaseModel):
    name: str

class RenameReq(BaseModel):
    old_name: str
    new_name: str

class BatchRenameReq(BaseModel):
    old_names: List[str]
    new_names: List[str]

class BatchTagReq(BaseModel):
    tag: str

class BatchTagItemsReq(BaseModel):
    names: List[str]
    tags: List[str]

class BatchReplaceTagReq(BaseModel):
    old_tag: str
    new_tag: str

class CopyGroupsReq(BaseModel):
    names: List[str]
    dst: str

class SwapRefReq(BaseModel):
    name_a: str
    name_b: str

class AlignCropReq(BaseModel):
    name: str

class SetModeReq(BaseModel):
    mode: str

class CaptionReq(BaseModel):
    name: str
    model: str = 'wd14'
    overwrite: str = 'skip'  # 'skip' | 'append' | 'overwrite'

class TranslateReq(BaseModel):
    text: str

class CreateProjectReq(BaseModel):
    name: str
    note: str = ''
    dirs: dict = {}
    mode: str = 'one'
    label_defs: list = []

class SaveProjectReq(BaseModel):
    dirs: dict = {}
    mode: str = 'one'
    label_defs: list = []

class UpdateProjectReq(BaseModel):
    name: Optional[str] = None
    note: Optional[str] = None

class PairSetFolderReq(BaseModel):
    side: str   # 'a' or 'b'
    path: str

class PairItem(BaseModel):
    a: str      # filename in folder a
    b: str      # filename in folder b
    name: str   # output group name

class PairExecuteReq(BaseModel):
    pairs: List[PairItem]
    out_input: Optional[str] = None
    out_result: Optional[str] = None


# ── 路由 ─────────────────────────────────────────────

@app.get('/')
def index():
    return FileResponse(str(_static_dir / 'index.html'))


@app.get('/api/state')
async def get_state():
    if state._loop is None:
        state._loop = asyncio.get_event_loop()
    return state.snapshot()


@app.post('/api/select-dir')
def select_dir(req: SelectDirReq):
    try:
        state.select_dir(req.key, req.path)
        return state.snapshot()
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/refresh')
def refresh():
    state.refresh_dirs()
    return state.snapshot()


@app.post('/api/set-mode')
def set_mode(req: SetModeReq):
    state.mode = req.mode
    return state.snapshot()


@app.post('/api/navigate')
def navigate(req: NavigateReq):
    if req.to is not None:
        if 0 <= req.to < len(state.filtered):
            state.cur = req.to
    elif req.delta is not None:
        n = state.cur + req.delta
        if 0 <= n < len(state.filtered):
            state.cur = n
    return state.snapshot()


@app.post('/api/set-filter')
def set_filter(req: FilterReq):
    state.filter_mode = req.mode
    state._apply()
    return state.snapshot()


@app.post('/api/set-tag-filter')
def set_tag_filter(req: TagFilterReq):
    state.tag_filter = req.tag.strip().lower() if req.tag else None
    state._tag_filter_neg = req.negative
    state._apply()
    return state.snapshot()


@app.post('/api/set-label-filter')
def set_label_filter(req: LabelFilterReq):
    state._label_filter = req.label
    state._apply()
    return state.snapshot()


@app.post('/api/save-tags')
def save_tags(req: SaveTagsReq):
    try:
        state.save_tags(req.name, req.tags)
        return state.snapshot()
    except Exception as e:
        raise HTTPException(400, str(e))


@app.get('/api/image/{key}/{name}')
def serve_image(key: str, name: str):
    p = state.get_image_path(key, name)
    if not p:
        raise HTTPException(404, 'Image not found')
    return FileResponse(str(p))


@app.get('/api/thumb/{key}/{name}')
def serve_thumb(key: str, name: str):
    data = state.get_thumb_bytes(key, name)
    if not data:
        raise HTTPException(404, 'Thumb not found')
    return Response(content=data, media_type='image/jpeg')


@app.post('/api/set-label')
def set_label(req: SetLabelReq):
    state.set_label(req.names, req.label)
    return state.snapshot()


@app.post('/api/label-defs')
def update_label_defs(req: LabelDefsReq):
    state._label_defs = req.defs
    state._save_labels_file()
    return state.snapshot()


@app.get('/api/label-stats')
def label_stats():
    return state.get_label_stats()


@app.post('/api/delete')
def delete_item(req: DeleteReq):
    errors = state.delete_item(req.name)
    result = state.snapshot()
    result['errors'] = errors
    return result


@app.post('/api/rename')
def rename_item(req: RenameReq):
    try:
        errors = state.rename_item(req.old_name, req.new_name)
        result = state.snapshot()
        result['errors'] = errors
        return result
    except ValueError as e:
        raise HTTPException(400, str(e))


@app.post('/api/batch-rename')
def batch_rename(req: BatchRenameReq):
    result = state.batch_rename(req.old_names, req.new_names)
    snap = state.snapshot()
    snap['batch_result'] = result
    return snap


@app.post('/api/copy-groups')
def copy_groups(req: CopyGroupsReq):
    try:
        result = state.copy_groups(req.names, req.dst)
        return result
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/swap-ref')
def swap_ref(req: SwapRefReq):
    try:
        status = state.swap_ref(req.name_a, req.name_b)
        return {'status': status, **state.snapshot()}
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/align-crop')
def align_crop(req: AlignCropReq):
    try:
        result = state.align_crop(req.name)
        snap = state.snapshot()
        snap['align_result'] = result
        return snap
    except Exception as e:
        raise HTTPException(400, str(e))


@app.post('/api/batch-align-crop')
def batch_align_crop():
    result = state.batch_align_crop()
    snap = state.snapshot()
    snap['batch_result'] = result
    return snap


@app.post('/api/batch-add-tag')
def batch_add_tag(req: BatchTagReq):
    count = state.batch_add_tag(req.tag)
    snap = state.snapshot()
    snap['count'] = count
    return snap


@app.post('/api/add-tags-to-items')
def add_tags_to_items(req: BatchTagItemsReq):
    """给指定的一批图片追加 tags（去重）"""
    count = 0
    for name in req.names:
        existing = [t.strip() for t in state.txt_content.get(name, '').split(',') if t.strip()]
        changed = False
        for tag in req.tags:
            if tag and tag not in existing:
                existing.append(tag)
                changed = True
        if changed:
            state.save_tags(name, existing)
            count += 1
    snap = state.snapshot()
    snap['count'] = count
    return snap


@app.post('/api/batch-del-tag')
def batch_del_tag(req: BatchTagReq):
    count = state.batch_del_tag(req.tag)
    snap = state.snapshot()
    snap['count'] = count
    return snap


@app.post('/api/batch-replace-tag')
def batch_replace_tag(req: BatchReplaceTagReq):
    count = state.batch_replace_tag(req.old_tag, req.new_tag)
    snap = state.snapshot()
    snap['count'] = count
    return snap


@app.get('/api/projects')
def list_projects():
    projs = proj_mgr.list_projects()
    last_id = proj_mgr.get_last_id()
    return {'projects': projs, 'last_id': last_id}


@app.post('/api/projects')
def create_project(req: CreateProjectReq):
    proj = proj_mgr.create(req.name, req.note, req.dirs, req.mode, req.label_defs)
    snap = state.load_project(proj)
    snap['project'] = proj
    return snap


@app.post('/api/projects/{pid}/open')
def open_project(pid: str):
    try:
        proj = proj_mgr.open_project(pid)
        snap = state.load_project(proj)
        snap['project'] = proj
        return snap
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post('/api/projects/{pid}/save')
def save_project(pid: str, req: SaveProjectReq):
    try:
        proj = proj_mgr.save_to_project(pid, req.dirs, req.mode, req.label_defs)
        return {'ok': True, 'project': proj}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.patch('/api/projects/{pid}')
def update_project(pid: str, req: UpdateProjectReq):
    try:
        proj = proj_mgr.update_meta(pid, req.name, req.note)
        return {'ok': True, 'project': proj}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.delete('/api/projects/{pid}')
def delete_project(pid: str):
    try:
        proj_mgr.delete(pid)
        projs = proj_mgr.list_projects()
        return {'ok': True, 'projects': projs, 'last_id': proj_mgr.get_last_id()}
    except ValueError as e:
        raise HTTPException(404, str(e))


@app.post('/api/translate')
async def translate_text(req: TranslateReq):
    import urllib.request, urllib.parse
    url = ('https://translate.googleapis.com/translate_a/single'
           '?client=gtx&sl=auto&tl=zh-CN&dt=t&q=' + urllib.parse.quote(req.text))
    try:
        r = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(r, timeout=15) as resp:
            data = json.loads(resp.read())
        result = ''.join(item[0] for item in data[0] if item[0])
        return {'result': result}
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post('/api/caption/start')
def cap_start():
    state.cap_start_service()
    return {'status': 'ok'}


@app.post('/api/caption/run')
def cap_run(req: CaptionReq):
    result = state.caption_current(req.name, req.model, req.overwrite)
    snap = state.snapshot()
    snap['caption_result'] = result
    return snap


@app.post('/api/caption/load-model')
def cap_load_model(req: CaptionReq):
    state._cap_model = req.model
    state._cap_send({'cmd': 'load', 'model': req.model})
    return {'status': 'loading'}


@app.post('/api/caption/stop')
def cap_stop():
    if hasattr(state, '_batch_stop'):
        state._batch_stop = True
        state._batch_queue = []
    state._cap_log_add('已停止', 'yellow')
    state._cap_status = '● 已停止'
    return {'status': 'ok'}


@app.get('/api/caption/log')
def cap_log():
    return {'log': state._cap_log[-100:], 'status': state._cap_status,
            'progress': state._cap_progress, 'ready': state._cap_ready,
            'model_loaded': state._cap_model_loaded}


@app.websocket('/ws')
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    state._ws_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if ws in state._ws_clients:
            state._ws_clients.remove(ws)


# ── 配对模式 ──────────────────────────────────────────

@app.get('/api/pair/image/{side}/{filename}')
def pair_image(side: str, filename: str):
    folder = state._pair_folders.get(side)
    if not folder:
        raise HTTPException(404, 'Folder not set')
    p = folder / filename
    if not p.exists() or p.parent.resolve() != folder.resolve():
        raise HTTPException(404, 'File not found')
    return FileResponse(str(p))


@app.post('/api/pair/set-folder')
def pair_set_folder(req: PairSetFolderReq):
    p = Path(req.path)
    if not p.exists() or not p.is_dir():
        raise HTTPException(400, f'目录不存在：{req.path}')
    state._pair_folders[req.side] = p
    files = sorted(
        [f.name for f in p.iterdir() if f.is_file() and f.suffix.lower() in IMAGE_EXTS],
        key=lambda x: state._nkey(x)
    )
    return {'files': files, 'path': str(p)}


@app.get('/api/pair/thumb/{side}/{filename}')
def pair_thumb(side: str, filename: str):
    folder = state._pair_folders.get(side)
    if not folder:
        raise HTTPException(404, 'Folder not set')
    p = folder / filename
    if not p.exists() or p.parent.resolve() != folder.resolve():
        raise HTTPException(404, 'File not found')
    try:
        img = Image.open(p)
        img.thumbnail((200, 140), Image.LANCZOS)
        buf = io.BytesIO()
        if img.mode not in ('RGB',):
            img = img.convert('RGB')
        img.save(buf, 'JPEG', quality=75)
        return Response(content=buf.getvalue(), media_type='image/jpeg')
    except Exception as e:
        raise HTTPException(500, str(e))


@app.post('/api/pair/execute')
def pair_execute(req: PairExecuteReq):
    folder_a = state._pair_folders.get('a')
    folder_b = state._pair_folders.get('b')
    if not folder_a or not folder_b:
        raise HTTPException(400, '请先设置两个文件夹')

    out_inp = Path(req.out_input) if req.out_input else (state.dirs.get('input') or folder_a.parent / 'paired_input')
    out_res = Path(req.out_result) if req.out_result else (state.dirs.get('result') or folder_b.parent / 'paired_result')
    out_inp.mkdir(parents=True, exist_ok=True)
    out_res.mkdir(parents=True, exist_ok=True)

    ok, errors = 0, []
    for pair in req.pairs:
        try:
            for src_dir, out_dir in [(folder_a / pair.a, out_inp / f'{pair.name}.png'),
                                      (folder_b / pair.b, out_res / f'{pair.name}.png')]:
                img = Image.open(src_dir)
                if img.mode == 'RGBA':
                    img.save(out_dir, 'PNG')
                else:
                    img.convert('RGB').save(out_dir, 'PNG')
            ok += 1
        except Exception as e:
            errors.append(f'{pair.name}: {e}')

    return {'ok': ok, 'errors': errors,
            'out_input': str(out_inp), 'out_result': str(out_res)}


# ── 浏览器目录选择（native dialog）─────────────────────

@app.get('/api/browse-dir')
def browse_dir():
    """在服务端弹出原生目录选择对话框（仅限本地运行）"""
    result = {'path': ''}
    event = threading.Event()

    def _dialog():
        try:
            import tkinter as tk
            from tkinter import filedialog
            root = tk.Tk()
            root.withdraw()
            root.wm_attributes('-topmost', True)
            p = filedialog.askdirectory(parent=root)
            root.destroy()
            result['path'] = p or ''
        except Exception:
            pass
        event.set()

    t = threading.Thread(target=_dialog, daemon=True)
    t.start()
    event.wait(timeout=60)
    return {'path': result['path']}


# ══════════════════════════════════════════════════════
# 启动
# ══════════════════════════════════════════════════════

def _open_browser():
    time.sleep(1.2)
    webbrowser.open(f'http://localhost:{PORT}')


if __name__ == '__main__':
    # Fix Windows console encoding so Chinese prints correctly
    if sys.platform == 'win32':
        try:
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
        except Exception:
            pass
        os.system('chcp 65001 >nul 2>&1')

    threading.Thread(target=_open_browser, daemon=True).start()
    print(f'DataTag Studio  http://localhost:{PORT}')
    uvicorn.run(app, host='0.0.0.0', port=PORT, log_level='warning')
