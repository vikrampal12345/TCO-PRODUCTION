import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  ArrowRight,
  Menu,
  X,
  ShieldCheck,
} from 'lucide-react';

import { AuthChoiceModal } from './AuthChoiceModal';

export const Navbar: React.FC = () => {
  const [scrolled, setScrolled] = useState(false);
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const [authModalOpen, setAuthModalOpen] = useState(false);

  useEffect(() => {
    const handleScroll = () => {
      setScrolled(window.scrollY > 20);
    };

    window.addEventListener('scroll', handleScroll);

    return () => {
      window.removeEventListener('scroll', handleScroll);
    };
  }, []);

  // Close modal with Escape
  useEffect(() => {
    const handleEscape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setAuthModalOpen(false);
      }
    };

    if (authModalOpen) {
      document.addEventListener('keydown', handleEscape);
    }

    return () => {
      document.removeEventListener('keydown', handleEscape);
    };
  }, [authModalOpen]);

  return (
    <>
      {/* =====================================================
          NAVBAR
      ===================================================== */}

      <header
        className={`fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
          scrolled
            ? 'bg-black/85 backdrop-blur-md border-b border-white/10 shadow-lg'
            : 'bg-transparent border-b border-transparent'
        }`}
      >
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">

          {/* ==================== BRAND ==================== */}

          <Link
            to="/"
            aria-label="TCO home"
            className="tco-brand-link group flex items-center gap-2.5"
          >
            <span className="tco-navbar-mark" aria-hidden="true">
              <img src="/tco-monogram.png" alt="" />
            </span>
          </Link>

          {/* ==================== DESKTOP NAV ==================== */}

          <nav className="hidden md:flex items-center gap-8 text-sm font-medium text-gray-300">

            <a
              href="#features"
              className="hover:text-white transition-colors"
            >
              Features
            </a>

            <a
              href="#how-it-works"
              className="hover:text-white transition-colors"
            >
              How It Works
            </a>

            <a
              href="#philosophy"
              className="hover:text-white transition-colors"
            >
              Philosophy
            </a>

            <a
              href="#security"
              className="hover:text-white transition-colors flex items-center gap-1.5"
            >
              <ShieldCheck className="w-3.5 h-3.5" />
              Security
            </a>

          </nav>

          {/* ==================== DESKTOP ACTIONS ==================== */}

          <div className="hidden md:flex items-center gap-3">

            {/* Sign In */}
            <Link
              to="/login"
              className="
                text-sm
                font-medium
                text-gray-300
                hover:text-white
                px-4
                py-2
                rounded-lg
                hover:bg-white/5
                transition-all
              "
            >
              Sign In
            </Link>

            {/* Get Started */}
            <button
              type="button"
              onClick={() => setAuthModalOpen(true)}
              className="
                group
                flex
                items-center
                gap-2
                text-sm
                font-semibold
                text-black
                bg-white
                px-4
                py-2
                rounded-lg
                hover:bg-gray-200
                transition-all
              "
            >
              <span>Get Started Free</span>

              <ArrowRight
                className="
                  w-4 h-4
                  transition-transform
                  group-hover:translate-x-0.5
                "
              />
            </button>

          </div>

          {/* ==================== MOBILE MENU BUTTON ==================== */}

          <button
            type="button"
            onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
            className="
              md:hidden
              p-2
              rounded-lg
              text-gray-400
              hover:text-white
              hover:bg-white/5
              transition-colors
            "
            aria-label="Toggle Menu"
          >
            {mobileMenuOpen ? (
              <X className="w-6 h-6" />
            ) : (
              <Menu className="w-6 h-6" />
            )}
          </button>

        </div>

        {/* ==================== MOBILE MENU ==================== */}

        {mobileMenuOpen && (
          <div
            className="
              md:hidden
              bg-black/95
              backdrop-blur-xl
              border-b
              border-white/10
              px-6
              py-6
            "
          >

            <nav className="flex flex-col space-y-3 text-base font-medium text-gray-300">

              <a
                href="#features"
                onClick={() => setMobileMenuOpen(false)}
                className="hover:text-white py-1 transition-colors"
              >
                Features
              </a>

              <a
                href="#how-it-works"
                onClick={() => setMobileMenuOpen(false)}
                className="hover:text-white py-1 transition-colors"
              >
                How It Works
              </a>

              <a
                href="#philosophy"
                onClick={() => setMobileMenuOpen(false)}
                className="hover:text-white py-1 transition-colors"
              >
                Philosophy
              </a>

              <a
                href="#security"
                onClick={() => setMobileMenuOpen(false)}
                className="hover:text-white py-1 transition-colors"
              >
                Security
              </a>

            </nav>

            {/* Mobile Actions */}
            <div className="pt-5 mt-5 border-t border-white/10 flex flex-col gap-3">

              {/* Sign In */}
              <Link
                to="/login"
                onClick={() => setMobileMenuOpen(false)}
                className="
                  w-full
                  text-center
                  py-2.5
                  rounded-lg
                  text-gray-200
                  border
                  border-white/10
                  hover:bg-white/5
                  transition-colors
                "
              >
                Sign In
              </Link>

              {/* Get Started */}
              <button
                type="button"
                onClick={() => {
                  setMobileMenuOpen(false);
                  setAuthModalOpen(true);
                }}
                className="
                  group
                  w-full
                  flex
                  items-center
                  justify-center
                  gap-2
                  py-2.5
                  rounded-lg
                  bg-white
                  text-black
                  font-semibold
                  hover:bg-gray-200
                  transition-colors
                "
              >
                <span>Get Started Free</span>

                <ArrowRight
                  className="
                    w-4 h-4
                    transition-transform
                    group-hover:translate-x-0.5
                  "
                />
              </button>

            </div>

          </div>
        )}
      </header>

      {/* =====================================================
          AUTH CHOICE MODAL
      ===================================================== */}

      <AuthChoiceModal
        isOpen={authModalOpen}
        onClose={() => setAuthModalOpen(false)}
        onEmailSignup={() => {
          setAuthModalOpen(false);
          window.location.href = '/signup?method=email';
        }}
      />
    </>
  );
};