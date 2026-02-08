"""
XDCCarr - XDCC Indexer for *arr ecosystem
Provides Torznab-compatible API for XDCC content
Supports: Movies, TV, Music, XXX, and all other XDCC content
"""
from fastapi import FastAPI, Query, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os
import httpx
from bs4 import BeautifulSoup
import re
from datetime import datetime
import hashlib

app = FastAPI(
    title="XDCCarr",
    description="XDCC Indexer for Prowlarr/*arr ecosystem",
    version="0.2.0"
)

# Torznab category mapping
CATEGORIES = {
    2000: "Movies",
    2010: "Movies/Foreign",
    2020: "Movies/Other",
    2030: "Movies/SD",
    2040: "Movies/HD",
    2045: "Movies/UHD",
    2050: "Movies/BluRay",
    2060: "Movies/3D",
    3000: "Audio",
    3010: "Audio/MP3",
    3020: "Audio/Video",
    3030: "Audio/Audiobook",
    3040: "Audio/Lossless",
    5000: "TV",
    5010: "TV/WEB-DL",
    5020: "TV/Foreign",
    5030: "TV/SD",
    5040: "TV/HD",
    5045: "TV/UHD",
    5050: "TV/Other",
    5060: "TV/Sport",
    5070: "TV/Anime",
    5080: "TV/Documentary",
    6000: "XXX",
    6010: "XXX/DVD",
    6020: "XXX/WMV",
    6030: "XXX/XviD",
    6040: "XXX/x264",
    6050: "XXX/Pack",
    6060: "XXX/ImageSet",
    6070: "XXX/Other",
    7000: "Other",
    7010: "Other/Misc",
    7020: "Other/Ebook",
    7030: "Other/Comics",
    8000: "Games",
}

# Torznab capabilities XML
CAPABILITIES_XML = """<?xml version="1.0" encoding="UTF-8"?>
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

async def search_xdcc(query: str, categories: list = None) -> list:
    """Search xdcc.eu for content"""
    results = []
    search_url = f"https://xdcc.eu/search.php?searchkey={query.replace(' ', '+')}"
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(search_url, timeout=30.0, follow_redirects=True)
            soup = BeautifulSoup(response.text, 'lxml')
            
            # Parse table rows
            rows = soup.select('table tr')[1:]  # Skip header
            for row in rows[:100]:  # Limit results
                cols = row.find_all('td')
                if len(cols) >= 6:
                    try:
                        network = cols[0].get_text(strip=True)
                        channel = cols[1].get_text(strip=True)
                        bot = cols[2].get_text(strip=True)
                        pack = cols[3].get_text(strip=True).replace('#', '')
                        size_text = cols[4].get_text(strip=True)
                        filename = cols[5].get_text(strip=True)
                        
                        # Parse size
                        size_bytes = parse_size(size_text)
                        
                        # Guess category
                        cat = guess_category(filename, channel)
                        
                        # Filter by category if specified
                        if categories:
                            cat_base = (cat // 1000) * 1000
                            if cat not in categories and cat_base not in categories:
                                continue
                        
                        # Generate unique ID
                        uid = hashlib.md5(f"{network}{channel}{bot}{pack}".encode()).hexdigest()[:16]
                        
                        results.append({
                            'id': uid,
                            'title': filename,
                            'size': size_bytes,
                            'network': network,
                            'channel': channel,
                            'bot': bot,
                            'pack': pack,
                            'category': cat
                        })
                    except Exception:
                        continue
        except Exception as e:
            print(f"Search error: {e}")
    
    return results

def parse_size(size_text: str) -> int:
    """Convert size string to bytes"""
    size_text = size_text.upper().strip()
    multipliers = {'K': 1024, 'M': 1024**2, 'G': 1024**3, 'T': 1024**4}
    
    match = re.match(r'([\d.]+)\s*([KMGT])?B?', size_text)
    if match:
        value = float(match.group(1))
        unit = match.group(2) or ''
        return int(value * multipliers.get(unit, 1))
    return 0

def guess_category(filename: str, channel: str = "") -> int:
    """Guess category from filename and channel"""
    fn = filename.lower()
    ch = channel.lower()
    
    # XXX detection
    xxx_keywords = ['xxx', 'porn', 'adult', '18+', 'sexart', 'vixen', 'tushy', 
                    'blacked', 'bangbros', 'brazzers', 'naughty', 'milf', 'jav']
    if any(kw in fn or kw in ch for kw in xxx_keywords):
        if '1080p' in fn or 'x264' in fn or 'x265' in fn:
            return 6040  # XXX/x264
        return 6070  # XXX/Other
    
    # Music detection
    music_keywords = ['flac', 'mp3', 'album', 'discography', '320kbps', 'lossless']
    music_extensions = ['.flac', '.mp3', '.m4a', '.ogg', '.wav']
    if any(kw in fn for kw in music_keywords) or any(fn.endswith(ext) for ext in music_extensions):
        if 'flac' in fn or 'lossless' in fn:
            return 3040  # Audio/Lossless
        return 3010  # Audio/MP3
    
    # Anime detection
    if 'anime' in ch or any(g in fn for g in ['[subsplease]', '[erai-raws]', '[horriblesubs]', 'nyaa']):
        return 5070  # TV/Anime
    
    # TV detection
    if re.search(r's\d{2}e\d{2}|season|episode|\d+x\d+', fn):
        if '2160p' in fn or '4k' in fn:
            return 5045  # TV/UHD
        if '1080p' in fn or '720p' in fn:
            return 5040  # TV/HD
        return 5030  # TV/SD
    
    # Games detection
    game_keywords = ['repack', 'gog', 'fitgirl', 'codex', 'plaza', 'skidrow']
    if any(kw in fn for kw in game_keywords):
        return 8000  # Games
    
    # Ebooks
    if any(fn.endswith(ext) for ext in ['.epub', '.mobi', '.pdf', '.azw3']):
        return 7020  # Other/Ebook
    
    # Movies (default for video content)
    if '2160p' in fn or '4k' in fn:
        return 2045  # Movies/UHD
    if 'bluray' in fn or 'blu-ray' in fn:
        return 2050  # Movies/BluRay
    if '1080p' in fn or '720p' in fn:
        return 2040  # Movies/HD
    
    return 2000  # Movies (default)

def results_to_torznab_xml(results: list) -> str:
    """Convert results to Torznab XML format"""
    items = []
    for r in results:
        # Create XDCC download link
        link = f"xdcc://{r['network']}/{r['channel']}/{r['bot']}/{r['pack']}"
        
        # Escape XML special characters
        title = r['title'].replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        
        item = f"""
        <item>
            <title>{title}</title>
            <guid>{r['id']}</guid>
            <link>{link}</link>
            <size>{r['size']}</size>
            <pubDate>{datetime.utcnow().strftime('%a, %d %b %Y %H:%M:%S +0000')}</pubDate>
            <category>{r['category']}</category>
            <torznab:attr name="category" value="{r['category']}" />
            <torznab:attr name="size" value="{r['size']}" />
            <enclosure url="{link}" length="{r['size']}" type="application/x-xdcc" />
        </item>"""
        items.append(item)
    
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom" xmlns:torznab="http://torznab.com/schemas/2015/feed">
    <channel>
        <title>XDCCarr</title>
        <description>XDCC Indexer</description>
        <atom:link href="http://localhost:9117/api" rel="self" type="application/rss+xml" />
        {''.join(items)}
    </channel>
</rss>"""

