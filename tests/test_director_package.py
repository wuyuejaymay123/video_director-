"""Contract regression checks; all test fixtures are local and synthetic."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parent
SCRIPT = ROOT.parent / "skills" / "video-script-director" / "scripts" / "director_package.py"
SPEC = importlib.util.spec_from_file_location("director_package", SCRIPT)
PACKAGE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(PACKAGE)


def fixture():
    return {
        "schema_version": "1.0",
        "project": {"title": "测试片", "topic": "表达", "angle": "先讲结果", "audience": "第一次写稿的人", "platform": "抖音", "target_duration_s": 7, "aspect_ratio": "9:16", "mode": "integrate", "assumptions": ["仅为结构测试"]},
        "timing": {"basis": "estimated", "rate_cps": 4.5, "source_media": None, "transcript_path": None, "note": "未拍摄，按试读预估"},
        "direction": {"promise": "会安排一句话", "emotion_arc": "疑问到理解", "persona": "像朋友交流", "visual_style": "简洁", "audio_style": "原声", "cover_title": "先看结果", "revision_notes": ["删去重复引子"]},
        "fragments": [{"id": "F01", "text": "先看结果。", "policy": "verbatim", "segment_ids": ["S01"], "reason": "保留原话"}],
        "claims": [{"id": "C01", "text": "测试场景", "status": "hypothetical", "source": "", "note": "原创测试，不是真实证据"}],
        "assets": [{"id": "A01", "kind": "diagram", "status": "available", "purpose": "结构测试", "path": "asset.txt", "source": "合成测试文件，非图片证据", "prompt": "", "negative": "", "aspect_ratio": "9:16", "placement": "居中", "fallback": "真人讲述", "alt": "测试文字"}],
        "segments": [{"id": "S01", "start_s": 0, "end_s": 7, "speech": "先看结果。再看方法。先看结果。", "purpose": "展示顺序", "techniques": ["重复"],
                      "performance": {"emotion": "平稳", "intensity": 2, "pace": "正常", "emphasis": ["先看结果"], "pauses": [{"after": "结果。", "seconds": 0.3}]},
                      "camera": {"visibility": "露脸", "framing": "中近景", "action": "固定"},
                      "visual": {"description": "文字按顺序出现", "asset_ids": ["A01"]},
                      "edits": [{"id": "E01", "anchor": "先看结果", "occurrence": 2, "offset_s": 4, "duration_s": 2, "priority": "must", "intent": "结果先行", "visual": "出现后停稳", "sound": "不加", "voice": "保留原声"}], "claim_ids": ["C01"], "fragment_ids": ["F01"]}]
    }


class ContractTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="director-test-", dir=ROOT)
        self.base = Path(self.temporary.name)
        (self.base / "asset.txt").write_text("synthetic test fixture", encoding="utf-8")
        self.plan = fixture()
        self.plan["segments"][0]["performance"].update(face="看镜头", gesture="手放松")

    def tearDown(self):
        self.temporary.cleanup()

    def errors(self, plan=None):
        return PACKAGE.validate(plan or self.plan, self.base)[0]

    def test_valid_plan_and_literal_narration(self):
        errors, warnings = PACKAGE.validate(self.plan, self.base)
        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])
        normalized = PACKAGE.normalize_paths(self.plan, self.base)
        output = PACKAGE.render(normalized, warnings)
        self.assertEqual(set(output), set(PACKAGE.OUTPUT_NAMES))
        self.assertEqual(output["口播稿.md"].split("\n\n", 1)[1].strip(), self.plan["segments"][0]["speech"])
        for name in ("拍摄导演表.md", "剪辑交接单.md"):
            self.assertIn(self.plan["segments"][0]["speech"], output[name])
            self.assertIn("疑问到理解", output[name])
            self.assertIn(str(self.base / "asset.txt"), output[name])
            self.assertIn("第 2 次", output[name])
            self.assertIn("保留原声", output[name])
        brief = json.loads(output["edit-brief.json"])
        self.assertEqual(brief["schema_version"], "1.0")
        self.assertEqual(brief["format"], PACKAGE.FORMAT)
        self.assertTrue(Path(brief["assets"][0]["path"]).is_absolute())

    def test_missing_fields_and_wrong_enums(self):
        for branch, field in (("project", "audience"), ("timing", "source_media"), ("direction", "emotion_arc")):
            with self.subTest(branch=branch, field=field):
                plan = copy.deepcopy(self.plan)
                del plan[branch][field]
                self.assertTrue(self.errors(plan))
        for branch, field, value in (("project", "mode", "magic"), ("timing", "basis", "measured")):
            with self.subTest(field=field):
                plan = copy.deepcopy(self.plan)
                plan[branch][field] = value
                self.assertTrue(self.errors(plan))
        for field in ("emotion", "intensity", "pace", "emphasis", "pauses", "face", "gesture"):
            with self.subTest(performance=field):
                plan = copy.deepcopy(self.plan)
                del plan["segments"][0]["performance"][field]
                self.assertTrue(self.errors(plan))

    def test_negative_nonfinite_bool_and_start_gap(self):
        for field, value in (("start_s", -1), ("start_s", 1), ("start_s", True), ("end_s", float("inf")), ("end_s", float("nan")), ("end_s", 0)):
            with self.subTest(field=field, value=value):
                plan = copy.deepcopy(self.plan)
                plan["segments"][0][field] = value
                self.assertTrue(self.errors(plan))

    def test_second_segment_overlap_or_gap(self):
        for start in (6, 8):
            with self.subTest(start=start):
                plan = copy.deepcopy(self.plan)
                second = copy.deepcopy(plan["segments"][0])
                second.update(id="S02", start_s=start, end_s=15, edits=[], fragment_ids=[])
                plan["segments"].append(second)
                self.assertTrue(any("连续" in error for error in self.errors(plan)))

    def test_anchor_occurrence_and_edit_range(self):
        cases = [("anchor", "不存在"), ("occurrence", 3), ("occurrence", 0), ("occurrence", True), ("offset_s", -1), ("offset_s", 6), ("duration_s", 0), ("priority", "always")]
        for field, value in cases:
            with self.subTest(field=field, value=value):
                plan = copy.deepcopy(self.plan)
                plan["segments"][0]["edits"][0][field] = value
                self.assertTrue(self.errors(plan))

    def test_pause_emphasis_and_pause_budget(self):
        plan = copy.deepcopy(self.plan)
        plan["segments"][0]["performance"]["emphasis"] = ["不存在"]
        self.assertTrue(self.errors(plan))
        for pause in ({"after": "不存在", "seconds": 0.3}, {"after": "结果。", "seconds": 0.3, "occurrence": 3}, {"after": "结果。", "seconds": 7}):
            with self.subTest(pause=pause):
                plan = copy.deepcopy(self.plan)
                plan["segments"][0]["performance"]["pauses"] = [pause]
                self.assertTrue(self.errors(plan))

    def test_silent_segment_start_trigger(self):
        plan = copy.deepcopy(self.plan)
        plan["fragments"] = []
        segment = plan["segments"][0]
        segment.update(speech="", fragment_ids=[])
        segment["performance"].update(emphasis=[], pauses=[])
        segment["edits"][0].update(anchor="", occurrence=1)
        self.assertEqual(self.errors(plan), [])
        segment["edits"][0]["occurrence"] = 2
        self.assertTrue(self.errors(plan))

    def test_fragment_exactness_and_two_way_references(self):
        for mutation in ("punctuation", "missing_forward", "missing_back", "invalid_ref"):
            with self.subTest(mutation=mutation):
                plan = copy.deepcopy(self.plan)
                if mutation == "punctuation":
                    plan["fragments"][0]["text"] = "先看结果！"
                elif mutation == "missing_forward":
                    plan["segments"][0]["fragment_ids"] = []
                elif mutation == "missing_back":
                    plan["fragments"][0]["segment_ids"] = []
                else:
                    plan["fragments"][0]["segment_ids"] = ["S99"]
                self.assertTrue(self.errors(plan))

    def test_reserved_fragment_is_visible_and_unspoken(self):
        plan = copy.deepcopy(self.plan)
        plan["fragments"][0].update(text="未经核实的锁定句。", disposition="reserved", segment_ids=[], reason="事实无依据，建议改为待验证问题")
        plan["segments"][0]["fragment_ids"] = []
        errors, warnings = PACKAGE.validate(plan, self.base)
        self.assertEqual(errors, [])
        self.assertTrue(any("未纳入口播" in warning for warning in warnings))
        output = PACKAGE.render(PACKAGE.normalize_paths(plan, self.base), warnings)
        self.assertNotIn("未经核实的锁定句", output["口播稿.md"])
        for name in ("拍摄导演表.md", "剪辑交接单.md"):
            self.assertIn("待处理，未纳入口播", output[name])
            self.assertIn("未经核实的锁定句。", output[name])
        plan["segments"][0]["fragment_ids"] = ["F01"]
        self.assertTrue(self.errors(plan))
        plan["segments"][0]["fragment_ids"] = []
        plan["fragments"][0]["segment_ids"] = ["S01"]
        self.assertTrue(self.errors(plan))

    def test_native_asset_output_keeps_actual_status(self):
        plan = copy.deepcopy(self.plan)
        asset = plan["assets"][0]
        asset.update(status="planned", path=None, delivery_state="native_output_only", native_reference="attachment:test-only")
        errors, warnings = PACKAGE.validate(plan, self.base)
        self.assertEqual(errors, [])
        self.assertTrue(any("已生成原生附件" in warning for warning in warnings))
        output = PACKAGE.render(plan, warnings)
        self.assertIn("已生成，待导出到剪辑设备", output["素材清单.md"])
        self.assertIn("attachment:test-only", output["素材清单.md"])
        self.assertEqual(json.loads(output["edit-brief.json"])["assets"][0]["delivery_state"], "native_output_only")
        del asset["native_reference"]
        self.assertTrue(self.errors(plan))

    def test_media_and_claim_reference_checks(self):
        for field, value in (("claim_ids", ["C99"]), ("fragment_ids", ["F99"])):
            plan = copy.deepcopy(self.plan)
            plan["segments"][0][field] = value
            self.assertTrue(self.errors(plan))
        plan = copy.deepcopy(self.plan)
        plan["segments"][0]["visual"]["asset_ids"] = ["A99"]
        self.assertTrue(self.errors(plan))
        for path in (None, "missing.png", "https://example.test/image.png", "."):
            with self.subTest(path=path):
                plan = copy.deepcopy(self.plan)
                plan["assets"][0]["path"] = path
                self.assertTrue(self.errors(plan))
        plan = copy.deepcopy(self.plan)
        plan["claims"][0]["status"] = "verified"
        self.assertTrue(self.errors(plan))

    def test_aligned_requires_both_actual_files(self):
        plan = copy.deepcopy(self.plan)
        plan["timing"]["basis"] = "aligned"
        self.assertTrue(self.errors(plan))
        plan["timing"]["source_media"] = "asset.txt"
        self.assertTrue(self.errors(plan))
        plan["timing"]["transcript_path"] = "asset.txt"
        self.assertEqual(self.errors(plan), [])
        normalized = PACKAGE.normalize_paths(plan, self.base)
        for key in ("source_media", "transcript_path"):
            self.assertTrue(Path(normalized["timing"][key]).is_absolute())

    def test_warnings_do_not_pretend_to_verify(self):
        plan = copy.deepcopy(self.plan)
        plan["project"]["target_duration_s"] = 60
        plan["segments"][0]["read_units"] = 100
        plan["claims"][0]["status"] = "needs_verification"
        plan["assets"][0].update(status="planned", path=None)
        errors, warnings = PACKAGE.validate(plan, self.base)
        self.assertEqual(errors, [])
        self.assertEqual(len(warnings), 4)
        self.assertTrue(any("偏快" in warning for warning in warnings))

    def test_preflight_last_file_collision_writes_nothing(self):
        output = self.base / "out"
        output.mkdir()
        (output / "edit-brief.json").write_text("KEEP", encoding="utf-8")
        rendered = PACKAGE.render(PACKAGE.normalize_paths(self.plan, self.base), [])
        with self.assertRaises(ValueError):
            PACKAGE.export_files(rendered, output, self.base / "input.json")
        self.assertEqual(sorted(path.name for path in output.iterdir()), ["edit-brief.json"])
        self.assertEqual((output / "edit-brief.json").read_text(), "KEEP")
        (output / "素材清单.md").mkdir()
        with self.assertRaises(ValueError):
            PACKAGE.export_files(rendered, output, self.base / "input.json", overwrite=True)
        self.assertFalse((output / "口播稿.md").exists())

    def test_export_input_and_media_cannot_be_overwritten(self):
        output = self.base / "out"
        rendered = PACKAGE.render(PACKAGE.normalize_paths(self.plan, self.base), [])
        with self.assertRaises(ValueError):
            PACKAGE.export_files(rendered, output, output / "edit-brief.json", overwrite=True)
        with self.assertRaises(ValueError):
            PACKAGE.export_files(rendered, output, self.base / "input.json", overwrite=True, protected=[output / "口播稿.md"])
        self.assertFalse(output.exists())

    def test_cli_export_overwrite_and_errors(self):
        source = self.base / "plan.json"
        source.write_text(json.dumps(self.plan, ensure_ascii=False), encoding="utf-8")
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        def run(*args):
            return subprocess.run([sys.executable, str(SCRIPT), str(source), *args], text=True, capture_output=True, encoding="utf-8", env=dict(env, PYTHONIOENCODING="utf-8"))
        self.assertEqual(run("--check").returncode, 0)
        self.assertEqual(sorted(path.name for path in self.base.iterdir()), ["asset.txt", "plan.json"])
        target = self.base / "out"
        self.assertEqual(run("--out", str(target)).returncode, 0)
        self.assertEqual(len(list(target.iterdir())), 5)
        self.assertEqual(run("--out", str(target)).returncode, 1)
        self.assertEqual(run("--out", str(target), "--overwrite").returncode, 0)
        source.write_text('{"schema_version": "1.0", "bad": NaN}', encoding="utf-8")
        result = run("--check")
        self.assertEqual(result.returncode, 1)
        self.assertNotIn("Traceback", result.stderr)
        source.write_text('{"schema_version":"1.0","schema_version":"9"}', encoding="utf-8")
        self.assertIn("重复字段", run("--check").stderr)

    def test_malformed_nested_values_report_errors(self):
        for mutate in (lambda p: p["assets"][0].update(status=[]), lambda p: p["fragments"][0].update(segment_ids=None), lambda p: p["segments"][0].update(performance=[]), lambda p: p.update(segments=[None])):
            plan = copy.deepcopy(self.plan)
            mutate(plan)
            self.assertTrue(self.errors(plan))


if __name__ == "__main__":
    unittest.main(verbosity=2)
