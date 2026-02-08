import { useQuery } from '@tanstack/react-query';

interface HistoryItem {
  query: string;
  category: string;
  results: number;
  timestamp: string;
  source: string;
}

export function HistoryPage() {
  const { data: history, isLoading } = useQuery<HistoryItem[]>({
    queryKey: ['history'],
    queryFn: () => fetch('/api/history').then(r => r.json()),
  });

  if (isLoading) return <div className="text-arr-text">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-arr-text mb-6">Search History</h1>
      {!history?.length ? (
        <p className="text-arr-text-muted">No search history yet</p>
      ) : (
        <div className="bg-arr-sidebar rounded-lg border border-arr-border">
          <table className="w-full">
            <thead>
              <tr className="border-b border-arr-border">
                <th className="text-left p-4 text-arr-text-muted">Query</th>
                <th className="text-left p-4 text-arr-text-muted">Category</th>
                <th className="text-left p-4 text-arr-text-muted">Source</th>
                <th className="text-left p-4 text-arr-text-muted">Results</th>
                <th className="text-left p-4 text-arr-text-muted">Time</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item, i) => (
                <tr key={i} className="border-b border-arr-border last:border-0">
                  <td className="p-4 text-arr-text">{item.query}</td>
                  <td className="p-4 text-arr-text-muted">{item.category}</td>
                  <td className="p-4 text-arr-text-muted">{item.source}</td>
                  <td className="p-4 text-arr-text-muted">{item.results}</td>
                  <td className="p-4 text-arr-text-muted">{new Date(item.timestamp).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
