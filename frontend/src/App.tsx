import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from './components/Sidebar';
import { SearchPage } from './pages/Search';
import { ActivityPage } from './pages/Activity';
import { HistoryPage } from './pages/History';
import { StatsPage } from './pages/Stats';
import { SettingsPage } from './pages/Settings';

const queryClient = new QueryClient();

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <div className="flex">
          <Sidebar />
          <main className="ml-56 flex-1 p-8 min-h-screen">
            <Routes>
              <Route path="/" element={<SearchPage />} />
              <Route path="/activity" element={<ActivityPage />} />
              <Route path="/history" element={<HistoryPage />} />
              <Route path="/stats" element={<StatsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
