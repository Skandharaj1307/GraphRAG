import json
import csv
from pathlib import Path

import numpy as np
import torch
from sentence_transformers import SentenceTransformer

from .config import (
    EMBEDDING_MODEL,
    EMBEDDING_DIMENSION,
)

from .screenshot_text_builder import (
    build_screenshot_text,
)


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

SCREENSHOT_DIR = (
    BASE_DIR
    / "dataset"
    / "unstructured"
    / "screenshots"
)

OUTPUT_DIR = (
    BASE_DIR
    / "embedding"
    / "data"
)

EMBEDDINGS_FILE = (
    OUTPUT_DIR
    / "screenshot_embeddings.npy"
)

IDS_FILE = (
    OUTPUT_DIR
    / "screenshot_ids.csv"
)

# ------------------------------------------------------------
# Batch size
# ------------------------------------------------------------

BATCH_SIZE = 16


# ============================================================
# LOAD SCREENSHOT RECORDS
# ============================================================

def load_records():

    files = sorted(
        SCREENSHOT_DIR.glob(
            "ocr_batch_*.json"
        )
    )

    if not files:
        raise FileNotFoundError(
            f"No screenshot JSON files found in:\n"
            f"{SCREENSHOT_DIR}"
        )

    print(
        f"Found {len(files)} screenshot files"
    )

    records = []

    for file_path in files:

        print(
            f"Reading {file_path.name}"
        )

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            data = json.load(f)

        if not isinstance(data, list):
            raise ValueError(
                f"{file_path.name} "
                f"must contain a JSON list."
            )

        for index, record in enumerate(data):

            records.append(
                {
                    "record": record,
                    "source_file": file_path.name,
                    "source_index": index,
                }
            )

        print(
            f"  Records: {len(data):,}"
        )

    print(
        f"\nTotal records: {len(records):,}"
    )

    return records


# ============================================================
# SCREENSHOT ID
# ============================================================

def create_screenshot_id(
    source_file,
    source_index,
):

    return (
        f"SCR-"
        f"{Path(source_file).stem}-"
        f"{source_index:04d}"
    )


# ============================================================
# BUILD TEXT
# ============================================================

def build_texts(records):

    texts = []
    screenshot_ids = []

    for item in records:

        record = item["record"]

        screenshot_id = create_screenshot_id(
            item["source_file"],
            item["source_index"],
        )

        text = build_screenshot_text(
            record,
            screenshot_id,
        )

        texts.append(text)
        screenshot_ids.append(
            screenshot_id
        )

    return texts, screenshot_ids


# ============================================================
# GENERATE EMBEDDINGS
# ============================================================

def generate_embeddings(texts):

    device = (
        "cuda"
        if torch.cuda.is_available()
        else "cpu"
    )

    print(
        f"\nLoading embedding model:"
        f" {EMBEDDING_MODEL}"
    )

    print(
        f"Device: {device}"
    )

    model = SentenceTransformer(
        EMBEDDING_MODEL,
        device=device,
    )

    dimension = (
        model.get_sentence_embedding_dimension()
    )

    print(
        f"Embedding dimension: {dimension}"
    )

    if dimension != EMBEDDING_DIMENSION:

        raise ValueError(
            f"Unexpected embedding dimension: "
            f"{dimension}. "
            f"Expected {EMBEDDING_DIMENSION}."
        )

    print(
        f"\nGenerating embeddings for "
        f"{len(texts):,} screenshots..."
    )

    embeddings = model.encode(
        texts,
        batch_size=BATCH_SIZE,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=True,
    )

    return embeddings


# ============================================================
# SAVE EMBEDDINGS
# ============================================================

def save_embeddings(
    embeddings,
    screenshot_ids,
):

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    np.save(
        EMBEDDINGS_FILE,
        embeddings,
    )

    with open(
        IDS_FILE,
        "w",
        newline="",
        encoding="utf-8",
    ) as f:

        writer = csv.writer(f)

        writer.writerow(
            ["screenshot_id"]
        )

        for screenshot_id in screenshot_ids:

            writer.writerow(
                [screenshot_id]
            )

    print(
        f"\nSaved embeddings:"
        f"\n  {EMBEDDINGS_FILE}"
    )

    print(
        f"Saved screenshot IDs:"
        f"\n  {IDS_FILE}"
    )


