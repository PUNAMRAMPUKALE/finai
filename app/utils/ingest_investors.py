import json
from pathlib import Path
from typing import Dict, Any
from sqlmodel import Session, select
from app.db.core import engine, init_db
from app.db.models import Investor

DATA_FILE = Path(__file__).resolve().parents[2] / "data" / "investors.json"

def load_investors() -> list[Dict[str, Any]]:
    if not DATA_FILE.exists():
        raise FileNotFoundError(f"Could not find investors json at: {DATA_FILE}")
    with open(DATA_FILE, "r") as f:
        return json.load(f)

def main():
    init_db()
    rows = load_investors()
    inserted, updated = 0, 0
    with Session(engine) as s:
        for r in rows:
            name = (r.get("name") or "").strip()
            if not name:
                continue
            inv = s.exec(select(Investor).where(Investor.name == name)).first()
            if inv:
                for k, v in r.items():
                    if hasattr(inv, k):
                        setattr(inv, k, v)
                updated += 1
            else:
                s.add(Investor(**{k: v for k, v in r.items() if hasattr(Investor, k)}))
                inserted += 1
        s.commit()
    print(f"Investors: inserted={inserted}, updated={updated}")

if __name__ == "__main__":
    main()