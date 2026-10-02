import { QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter, Route, Routes } from 'react-router-dom';
import { queryClientInstance } from '@/lib/query-client';
import Layout from '@/components/layout/Layout';
import ScrollToTop from '@/components/ScrollToTop';
import Home from '@/pages/Home';
import RiskMap from '@/pages/RiskMap';
import AreaDetail from '@/pages/AreaDetail';
import HistoricalReplay from '@/pages/HistoricalReplay';
import Performance from '@/pages/Performance';
import ReportEvent from '@/pages/ReportEvent';
import PageNotFound from '@/lib/PageNotFound';

export default function App() {
  return <QueryClientProvider client={queryClientInstance}>
    <BrowserRouter>
      <ScrollToTop />
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Home />} />
          <Route path="/map" element={<RiskMap />} />
          <Route path="/area/:id" element={<AreaDetail />} />
          <Route path="/replay" element={<HistoricalReplay />} />
          <Route path="/performance" element={<Performance />} />
          <Route path="/report" element={<ReportEvent />} />
          <Route path="*" element={<PageNotFound />} />
        </Route>
      </Routes>
    </BrowserRouter>
  </QueryClientProvider>;
}
