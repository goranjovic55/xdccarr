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

app = FastAPI(title="XDCCarr", version="0.2.0")

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

async def search_xdcc(query: str, limit: int = 100) -> list:
    """Search xdcc.eu and parse results"""
    results = []
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            url = f"https://www.xdcc.eu/search.php?searchkey={query}"
            resp = await client.get(url, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
            })
            
            if resp.status_code != 200:
                return results
            
            soup = BeautifulSoup(resp.text, 'html.parser')
            
            # Find the results table
            table = soup.find('table', {'id': 'packets'})
            if not table:
                return results
            
            rows = table.find_all('tr')[1:]  # Skip header
            
            for row in rows[:limit]:
                cols = row.find_all('td')
                if len(cols) < 7:
                    continue
                
                try:
                    # Column mapping for xdcc.eu:
                    # 0: Network, 1: Channel info, 2: Bot, 3: Pack, 4: Downloads, 5: Size, 6: Filename
                    network = cols[0].get_text(strip=True)
                    
                    # Extract IRC details from channel column data attributes
                    channel_td = cols[1]
                    info_link = channel_td.find('a', {'class': 'info'})
                    
                    if info_link:
                        server = info_link.get('data-s', network)
                        channel = info_link.get('data-c', '')
                        xdcc_cmd = info_link.get('data-p', '')
                    else:
                        server = network
                        channel = channel_td.get_text(strip=True).split()[0] if channel_td.get_text() else ''
                        xdcc_cmd = ''
                    
                    bot = cols[2].get_text(strip=True)
                    pack = cols[3].get_text(strip=True).replace('#', '')
                    # cols[4] is download count, skip
                    size_str = cols[5].get_text(strip=True)
                    
                    # Filename - strip hit highlighting
                    filename_td = cols[6]
                    for span in filename_td.find_all('span', {'class': 'hit'}):
                        span.unwrap()
                    filename = filename_td.get_text(strip=True)
                    
                    if not filename:
                        continue
                    
                    # Generate unique ID
                    uid = hashlib.md5(f"{server}{channel}{bot}{pack}".encode()).hexdigest()[:16]
                    
                    # Build xdcc:// link
                    xdcc_link = f"xdcc://{server}/{channel}/{bot}/{pack}"
                    
                    results.append({
                        "id": uid,
                        "title": filename,
                        "size": parse_size(size_str),
                        "size_str": size_str,
                        "network": network,
                        "server": server,
                        "channel": channel,
                        "bot": bot,
                        "pack": pack,
                        "xdcc_cmd": xdcc_cmd,
                        "category": detect_category(filename),
                        "link": xdcc_link,
                        "pubdate": datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")
                    })
                    
                except Exception as e:
                    continue
                    
    except Exception as e:
        print(f"Search error: {e}")
    
    return results

def generate_torznab_xml(results: list, title: str = "XDCCarr") -> str:
    """Generate Torznab-compatible XML response"""
    items = []
    for r in results:
        items.append(f"""
        <item>
            <title>{r['title']}</title>
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
    limit: int = Query(100, description="Result limit")
):
    """Torznab-compatible API endpoint"""
    
    if t == "caps":
        return Response(content=generate_caps_xml(), media_type="application/xml")
    
    if t in ["search", "tvsearch", "movie", "music"]:
        if not q:
            return Response(content=generate_torznab_xml([]), media_type="application/xml")
        
        results = await search_xdcc(q, limit)
        
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
    results = await search_xdcc(q, limit)
    return results

@app.post("/api/grab")
async def api_grab(item: dict):
    """Trigger XDCC download"""
    # TODO: Integrate with irssi/autodl
    return {"status": "queued", "item": item}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9117)
