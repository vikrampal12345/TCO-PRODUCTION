import React from 'react';
import {
  MessageSquareText,
  ClipboardCheck,
  CheckCircle2,
} from 'lucide-react';

export const WorkflowTimeline: React.FC = () => {
  const steps = [
    {
      num: '01',
      title: 'Describe the task',
      text: 'Type your request or add source material.',
      icon: MessageSquareText,
    },
    {
      num: '02',
      title: 'Review the draft',
      text: 'Check questions, marks, sources, or slides.',
      icon: ClipboardCheck,
    },
    {
      num: '03',
      title: 'Approve the result',
      text: 'Confirm the final output before use.',
      icon: CheckCircle2,
    },
  ];

  return (
    <section
      id="how-it-works"
      className="py-20 sm:py-24 relative overflow-hidden bg-black border-t border-white/[0.06]"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="text-center max-w-3xl mx-auto mb-12 sm:mb-14">
          <div className="inline-flex items-center px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold text-gray-300 mb-4">
            How to Work with TCO
          </div>
          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            Three simple steps
          </h2>
          <p className="mt-4 text-sm sm:text-base text-gray-400">
            From your request to a teacher-approved result.
          </p>
        </div>

        <div className="relative">
          <div className="hidden lg:block absolute top-14 left-[17%] right-[17%] h-px bg-white/10" />

          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 sm:gap-5 relative">
            {steps.map((step) => {
              const Icon = step.icon;

              return (
                <div
                  key={step.num}
                  className="relative rounded-2xl border border-white/10 bg-[#0b0b0b] p-6 sm:p-7 text-center transition-all hover:border-white/25 hover:bg-[#111111]"
                >
                  <div className="mx-auto w-12 h-12 rounded-xl bg-white flex items-center justify-center mb-5">
                    <Icon className="w-5 h-5 text-black" />
                  </div>
                  <div className="text-[10px] font-mono text-gray-500 mb-2">
                    STEP {step.num}
                  </div>
                  <h3 className="text-base font-bold text-white mb-2">
                    {step.title}
                  </h3>
                  <p className="text-sm leading-relaxed text-gray-400">
                    {step.text}
                  </p>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </section>
  );
};
