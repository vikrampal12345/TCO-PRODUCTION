import React from 'react';
import {
  ShieldCheck,
  Eye,
  Lock,
  CheckCircle2,
} from 'lucide-react';

export const SecuritySection: React.FC = () => {
  const securityPoints = [
    {
      title: 'You Review',
      desc: 'AI prepares the work. You check it before anything is finalized.',
      icon: Eye,
    },
    {
      title: 'You Approve',
      desc: 'Grades, marksheets, and important academic records need your approval.',
      icon: CheckCircle2,
    },
    {
      title: 'Your Data Stays Private',
      desc: 'Student data and academic documents stay protected inside your workspace.',
      icon: Lock,
    },
    {
      title: 'AI Stays Within Limits',
      desc: 'TCO follows controlled workflows instead of making important decisions on its own.',
      icon: ShieldCheck,
    },
  ];

  return (
    <section
      id="security"
      className="py-24 relative bg-black border-t border-white/10"
    >
      <div className="max-w-6xl mx-auto px-4 sm:px-6 lg:px-8">

        {/* Header */}
        <div className="text-center max-w-3xl mx-auto mb-14">

          <div className="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-white/5 border border-white/10 text-xs font-semibold text-gray-300 mb-5">
            <ShieldCheck className="w-3.5 h-3.5 text-white" />
            Safe & Controlled
          </div>

          <h2 className="text-3xl sm:text-5xl font-extrabold text-white tracking-tight">
            You Stay in Control.
          </h2>

          <p className="mt-4 text-base sm:text-lg text-gray-400">
            TCO helps with the work. You make the final decisions.
          </p>

        </div>

        {/* Security Points */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-5 max-w-5xl mx-auto">

          {securityPoints.map((point, index) => {
            const Icon = point.icon;

            return (
              <div
                key={index}
                className="
                  rounded-2xl
                  bg-white/[0.03]
                  border border-white/10
                  p-6
                  hover:bg-white/[0.05]
                  hover:border-white/20
                  transition-all
                "
              >
                <div className="flex items-start gap-4">

                  <div className="w-11 h-11 rounded-xl bg-white text-black flex items-center justify-center shrink-0">
                    <Icon className="w-5 h-5" />
                  </div>

                  <div>
                    <h3 className="text-base font-bold text-white mb-1.5">
                      {point.title}
                    </h3>

                    <p className="text-sm text-gray-400 leading-relaxed">
                      {point.desc}
                    </p>
                  </div>

                </div>
              </div>
            );
          })}

        </div>

        <div className="text-center mt-10">
          <p className="text-sm font-medium text-gray-300">
            Your workflow. Your review. Your approval.
          </p>
        </div>

      </div>
    </section>
  );
};