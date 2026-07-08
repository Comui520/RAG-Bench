import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { Layout } from './components/Layout';
import { ConfigPage } from './pages/ConfigPage';
import { GoldensPage } from './pages/GoldensPage';
import { ProgressPage } from './pages/ProgressPage';
import { ResultsPage } from './pages/ResultsPage';

const queryClient = new QueryClient({
  defaultOptions: { queries: { retry: 1, staleTime: 5000 } },
});

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<ConfigPage />} />
            <Route path="/task/:taskId/goldens" element={<GoldensPage />} />
            <Route path="/task/:taskId/progress" element={<ProgressPage />} />
            <Route path="/task/:taskId/results" element={<ResultsPage />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  );
}

export default App;
