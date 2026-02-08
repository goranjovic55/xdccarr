"""XDCCarr - XDCC Indexer for *arr ecosystem"""
from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, FileResponse
import httpx
from bs4 import BeautifulSoup
import hashlib
import re
from datetime import datetime
from pathlib import Path
from typing import Optional
import os
from src.sources import search_all_sources, SOURCES


app = FastAPI(title="XDCCarr", version="0.2.0")

# In-memory cache for grab lookups - define BEFORE it's used
_result_cache = {}

# Serve static files for WebUI
static_path = Path(__file__).parent.parent / "static"
if static_path.exists() and (static_path / "index.html").exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")

CATEGORIES = {
    "Movies": 2000, "Movies/HD": 2040, "Movies/UHD": 2045, "Movies/BluRay": 2050,
    "Audio": 3000, "Audio/MP3": 3010, "Audio/Lossless": 3040,
    "TV": 5000, "TV/HD": 5040, "TV/UHD": 5045, "TV/Anime": 5070,
    "XXX": 6000, "XXX/x264": 6040, "XXX/Other": 6070,
    "Other": 7000, "Other/Ebook": 7020,
    "Games": 8000,
}

def parse_size(size_str: str) -> int:
    """Convert size string like '3.5G' to bytes"""
    if not size_str:
        return 0
    size_str = size_str.strip().upper()
    multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    for suffix, mult in multipliers.items():
        if size_str.endswith(suffix):
            try:
                return int(float(size_str[:-1]) * mult)
            except ValueError:
                return 0
    try:
        return int(size_str)
    except ValueError:
        return 0

def detect_category(filename: str) -> int:
    """Detect category from filename"""
    fn = filename.lower()
    
    # XXX detection
    if any(x in fn for x in ['xxx', 'porn', 'adult', 'sex', 'brazzers', 'bangbros', 'naughty']):
        if '264' in fn or 'hevc' in fn or 'x265' in fn:
            return 6040
        return 6070
    
    # TV detection
    if re.search(r's\d{1,2}e\d{1,2}', fn) or re.search(r'\d{1,2}x\d{1,2}', fn):
        if any(x in fn for x in ['anime', 'horriblesubs', 'erai', 'subsplease']):
            return 5070
        if any(x in fn for x in ['2160p', '4k', 'uhd']):
            return 5045
        if any(x in fn for x in ['1080p', '720p', 'hdtv', 'webrip', 'web-dl']):
            return 5040
        return 5000
    
    # Audio detection
    if any(x in fn for x in ['.flac', '.wav', '.alac', 'lossless']):
        return 3040
    if any(x in fn for x in ['.mp3', '.aac', '.m4a', 'album', 'discography']):
        return 3010
    if any(x in fn for x in ['music', 'soundtrack', 'ost']):
        return 3000
    
    # Games detection
    if any(x in fn for x in ['fitgirl', 'codex', 'skidrow', 'plaza', 'gog', '.iso', 'repack']):
        return 8000
    
    # Ebook detection
    if any(x in fn for x in ['.epub', '.mobi', '.pdf', 'ebook', '.azw']):
        return 7020
    
    # Movies (default for video)
    if any(x in fn for x in ['2160p', '4k', 'uhd']):
        return 2045
    if 'bluray' in fn or 'blu-ray' in fn:
        return 2050
    if any(x in fn for x in ['1080p', '720p', 'brrip', 'dvdrip', 'webrip']):
        return 2040
    if any(x in fn for x in ['.mkv', '.mp4', '.avi']):
        return 2000
    
    return 7000  # Other


def transform_results(raw_results: list, base_url: str = "http://localhost:9117") -> list:
    """Transform raw source results into Torznab-compatible format"""
    results = []
    
    for r in raw_results:
        try:
            filename = r.get('filename', '')
            if not filename:
                continue
            
            server = r.get('server', r.get('network', ''))
            channel = r.get('channel', '')
            bot = r.get('bot', '')
            pack = r.get('pack', '')
            
            # Generate unique ID
            uid = hashlib.md5(f"{server}{channel}{bot}{pack}".encode()).hexdigest()[:16]
            
            # Store in cache for grab endpoint
            _result_cache[uid] = {
                "server": server,
                "channel": channel, 
                "bot": bot,
                "pack": pack,
                "filename": filename
            }
            
            # Use HTTP grab URL for Prowlarr compatibility
            grab_url = f"{base_url}/grab?id={uid}"
            
            results.append({
                "id": uid,
                "title": filename,
                "size": parse_size(r.get('size_str', '0')),
                "size_str": r.get('size_str', ''),
                "network": r.get('network', ''),
                "server": server,
                "channel": channel,
                "bot": bot,
                "pack": pack,
                "category": detect_category(filename),
                "link": grab_url,
                "pubdate": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
            })
        except Exception as e:
            continue
    
    return results


