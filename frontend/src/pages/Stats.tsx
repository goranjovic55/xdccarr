import { useQuery } from '@tanstack/react-query';

interface Stats {
  totalSearches: number;
  totalGrabs: number;
  searchesBySource: Record<string, number>;
  topSearches: Array<{ query: string; count: number }>;
  grabsByCategory: Record<string, number>;
  lastUpdated: string | null;
}

export function StatsPage() {
  const { data: stats, isLoading } = useQuery<Stats>({
    queryKey: ['stats'],
    queryFn: () => fetch('/api/stats').then(r => r.json()),
  });

  if (isLoading) return <div className="text-arr-text">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-arr-text mb-6">Statistics</h1>
      
      <div className="grid grid-cols-2 gap-4 mb-6">
        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <div className="text-3xl font-bold text-arr-accent">{stats?.totalSearches || 0}</div>
          <div className="text-arr-text-muted">Total Searches</div>
        </div>
        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <div className="text-3xl font-bold text-arr-success">{stats?.totalGrabs || 0}</div>
          <div className="text-arr-text-muted">Total Grabs</div>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <h2 className="text-lg font-semibold text-arr-text mb-4">Searches by Source</h2>
          {Object.entries(stats?.searchesBySource || {}).length === 0 ? (
            <p className="text-arr-text-muted">No data yet</p>
          ) : (
            <ul className="space-y-2">
              {Object.entries(stats?.searchesBySource || {}).map(([source, count]) => (
                <li key={source} className="flex justify-between text-arr-text">
                  <span>{source}</span>
                  <span className="text-arr-text-muted">{count}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
        
        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <h2 className="text-lg font-semibold text-arr-text mb-4">Top Searches</h2>
          {(stats?.topSearches?.length || 0) === 0 ? (
            <p className="text-arr-text-muted">No data yet</p>
          ) : (
            <ul className="space-y-2">
              {stats?.topSearches?.map((item, i) => (
                <li key={i} className="flex justify-between text-arr-text">
                  <span>{item.query}</span>
                  <span className="text-arr-text-muted">{item.count}</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
