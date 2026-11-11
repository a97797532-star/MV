"""Real-IAD mask -> component boxes -> COCO/YOLO, with explicit mask-policy review.
Run: python realiad_bbox_pipeline.py --data-dir notebook_results_real --mode inspect
Then: python realiad_bbox_pipeline.py --data-dir notebook_results_real --mode export --threshold 127 --limit 100
Threshold is an EXAMPLE ONLY; select after inspecting mask semantics and previews.
"""
import argparse
import json
import re
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from PIL import Image

KEYS = ["category", "defect_type", "view"]
BOX_COLUMNS = ["image_id", "image_path", "mask_path", "category", "defect_type", "view", "project_split", "product_key", "component_id", "class_id", "class_name", "x0", "y0", "x1", "y1", "width", "height", "area_pixels"]
IMAGE_COLUMNS = ["image_id", "image_path", "mask_path", "project_split", "product_key", "width", "height", "component_count", "mask_status"]
ERROR_COLUMNS = ["image_id", "image_path", "mask_path", "error"]


def read_data(data_dir):
    pairs = pd.read_csv(data_dir / "image_mask_pairs.csv", dtype=str).fillna("")
    images = pd.read_csv(data_dir / "image_metadata_with_split.csv", dtype=str).fillna("")
    mask_col = "mask_path" if "mask_path" in pairs.columns else "image_path"
    for c in ("original_image_id", "original_image_path", mask_col):
        if c not in pairs.columns:
            raise ValueError(f"Missing column in pairs: {c}")
    for c in ("image_id", "project_split", "product_key", "category", "view", "relative_path"):
        if c not in images.columns:
            raise ValueError(f"Missing column in image metadata: {c}")
    if images.image_id.duplicated().any() or pairs.original_image_id.duplicated().any():
        raise ValueError("Duplicate image_id in metadata or pairs")
    lookup = pairs[["original_image_id", "original_image_path", mask_col]].rename(columns={
        "original_image_id": "image_id", "original_image_path": "pair_image_path", mask_col: "mask_path"})
    merged = images.merge(lookup, on="image_id", how="inner", validate="one_to_one")
    def defect(row):
        if row.get("defect_type", ""):
            return row["defect_type"]
        parts = re.split(r"[/\\]", row["relative_path"])
        up = [p.upper() for p in parts]
        return parts[up.index("NG") + 1] if "NG" in up and up.index("NG") + 1 < len(parts) else "UNKNOWN"
    merged["defect_type"] = merged.apply(defect, axis=1)
    merged["project_split"] = merged["project_split"].str.lower().str.strip()
    if not merged["project_split"].isin(["train", "val", "validation", "test"]).all():
        raise ValueError("Missing or unknown project_split. Do not infer a split.")
    if images.groupby("product_key")["project_split"].nunique().max() > 1:
        raise ValueError("Product leakage across splits")
    if (merged["image_path"].str.lower().str.replace("\\", "/", regex=False) != merged["pair_image_path"].str.lower().str.replace("\\", "/", regex=False)).any():
        raise ValueError("Image paths disagree between the two CSVs")
    return merged


def raw_mask(path):
    with Image.open(path) as im:
        mode = im.mode
        arr = np.asarray(im)
    if arr.ndim != 2:
        raise ValueError(f"Mask mode {mode}, shape {arr.shape}: inspect channels/encoding before export")
    if arr.dtype != np.uint8:
        raise ValueError(f"Mask dtype {arr.dtype}: inspect encoding before export")
    return arr, mode


def binary_mask(arr, threshold):
    if threshold is None or not 0 <= threshold <= 254:
        raise ValueError("An explicitly reviewed threshold between 0 and 254 is required")
    return np.ascontiguousarray(arr > threshold, dtype=np.uint8)


def boxes_from_binary(binary):
    n, labels, stats, _ = cv2.connectedComponentsWithStats(binary, connectivity=8)
    out = []
    for component_id in range(1, n):
        x, y, w, h, area = (int(v) for v in stats[component_id])
        out.append(dict(component_id=component_id, x0=x, y0=y, x1=x+w, y1=y+h,
                        width=w, height=h, area_pixels=area))
    return out


def inspect(rows, outdir, count=8):
    import matplotlib.pyplot as plt
    outdir.mkdir(parents=True, exist_ok=True)
    details = []
    for _, row in rows.head(count).iterrows():
        try:
            arr, mode = raw_mask(row.mask_path)
            vals, counts = np.unique(arr, return_counts=True)
            details.append({"image_id": row.image_id, "mode": mode, "min": int(arr.min()),
                            "max": int(arr.max()), "unique_count": len(vals),
                            "top_values": str(sorted(zip(vals.tolist(), counts.tolist()), key=lambda x: -x[1])[:12])})
            with Image.open(row.image_path) as im:
                rgb = np.asarray(im.convert("RGB"))
            if arr.shape != rgb.shape[:2]:
                raise ValueError("Image and mask sizes differ")
            fig, axes = plt.subplots(2, 4, figsize=(16, 8))
            axes[0, 0].imshow(rgb); axes[0, 0].set_title("Original JPG")
            axes[0, 1].imshow(arr, cmap="gray", vmin=0, vmax=255); axes[0, 1].set_title("Raw PNG")
            for ax, t in zip(axes.flat[2:], [0, 32, 64, 127, 192, 254]):
                binary = arr > t
                overlay = rgb.copy()
                overlay[binary] = (0.5 * rgb[binary] + 0.5 * np.array([255, 0, 0])).astype(np.uint8)
                ax.imshow(overlay); ax.set_title(f"> {t}: {binary.sum()} pixels")
            for ax in axes.flat: ax.axis("off")
            fig.tight_layout()
            fig.savefig(outdir / f"inspect_{row.image_id}.png", dpi=130)
            plt.close(fig)
        except Exception as exc:
            details.append({"image_id": row.image_id, "error": str(exc)})
    pd.DataFrame(details).to_csv(outdir / "mask_inspection.csv", index=False, encoding="utf-8-sig")
    print("Inspection saved to", outdir)


