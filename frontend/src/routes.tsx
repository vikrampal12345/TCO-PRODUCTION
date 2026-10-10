
import React from 'react';
import { Routes, Route, Navigate, useLocation } from 'react-router-dom';

import { Home } from './pages/Home';
import { Login } from './pages/Login';
import { Signup } from './pages/Signup';
import { Workspace } from './pages/Workspace';
import { Tasks } from './pages/Tasks';
import { Files } from './pages/Files';
import { Analytics } from './pages/Analytics';
import { Settings } from './pages/Settings';
import { useAuth } from './context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactElement;
  allowDevBypass?: boolean;
}

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  allowDevBypass = false,
}) => {
  const { isAuthenticated } = useAuth();
  const location = useLocation();

  // Development-only bypass for direct Workspace testing.
  const devWorkspaceBypass =
    allowDevBypass &&
    import.meta.env.VITE_DEV_WORKSPACE_BYPASS === 'true';

  if (isAuthenticated || devWorkspaceBypass) {
    return children;
  }

  return (
    <Navigate
      to="/login"
      replace
      state={{ from: location.pathname }}
    />
  );
};

export const AppRoutes: React.FC = () => {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/login" element={<Login />} />
      <Route path="/signup" element={<Signup />} />

      <Route
        path="/workspace"
        element={
          <ProtectedRoute allowDevBypass>
            <Workspace />
          </ProtectedRoute>
        }
      />

      <Route
        path="/tasks"
        element={
          <ProtectedRoute>
            <Tasks />
          </ProtectedRoute>
        }
      />

      <Route
        path="/files"
        element={
          <ProtectedRoute>
            <Files />
          </ProtectedRoute>
        }
      />

      <Route
        path="/analytics"
        element={
          <ProtectedRoute>
            <Analytics />
          </ProtectedRoute>
        }
      />

      <Route
        path="/settings"
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};