def generate_torznab_xml(results: list, title: str = "XDCCarr") -> str:
    """Generate Torznab-compatible XML response"""
    items = []
    for r in results:
        # Escape XML special characters
        title_text = str(r.get('title', '')).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        items.append(f"""
        <item>
            <title>{title_text}</title>
            <guid>{r['id']}</guid>
            <link>{r['link']}</link>
            <size>{r['size']}</size>
            <pubDate>{r['pubdate']}</pubDate>
            <category>{r['category']}</category>
            <torznab:attr name="category" value="{r['category']}" />
            <torznab:attr name="size" value="{r['size']}" />
            <enclosure url="{r['link']}" length="{r['size']}" type="application/x-xdcc" />
        </item>""")
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <title>{title}</title>
        <description>XDCC Indexer</description>
        <atom:link href="http://localhost:9117/api" rel="self" type="application/rss+xml" />
        {"".join(items)}
    </channel>
</rss>"""

def generate_caps_xml() -> str:
    """Generate Torznab capabilities XML"""
    return """<?xml version="1.0" encoding="UTF-8"?>
<caps>
    <server title="XDCCarr" />
    <limits default="100" max="500" />
    <searching>
        <search available="yes" supportedParams="q" />
        <tv-search available="yes" supportedParams="q,season,ep" />
        <movie-search available="yes" supportedParams="q" />
        <music-search available="yes" supportedParams="q,artist,album" />
        <book-search available="yes" supportedParams="q,author,title" />
    </searching>
    <categories>
        <category id="2000" name="Movies">
            <subcat id="2040" name="Movies/HD" />
            <subcat id="2045" name="Movies/UHD" />
            <subcat id="2050" name="Movies/BluRay" />
        </category>
        <category id="3000" name="Audio">
            <subcat id="3010" name="Audio/MP3" />
            <subcat id="3040" name="Audio/Lossless" />
        </category>
        <category id="5000" name="TV">
            <subcat id="5040" name="TV/HD" />
            <subcat id="5045" name="TV/UHD" />
            <subcat id="5070" name="TV/Anime" />
        </category>
        <category id="6000" name="XXX">
            <subcat id="6040" name="XXX/x264" />
            <subcat id="6070" name="XXX/Other" />
        </category>
        <category id="7000" name="Other">
            <subcat id="7020" name="Other/Ebook" />
        </category>
        <category id="8000" name="Games" />
    </categories>
