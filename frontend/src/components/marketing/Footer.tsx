import React from 'react';
import { Link } from 'react-router-dom';
import { Heart, ArrowUpRight } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-black border-t border-white/10 text-gray-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="py-12 sm:py-14 grid grid-cols-1 md:grid-cols-4 gap-10">
          <div className="md:col-span-2">
            <Link to="/" className="inline-flex items-center gap-3 mb-5">
              <div className="w-9 h-9 rounded-xl bg-white flex items-center justify-center">
                <span className="font-extrabold text-sm tracking-wider text-black">TCO</span>
              </div>
              <span className="font-bold text-white text-lg">Teacher Co-Worker</span>
            </Link>

            <p className="text-sm text-gray-400 max-w-md leading-relaxed">
              Your co-worker for the work behind the classroom. Create, check, organize, and prepare academic work in one place.
            </p>

            <p className="mt-4 text-sm font-semibold text-white">
              Teacher Co-Worker
            </p>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-200 mb-4">Product</h3>
            <ul className="space-y-3 text-sm">
              <li><a href="#features" className="hover:text-white transition-colors">Features</a></li>
              <li><a href="#how-it-works" className="hover:text-white transition-colors">How It Works</a></li>
              <li><a href="#security" className="hover:text-white transition-colors">Security</a></li>
            </ul>
          </div>

          <div>
            <h3 className="text-xs font-semibold uppercase tracking-wider text-gray-200 mb-4">Get Started</h3>
            <ul className="space-y-3 text-sm">
              <li>
                <Link to="/workspace" className="inline-flex items-center gap-1 text-gray-300 font-medium hover:text-white transition-colors">
                  Open Workspace <ArrowUpRight className="w-3.5 h-3.5" />
                </Link>
              </li>
              <li><Link to="/login" className="hover:text-white transition-colors">Sign In</Link></li>
              <li><Link to="/signup" className="hover:text-white transition-colors">Create Account</Link></li>
            </ul>
          </div>
        </div>

        <div className="py-6 border-t border-white/10 flex flex-col sm:flex-row items-center justify-between gap-4 text-xs text-gray-500">
          <p className="flex items-center gap-1">
            © {new Date().getFullYear()} TCO. Made with
            <Heart className="w-3.5 h-3.5 text-gray-300 fill-current" />
            for teachers.
          </p>
          <p>Teacher-controlled AI</p>
        </div>
      </div>
    </footer>
  );
};
