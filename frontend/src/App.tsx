import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Sidebar } from './components/Sidebar';
import { SearchPage } from './pages/Search';
import { ActivityPage } from './pages/Activity';

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
              <Route path="/history" element={<div>History - Coming Soon</div>} />
              <Route path="/stats" element={<div>Stats - Coming Soon</div>} />
              <Route path="/settings" element={<div>Settings - Coming Soon</div>} />
            </Routes>
          </main>
        </div>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
