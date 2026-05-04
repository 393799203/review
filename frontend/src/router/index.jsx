import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { GlobalProvider } from '../contexts/GlobalContext';
import MainLayout from '../layouts/MainLayout';
import LadderPage from '../pages/LadderPage';
import SettingsPage from '../pages/SettingsPage';

const AppRouter = () => {
  return (
    <GlobalProvider>
      <Router>
        <MainLayout>
          {(props) => (
            <Routes>
              <Route path="/" element={<LadderPage {...props} />} />
              <Route path="/analysis" element={<div style={{ padding: 24, textAlign: 'center' }}>数据分析页面（开发中）</div>} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          )}
        </MainLayout>
      </Router>
    </GlobalProvider>
  );
};

export default AppRouter;
