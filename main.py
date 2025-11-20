import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Any
import json
from urllib.parse import urlencode
from urllib.request import urlopen, Request

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI Backend!"}

@app.get("/api/hello")
def hello():
    return {"message": "Hello from the backend API!"}


def _fetch_json(url: str) -> Dict[str, Any]:
    req = Request(url, headers={"User-Agent": "Flames.Blue Omsk Gallery/1.0"})
    with urlopen(req, timeout=10) as resp:
        data = resp.read().decode("utf-8")
        return json.loads(data)


def search_commons_images(queries: List[str], limit: int = 30, thumb_size: int = 800) -> List[Dict[str, Any]]:
    """Search Wikimedia for images related to provided queries and return unique results with thumbnails."""
    results: Dict[int, Dict[str, Any]] = {}

    for q in queries:
        params = {
            "action": "query",
            "format": "json",
            "generator": "search",
            "gsrsearch": q,
            "gsrlimit": min(limit, 50),
            "prop": "pageimages|info",
            "inprop": "url",
            "pithumbsize": thumb_size,
            # namespace 6 is File:, but we search pages and get thumbnails if present
        }
        url = "https://commons.wikimedia.org/w/api.php?" + urlencode(params)
        try:
            data = _fetch_json(url)
            pages = data.get("query", {}).get("pages", {})
            for pid, page in pages.items():
                if "thumbnail" in page:
                    results[int(pid)] = {
                        "id": int(pid),
                        "title": page.get("title"),
                        "page_url": page.get("fullurl"),
                        "thumbnail": page.get("thumbnail", {}).get("source"),
                        "width": page.get("thumbnail", {}).get("width"),
                        "height": page.get("thumbnail", {}).get("height"),
                        "source": "Wikimedia Commons",
                        "license": "See source page",
                    }
        except Exception:
            # Continue with what we have
            continue

    # Return up to limit unique images
    return list(results.values())[:limit]


@app.get("/api/omsk/photos")
def omsk_photos() -> Dict[str, Any]:
    """Return curated set of Wikimedia Commons images for Omsk at night/winter."""
    queries = [
        "Омск ночь",
        "Омск зима",
        "Lyubinsky Avenue Omsk night",
        "Assumption Cathedral Omsk night",
        "Omsk Irtysh embankment night",
        "Omsk Drama Theater night",
        "Buchholz Square Omsk night",
        "Omsk fortress night",
    ]
    items = search_commons_images(queries, limit=32, thumb_size=1024)
    return {"items": items}


@app.get("/api/sim-info")
def sim_info() -> Dict[str, Any]:
    """Provide general info about buying and registering SIM cards in Omsk (Russia)."""
    return {
        "city": "Омск",
        "country": "Россия",
        "operators": [
            {
                "name": "МТС",
                "notes": "Широкое покрытие по городу, выгодные пакеты интернета. Фирменные салоны в центре и ТРЦ.",
                "website": "https://omsk.mts.ru/",
            },
            {
                "name": "Билайн",
                "notes": "Стабильный 4G в центральных районах, гибкие тарифы.",
                "website": "https://omsk.beeline.ru/",
            },
            {
                "name": "МегаФон",
                "notes": "Хороший мобильный интернет, много точек продаж.",
                "website": "https://omsk.megafon.ru/",
            },
            {
                "name": "Tele2",
                "notes": "Доступные пакеты, часто выгодные акции для интернета.",
                "website": "https://omsk.tele2.ru/",
            },
        ],
        "where_to_buy": [
            "Фирменные салоны операторов в центре (Любинский проспект, ул. Ленина, ТРЦ МЕГА, Континент).",
            "Официальные точки продаж в ТЦ/ТЦ у метро (если есть), а также киоски связи.",
            "В аэропорту Омск (OMS) выбор ограничен — лучше покупать в городе.",
        ],
        "requirements": [
            "Паспорт РФ для граждан России.",
            "Для иностранцев: загранпаспорт, миграционная карта/регистрация. Оформление по закону обязательно.",
            "Оформление SIM занимает 5–10 минут, номер активируется сразу или в течение суток.",
        ],
        "tips": [
            "Проверьте покрытие и действующие акции на сайтах операторов.",
            "Сохраните чек и договор — пригодится для поддержки.",
            "Пополнение: терминалы, банки, приложения операторов.",
        ],
        "disclaimer": "Информация носит справочный характер. Уточняйте актуальные условия на сайтах операторов или в салонах."
    }


@app.get("/test")
def test_database():
    """Test endpoint to check if database is available and accessible"""
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }
    
    try:
        # Try to import database module
        from database import db
        
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"
            
            # Try to list collections to verify connectivity
            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]  # Show first 10 collections
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"
            
    except ImportError:
        response["database"] = "❌ Database module not found (run enable-database first)"
    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"
    
    # Check environment variables
    import os
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"
    
    return response


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
