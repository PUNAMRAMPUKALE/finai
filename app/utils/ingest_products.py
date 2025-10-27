# app/utils/ingest_products.py
import json
import re
from pathlib import Path
from sqlmodel import Session, select
from app.db.core import engine, init_db
from app.db.models import Product

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "product_catalog.json"

def slugify_name(name: str) -> str:
    s = name.strip().lower()
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")

def main():
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Could not find product catalog at: {DATA_FILE}")

    init_db()  # ensure tables exist
    items = json.loads(DATA_FILE.read_text())

    inserted, updated = 0, 0
    with Session(engine) as s:
        for it in items:
            pid = slugify_name(it.get("name", ""))
            if not pid:
                continue

            existing = s.exec(select(Product).where(Product.product_id == pid)).first()
            payload = Product(
                product_id=pid,
                name=it.get("name", ""),
                type=it.get("type"),
                description=it.get("description"),
                region=it.get("region"),
                terms=it.get("terms"),
                fees=it.get("fees"),
                eligibility=it.get("eligibility"),
                risk_label=it.get("riskLabel"),
                meta=it,
            )
            if existing:
                # update fields
                for f in ["name","type","description","region","terms","fees","eligibility","risk_label","meta"]:
                    setattr(existing, f, getattr(payload, f))
                updated += 1
            else:
                s.add(payload)
                inserted += 1
        s.commit()
    print(f"Products: inserted={inserted}, updated={updated}")

if __name__ == "__main__":
    main()
