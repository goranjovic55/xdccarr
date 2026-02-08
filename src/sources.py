"""XDCC Source Providers"""
import httpx
from bs4 import BeautifulSoup
from typing import List, Dict
import re

class XDCCSource:
    """Base class for XDCC sources"""
    name: str = "base"
    base_url: str = ""
    
    async def search(self, query: str, limit: int = 100) -> List[Dict]:
        raise NotImplementedError

class XDCCEUSource(XDCCSource):
    """xdcc.eu parser"""
    name = "xdcc.eu"
    base_url = "https://www.xdcc.eu"
    
    async def search(self, query: str, limit: int = 100) -> List[Dict]:
        results = []
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                url = f"{self.base_url}/search.php?searchkey={query}"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
                })
                
                if resp.status_code != 200:
                    return results
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                table = soup.find('table', {'id': 'table'}) or soup.find('table', {'id': 'packets'})
                
                if not table:
                    return results
                
                rows = table.find_all('tr')[1:]
                
                for row in rows[:limit]:
                    cols = row.find_all('td')
                    if len(cols) < 7:
                        continue
                    
                    try:
                        network = cols[0].get_text(strip=True)
                        channel_td = cols[1]
                        info_link = channel_td.find('a', {'class': 'info'})
                        
                        if info_link:
                            server = info_link.get('data-s', network)
                            channel = info_link.get('data-c', '')
                        else:
                            server = network
                            channel = channel_td.get_text(strip=True).split()[0] if channel_td.get_text() else ''
                        
                        bot = cols[2].get_text(strip=True)
                        pack = cols[3].get_text(strip=True).replace('#', '')
                        size_str = cols[5].get_text(strip=True)
                        
                        filename_td = cols[6]
                        for span in filename_td.find_all('span', {'class': 'hit'}):
                            span.unwrap()
                        filename = filename_td.get_text(strip=True)
                        
                        if filename:
                            results.append({
                                "source": self.name,
                                "network": network,
                                "server": server,
                                "channel": channel,
                                "bot": bot,
                                "pack": pack,
                                "size_str": size_str,
                                "filename": filename
                            })
                    except:
                        continue
                        
        except Exception as e:
            print(f"xdcc.eu error: {e}")
        
        return results

class XDCCITSource(XDCCSource):
    """xdcc.it parser"""
    name = "xdcc.it"
    base_url = "https://www.xdcc.it"
    
    async def search(self, query: str, limit: int = 100) -> List[Dict]:
        results = []
        try:
            async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
                url = f"{self.base_url}/search?q={query}"
                resp = await client.get(url, headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"
                })
                
                if resp.status_code != 200:
                    return results
                
                soup = BeautifulSoup(resp.text, 'html.parser')
                
                # xdcc.it uses table rows with class 'pkt'
                rows = soup.find_all('tr', {'class': 'pkt'})
                
                for row in rows[:limit]:
                    cols = row.find_all('td')
                    if len(cols) < 5:
                        continue
                    
                    try:
                        # xdcc.it structure: Network, Channel, Bot, Pack#, Size, Filename
                        network = cols[0].get_text(strip=True)
                        channel = cols[1].get_text(strip=True)
                        bot = cols[2].get_text(strip=True)
                        pack = cols[3].get_text(strip=True).replace('#', '')
                        size_str = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                        filename = cols[5].get_text(strip=True) if len(cols) > 5 else cols[4].get_text(strip=True)
                        
                        # Determine server from network name
                        server_map = {
                            'Rizon': 'irc.rizon.net',
                            'EFnet': 'irc.efnet.org',
                            'Undernet': 'us.undernet.org',
                            'IRCHighway': 'irc.irchighway.net',
                            'Abjects': 'irc.abjects.net',
                        }
                        server = server_map.get(network, f"irc.{network.lower()}.net")
                        
                        if filename:
                            results.append({
                                "source": self.name,
                                "network": network,
                                "server": server,
                                "channel": channel,
                                "bot": bot,
                                "pack": pack,
                                "size_str": size_str,
                                "filename": filename
                            })
                    except:
                        continue
                        
        except Exception as e:
            print(f"xdcc.it error: {e}")
        
        return results

# Available sources
SOURCES = [
    XDCCEUSource(),
    XDCCITSource(),
]

async def search_all_sources(query: str, limit: int = 100) -> List[Dict]:
    """Search all configured XDCC sources"""
    all_results = []
    
    for source in SOURCES:
        try:
            results = await source.search(query, limit)
            all_results.extend(results)
        except Exception as e:
            print(f"Source {source.name} failed: {e}")
    
    return all_results[:limit]
