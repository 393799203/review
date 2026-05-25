import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, useLocation } from 'react-router-dom';
import { GlobalProvider } from '../contexts/GlobalContext';
import { AuthProvider, useAuth } from '../contexts/AuthContext';
import MainLayout from '../layouts/MainLayout';
import LadderPage from '../pages/LadderPage';
import WatchlistPage from '../pages/WatchlistPage';
import StatisticsPage from '../pages/StatisticsPage';
import NewsPage from '../pages/NewsPage';
import ReportPage from '../pages/ReportPage';
import UserDashboardPage from '../pages/UserDashboardPage';
import HotStocksPage from '../pages/HotStocksPage';
import AuthPage from '../pages/AuthPage';

const ProtectedRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return null;
  }

  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  return children;
};

const AdminRoute = ({ children }) => {
  const { isAdmin, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return null;
  }

  if (!isAdmin) {
    return <Navigate to="/" replace />;
  }

  return children;
};

const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading } = useAuth();
  const location = useLocation();

  if (loading) {
    return null;
  }

  if (isAuthenticated) {
    const from = location.state?.from?.pathname || '/';
    return <Navigate to={from} replace />;
  }

  return children;
};

const AppRouter = () => {
  return (
    <AuthProvider>
      <Router>
        <Routes>
          <Route
            path="/login"
            element={
              <PublicRoute>
                <AuthPage />
              </PublicRoute>
            }
          />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <GlobalProvider>
                  <MainLayout>
                    <Routes>
                      <Route path="/" element={<LadderPage />} />
                      <Route path="/watchlist" element={<WatchlistPage />} />
                      <Route path="/statistics" element={<StatisticsPage />} />
                      <Route path="/news" element={<NewsPage />} />
                      <Route path="/reports" element={<ReportPage />} />
                      <Route path="/hot-stocks" element={<HotStocksPage />} />
                      <Route 
                        path="/user" 
                        element={
                          <AdminRoute>
                            <UserDashboardPage />
                          </AdminRoute>
                        } 
                      />
                    </Routes>
                  </MainLayout>
                </GlobalProvider>
              </ProtectedRoute>
            }
          />
        </Routes>
      </Router>
    </AuthProvider>
  );
};

export default AppRouter;
