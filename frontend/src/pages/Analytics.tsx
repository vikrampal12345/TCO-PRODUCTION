import React from 'react';
import { useNavigate } from 'react-router-dom';
import { AnalyticsPreview } from '../components/workspace/reviews/AnalyticsPreview';
import { DEMO_ANALYTICS } from '../services/demoData';
import { ArrowLeft } from 'lucide-react';

export const Analytics: React.FC = () => {
  const navigate = useNavigate();

  return (
    <div className="min-h-screen bg-black text-gray-100 flex flex-col font-sans">
      <header className="flex min-h-16 flex-col gap-3 border-b border-white/10 bg-[#0a0a0a] px-4 py-3 sm:flex-row sm:items-center sm:justify-between sm:px-6">
        <div className="flex min-w-0 flex-wrap items-center gap-3 sm:gap-4">
          <button
            onClick={() => navigate('/workspace')}
            className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 flex items-center gap-1.5 text-xs font-medium"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Workspace</span>
          </button>
          <h1 className="text-sm font-bold text-white sm:text-base">Class Diagnostics & Insights</h1>
        </div>
      </header>

      <main className="mx-auto w-full max-w-4xl flex-1 space-y-5 px-4 py-5 sm:space-y-6 sm:p-6">
        <AnalyticsPreview data={DEMO_ANALYTICS} />
      </main>
    </div>
  );
};
