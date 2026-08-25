"""Planted P1: dual public paths populate different output fields."""


def process_full(row: dict) -> dict:
    return {"name": row["name"].strip(), "batch_id": row.get("batch_id")}


def process_only(row: dict) -> dict:
    return {"name": row["name"].strip()}
