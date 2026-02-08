import { useQuery } from '@tanstack/react-query';
import axios from 'axios';

interface Download {
  id: string;
  title: string;
  progress: number;
  speed: string;
  eta: string;
  status: 'downloading' | 'queued' | 'completed' | 'failed';
}

export function ActivityPage() {
  const { data: downloads } = useQuery({
    queryKey: ['activity'],
    queryFn: async () => {
      const res = await axios.get('/api/activity');
      return res.data as Download[];
    },
    refetchInterval: 2000,
  });

  return (
    <div>
      <h2 className="text-2xl font-bold mb-6">Activity</h2>
      
      <div className="card-arr">
        {!downloads || downloads.length === 0 ? (
          <p className="text-arr-text-muted py-8 text-center">No active downloads</p>
        ) : (
          <table className="table-arr">
            <thead>
              <tr>
                <th>Title</th>
                <th>Progress</th>
                <th>Speed</th>
                <th>ETA</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {downloads.map((d) => (
                <tr key={d.id}>
                  <td>{d.title}</td>
                  <td>
                    <div className="w-32 bg-arr-bg rounded-full h-2">
                      <div 
                        className="bg-arr-accent h-2 rounded-full transition-all"
                        style={{ width: `${d.progress}%` }}
                      />
                    </div>
                  </td>
                  <td>{d.speed}</td>
                  <td>{d.eta}</td>
                  <td>
                    <span className={`px-2 py-1 rounded text-sm ${
                      d.status === 'completed' ? 'bg-arr-success/20 text-arr-success' :
                      d.status === 'failed' ? 'bg-arr-danger/20 text-arr-danger' :
                      d.status === 'downloading' ? 'bg-arr-accent/20 text-arr-accent' :
                      'bg-arr-bg text-arr-text-muted'
                    }`}>
                      {d.status}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
