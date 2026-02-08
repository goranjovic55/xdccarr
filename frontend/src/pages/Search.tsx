import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface SearchResult {
  id: string;
  title: string;
  size: number;
  network: string;
  channel: string;
  bot: string;
  pack: string;
  category: number;
}

const CATEGORY_NAMES: Record<number, string> = {
  2000: 'Movies',
  2040: 'Movies/HD',
  2045: 'Movies/UHD',
  3000: 'Audio',
  3010: 'Audio/MP3',
  3040: 'Audio/Lossless',
  5000: 'TV',
  5040: 'TV/HD',
  5070: 'TV/Anime',
  6000: 'XXX',
  6040: 'XXX/x264',
  8000: 'Games',
};

function formatSize(bytes: number): string {
  if (bytes >= 1073741824) return (bytes / 1073741824).toFixed(2) + ' GB';
  if (bytes >= 1048576) return (bytes / 1048576).toFixed(2) + ' MB';
  return (bytes / 1024).toFixed(2) + ' KB';
}

export function SearchPage() {
  const [query, setQuery] = useState('');
  const [searchTerm, setSearchTerm] = useState('');

  const { data: results, isLoading, error } = useQuery({
    queryKey: ['search', searchTerm],
    queryFn: async () => {
      if (!searchTerm) return [];
      const res = await axios.get(`/api/search?q=${encodeURIComponent(searchTerm)}`);
      return res.data as SearchResult[];
    },
    enabled: !!searchTerm,
  });

  const handleSearch = (e: React.FormEvent) => {
    e.preventDefault();
    setSearchTerm(query);
  };

  const handleGrab = async (result: SearchResult) => {
    try {
      await axios.post('/api/grab', result);
      alert('Download started!');
    } catch (err) {
      alert('Failed to start download');
    }
  };

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Search XDCC</h2>
      
      {/* Search Form */}
      <form onSubmit={handleSearch} className="mb-6">
        <div className="flex gap-4">
          <input
            type="text"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search for movies, TV, music, XXX..."
            className="flex-1 px-4 py-3 bg-arr-bg-alt border border-arr-border rounded-lg focus:outline-none focus:border-arr-accent"
          />
          <button type="submit" className="btn-arr-primary">
            Search
          </button>
        </div>
      </form>

      {/* Results */}
      {isLoading && <p>Searching...</p>}
      {error && <p className="text-arr-danger">Search failed</p>}
      
      {results && results.length > 0 && (
        <div className="card-arr overflow-hidden">
          <table className="table-arr">
            <thead>
              <tr>
                <th>Title</th>
                <th>Category</th>
                <th>Size</th>
                <th>Network</th>
                <th>Channel</th>
                <th>Bot</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {results.map((r) => (
                <tr key={r.id}>
                  <td className="max-w-md truncate">{r.title}</td>
                  <td>
                    <span className="px-2 py-1 bg-arr-sidebar rounded text-sm">
                      {CATEGORY_NAMES[r.category] || r.category}
                    </span>
                  </td>
                  <td>{formatSize(r.size)}</td>
                  <td className="text-arr-text-muted">{r.network}</td>
                  <td className="text-arr-text-muted">{r.channel}</td>
                  <td className="text-arr-text-muted">{r.bot}</td>
                  <td>
                    <button
                      onClick={() => handleGrab(r)}
                      className="btn-arr-primary text-sm py-1"
                    >
                      Grab
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      
      {results && results.length === 0 && searchTerm && (
        <p className="text-arr-text-muted">No results found</p>
      )}
    </div>
  );
}
