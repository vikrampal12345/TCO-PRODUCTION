import React from 'react';
import { AnalyticsData } from '../../../types/review';
import {
  BarChart3,
  TrendingUp,
  AlertTriangle,
} from 'lucide-react';

interface AnalyticsPreviewProps {
  data: AnalyticsData;
  onApprove?: () => void;
}

export const AnalyticsPreview: React.FC<AnalyticsPreviewProps> = ({
  data,
}) => {
  return (
    <div className="flex h-full flex-col space-y-6 text-white/80">
      {/* Header */}
      <div className="space-y-2 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-white/80">
              <BarChart3 className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <h3 className="text-sm font-semibold text-white">
                Classroom Performance Analytics
              </h3>

              <p className="mt-1 text-xs text-white/45">
                Diagnostic evaluation across recent assessments
              </p>
            </div>
          </div>

          <span className="shrink-0 rounded-md border border-white/15 bg-white/[0.04] px-2 py-1 text-[9px] font-medium tracking-wide text-white/50">
            DEMO DATA
          </span>
        </div>
      </div>

      {/* Performance Metrics */}
      <div className="grid grid-cols-2 gap-3">
        {/* Class Average */}
        <div className="space-y-2 rounded-xl border border-white/10 bg-[#0b0b0b] p-3.5">
          <p className="text-[11px] font-medium text-white/50">
            Class Average
          </p>

          <p className="font-mono text-2xl font-semibold text-white">
            {data.classAverage}%
          </p>

          <div className="flex items-center gap-1 text-[10px] text-white/45">
            <TrendingUp className="h-3 w-3" />
            <span>+4.2% from Unit Test 1</span>
          </div>
        </div>

        {/* Students Evaluated */}
        <div className="space-y-2 rounded-xl border border-white/10 bg-[#0b0b0b] p-3.5">
          <p className="text-[11px] font-medium text-white/50">
            Students Evaluated
          </p>

          <p className="font-mono text-2xl font-semibold text-white">
            {data.studentsEvaluated}
          </p>

          <p className="text-[10px] text-white/40">
            100% Roster Checked
          </p>
        </div>

        {/* Questions Assessed */}
        <div className="space-y-2 rounded-xl border border-white/10 bg-[#0b0b0b] p-3.5">
          <p className="text-[11px] font-medium text-white/50">
            Questions Assessed
          </p>

          <p className="font-mono text-2xl font-semibold text-white">
            {data.totalQuestions}
          </p>

          <p className="text-[10px] text-white/40">
            Total Marks: 50
          </p>
        </div>

        {/* Students Needing Attention */}
        <div className="space-y-2 rounded-xl border border-white/15 bg-white/[0.03] p-3.5">
          <p className="text-[11px] font-medium text-white/60">
            Needing Attention
          </p>

          <p className="font-mono text-2xl font-semibold text-white">
            {data.studentsNeedingAttention}
          </p>

          <div className="flex items-center gap-1 text-[10px] text-white/45">
            <AlertTriangle className="h-3 w-3" />
            <span>Below 60% threshold</span>
          </div>
        </div>
      </div>

      {/* Question-Wise Performance */}
      <div className="space-y-4 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex items-center justify-between gap-3">
          <span className="text-xs font-semibold text-white">
            Question-Wise Mastery Rate
          </span>

          <span className="text-[10px] text-white/40">
            Class Average %
          </span>
        </div>

        <div className="space-y-4">
          {data.questionPerformance.map((qp, idx) => {
            const score = Math.max(
              0,
              Math.min(100, qp.avgScorePercent)
            );

            return (
              <div key={idx} className="space-y-1.5">
                <div className="flex items-center justify-between gap-3 text-xs">
                  <span className="max-w-[200px] truncate font-medium text-white/70">
                    {qp.question}
                  </span>

                  <span className="shrink-0 font-mono font-medium text-white">
                    {qp.avgScorePercent}%
                  </span>
                </div>

                <div className="h-1.5 w-full overflow-hidden rounded-full bg-white/10">
                  <div
                    className="h-full rounded-full bg-white transition-all duration-500"
                    style={{ width: `${score}%` }}
                  />
                </div>
              </div>
            );
          })}
        </div>
      </div>

      {/* Score Distribution */}
      <div className="space-y-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <h4 className="text-xs font-semibold text-white">
          Score Distribution
        </h4>

        <div className="grid grid-cols-5 gap-1.5 text-center">
          {data.scoreDistribution.map((d, i) => (
            <div
              key={i}
              className="rounded-lg border border-white/[0.08] bg-white/[0.03] p-2"
            >
              <span className="block text-[10px] text-white/45">
                {d.range}
              </span>

              <span className="mt-1 block font-mono text-sm font-semibold text-white">
                {d.count}
              </span>
            </div>
          ))}
        </div>
      </div>

      {/* Footer */}
      <p className="pt-1 text-center text-[10px] text-white/35">
        Demo data · Student identities remain protected
      </p>
    </div>
  );
};