# ============================================================
# VALIDATE
# ============================================================

def validate_embeddings(
    embeddings,
    screenshot_ids,
):

    print("\n" + "-" * 60)
    print("EMBEDDING VALIDATION")
    print("-" * 60)

    print(
        f"Shape: {embeddings.shape}"
    )

    print(
        f"Dtype: {embeddings.dtype}"
    )

    print(
        f"Screenshot IDs: "
        f"{len(screenshot_ids):,}"
    )

    # --------------------------------------------------------
    # Shape
    # --------------------------------------------------------

    if embeddings.ndim != 2:

        raise ValueError(
            "Embeddings must be a 2D array."
        )

    if embeddings.shape[1] != EMBEDDING_DIMENSION:

        raise ValueError(
            f"Expected dimension "
            f"{EMBEDDING_DIMENSION}, "
            f"got {embeddings.shape[1]}"
        )

    # --------------------------------------------------------
    # Count
    # --------------------------------------------------------

    if embeddings.shape[0] != len(
        screenshot_ids
    ):

        raise ValueError(
            "Embedding count does not "
            "match screenshot ID count."
        )

    # --------------------------------------------------------
    # Finite values
    # --------------------------------------------------------

    if not np.isfinite(
        embeddings
    ).all():

        raise ValueError(
            "Embeddings contain "
            "NaN or infinite values."
        )

    print(
        "✓ All values are finite"
    )

    # --------------------------------------------------------
    # Norm validation
    # --------------------------------------------------------

    norms = np.linalg.norm(
        embeddings,
        axis=1,
    )

    print(
        f"Norm range: "
        f"{norms.min():.6f} → "
        f"{norms.max():.6f}"
    )

    print(
        f"Norm mean: "
        f"{norms.mean():.6f}"
    )

    if not np.allclose(
        norms,
        1.0,
        atol=5e-3,
    ):

        raise ValueError(
            "Embeddings are not normalized."
        )

    print(
        "✓ Embeddings are normalized"
    )

    # --------------------------------------------------------
    # ID uniqueness
    # --------------------------------------------------------

    if len(
        screenshot_ids
    ) != len(
        set(screenshot_ids)
    ):

        raise ValueError(
            "Duplicate screenshot IDs found."
        )

    print(
        "✓ Screenshot IDs are unique"
    )

    print(
        "\n✓ SCREENSHOT EMBEDDING "
        "VALIDATION SUCCESSFUL"
    )


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("SCREENSHOT EMBEDDING GENERATION")
    print("=" * 70)

    # --------------------------------------------------------
    # Load
    # --------------------------------------------------------

    records = load_records()

    # --------------------------------------------------------
    # Build text
    # --------------------------------------------------------

    print(
        "\nBuilding screenshot text..."
    )

    texts, screenshot_ids = (
        build_texts(records)
    )

    print(
        f"Built text for "
        f"{len(texts):,} screenshots"
    )

    # --------------------------------------------------------
    # Display one example
    # --------------------------------------------------------

    print("\n" + "-" * 70)
    print("SAMPLE SCREENSHOT TEXT")
    print("-" * 70)

    print(texts[0])

    # --------------------------------------------------------
    # Generate
    # --------------------------------------------------------

    embeddings = generate_embeddings(
        texts
    )

    # --------------------------------------------------------
    # Save
    # --------------------------------------------------------

    save_embeddings(
        embeddings,
        screenshot_ids,
    )

    # --------------------------------------------------------
    # Validate
    # --------------------------------------------------------

    validate_embeddings(
        embeddings,
        screenshot_ids,
    )

    # --------------------------------------------------------
    # Final
    # --------------------------------------------------------

    print("\n" + "=" * 70)
    print("✓ SCREENSHOT EMBEDDINGS COMPLETED")
    print("=" * 70)

    print(
        f"Screenshot embeddings : "
        f"{len(screenshot_ids):,}"
    )

    print(
        f"Vector dimension      : "
        f"{embeddings.shape[1]}"
    )


if __name__ == "__main__":
    main()