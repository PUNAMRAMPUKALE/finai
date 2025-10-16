# app/routes/products.py
from fastapi import APIRouter, HTTPException
from app.schemas import IngestResponse
from app.services.embeddings import embed_texts
from app.services.weaviate_db import insert_product
import json, os

router = APIRouter(prefix="/ingest/products", tags=["ingest-products"])

@router.post("", response_model=IngestResponse)
def ingest_products(path: str = "data/catalog/product_catalog.json"):
    """
    POST /ingest/products?path=...
    Reads a JSON list of products from disk and stores them with vectors for matching.
    """
    if not os.path.exists(path):
        raise HTTPException(400, f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        products = json.load(f)

    # Build one text per product for embedding
    texts = []
    for p in products:
        texts.append(" | ".join([
            p.get("name",""), p.get("type",""), p.get("region",""),
            p.get("terms",""), p.get("fees",""), p.get("eligibility",""),
            p.get("riskLabel",""), p.get("description","")
        ]))

    vectors = embed_texts(texts)
    for p, v in zip(products, vectors):
        insert_product(p, v)
    return IngestResponse(inserted=len(products))