@app.get("/")
async def root():
    return {
        "name": "XDCCarr",
        "version": "0.2.0",
        "status": "ok",
        "categories": ["Movies", "TV", "Music", "XXX", "Games", "Other"]
    }

@app.get("/api")
async def torznab_api(
    t: str = Query(..., description="Action type"),
    q: str = Query(None, description="Search query"),
    apikey: str = Query(None, description="API key"),
    cat: str = Query(None, description="Categories (comma-separated)"),
    season: str = Query(None, description="Season number"),
    ep: str = Query(None, description="Episode number"),
    artist: str = Query(None, description="Artist name"),
    album: str = Query(None, description="Album name"),
    author: str = Query(None, description="Book author"),
    title: str = Query(None, description="Book title")
):
    """Torznab-compatible API endpoint"""
    
    if t == "caps":
        return Response(content=CAPABILITIES_XML, media_type="application/xml")
    
    # Parse categories
    categories = None
    if cat:
        try:
            categories = [int(c) for c in cat.split(',')]
        except ValueError:
            pass
    
    # Build search query based on type
    query_parts = []
    
    if q:
        query_parts.append(q)
    
    if t == "tvsearch":
        if season and ep:
            query_parts.append(f"S{int(season):02d}E{int(ep):02d}")
        elif season:
            query_parts.append(f"S{int(season):02d}")
    
    elif t == "music":
        if artist:
            query_parts.append(artist)
        if album:
            query_parts.append(album)
    
    elif t == "book":
        if author:
            query_parts.append(author)
        if title:
            query_parts.append(title)
    
    query = " ".join(query_parts)
    
    if not query.strip():
        return Response(content=results_to_torznab_xml([]), media_type="application/xml")
    
    results = await search_xdcc(query, categories)
    return Response(content=results_to_torznab_xml(results), media_type="application/xml")

@app.get("/health")
async def health():
    return {"status": "ok"}

# Serve frontend static files
static_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static")
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

@app.get("/")
async def serve_frontend():
    """Serve the frontend UI"""
    index_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "XDCCarr API", "docs": "/docs"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9117)
