import React from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Mail, X } from 'lucide-react';

interface AuthChoiceModalProps {
  isOpen: boolean;
  onClose: () => void;
  onEmailSignup: () => void;
}

export const AuthChoiceModal: React.FC<AuthChoiceModalProps> = ({
  isOpen,
  onClose,
  onEmailSignup,
}) => {
  if (!isOpen) return null;

  const handleGoogleSignup = () => {
    // Connect Google OAuth here later
    console.log('Continue with Google');
  };

  return (
    <div
      className="
        fixed inset-0 z-[100]
        flex items-center justify-center
        bg-black/70
        backdrop-blur-md
        px-4
      "
      onMouseDown={(e) => {
        if (e.target === e.currentTarget) {
          onClose();
        }
      }}
    >
      <div
        className="
          relative
          w-full max-w-md
          rounded-3xl
          bg-[#111111]
          border border-white/10
          shadow-2xl
          px-7 py-8
          sm:px-10
        "
      >

        {/* Close */}
        <button
          type="button"
          onClick={onClose}
          className="
            absolute top-4 right-4
            w-9 h-9
            rounded-full
            flex items-center justify-center
            text-gray-500
            hover:text-white
            hover:bg-white/10
            transition-colors
          "
          aria-label="Close"
        >
          <X className="w-5 h-5" />
        </button>

        {/* Logo */}
        <div className="flex justify-center mb-6">
          <div
            className="
              w-11 h-11
              rounded-xl
              bg-white
              flex items-center justify-center
            "
          >
            <span className="font-extrabold text-lg text-black tracking-wider">
              TCO
            </span>
          </div>
        </div>

        {/* Heading */}
        <div className="text-center mb-7">
          <h2 className="text-2xl sm:text-3xl font-bold text-white">
            Get started with TCO
          </h2>

          <p className="mt-2 text-sm text-gray-500">
            Choose how you'd like to continue.
          </p>
        </div>

        {/* Google */}
        <button
          type="button"
          onClick={handleGoogleSignup}
          className="
            w-full h-12
            rounded-xl
            bg-white
            text-black
            font-semibold
            text-sm
            flex items-center justify-center gap-3
            hover:bg-gray-200
            transition-colors
          "
        >
          <span className="font-bold">G</span>
          Continue with Google
        </button>

        {/* Divider */}
        <div className="flex items-center gap-4 my-6">
          <div className="h-px flex-1 bg-white/10" />

          <span className="text-xs text-gray-500">
            OR
          </span>

          <div className="h-px flex-1 bg-white/10" />
        </div>

        {/* Email */}
        <button
          type="button"
          onClick={onEmailSignup}
          className="
            group
            w-full h-12
            rounded-xl
            bg-white/[0.04]
            border border-white/10
            text-white
            font-medium
            text-sm
            flex items-center justify-center gap-3
            hover:bg-white/[0.08]
            hover:border-white/20
            transition-all
          "
        >
          <Mail className="w-4 h-4 text-gray-400" />

          <span>Continue with Email</span>

          <ArrowRight
            className="
              w-4 h-4
              text-gray-400
              transition-transform
              group-hover:translate-x-1
            "
          />
        </button>

        {/* Sign in */}
        <p className="text-center text-xs text-gray-500 mt-7">
          Already have an account?{' '}

          <Link
            to="/login"
            onClick={onClose}
            className="
              text-white
              hover:text-gray-300
              font-medium
              transition-colors
            "
          >
            Sign in
          </Link>
        </p>

      </div>
    </div>
  );
};