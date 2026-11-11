"""Offline-only environment checks; never load weights, datasets, or API keys."""
import argparse
import importlib
import importlib.metadata as metadata
import json
import os
from pathlib import Path
import platform
import socket
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")

def deny_network(*args, **kwargs):
    raise RuntimeError("Network access disabled by environment validation")
socket.socket.connect = deny_network
socket.create_connection = deny_network

PACKAGES = {
    "torch": "torch", "torchvision": "torchvision", "numpy": "numpy",
    "scipy": "scipy", "scikit-learn": "sklearn", "pandas": "pandas",
    "Pillow": "PIL", "opencv-python": "cv2", "matplotlib": "matplotlib",
    "seaborn": "seaborn", "tqdm": "tqdm", "PyYAML": "yaml", "psutil": "psutil",
    "timm": "timm", "einops": "einops", "transformers": "transformers",
    "safetensors": "safetensors", "torchmetrics": "torchmetrics",
    "pycocotools": "pycocotools", "openai": "openai", "pydantic": "pydantic",
    "python-dotenv": "dotenv", "fastapi": "fastapi", "uvicorn": "uvicorn",
    "sqlalchemy": "sqlalchemy", "aiosqlite": "aiosqlite", "streamlit": "streamlit",
    "plotly": "plotly",
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dummy", action="store_true")
    parser.add_argument("--output", default="outputs/environment_validation.json")
    args = parser.parse_args()
    results = {"python": platform.python_version(), "executable": sys.executable,
               "platform": platform.platform(), "actual_data_inference": "unverified",
               "packages": {}, "checks": {}}
    failures = []
    def check(name, action):
        try:
            value = action()
            results["checks"][name] = {"status": "pass", "result": value}
            print(name + ": pass", flush=True)
        except Exception as exc:
            results["checks"][name] = {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)}
            failures.append(name)
            print(name + ": fail (" + type(exc).__name__ + ")", flush=True)
    check("python_3_12", lambda: sys.version_info[:2] == (3, 12) or (_ for _ in ()).throw(RuntimeError("Python 3.12 required")))
    for package, module in PACKAGES.items():
        try:
            version = metadata.version(package)
            importlib.import_module(module)
            results["packages"][package] = {"version": version, "status": "import_success"}
        except Exception as exc:
            results["packages"][package] = {"status": "fail", "error": type(exc).__name__ + ": " + str(exc)}
            failures.append(package)
    def tensor():
        import torch
        torch.set_num_threads(2)
        assert torch.equal(torch.ones(2, 2) @ torch.ones(2, 2), torch.full((2, 2), 2.0))
        return {"backend": "cuda" if torch.cuda.is_available() else "cpu", "cuda_build": torch.version.cuda}
    check("tensor", tensor)
    def sqlite_check():
        import sqlite3
        with sqlite3.connect(":memory:") as con:
            con.executescript((ROOT / "configs/experiments.sql").read_text(encoding="utf-8"))
            return con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    check("sqlite_schema", sqlite_check)
    def detection_imports():
        from torchvision.models.detection import fasterrcnn_resnet50_fpn, retinanet_resnet50_fpn
        from transformers import YolosForObjectDetection, RTDetrV2ForObjectDetection
        return [x.__name__ for x in (fasterrcnn_resnet50_fpn, retinanet_resnet50_fpn, YolosForObjectDetection, RTDetrV2ForObjectDetection)]
    check("detection_framework_classes", detection_imports)
    if args.dummy:
        def torchvision_model(factory):
            import torch
            import torchvision.models.detection as detection
            model = getattr(detection, factory)(weights=None, weights_backbone=None, min_size=64, max_size=64).eval()
            with torch.inference_mode():
                output = model([torch.zeros(3, 64, 64)])
            assert {"boxes", "labels", "scores"} <= output[0].keys()
            return {"created": True, "dummy_inference": True, "pretrained": False, "input": [3, 64, 64]}
        for name in ("fasterrcnn_resnet50_fpn", "retinanet_resnet50_fpn"):
            check(name, lambda n=name: torchvision_model(n))
        def yolos():
            import torch
            from transformers import YolosConfig, YolosForObjectDetection
            config = YolosConfig(image_size=[64,64], patch_size=16, hidden_size=48,
                num_hidden_layers=1, num_attention_heads=3, intermediate_size=96,
                num_detection_tokens=5, num_labels=2, use_mid_position_embeddings=False)
            model = YolosForObjectDetection(config).eval()
            with torch.inference_mode():
                output = model(pixel_values=torch.zeros(1, 3, 64, 64))
            assert output.pred_boxes.shape == (1, 5, 4)
            return {"created": True, "dummy_inference": True, "variant": "reduced_config", "pretrained": False}
        check("yolos", yolos)
    results["failed_count"] = len(failures)
    results["timestamp_unix"] = time.time()
    path = Path(args.output)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print("Report:", path, "failures:", len(failures))
    return bool(failures)

if __name__ == "__main__":
    sys.exit(main())
