import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, Mail } from 'lucide-react';

export const Signup: React.FC = () => {
  const [emailSignup, setEmailSignup] = useState(false);

  if (!emailSignup) {
    return (
      <div className="space-y-5">

        <button
          type="button"
          className="
            w-full h-11 rounded-lg
            bg-white text-black
            text-sm font-semibold
            flex items-center justify-center gap-3
            hover:bg-gray-200
            transition-colors
          "
        >
          <span className="font-bold">G</span>
          Continue with Google
        </button>

        <div className="flex items-center gap-4">
          <div className="h-px flex-1 bg-white/10" />
          <span className="text-xs text-gray-500">or</span>
          <div className="h-px flex-1 bg-white/10" />
        </div>

        <button
          type="button"
          onClick={() => setEmailSignup(true)}
          className="
            group
            w-full h-11 rounded-lg
            border border-white/10
            bg-white/[0.03]
            text-white
            text-sm font-medium
            flex items-center justify-center gap-2
            hover:bg-white/[0.06]
            hover:border-white/20
            transition-all
          "
        >
          <Mail className="w-4 h-4" />

          <span>Continue with Email</span>

          <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
        </button>

        <p className="text-center text-sm text-gray-500 pt-2">
          Already have an account?{' '}
          <Link
            to="/login"
            className="text-white hover:text-gray-300"
          >
            Sign in
          </Link>
        </p>

      </div>
    );
  }

  return (
    <EmailSignupForm
      onBack={() => setEmailSignup(false)}
    />
  );
};


const EmailSignupForm = ({
  onBack,
}: {
  onBack: () => void;
}) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  return (
    <form className="space-y-5">

      {/* Name */}
      <div>
        <label
          htmlFor="name"
          className="block text-sm font-medium text-gray-300 mb-2"
        >
          Name
        </label>

        <input
          id="name"
          type="text"
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder="Enter your name"
          className="
            w-full h-11 px-3.5 rounded-lg
            bg-white/[0.03]
            border border-white/10
            text-white
            placeholder:text-gray-600
            text-sm
            outline-none
            focus:border-white/30
            focus:bg-white/[0.05]
          "
          required
        />
      </div>

      {/* Email */}
      <div>
        <label
          htmlFor="email"
          className="block text-sm font-medium text-gray-300 mb-2"
        >
          Email
        </label>

        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="you@example.com"
          className="
            w-full h-11 px-3.5 rounded-lg
            bg-white/[0.03]
            border border-white/10
            text-white
            placeholder:text-gray-600
            text-sm
            outline-none
            focus:border-white/30
            focus:bg-white/[0.05]
          "
          required
        />
      </div>

      {/* Password */}
      <div>
        <label
          htmlFor="password"
          className="block text-sm font-medium text-gray-300 mb-2"
        >
          Password
        </label>

        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="Create a password"
          className="
            w-full h-11 px-3.5 rounded-lg
            bg-white/[0.03]
            border border-white/10
            text-white
            placeholder:text-gray-600
            text-sm
            outline-none
            focus:border-white/30
            focus:bg-white/[0.05]
          "
          required
        />
      </div>

      {/* Submit */}
      <button
        type="submit"
        className="
          group
          w-full h-11 rounded-lg
          bg-white text-black
          text-sm font-semibold
          flex items-center justify-center gap-2
          hover:bg-gray-200
          transition-colors
        "
      >
        Create Account

        <ArrowRight className="w-4 h-4 transition-transform group-hover:translate-x-0.5" />
      </button>

      {/* Back */}
      <button
        type="button"
        onClick={onBack}
        className="
          w-full
          text-sm text-gray-500
          hover:text-white
          transition-colors
        "
      >
        ← Other sign up options
      </button>

    </form>
  );
};