"""CPU-only regression checks for experiment boundaries, not model quality."""
import copy
import csv
import json
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from pathlib import Path

from PIL import Image

from filename_bench.backends import LlamaBackend, MockBackend
from filename_bench.common import ROOT, BenchError, load_config, read_json, read_rows, validate_output, write_json
from filename_bench.data import load_cases, prepare, select_frames, uniform_indices
from filename_bench.report import build_report
from filename_bench.runner import execute_wave, profiles, run


class ExamplesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.data = self.root / "data"
        self.data.mkdir()
        rows = []
        for case, media, count in [("I01", "image", 1), ("V01", "video", 12)]:
            names = []
            for i in range(count):
                name = f"{case}_{i}.png"
                Image.new("RGB", (64, 48), (i * 10, 80, 140)).save(self.data / name)
                names.append(name)
            rows.append({"id": case, "media_type": media, "image_paths": names})
        (self.data / "model_inputs.jsonl").write_text("\n".join(json.dumps(r) for r in rows), encoding="utf-8")
        self.cfg = load_config(ROOT / "configs/b_local.json")
        self.cfg.update(dataset_root=str(self.data), run_dir=str(self.root / "runs"), case_ids=["I01", "V01"])
        self.schema = read_json(ROOT / "assets/schema_v3.json")
        self.setting = self.cfg["baseline"]


    def tearDown(self):
        self.temp.cleanup()


    def test_strict_output_contract(self):
        good = '{"keywords":["고양이"],"reason":"소파 위 고양이","place_name":null,"needs_review":false}'
        self.assertTrue(validate_output(good, self.schema)["schema_valid"])
        for bad in ["```json\n" + good + "\n```", good.replace('"needs_review":false', '"needs_review":"false"'),
                    good.replace('"고양이"', ','.join('"태그%d"' % i for i in range(6))),
                    good.replace('"place_name":null', '"place_name":null,"title":"제목"'),
                    good.replace('"place_name":null', '"place_name":null,"place_name":"서울"'),
                    good.replace('"place_name":null', '"place_name":NaN')]:
            self.assertFalse(validate_output(bad, self.schema)["schema_valid"], bad)


    def test_frame_selection_and_no_upscale(self):
        cases, _ = load_cases(self.data)
        video = cases[1]
        self.assertEqual(uniform_indices(12, 1), [6])
        for policy in ["uniform", "blur", "dedup", "both"]:
            chosen, _ = select_frames(video["paths"], 6, policy)
            self.assertEqual(chosen, sorted(set(chosen)))
            self.assertEqual(len(chosen), 6)
            for i, n in enumerate(chosen):
                self.assertTrue(i * 2 <= n < (i + 1) * 2)
        _, details = select_frames(video["paths"], 6, "dedup")
        self.assertGreater(details["fallback_count"], 0)
        prepared, meta = prepare(video, {**self.setting, "short_edge_px": 1080, "frames": 3})
        self.assertEqual(meta["prepared_sizes_wh"], [[64, 48]] * 3)
        self.assertEqual(len(prepared), 3)
        with self.assertRaises(BenchError):
            prepare(video, {**self.setting, "frames": 24})


    def test_resume_and_review_preservation(self):
        first = run(self.cfg, "b", mock=True, limit=1)
        second = run(self.cfg, "b", mock=True, resume=True)
        self.assertEqual(first["recorded_attempts"], 1)
        self.assertEqual(second["recorded_attempts"], 2)
        directory = Path(second["run_dir"])
        rows = read_rows(directory / "requests.jsonl")
        self.assertEqual(len({r["job_id"] for r in rows}), 2)
        with (directory / "review.csv").open(encoding="utf-8-sig", newline="") as f:
            reviews = list(csv.DictReader(f))
        reviews[0]["notes"] = "사람 검수 기록 유지"
        with (directory / "review.csv").open("w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(reviews[0]))
            writer.writeheader(); writer.writerows(reviews)
        build_report(directory, self.data)
        self.assertIn("사람 검수 기록 유지", (directory / "review.csv").read_text(encoding="utf-8-sig"))
        self.assertIn("모델 성능 결과 아님", (directory / "report.html").read_text())
        Image.new("RGB", (64, 48), "red").save(self.data / "I01_0.png")
        with self.assertRaisesRegex(ValueError, "changed"):
            run(self.cfg, "b", mock=True, resume=True)


    def jobs(self, n=2):
        return [{"job_id": str(i), "images": (bytes([i]),), "prompt": "test", "setting": copy.deepcopy(self.setting),
                 "seed": i} for i in range(n)]


    def test_concurrent_result_mapping(self):
        class Echo(MockBackend):
            def infer(self, images, prompt, setting, seed):
                row = super().infer(images, prompt, setting, seed)
                row["observed_seed"] = seed
                return row
        backend = Echo({})
        result, meta, _ = execute_wave(backend, self.jobs(), self.schema)
        self.assertEqual(result["0"]["observed_seed"], 0)
        self.assertEqual(result["1"]["observed_seed"], 1)
        self.assertEqual(meta["wave_request_count"], 2)


    def test_fatal_error_cancels_owned_work(self):
        class Fault(MockBackend):
            def __init__(self):
                super().__init__({}); self.closed = threading.Event()
            def infer(self, images, prompt, setting, seed):
                if seed == 0:
                    raise BenchError("oom", "simulated allocation failure")
                self.closed.wait(2)
                return super().infer(images, prompt, setting, seed)
            def close(self):
                self.closed.set()
        backend = Fault()
        result, _, _ = execute_wave(backend, self.jobs(), self.schema)
        self.assertTrue(backend.closed.is_set())
        self.assertEqual(result["0"]["execution_status"], "oom")
        self.assertEqual(len(result), 2)


    def test_cancelled_single_request(self):
        class Cancel(MockBackend):
            def infer(self, *args):
                raise KeyboardInterrupt
        result, _, _ = execute_wave(Cancel({}), self.jobs(1), self.schema)
        self.assertEqual(result["0"]["execution_status"], "cancelled")


    def fake_server_config(self):
        script = self.root / "fake-llama-server"
        shutil.copyfile(ROOT / "tests/fake_llama_server.py", script)
        script.chmod(0o755)
        return {"server_path": str(script), "model_path": str(script), "mmproj_path": str(script),
                "startup_timeout_s": 5, "request_timeout_s": 2}


    @unittest.skipIf(sys.platform == "win32", "POSIX executable fixture; real Windows GPU needs separate test")
    def test_owned_http_server_and_message_isolation(self):
        backend = LlamaBackend(self.fake_server_config())
        try:
            backend.start(self.setting, self.root / "server.log")
            process = backend.process
            self.assertEqual(backend.info["effective_context"], self.setting["context_per_request"])
            for n in [3, 1]:
                response = backend.infer((b"test",) * n, "test", self.setting, 42)
                self.assertEqual(response["raw_response"]["test_message_count"], 1)
                self.assertEqual(response["raw_response"]["test_image_count"], n)
                self.assertTrue(response["raw_response"]["test_text_last"])
        finally:
            backend.close()
        self.assertIsNotNone(process.poll())


    @unittest.skipIf(sys.platform == "win32", "POSIX executable fixture")
    def test_context_probe_records_measured_occupancy(self):
        cfg = load_config(ROOT / "configs/b_local.json")
        cfg.update(dataset_root=str(self.data), run_dir=str(self.root / "context"), case_ids=["I01"], rounds_per_profile=1)
        cfg["backend"] = {"kind": "llama-server", **self.fake_server_config()}
        cfg["sweeps"]["context_per_request"] = [4096]
        result = run(cfg, "b", "context")
        rows = read_rows(Path(result["run_dir"]) / "requests.jsonl")
        self.assertEqual(len(rows), 1)
        self.assertTrue(rows[0]["context_load_confirmed"])
        self.assertTrue(rows[0]["capacity_only"])
        self.assertGreaterEqual(rows[0]["context_occupancy"], .70)
        self.assertLess(rows[0]["context_occupancy"], .80)


    @unittest.skipIf(sys.platform == "win32", "POSIX executable fixture")
    def test_http_timeout_stops_owned_server(self):
        cfg = self.fake_server_config(); cfg["request_timeout_s"] = .005
        backend = LlamaBackend(cfg)
        try:
            backend.start(self.setting, self.root / "timeout.log")
            process = backend.process
            result, _, _ = execute_wave(backend, self.jobs(1), self.schema)
            self.assertEqual(result["0"]["execution_status"], "timeout")
            self.assertIsNotNone(process.poll())
        finally:
            backend.close()


    def test_soak_requires_one_uninterrupted_process(self):
        cfg = load_config(ROOT / "configs/b_local.json")
        cfg.update(dataset_root=str(self.data), run_dir=str(self.root / "b"), case_ids=["I01", "V01"], reuse_requests=3)
        run(cfg, "b", "soak", mock=True, limit=1)
        with self.assertRaisesRegex(ValueError, "uninterrupted"):
            run(cfg, "b", "soak", mock=True, resume=True)


    def test_cli_nonzero_on_load_failure(self):
        cfg = load_config(ROOT / "configs/b_local.json")
        cfg.update(dataset_root=str(self.data), run_dir=str(self.root / "load_failure"), case_ids=["I01", "V01"])
        cfg["backend"]["server_path"] = str(self.root / "missing-server")
        config_path = self.root / "config.json"
        write_json(config_path, cfg)
        result = subprocess.run([sys.executable, str(ROOT / "b_capacity.py"), "--config", str(config_path)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        directory = Path(cfg["run_dir"]) / "smoke"
        self.assertTrue((directory / "report.html").exists())
        self.assertEqual(read_rows(directory / "events.jsonl")[0]["execution_status"], "unsupported")


if __name__ == "__main__":
    unittest.main()
