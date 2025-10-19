# app/routes/products.py
from fastapi import APIRouter, HTTPException
from app.api.v1.schemas import IngestResponse
from app.ml.embeddings import embed_texts
from app.adapters.vector.weaviate_products import insert_product
import json, os
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel
from typing import List, Dict, Any, Optional


router = APIRouter(prefix="/ingest/products", tags=["ingest-products"])

# --- existing path-based endpoint (kept) ---
@router.post("", response_model=IngestResponse)
def ingest_products(path: str = "data/catalog/product_catalog.json"):
    if not os.path.exists(path):
        raise HTTPException(400, f"File not found: {path}")
    with open(path, "r", encoding="utf-8") as f:
        products = json.load(f)
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

# --- NEW: JSON body endpoint ---
class ProductList(BaseModel):
    products: List[Dict[str, Any]]

@router.post("/json", response_model=IngestResponse)
def ingest_products_json(payload: ProductList):
    products = payload.products or []
    if not products:
        raise HTTPException(400, "No products provided.")
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
