import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { GlobalProvider } from '../contexts/GlobalContext';
import MainLayout from '../layouts/MainLayout';
import LadderPage from '../pages/LadderPage';
import WatchlistPage from '../pages/WatchlistPage';
import StatisticsPage from '../pages/StatisticsPage';

const AppRouter = () => {
  return (
    <GlobalProvider>
      <Router>
        <MainLayout>
          {(props) => (
            <Routes>
              <Route path="/" element={<LadderPage {...props} />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/statistics" element={<StatisticsPage />} />
            </Routes>
          )}
        </MainLayout>
      </Router>
    </GlobalProvider>
  );
};

export default AppRouter;
