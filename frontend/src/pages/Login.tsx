import React, { useState } from 'react';
import {
  Link,
  useNavigate,
  useLocation,
} from 'react-router-dom';

import { AuthLayout } from '../components/auth/AuthLayout';
import { useAuth } from '../context/AuthContext';

import {
  ArrowRight,
  Loader2,
  Lock,
  Mail,
} from 'lucide-react';

import { errorMessage } from '../services/http';

interface LoginLocationState {
  message?: string;
  from?: {
    pathname?: string;
  };
}

export const Login: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const [authError, setAuthError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [loadingText, setLoadingText] = useState(
    'Signing you into TCO...'
  );

  const { login, loginWithGoogle } = useAuth();

  const navigate = useNavigate();
  const location = useLocation();

  const locationState =
    (location.state as LoginLocationState | null) ?? null;

  const confirmationMessage = locationState?.message;

  const handleSubmit = async (
    e: React.FormEvent<HTMLFormElement>
  ) => {
    e.preventDefault();

    setAuthError(null);

    const normalizedEmail = email.trim().toLowerCase();

    if (!normalizedEmail || !password) {
      setAuthError('Please enter your email and password.');
      return;
    }

    setIsSubmitting(true);
    setLoadingText('Signing you into TCO...');

    try {
      await login({
        email: normalizedEmail,
        password,
      });

      const destination =
        locationState?.from?.pathname || '/workspace';

      navigate(destination, { replace: true });
    } catch (error) {
      setAuthError(errorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleLogin = async () => {
    setAuthError(null);
    setIsSubmitting(true);
    setLoadingText('Authenticating with Google...');

    try {
      await loginWithGoogle();

      /*
       * Supabase OAuth redirects the browser to Google.
       * Do not navigate manually here.
       */
    } catch (error) {
      setAuthError(errorMessage(error));
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Welcome Back, Teacher"
      subtitle="Sign in to your TCO workspace to resume your workflows"
    >
      {/* Loading Overlay */}
      {isSubmitting && (
        <div
          className="
            absolute
            inset-0
            bg-[#090909]/90
            backdrop-blur-md
            rounded-2xl
            flex
            flex-col
            items-center
            justify-center
            z-20
            space-y-3
          "
        >
          <Loader2 className="w-8 h-8 text-white animate-spin" />

          <div className="text-sm font-semibold text-white">
            {loadingText}
          </div>

          <div className="text-xs text-gray-500">
            Loading your active academic sessions...
          </div>
        </div>
      )}

      {/* Email Confirmation Message */}
      {confirmationMessage && (
        <div
          role="status"
          className="
            mb-4
            rounded-xl
            border
            border-white/15
            bg-white/[0.05]
            px-3
            py-2.5
            text-xs
            text-gray-200
          "
        >
          {confirmationMessage}
        </div>
      )}

      {/* Authentication Error */}
      {authError && (
        <div
          role="alert"
          className="
            mb-4
            rounded-xl
            border
            border-white/15
            bg-white/[0.05]
            px-3
            py-2.5
            text-xs
            text-gray-200
          "
        >
          {authError}
        </div>
      )}

      <form onSubmit={handleSubmit} className="space-y-5">
        {/* Email Field */}
        <div>
          <label
            htmlFor="login-email"
            className="block text-xs font-medium text-gray-300 mb-1.5"
          >
            Email
          </label>

          <div className="relative">
            <div
              className="
                absolute
                inset-y-0
                left-0
                pl-3.5
                flex
                items-center
                pointer-events-none
                text-gray-500
              "
            >
              <Mail className="w-4 h-4" />
            </div>

            <input
              id="login-email"
              type="email"
              value={email}
              onChange={(e) => {
                setEmail(e.target.value);
                setAuthError(null);
              }}
              placeholder="prof.name@university.edu"
              autoComplete="email"
              required
              disabled={isSubmitting}
              className="
                w-full
                pl-10
                pr-4
                py-2.5
                bg-[#070707]
                border
                border-white/10
                rounded-xl
                text-sm
                text-white
                placeholder-gray-600
                focus:outline-none
                focus:border-white/30
                focus:ring-1
                focus:ring-white/10
                transition-all
              "
            />
          </div>
        </div>

        {/* Password Field */}
        <div>
          <div className="flex items-center justify-between mb-1.5">
            <label
              htmlFor="login-password"
              className="block text-xs font-medium text-gray-300"
            >
              Password
            </label>

            <Link
              to="/forgot-password"
              className="
                text-xs
                text-gray-400
                hover:text-white
                transition-colors
              "
            >
              Forgot password?
            </Link>
          </div>

          <div className="relative">
            <div
              className="
                absolute
                inset-y-0
                left-0
                pl-3.5
                flex
                items-center
                pointer-events-none
                text-gray-500
              "
            >
              <Lock className="w-4 h-4" />
            </div>

            <input
              id="login-password"
              type="password"
              value={password}
              onChange={(e) => {
                setPassword(e.target.value);
                setAuthError(null);
              }}
              placeholder="••••••••"
              autoComplete="current-password"
              required
              disabled={isSubmitting}
              className="
                w-full
                pl-10
                pr-4
                py-2.5
                bg-[#070707]
                border
                border-white/10
                rounded-xl
                text-sm
                text-white
                placeholder-gray-600
                focus:outline-none
                focus:border-white/30
                focus:ring-1
                focus:ring-white/10
                transition-all
              "
            />
          </div>
        </div>

        {/* Submit Button */}
        <button
          type="submit"
          disabled={isSubmitting}
          className="
            w-full
            py-3
            px-4
            rounded-xl
            bg-white
            text-black
            font-bold
            text-sm
            hover:bg-gray-200
            transition-all
            duration-300
            flex
            items-center
            justify-center
            gap-2
            group
            disabled:opacity-50
            disabled:cursor-not-allowed
          "
        >
          <span>
            {isSubmitting ? 'Signing In...' : 'Sign In'}
          </span>

          {!isSubmitting && (
            <ArrowRight
              className="
                w-4
                h-4
                transition-transform
                group-hover:translate-x-1
              "
            />
          )}
        </button>

        {/* Divider */}
        <div className="relative my-6">
          <div className="absolute inset-0 flex items-center">
            <div className="w-full border-t border-white/10" />
          </div>

          <div className="relative flex justify-center text-xs uppercase">
            <span className="bg-[#0a0a0a] px-2 text-gray-500 font-mono">
              Or continue with
            </span>
          </div>
        </div>

        {/* Google SSO Button */}
        <button
          type="button"
          onClick={handleGoogleLogin}
          disabled={isSubmitting}
          className="
            w-full
            py-2.5
            px-4
            rounded-xl
            bg-white/[0.05]
            border
            border-white/10
            hover:bg-white/[0.08]
            text-gray-200
            text-xs
            font-semibold
            flex
            items-center
            justify-center
            gap-3
            transition-colors
            disabled:opacity-50
          "
        >
          <svg
            className="w-4 h-4"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <path
              fill="#4285F4"
              d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"
            />

            <path
              fill="#34A853"
              d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"
            />

            <path
              fill="#FBBC05"
              d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.06H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.94l2.85-2.22.81-.63z"
            />

            <path
              fill="#EA4335"
              d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.06l3.66 2.84c.87-2.6 3.3-4.52 6.16-4.52z"
            />
          </svg>

          <span>Continue with Google</span>
        </button>

        {/* Footer Link */}
        <div className="text-center pt-2 text-xs text-gray-400">
          Don't have an account yet?{' '}

          <Link
            to="/signup"
            className="
              text-white
              hover:text-gray-300
              font-semibold
              transition-colors
            "
          >
            Create account
          </Link>
        </div>
      </form>
    </AuthLayout>
  );
};