def export(rows, outdir, threshold):
    outdir.mkdir(parents=True, exist_ok=True)
    records, image_records, errors = [], [], []
    for i, row in enumerate(rows.itertuples(index=False), start=1):
        try:
            with Image.open(row.image_path) as im: W, H = im.size
            mask, mode = raw_mask(row.mask_path)
            if mask.shape != (H, W):
                raise ValueError(f"Size mismatch: image {(H, W)} vs mask {mask.shape}")
            binary = binary_mask(mask, threshold)
            boxes = boxes_from_binary(binary)
            image_records.append(dict(image_id=row.image_id, image_path=row.image_path,
                                      mask_path=row.mask_path, project_split=row.project_split,
                                      product_key=row.product_key, width=W, height=H,
                                      component_count=len(boxes), mask_status="positive" if binary.any() else "empty"))
            for b in boxes:
                records.append(dict(image_id=row.image_id, image_path=row.image_path, mask_path=row.mask_path,
                                    category=row.category, defect_type=row.defect_type, view=row.view,
                                    project_split=row.project_split, product_key=row.product_key,
                                    class_id=0, class_name="defect", **b))
        except Exception as exc:
            errors.append(dict(image_id=row.image_id, image_path=row.image_path,
                               mask_path=row.mask_path, error=str(exc)))
        if i % 1000 == 0: print(f"Processed {i}/{len(rows)}")
    bdf = pd.DataFrame(records, columns=BOX_COLUMNS)
    idf = pd.DataFrame(image_records, columns=IMAGE_COLUMNS)
    edf = pd.DataFrame(errors, columns=ERROR_COLUMNS)
    bdf.to_csv(outdir / "defect_bboxes.csv", index=False, encoding="utf-8-sig")
    idf.to_csv(outdir / "image_component_summary.csv", index=False, encoding="utf-8-sig")
    edf.to_csv(outdir / "bbox_errors.csv", index=False, encoding="utf-8-sig")
    coco = {"images": [], "annotations": [], "categories": [{"id": 1, "name": "defect"}]}
    coco_id = {}
    for i, r in enumerate(idf.itertuples(index=False), start=1):
        coco_id[r.image_id] = i
        coco["images"].append(dict(id=i, file_name=r.image_path, width=int(r.width), height=int(r.height)))
    for j, r in enumerate(bdf.itertuples(index=False), start=1):
        coco["annotations"].append(dict(id=j, image_id=coco_id[r.image_id], category_id=1,
                                        bbox=[int(r.x0), int(r.y0), int(r.width), int(r.height)],
                                        area=int(r.area_pixels), iscrowd=0))
    (outdir / "defect_coco.json").write_text(json.dumps(coco, ensure_ascii=False), encoding="utf-8")
    label_dir = outdir / "yolo_labels"
    label_dir.mkdir(exist_ok=True)
    groups = {k: g for k, g in bdf.groupby("image_id")}
    for r in idf.itertuples(index=False):
        lines = []
        for b in groups.get(r.image_id, pd.DataFrame()).itertuples(index=False):
            cx = (b.x0 + b.x1) / (2 * r.width)
            cy = (b.y0 + b.y1) / (2 * r.height)
            lines.append(f"0 {cx:.9f} {cy:.9f} {b.width/r.width:.9f} {b.height/r.height:.9f}")
        (label_dir / f"{r.image_id}.txt").write_text("\n".join(lines), encoding="utf-8")
    if len(bdf):
        dimensions = idf.set_index("image_id")[["width", "height"]]
        joined = bdf.join(dimensions, on="image_id", rsuffix="_image")
        assert ((joined.x0 >= 0) & (joined.y0 >= 0) & (joined.x1 <= joined.width_image) & (joined.y1 <= joined.height_image)).all()
        assert ((joined.x1 > joined.x0) & (joined.y1 > joined.y0)).all()
    assert len(idf) + len(edf) == len(rows)
    assert len(coco["annotations"]) == len(bdf)
    print(f"Success images: {len(idf)}; boxes: {len(bdf)}; errors: {len(edf)}; empty masks: {(idf.mask_status == 'empty').sum() if len(idf) else 0}")
    print("Outputs:", outdir)
    return bdf, idf, edf


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data-dir", type=Path, default=Path("notebook_results_real"))
    p.add_argument("--mode", choices=["inspect", "export"], required=True)
    p.add_argument("--threshold", type=int)
    p.add_argument("--limit", type=int, default=100, help="0 means all")
    p.add_argument("--inspect-count", type=int, default=8)
    args = p.parse_args()
    rows = read_data(args.data_dir)
    if args.limit: rows = rows.head(args.limit)
    outdir = args.data_dir / "bbox_results"
    if args.mode == "inspect": inspect(rows, outdir / "inspection", args.inspect_count)
    else: export(rows, outdir, args.threshold)

if __name__ == "__main__":
    main()
