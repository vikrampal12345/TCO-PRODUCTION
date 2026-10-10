import React from 'react';
import { useNavigate } from 'react-router-dom';
import { Clock, ArrowLeft, Plus } from 'lucide-react';

export const Tasks: React.FC = () => {
  const navigate = useNavigate();

  const taskList = [
    { id: 't-1', title: 'Check DBMS Unit 3 Answer Sheets', agent: 'Answer Sheet Checking Agent', status: 'Review Required', dueDate: 'Today, 5:00 PM', items: '35 Submissions' },
    { id: 't-2', title: 'Prepare Operating Systems Question Paper', agent: 'Assessment Agent', status: 'Completed', dueDate: 'Yesterday', items: '20 Questions' },
    { id: 't-3', title: 'Reconcile CS-301 Lecture Attendance', agent: 'Attendance Agent', status: 'Completed', dueDate: 'Oct 7', items: '42 Students' },
    { id: 't-4', title: 'Draft Java Multithreading Lecture PPT', agent: 'Presentation Agent', status: 'Draft Ready', dueDate: 'Oct 10', items: '12 Slides' },
  ];

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
          <h1 className="text-sm font-bold text-white sm:text-base">Active Academic Tasks</h1>
        </div>

        <button
          onClick={() => navigate('/workspace')}
          className="inline-flex shrink-0 items-center justify-center gap-1.5 self-start rounded-lg bg-white px-3.5 py-2 text-xs font-semibold text-black transition-colors hover:bg-gray-200 sm:self-auto"
        >
          <Plus className="w-3.5 h-3.5" />
          <span>New Workflow</span>
        </button>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 space-y-5 px-4 py-5 sm:space-y-6 sm:p-6">
        <div className="flex flex-col items-start justify-between gap-3 sm:flex-row sm:items-center">
          <div>
            <h2 className="text-lg font-extrabold text-white sm:text-xl">Academic Task Ledger</h2>
            <p className="mt-1 max-w-xl text-xs leading-relaxed text-gray-400 sm:mt-0.5">Automated workflows dispatched via the TCO Master Agent.</p>
          </div>
          <span className="shrink-0 rounded-full border border-white/10 bg-white/5 px-3 py-1 font-mono text-[10px] text-white/70 sm:text-xs">
            4 Workflows Tracked
          </span>
        </div>

        <div className="space-y-3">
          {taskList.map((task) => (
            <div
              key={task.id}
              onClick={() => navigate('/workspace')}
              className="group flex cursor-pointer flex-col justify-between gap-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-4 shadow-glass transition-all hover:border-white/25 sm:flex-row sm:items-center sm:gap-4"
            >
              <div>
                <div className="mb-1 flex flex-wrap items-center gap-2">
                  <h3 className="text-sm font-bold text-white transition-colors group-hover:text-white/80">
                    {task.title}
                  </h3>
                  <span className={`text-[10px] font-mono px-2 py-0.5 rounded-full ${
                    task.status === 'Review Required'
                      ? 'bg-white/5 text-gray-200 border border-white/10'
                      : 'bg-white/5 text-gray-200 border border-white/10'
                  }`}>
                    {task.status}
                  </span>
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-400">
                  <span>Assigned: <strong className="text-gray-300">{task.agent}</strong></span>
                  <span>•</span>
                  <span>Scope: {task.items}</span>
                </div>
              </div>

              <div className="flex shrink-0 flex-wrap items-center gap-3 text-xs font-mono text-gray-400 sm:gap-4">
                <span className="flex items-center gap-1">
                  <Clock className="w-3.5 h-3.5 text-white/70" />
                  {task.dueDate}
                </span>
                <span className="text-white/70 group-hover:translate-x-1 transition-transform">
                  Open →
                </span>
              </div>
            </div>
          ))}
        </div>
      </main>
    </div>
  );
};
