"""Validate and export a video-script-director 1.0 package (Python 3.10+, stdlib).

This checks structure, text anchors and local files, not factual truth, audiovisual
quality, or whether an audio transcript really matches its media.
"""
from __future__ import annotations

import argparse
import copy
import json
import math
import os
from pathlib import Path
import re
import sys
import tempfile

OUTPUT_NAMES = ("口播稿.md", "拍摄导演表.md", "剪辑交接单.md", "素材清单.md", "edit-brief.json")
FORMAT = "video-script-director/edit-brief"
EPSILON = 1e-6
ASSET_KINDS = {"generated_image", "real_image", "screen_recording", "video", "diagram", "audio"}
ASSET_STATUSES = {"planned", "generated", "available", "needs_user_media", "failed"}
CLAIM_STATUSES = {"verified", "user_provided", "hypothetical", "needs_verification"}


def local_path(value, base):
    if not isinstance(value, str) or not value.strip():
        raise ValueError("需要非空本地文件路径")
    if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*://", value):
        raise ValueError("需要本地文件路径，不能填写 URL")
    path = Path(value).expanduser()
    return (path if path.is_absolute() else base / path).resolve()


class Checks:
    def __init__(self):
        self.errors = []
        self.warnings = []

    def error(self, path, message):
        self.errors.append(f"{path}: {message}")

    def obj(self, value, path):
        if not isinstance(value, dict):
            self.error(path, "必须是对象")
            return {}
        return value

    def array(self, value, path, nonempty=False):
        if not isinstance(value, list):
            self.error(path, "必须是列表")
            return []
        if nonempty and not value:
            self.error(path, "列表不能为空")
        return value

    def text(self, value, path, empty=False):
        if not isinstance(value, str) or (not empty and not value.strip()):
            self.error(path, "必须是文本" if empty else "必须是非空文本")
            return False
        return True

    def texts(self, value, path):
        items = self.array(value, path)
        for index, item in enumerate(items):
            self.text(item, f"{path}[{index}]")
        return items

    def number(self, value, path, minimum=0, positive=False, integer=False):
        try:
            valid = type(value) in (int, float) and math.isfinite(value)
        except OverflowError:
            valid = False
        valid = valid and (not integer or type(value) is int)
        valid = valid and (value > minimum if positive else value >= minimum)
        if not valid:
            bound = ">" if positive else ">="
            self.error(path, f"必须是有限{'整数' if integer else '数字'}，且 {bound} {minimum}")
        return valid

    def enum(self, value, path, choices):
        if not isinstance(value, str) or value not in choices:
            self.error(path, "必须是 " + "/".join(sorted(choices)))

    def fields(self, obj, path, fields, empty=()):
        for field in fields:
            self.text(obj.get(field), f"{path}.{field}", empty=field in empty)

    def file(self, value, path, base):
        try:
            resolved = local_path(value, base)
            if not resolved.is_file():
                self.error(path, f"本地文件不存在或不是文件：{resolved}")
        except (OSError, ValueError) as error:
            self.error(path, str(error))

    def anchor(self, speech, anchor, occurrence, path, silent=False):
        valid = self.number(occurrence, path + ".occurrence", minimum=1, integer=True)
        if silent:
            if anchor != "" or occurrence != 1:
                self.error(path, "无台词段必须用空 anchor、occurrence=1")
            return
        if not self.text(anchor, path + ".anchor") or not isinstance(speech, str):
            return
        count = speech.count(anchor)
        if count == 0:
            self.error(path, f"锚点未逐字出现在本段口播中：{anchor!r}")
        elif valid and occurrence > count:
            self.error(path, f"occurrence={occurrence} 超出锚点出现次数 {count}")


def _records(checks, plan, field, nonempty=False):
    rows = checks.array(plan.get(field), field, nonempty)
    result, ids = [], {}
    for index, row in enumerate(rows):
        label = f"{field}[{index}]"
        row = checks.obj(row, label)
        result.append(row)
        identifier = row.get("id")
        if checks.text(identifier, label + ".id"):
            if identifier in ids:
                checks.error(label + ".id", "ID 重复：" + identifier)
            ids[identifier] = row
    return result, ids


