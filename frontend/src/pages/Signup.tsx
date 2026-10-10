import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { AuthLayout } from '../components/auth/AuthLayout';
import { useAuth } from '../context/AuthContext';
import { UserRole } from '../types/auth';
import {
  ArrowRight,
  Loader2,
  User,
  Mail,
  Lock,
} from 'lucide-react';
import { errorMessage } from '../services/http';

export const Signup: React.FC = () => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [passwordError, setPasswordError] = useState<string | null>(null);
  const [authError, setAuthError] = useState<string | null>(null);
  const [role] = useState<UserRole>('Teacher');
  const [school] = useState(
    'Department of Computer Science & Engineering'
  );
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { signup } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!name.trim() || !email.trim()) return;

    setAuthError(null);

    if (password !== confirmPassword) {
      setPasswordError('Passwords do not match.');
      return;
    }

    setPasswordError(null);
    setIsSubmitting(true);

    try {
      await signup({
        name: name.trim(),
        email: email.trim(),
        password,
        role,
        school,
      });

      navigate('/workspace');
    } catch (error) {
      setAuthError(errorMessage(error));
    } finally {
      setIsSubmitting(false);
    }
  };

  const inputClassName = `
    w-full
    pl-10
    pr-4
    py-2.5
    bg-white/5
    border
    border-white/15
    rounded-xl
    text-sm
    text-white
    placeholder-gray-500
    focus:outline-none
    focus:border-white/40
    focus:ring-1
    focus:ring-white/10
    transition-all
    duration-200
  `;

  return (
    <AuthLayout
      title="Create Your Account"
      subtitle="Let TCO handle the busywork. You stay in control."
    >
      {authError && <div role="alert" className="mb-4 rounded-xl border border-white/15 bg-white/[0.05] px-3 py-2.5 text-xs text-gray-200">{authError}</div>}
      <div className="relative">

        {/* Loading Overlay */}
        {isSubmitting && (
          <div
            className="
              absolute
              inset-0
              z-20
              flex
              flex-col
              items-center
              justify-center
              space-y-3
              rounded-2xl
              bg-[#171717]/95
              backdrop-blur-md
            "
          >
            <Loader2 className="w-8 h-8 text-white animate-spin" />

            <div className="text-sm font-semibold text-white">
              Setting up your TCO workspace...
            </div>

            <div className="text-xs text-gray-400">
              Initializing your personal Master Agent mesh...
            </div>
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">

          {/* FULL NAME */}
          <div>
            <label
              htmlFor="signup-name"
              className="block text-xs font-medium text-gray-300 mb-1.5"
            >
              Full Name
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
                  text-gray-400
                "
              >
                <User className="w-4 h-4" />
              </div>

              <input
                id="signup-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Prof. Jane Doe"
                autoComplete="name"
                required
                className={inputClassName}
              />
            </div>
          </div>

          {/* EMAIL ADDRESS */}
          <div>
            <label
              htmlFor="signup-email"
              className="block text-xs font-medium text-gray-300 mb-1.5"
            >
              Email Address
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
                  text-gray-400
                "
              >
                <Mail className="w-4 h-4" />
              </div>

              <input
                id="signup-email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="jane.doe@university.edu"
                autoComplete="email"
                required
                className={inputClassName}
              />
            </div>
          </div>

          {/* PASSWORD */}
          <div>
            <label
              htmlFor="signup-password"
              className="block text-xs font-medium text-gray-300 mb-1.5"
            >
              Password
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
                  text-gray-400
                "
              >
                <Lock className="w-4 h-4" />
              </div>

              <input
                id="signup-password"
                type="password"
                value={password}
                onChange={(e) => {
                  const nextPassword = e.target.value;
                  setPassword(nextPassword);
                  setAuthError(null);
                  setPasswordError(
                    confirmPassword.length > 0 && nextPassword !== confirmPassword
                      ? 'Passwords do not match.'
                      : null
                  );
                }}
                placeholder="Create a strong password"
                autoComplete="new-password"
                required
                className={inputClassName}
              />
            </div>
          </div>

          {/* CONFIRM PASSWORD */}
          <div>
            <label
              htmlFor="signup-confirm-password"
              className="block text-xs font-medium text-gray-300 mb-1.5"
            >
              Confirm Password
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
                  text-gray-400
                "
              >
                <Lock className="w-4 h-4" />
              </div>

              <input
                id="signup-confirm-password"
                type="password"
                value={confirmPassword}
                onChange={(e) => {
                  const nextConfirmPassword = e.target.value;
                  setConfirmPassword(nextConfirmPassword);
                  setAuthError(null);
                  setPasswordError(
                    nextConfirmPassword.length > 0 && nextConfirmPassword !== password
                      ? 'Passwords do not match.'
                      : null
                  );
                }}
                placeholder="Re-enter your password"
                autoComplete="new-password"
                required
                aria-invalid={Boolean(passwordError)}
                aria-describedby={passwordError ? 'signup-password-error' : undefined}
                className={`${inputClassName} ${passwordError ? 'border-white/50' : ''}`}
              />
            </div>

            {passwordError && (
              <p id="signup-password-error" role="alert" className="mt-1.5 text-xs text-gray-300">
                {passwordError}
              </p>
            )}

            {!passwordError && confirmPassword.length > 0 && password === confirmPassword && (
              <p className="mt-1.5 text-xs text-gray-400">Passwords match.</p>
            )}
          </div>

          {/* CREATE ACCOUNT */}
          <div className="pt-2">
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
                font-semibold
                text-sm
                hover:bg-gray-200
                active:scale-[0.99]
                transition-all
                duration-200
                flex
                items-center
                justify-center
                gap-2
                group
                disabled:opacity-50
                disabled:cursor-not-allowed
                disabled:active:scale-100
              "
            >
              <span>
                {isSubmitting ? 'Creating Account...' : 'Create Account'}
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
          </div>

          {/* LOGIN LINK */}
          <div className="text-center pt-2 text-xs text-gray-400">
            Already have an account?{' '}

            <Link
              to="/login"
              className="
                text-white
                hover:text-gray-300
                font-semibold
                transition-colors
                underline-offset-4
                hover:underline
              "
            >
              Sign In
            </Link>
          </div>

        </form>
      </div>
    </AuthLayout>
  );
};