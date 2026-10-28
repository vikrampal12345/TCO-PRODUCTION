import React from 'react';
import {
  Routes,
  Route,
  Navigate,
  useLocation,
} from 'react-router-dom';

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
  const { isAuthenticated, isLoading } = useAuth();
  const location = useLocation();

  const devWorkspaceBypass =
    allowDevBypass &&
    import.meta.env.DEV &&
    import.meta.env.VITE_DEV_WORKSPACE_BYPASS === 'true';

  // Allow the explicitly configured development bypass.
  if (devWorkspaceBypass) {
    return children;
  }

  // Wait until Supabase session restoration has completed.
  if (isLoading) {
    return (
      <div className="min-h-screen bg-[#090909] flex items-center justify-center">
        <div className="flex flex-col items-center gap-3">
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-white/20 border-t-white" />

          <p className="text-sm text-gray-400">
            Restoring your TCO session...
          </p>
        </div>
      </div>
    );
  }

  // Redirect only after the authentication check has completed.
  if (!isAuthenticated) {
    return (
      <Navigate
        to="/login"
        replace
        state={{ from: { pathname: location.pathname } }}
      />
    );
  }

  return children;
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