</caps>"""

@app.get("/")
async def root():
    """Root endpoint - serve WebUI or API info"""
    index_file = static_path / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "name": "XDCCarr",
        "version": "0.2.0",
        "status": "ok",
        "categories": list(CATEGORIES.keys())[:6]
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/api")
async def api(
    t: str = Query("search", description="API function"),
    q: Optional[str] = Query(None, description="Search query"),
    cat: Optional[str] = Query(None, description="Category filter"),
    limit: int = Query(100, description="Result limit"),
    extended: int = Query(0, description="Extended info"),
    offset: int = Query(0, description="Result offset")
):
    """Torznab-compatible API endpoint"""
    
    if t == "caps":
        return Response(content=generate_caps_xml(), media_type="application/xml")
    
    if t in ["search", "tvsearch", "movie", "music"]:
        if not q:
            return Response(content=generate_torznab_xml([]), media_type="application/xml")
        
        # Get raw results from sources
        raw_results = await search_all_sources(q, limit if limit > 0 else 100)
        
        # Transform into Torznab-compatible format
        results = transform_results(raw_results)
        
        # Filter by category if specified
        if cat:
            try:
                cat_ids = [int(c) for c in cat.split(",")]
                results = [r for r in results if r["category"] in cat_ids or r["category"] // 1000 * 1000 in cat_ids]
            except ValueError:
                pass
        
        return Response(content=generate_torznab_xml(results), media_type="application/xml")
    
    return Response(content=generate_caps_xml(), media_type="application/xml")

@app.get("/api/search")
async def api_search(q: str = Query(...), limit: int = Query(100)):
    """JSON search endpoint for WebUI"""
    raw_results = await search_all_sources(q, limit)
    return transform_results(raw_results)

@app.post("/api/grab")
async def api_grab(item: dict):
    """Trigger XDCC download"""
    # TODO: Integrate with irssi/autodl
    return {"status": "queued", "item": item}


@app.get("/grab")
async def grab(id: str = Query(..., description="Result ID to grab")):
    """
    Trigger XDCC download for a result.
    Called by Prowlarr when user clicks download.
    """
    if id not in _result_cache:
        return Response(
            content='{"status": "error", "message": "Result not found or expired. Please search again."}',
            media_type="application/json",
            status_code=404
        )
    
    item = _result_cache[id]
    
    # Build irssi command
    server = item.get("server", "")
    channel = item.get("channel", "")
    bot = item.get("bot", "")
    pack = item.get("pack", "")
    
    if not all([server, bot, pack]):
        return Response(
            content='{"status": "error", "message": "Missing XDCC details"}',
            media_type="application/json",
            status_code=400
        )
    
    # Create XDCC command
    xdcc_cmd = f"/msg {bot} xdcc send #{pack}"
    
    # Write to queue file for processing
    queue_file = Path("/app/config/xdcc_queue.txt")
    queue_file.parent.mkdir(parents=True, exist_ok=True)
    
    with open(queue_file, "a") as f:
        f.write(f"{server}|{channel}|{bot}|{pack}|{item.get('filename', '')}\n")
    
    return {
        "status": "queued",
        "message": f"XDCC download queued: {bot} #{pack}",
        "details": item,
        "command": xdcc_cmd
    }


@app.get("/sources")
async def list_sources():
    """List configured XDCC sources"""
    return {
        "sources": [{"name": s.name, "url": s.base_url} for s in SOURCES]
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9117)

# ============== ACTIVITY HISTORY ==============
from datetime import datetime
import json
from pathlib import Path

DATA_DIR = Path("/app/data")
DATA_DIR.mkdir(exist_ok=True)

HISTORY_FILE = DATA_DIR / "history.json"
SETTINGS_FILE = DATA_DIR / "settings.json"
STATS_FILE = DATA_DIR / "stats.json"

def load_json(path: Path, default=None):
    if default is None:
        default = []
    try:
        if path.exists():
            return json.loads(path.read_text())
    except:
        pass
    return default

def save_json(path: Path, data):
    path.write_text(json.dumps(data, indent=2))

# Activity History
@app.get("/api/history")
async def get_history(limit: int = Query(100)):
    """Get recent activity/search history"""
    history = load_json(HISTORY_FILE, [])
    return history[:limit]

@app.post("/api/history")
async def add_history(entry: dict):
    """Add entry to history"""
    history = load_json(HISTORY_FILE, [])
    entry["timestamp"] = datetime.utcnow().isoformat()
    history.insert(0, entry)
    history = history[:1000]  # Keep last 1000
    save_json(HISTORY_FILE, history)
    return {"status": "ok"}

@app.delete("/api/history")
async def clear_history():
    """Clear all history"""
    save_json(HISTORY_FILE, [])
    return {"status": "cleared"}

# Settings
DEFAULT_SETTINGS = {
    "sources": {
        "xdcc.eu": {"enabled": True, "priority": 1},
        "xdcc.it": {"enabled": True, "priority": 2},
    },
    "search": {
        "defaultLimit": 100,
        "timeout": 30,
    },
    "ui": {
        "theme": "dark",
        "resultsPerPage": 50,
    }
}

@app.get("/api/settings")
async def get_settings():
    """Get current settings"""
    settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    return settings

@app.put("/api/settings")
async def update_settings(settings: dict):
    """Update settings"""
    current = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
    current.update(settings)
    save_json(SETTINGS_FILE, current)
    return {"status": "ok", "settings": current}

# Stats
@app.get("/api/stats")
async def get_stats():
    """Get usage statistics"""
    stats = load_json(STATS_FILE, {
        "totalSearches": 0,
        "totalGrabs": 0,
        "searchesBySource": {},
        "topSearches": [],
        "grabsByCategory": {},
        "lastUpdated": None
    })
    return stats

def update_stats(search_term: str = None, source: str = None, grab: bool = False, category: int = None):
    """Update statistics"""
    stats = load_json(STATS_FILE, {
        "totalSearches": 0,
        "totalGrabs": 0,
        "searchesBySource": {},
        "topSearches": [],
        "grabsByCategory": {},
        "lastUpdated": None
    })
    
    if search_term:
        stats["totalSearches"] += 1
        # Track top searches
        top = stats.get("topSearches", [])
        found = False
        for item in top:
            if item["term"] == search_term:
                item["count"] += 1
                found = True
                break
        if not found:
            top.append({"term": search_term, "count": 1})
        top.sort(key=lambda x: x["count"], reverse=True)
        stats["topSearches"] = top[:50]
    
    if source:
        stats["searchesBySource"][source] = stats["searchesBySource"].get(source, 0) + 1
    
    if grab:
        stats["totalGrabs"] += 1
        if category:
            cat_str = str(category)
            stats["grabsByCategory"][cat_str] = stats["grabsByCategory"].get(cat_str, 0) + 1
    
    stats["lastUpdated"] = datetime.utcnow().isoformat()
    save_json(STATS_FILE, stats)