def _refs(checks, value, label, known):
    refs = checks.texts(value, label)
    seen = set()
    for ref in refs:
        if not isinstance(ref, str):
            continue
        if ref not in known:
            checks.error(label, "引用不存在：" + ref)
        if ref in seen:
            checks.error(label, "重复引用：" + ref)
        seen.add(ref)
    return [ref for ref in refs if isinstance(ref, str)]


def validate(plan, base_dir=None):
    """Return (errors, warnings); paths are relative to the input plan directory."""
    base = Path(base_dir or ".").resolve()
    c = Checks()
    plan = c.obj(plan, "plan")
    if plan.get("schema_version") != "1.0":
        c.error("schema_version", '必须是字符串 "1.0"')
    project = c.obj(plan.get("project"), "project")
    c.fields(project, "project", ("title", "topic", "angle", "audience", "platform", "aspect_ratio"))
    c.enum(project.get("mode"), "project.mode", {"rewrite", "topic", "integrate"})
    c.texts(project.get("assumptions"), "project.assumptions")
    target_valid = c.number(project.get("target_duration_s"), "project.target_duration_s", positive=True)
    ratio = project.get("aspect_ratio")
    if isinstance(ratio, str) and not re.fullmatch(r"[1-9]\d*:[1-9]\d*", ratio):
        c.error("project.aspect_ratio", "使用正整数比例，例如 9:16")
    timing = c.obj(plan.get("timing"), "timing")
    c.enum(timing.get("basis"), "timing.basis", {"estimated", "aligned"})
    rate_valid = c.number(timing.get("rate_cps"), "timing.rate_cps", positive=True)
    c.text(timing.get("note"), "timing.note")
    for field in ("source_media", "transcript_path"):
        if field not in timing:
            c.error("timing." + field, "字段必需，未拍摄时填 null")
        elif timing[field] is not None:
            c.text(timing[field], "timing." + field)
            try:
                local_path(timing[field], base)
            except (OSError, ValueError) as error:
                c.error("timing." + field, str(error))
        if timing.get("basis") == "aligned":
            c.file(timing.get(field), "timing." + field, base)
    direction = c.obj(plan.get("direction"), "direction")
    c.fields(direction, "direction", ("promise", "emotion_arc", "persona", "visual_style", "audio_style", "cover_title"))
    c.texts(direction.get("revision_notes"), "direction.revision_notes")
    segments, segment_ids = _records(c, plan, "segments", nonempty=True)
    fragments, fragment_ids = _records(c, plan, "fragments")
    claims, claim_ids = _records(c, plan, "claims")
    assets, asset_ids = _records(c, plan, "assets")

    for index, asset in enumerate(assets):
        label = f"assets[{index}]"
        c.enum(asset.get("kind"), label + ".kind", ASSET_KINDS)
        c.enum(asset.get("status"), label + ".status", ASSET_STATUSES)
        c.fields(asset, label, ("purpose", "source", "prompt", "negative", "aspect_ratio", "placement", "fallback", "alt"), empty=("prompt", "negative"))
        if asset.get("kind") in ("generated_image", "screen_recording"):
            c.text(asset.get("prompt"), label + ".prompt")
        if isinstance(asset.get("aspect_ratio"), str) and not re.fullmatch(r"[1-9]\d*:[1-9]\d*", asset["aspect_ratio"]):
            c.error(label + ".aspect_ratio", "使用正整数比例，例如 9:16")
        if "path" not in asset:
            c.error(label + ".path", "字段必需，未取得文件时填 null")
        elif asset["path"] is not None:
            try:
                local_path(asset["path"], base)
            except (OSError, ValueError) as error:
                c.error(label + ".path", str(error))
        if "delivery_state" in asset:
            c.enum(asset["delivery_state"], label + ".delivery_state", {"native_output_only"})
            c.text(asset.get("native_reference"), label + ".native_reference")
            if asset.get("status") != "planned" or asset.get("path") is not None:
                c.error(label, "native_output_only 必须用 status=planned、path=null；导出到本地后移除该状态")
        elif "native_reference" in asset:
            c.text(asset["native_reference"], label + ".native_reference")
        if asset.get("status") in ("generated", "available"):
            c.file(asset.get("path"), label + ".path", base)
        elif asset.get("delivery_state") == "native_output_only":
            c.warnings.append(f"素材 {asset.get('id', index)} 已生成原生附件，待导出到剪辑设备（{asset.get('native_reference', '')}）")
        elif asset.get("status") in ("planned", "needs_user_media", "failed"):
            c.warnings.append(f"素材 {asset.get('id', index)} 尚未就绪（{asset['status']}）")

    for index, claim in enumerate(claims):
        label = f"claims[{index}]"
        c.fields(claim, label, ("text", "source", "note"), empty=("source",))
        c.enum(claim.get("status"), label + ".status", CLAIM_STATUSES)
        if claim.get("status") == "verified":
            c.text(claim.get("source"), label + ".source")
        elif claim.get("status") == "needs_verification":
            c.warnings.append(f"事实 {claim.get('id', index)} 待核实：{claim.get('text', '')}")
        elif claim.get("status") == "user_provided":
            c.warnings.append(f"事实 {claim.get('id', index)} 由用户提供，尚未独立核实")

    previous_end, total, intensities, edit_ids = 0.0, None, [], set()
    segment_fragment_refs = {}
    for index, segment in enumerate(segments):
        label = f"segments[{index}]"
        start, end, speech = segment.get("start_s"), segment.get("end_s"), segment.get("speech")
        start_ok = c.number(start, label + ".start_s")
        end_ok = c.number(end, label + ".end_s", positive=True)
        duration = end - start if start_ok and end_ok else None
        if start_ok and previous_end is not None and abs(start - previous_end) > EPSILON:
            c.error(label + ".start_s", f"必须连续接在 {previous_end:g} 秒；不能有重叠或缺口")
        if duration is not None and duration <= 0:
            c.error(label + ".end_s", "必须大于 start_s")
        previous_end = end if end_ok else None
        total = previous_end
        c.text(speech, label + ".speech", empty=True)
        c.text(segment.get("purpose"), label + ".purpose")
        c.texts(segment.get("techniques"), label + ".techniques")
        performance = c.obj(segment.get("performance"), label + ".performance")
        c.fields(performance, label + ".performance", ("emotion", "pace", "face", "gesture"))
        intensity = performance.get("intensity")
        if c.number(intensity, label + ".performance.intensity", minimum=1, integer=True) and intensity > 5:
            c.error(label + ".performance.intensity", "不能超过 5")
        if isinstance(speech, str) and speech.strip():
            intensities.append(intensity)
        for item_index, emphasis in enumerate(c.texts(performance.get("emphasis"), label + ".performance.emphasis")):
            c.anchor(speech, emphasis, 1, f"{label}.performance.emphasis[{item_index}]")
        pause_sum = 0.0
        for pause_index, pause in enumerate(c.array(performance.get("pauses"), label + ".performance.pauses")):
            pause_label = f"{label}.performance.pauses[{pause_index}]"
            pause = c.obj(pause, pause_label)
            c.anchor(speech, pause.get("after"), pause.get("occurrence", 1), pause_label)
            if c.number(pause.get("seconds"), pause_label + ".seconds", positive=True):
                pause_sum += pause["seconds"]
        if duration is not None and pause_sum > duration + EPSILON:
            c.error(label + ".performance.pauses", "停顿总时长超过本段时长")
        camera = c.obj(segment.get("camera"), label + ".camera")
        c.enum(camera.get("visibility"), label + ".camera.visibility", {"露脸", "仅声音"})
        c.fields(camera, label + ".camera", ("framing", "action"))
        visual = c.obj(segment.get("visual"), label + ".visual")
        c.text(visual.get("description"), label + ".visual.description")
        _refs(c, visual.get("asset_ids"), label + ".visual.asset_ids", asset_ids)
        _refs(c, segment.get("claim_ids"), label + ".claim_ids", claim_ids)
        refs = _refs(c, segment.get("fragment_ids"), label + ".fragment_ids", fragment_ids)
        if isinstance(segment.get("id"), str):
            segment_fragment_refs[segment["id"]] = refs
        for edit_index, edit in enumerate(c.array(segment.get("edits"), label + ".edits")):
            edit_label = f"{label}.edits[{edit_index}]"
            edit = c.obj(edit, edit_label)
            c.fields(edit, edit_label, ("id", "intent", "visual", "sound", "voice"))
            if isinstance(edit.get("id"), str):
                if edit["id"] in edit_ids:
                    c.error(edit_label + ".id", "全片剪辑 ID 重复：" + edit["id"])
                edit_ids.add(edit["id"])
            c.anchor(speech, edit.get("anchor"), edit.get("occurrence"), edit_label, silent=speech == "")
            offset_ok = c.number(edit.get("offset_s"), edit_label + ".offset_s")
            length_ok = c.number(edit.get("duration_s"), edit_label + ".duration_s", positive=True)
            if duration is not None and offset_ok and length_ok and edit["offset_s"] + edit["duration_s"] > duration + EPSILON:
                c.error(edit_label, "效果起点加时长超过本段；跨段效果请拆分")
            c.enum(edit.get("priority"), edit_label + ".priority", {"must", "optional"})
        units = segment.get("read_units")
        if "read_units" in segment:
            units_valid = c.number(units, label + ".read_units", positive=bool(speech))
        else:
            units = sum(ch.isalnum() for ch in speech) if isinstance(speech, str) else 0
            units_valid = True
        if duration is not None and units_valid and duration > pause_sum and rate_valid:
            actual_rate = units / (duration - pause_sum)
            if actual_rate > max(6.0, timing["rate_cps"] * 1.35):
                c.warnings.append(f"段落 {segment.get('id', index)} 扣除停顿后的粗估语速 {actual_rate:.1f} 单位/秒偏快，请试读或压缩")
        elif duration is not None and units_valid and units > 0 and duration <= pause_sum:
            c.error(label, "本段停顿占满时长，没有留出口播时间")
    if intensities and all(value == 5 for value in intensities):
        c.error("segments.performance.intensity", "不能整条口播都是强度 5")
    if total is not None and target_valid and abs(total - project["target_duration_s"]) > max(3, project["target_duration_s"] * 0.1):
        c.warnings.append(f"规划总长 {total:g} 秒与目标 {project['target_duration_s']:g} 秒有明显偏差")

    for index, fragment in enumerate(fragments):
        label = f"fragments[{index}]"
        c.fields(fragment, label, ("text", "reason"))
        c.enum(fragment.get("policy"), label + ".policy", {"verbatim", "meaning"})
        disposition = fragment.get("disposition", "included")
        c.enum(disposition, label + ".disposition", {"included", "reserved"})
        refs = _refs(c, fragment.get("segment_ids"), label + ".segment_ids", segment_ids)
        if disposition == "reserved":
            if refs:
                c.error(label + ".segment_ids", "reserved 片段必须为空列表，不能引用段落")
            if any(fragment.get("id") in used for used in segment_fragment_refs.values()):
                c.error(label, "reserved 片段不得被任何段落引用")
            c.warnings.append(f"片段 {fragment.get('id', index)} 待处理，未纳入口播：{fragment.get('reason', '')}；保留要求尚未全部解决")
            continue
        if not refs:
            c.error(label + ".segment_ids", "必须引用至少一个段落")
        fragment_id = fragment.get("id")
        for ref in refs:
            if ref in segment_ids and fragment_id not in segment_fragment_refs.get(ref, []):
                c.error(label, f"与 {ref}.fragment_ids 未双向对应")
        if fragment.get("policy") == "verbatim" and isinstance(fragment.get("text"), str):
            if not any(isinstance(segment_ids.get(ref, {}).get("speech"), str) and fragment["text"] in segment_ids[ref]["speech"] for ref in refs):
                c.error(label, "verbatim 原句（含标点）未完整出现在任一所引用段落中")
    for segment_id, refs in segment_fragment_refs.items():
        for ref in refs:
            linked = fragment_ids.get(ref, {}).get("segment_ids", [])
            if ref in fragment_ids and (not isinstance(linked, list) or segment_id not in linked):
                c.error(f"segment {segment_id}.fragment_ids", f"与片段 {ref}.segment_ids 未双向对应")
    return c.errors, c.warnings


