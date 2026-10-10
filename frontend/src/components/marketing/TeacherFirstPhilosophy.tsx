import React from 'react';
import {
  ClipboardCheck,
  FileText,
  FileSpreadsheet,
  CalendarCheck,
  Presentation,
  Mail,
} from 'lucide-react';

export const TeacherFirstPhilosophy: React.FC = () => {
  const capabilities = [
    {
      title: 'Answer-sheet checking',
      description: 'Read handwritten or typed answers and prepare marks for review.',
      icon: ClipboardCheck,
    },
    {
      title: 'Question paper creation',
      description: 'Draft questions from your approved study material.',
      icon: FileText,
    },
    {
      title: 'Marksheet generation',
      description: 'Organize marks, grades, and class results.',
      icon: FileSpreadsheet,
    },
    {
      title: 'Attendance management',
      description: 'Structure attendance records and flag entries to review.',
      icon: CalendarCheck,
    },
    {
      title: 'Lecture presentations',
      description: 'Turn lesson topics and notes into slide drafts.',
      icon: Presentation,
    },
    {
      title: 'Result communication',
      description: 'Prepare result summaries and parent notifications.',
      icon: Mail,
    },
  ];

  return (
    <section id="features" className="relative bg-black py-20 sm:py-24 border-t border-white/[0.06]">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-14">
          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold text-gray-300 mb-5">
            Teacher Co-Worker
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            What TCO Can Do
          </h2>
          <p className="mt-4 text-sm sm:text-lg text-gray-400">
            Less repetitive work. More time for teaching.
          </p>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 sm:gap-5">
          {capabilities.map((item) => {
            const Icon = item.icon;

            return (
              <div
                key={item.title}
                className="rounded-2xl border border-white/10 bg-[#0b0b0b] p-5 sm:p-6 transition-all hover:bg-[#111111] hover:border-white/25"
              >
                <div className="w-11 h-11 rounded-xl bg-white/[0.08] border border-white/10 flex items-center justify-center mb-5">
                  <Icon className="w-5 h-5 text-white" />
                </div>
                <h3 className="text-base font-bold text-white mb-2">
                  {item.title}
                </h3>
                <p className="text-sm leading-relaxed text-gray-400">
                  {item.description}
                </p>
              </div>
            );
          })}
        </div>
      </div>
    </section>
  );
};
