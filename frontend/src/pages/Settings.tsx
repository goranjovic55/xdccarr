import { useQuery } from '@tanstack/react-query';

interface Settings {
  sources: Record<string, { enabled: boolean; priority: number; timeout: number }>;
  search: { defaultCategory: string; maxResults: number; timeout: number };
  ui: { theme: string; resultsPerPage: number };
}

export function SettingsPage() {
  const { data: settings, isLoading } = useQuery<Settings>({
    queryKey: ['settings'],
    queryFn: () => fetch('/api/settings').then(r => r.json()),
  });

  if (isLoading) return <div className="text-arr-text">Loading...</div>;

  return (
    <div>
      <h1 className="text-2xl font-bold text-arr-text mb-6">Settings</h1>
      
      <div className="space-y-6">
        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <h2 className="text-lg font-semibold text-arr-text mb-4">Sources</h2>
          <div className="space-y-3">
            {Object.entries(settings?.sources || {}).map(([name, config]) => (
              <div key={name} className="flex items-center justify-between p-3 bg-arr-bg rounded border border-arr-border">
                <div>
                  <span className="text-arr-text font-medium">{name}</span>
                  <span className="text-arr-text-muted ml-2">Priority: {config.priority}</span>
                </div>
                <span className={config.enabled ? 'text-arr-success' : 'text-arr-danger'}>
                  {config.enabled ? '● Enabled' : '○ Disabled'}
                </span>
              </div>
            ))}
          </div>
        </div>

        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <h2 className="text-lg font-semibold text-arr-text mb-4">Search Settings</h2>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <div className="text-arr-text-muted text-sm">Default Category</div>
              <div className="text-arr-text">{settings?.search?.defaultCategory || 'All'}</div>
            </div>
            <div>
              <div className="text-arr-text-muted text-sm">Max Results</div>
              <div className="text-arr-text">{settings?.search?.maxResults || 100}</div>
            </div>
            <div>
              <div className="text-arr-text-muted text-sm">Timeout</div>
              <div className="text-arr-text">{settings?.search?.timeout || 30}s</div>
            </div>
          </div>
        </div>

        <div className="bg-arr-sidebar p-6 rounded-lg border border-arr-border">
          <h2 className="text-lg font-semibold text-arr-text mb-4">UI Settings</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="text-arr-text-muted text-sm">Theme</div>
              <div className="text-arr-text">{settings?.ui?.theme || 'dark'}</div>
            </div>
            <div>
              <div className="text-arr-text-muted text-sm">Results per Page</div>
              <div className="text-arr-text">{settings?.ui?.resultsPerPage || 25}</div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