def normalize_paths(plan, base):
    result = copy.deepcopy(plan)
    for asset in result["assets"]:
        if asset["path"] is not None:
            asset["path"] = str(local_path(asset["path"], base))
    for key in ("source_media", "transcript_path"):
        if result["timing"][key] is not None:
            result["timing"][key] = str(local_path(result["timing"][key], base))
    return result


def cell(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br>")


def table(headers, rows):
    lines = ["| " + " | ".join(headers) + " |", "|" + "---|" * len(headers)]
    lines.extend("| " + " | ".join(cell(value) for value in row) + " |" for row in rows)
    return "\n".join(lines) + "\n"


def as_text(value):
    if value is None:
        return "未提供"
    if isinstance(value, list):
        return "；".join(as_text(item) for item in value) or "无"
    if isinstance(value, dict):
        return "；".join(f"{key}：{as_text(item)}" for key, item in value.items())
    return str(value)


def context(plan, warnings):
    p, t, d = plan["project"], plan["timing"], plan["direction"]
    rows = [("主题", p["topic"]), ("本期切口", p["angle"]), ("观众", p["audience"]),
            ("平台 / 画幅 / 模式", f"{p['platform']} / {p['aspect_ratio']} / {p['mode']}"),
            ("目标 / 规划总长", f"{p['target_duration_s']:g} / {plan['segments'][-1]['end_s']:g} 秒"),
            ("时间依据 / 估算语速", f"{t['basis']} / {t['rate_cps']:g} 单位每秒"),
            ("对齐说明", t["note"]), ("原片", as_text(t["source_media"])), ("转写", as_text(t["transcript_path"])),
            ("合理假设", as_text(p["assumptions"])), ("开头承诺", d["promise"]),
            ("整体情绪曲线", d["emotion_arc"]), ("表达状态", d["persona"]),
            ("画面风格", d["visual_style"]), ("声音风格", d["audio_style"]),
            ("封面文字", d["cover_title"]), ("改动说明", as_text(d["revision_notes"]))]
    result = table(["项目", "具体安排"], rows)
    result += "\n时间码为排练预估，剪辑前必须按真实录音重对齐。\n" if t["basis"] == "estimated" else "\n时间码标记为实录对齐；文件存在检查不能证明对齐正确，剪辑前仍需抽听核对。\n"
    if warnings:
        result += "\n待处理提醒：\n\n" + "\n".join("- " + warning for warning in warnings) + "\n"
    return result


def segment_rows(plan):
    assets = {asset["id"]: asset for asset in plan["assets"]}
    rows = []
    for s in plan["segments"]:
        p, camera = s["performance"], s["camera"]
        pauses = "；".join(f"“{pause['after']}”后第 {pause.get('occurrence', 1)} 次停 {pause['seconds']:g} 秒" for pause in p["pauses"]) or "无"
        performance = f"情绪：{p['emotion']}；强度：{p['intensity']}/5；语速：{p['pace']}；重音：{as_text(p['emphasis'])}；停顿：{pauses}；表情：{p['face']}；动作：{p['gesture']}"
        media = "；".join(f"{ref}（{asset_status(assets[ref])}）：{assets[ref]['path'] or assets[ref].get('native_reference') or '尚无文件'}" for ref in s["visual"]["asset_ids"]) or "无"
        purpose = f"用途：{s['purpose']}；方法：{as_text(s['techniques'])}；事实：{as_text(s['claim_ids'])}；保留句：{as_text(s['fragment_ids'])}"
        if "read_units" in s:
            purpose += f"；读音单位：{s['read_units']}"
        rows.append((f"{s['start_s']:g}–{s['end_s']:g} 秒 / {s['id']}", s["speech"] or "（静默，不口播）", purpose,
                     performance, f"{camera['visibility']}；{camera['framing']}；{camera['action']}", s["visual"]["description"] + "；素材：" + media))
    return rows


def edit_table(plan):
    rows = []
    for s in plan["segments"]:
        for e in s["edits"]:
            begin = s["start_s"] + e["offset_s"]
            rows.append((f"{s['id']} / {e['id']}", s["speech"] or "（静默，不口播）", f"{begin:g}–{begin + e['duration_s']:g} 秒",
                         f"“{e['anchor']}”第 {e['occurrence']} 次；段内偏移 {e['offset_s']:g} 秒；持续 {e['duration_s']:g} 秒",
                         f"{e['priority']}；{e['intent']}", e["visual"], e["sound"], e["voice"]))
    if not rows:
        return "没有单独指定的特效节点，按逐段导演表保持自然表达。\n"
    return table(["段落 / 效果", "完整台词", "全片时间", "触发与段内时间", "优先级与目的", "画面", "音效 / 配乐", "人声处理"], rows)


def references(plan):
    text = "## 保留句与事实依据\n\n"
    text += table(["保留句", "完整原文", "保留规则 / 处理状态", "对应段落", "原因"],
                  [(f["id"], f["text"], f["policy"] + (" / 待处理，未纳入口播" if f.get("disposition") == "reserved" else " / 已采用"), as_text(f["segment_ids"]), f["reason"]) for f in plan["fragments"]]) if plan["fragments"] else "没有锁定片段。\n"
    text += "\n"
    text += table(["事实", "具体说法", "状态", "来源", "说明"],
                  [(f["id"], f["text"], f["status"], f["source"], f["note"]) for f in plan["claims"]]) if plan["claims"] else "没有单列事实条目；这不代表事实已经核实。\n"
    return text


def asset_status(asset):
    if asset.get("delivery_state") == "native_output_only":
        return "已生成，待导出到剪辑设备；本地状态 planned"
    return asset["status"]


def render(plan, warnings):
    title = plan["project"]["title"]
    narration = f"# {title}｜口播稿\n\n" + "\n\n".join(s["speech"] for s in plan["segments"] if s["speech"]) + "\n"
    common = context(plan, warnings)
    segments = table(["时间 / 段落", "你要说的完整台词", "为什么说 / 引用", "你怎么说、怎么做", "镜头安排", "观众看到什么 / 素材文件"], segment_rows(plan))
    director = f"# {title}｜拍摄导演表\n\n" + common + "\n## 逐段拍摄\n\n" + segments + "\n## 配合表演的剪辑节点\n\n" + edit_table(plan) + "\n" + references(plan)
    handoff = f"# {title}｜剪辑交接单\n\n" + common
    handoff += "\n先读取实际音轨和转写，逐段核对以下完整台词，再定位触发词的第几次出现。重新确定效果起点和停留时间，保留停顿与呼吸的表达意图。单段效果不得跨段；跨段项目按描述衔接。must 是理解所需重点，optional 可按预算省略。人声清晰优先于音效冲击。\n\n本文件与 edit-brief.json 是供剪辑 agent 读取的要求，不是剪映、Remotion 或 HyperFrames 的原生工程；尚未执行剪辑或渲染。\n"
    handoff += "\n## 完整台词与导演意图\n\n" + segments + "\n## 重点剪辑时间线\n\n" + edit_table(plan) + "\n" + references(plan)
    materials = f"# {title}｜素材清单\n\n" + common
    for asset in plan["assets"]:
        used = [s["id"] for s in plan["segments"] if asset["id"] in s["visual"]["asset_ids"]]
        materials += f"\n## {asset['id']}｜{asset['purpose']}\n\n"
        materials += table(["项目", "要求"], [("类型 / 状态", f"{asset['kind']} / {asset_status(asset)}"), ("对应段落", as_text(used)),
            ("本地路径", as_text(asset["path"])), ("来源与真实性", asset["source"]), ("画幅", asset["aspect_ratio"]),
            ("构图与留白", asset["placement"]), ("生成指令 / 采集清单", asset["prompt"]), ("避免项", asset["negative"]),
            ("失败替代", asset["fallback"]), ("图片说明", asset["alt"])])
        if "delivery_state" in asset or "native_reference" in asset:
            materials += "\n" + table(["原生附件字段", "内容"], [(key, as_text(asset[key])) for key in ("delivery_state", "native_reference") if key in asset])
    if not plan["assets"]:
        materials += "\n本片没有单列外部素材。\n"
    brief = copy.deepcopy(plan)
    brief["format"] = FORMAT
    return dict(zip(OUTPUT_NAMES, (narration, director, handoff, materials, json.dumps(brief, ensure_ascii=False, indent=2, allow_nan=False) + "\n")))


def _no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON 对象含重复字段：" + key)
        result[key] = value
    return result


def read_plan(path):
    def invalid_constant(value):
        raise ValueError("JSON 不允许非有限数字：" + value)
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=_no_duplicate_keys, parse_constant=invalid_constant)


def export_files(rendered, output, source, overwrite=False, protected=()):
    """Preflight every destination before writing; stage all content first."""
    output = Path(output).resolve()
    if output.exists() and not output.is_dir():
        raise ValueError("输出路径不是目录：" + str(output))
    blocked = {Path(path).resolve() for path in (source, *protected)}
    targets = [output / name for name in OUTPUT_NAMES]
    for target in targets:
        resolved = target.resolve()
        if resolved.parent != output or target.is_symlink():
            raise ValueError("输出文件不得跳转到其他目录：" + str(target))
        if resolved in blocked:
            raise ValueError("输出不能覆盖输入计划或引用的素材：" + str(target))
        if target.exists():
            if not target.is_file():
                raise ValueError("输出目标不是普通文件：" + str(target))
            if not overwrite:
                raise ValueError("输出已存在；请用新目录或显式 --overwrite：" + str(target))
            if not os.access(target, os.W_OK):
                raise ValueError("输出文件不可写：" + str(target))
    output.mkdir(parents=True, exist_ok=True)
    staged = []
    try:
        for target in targets:
            with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", newline="\n", dir=output, prefix=".director-", suffix=".tmp", delete=False) as handle:
                staged.append(Path(handle.name))
                handle.write(rendered[target.name])
        for temporary, target in zip(staged, targets):
            # A late new file must not be silently replaced without --overwrite.
            if target.exists() and not overwrite:
                raise ValueError("输出在导出期间出现，停止覆盖：" + str(target))
            os.replace(temporary, target)
    finally:
        for temporary in staged:
            temporary.unlink(missing_ok=True)
    return targets


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--out", type=Path)
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        plan = read_plan(args.plan)
        errors, warnings = validate(plan, args.plan.resolve().parent)
        for warning in warnings:
            print("WARNING: " + warning)
        if errors:
            print("INVALID\n" + "\n".join("- " + error for error in errors), file=sys.stderr)
            return 1
        print(f"VALID: {len(plan['segments'])} 段；仅完成结构、锚点、时序与文件检查。")
        if args.check:
            return 0
        normalized = normalize_paths(plan, args.plan.resolve().parent)
        protected = [asset["path"] for asset in normalized["assets"] if asset["path"]]
        protected += [normalized["timing"][key] for key in ("source_media", "transcript_path") if normalized["timing"][key]]
        targets = export_files(render(normalized, warnings), args.out, args.plan, args.overwrite, protected)
        for target in targets:
            print(target)
        return 0
    except (OSError, ValueError, TypeError, OverflowError) as error:
        print("ERROR: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
