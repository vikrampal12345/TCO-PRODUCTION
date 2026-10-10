import React from 'react';
import { AttendanceReviewData } from '../../../types/review';
import {
  Users2,
  CheckCircle2,
  XCircle,
  AlertCircle,
  ThumbsUp,
  ShieldCheck,
} from 'lucide-react';

interface AttendancePreviewProps {
  data: AttendanceReviewData;
  onApprove: (notes?: string) => void;
}

export const AttendancePreview: React.FC<AttendancePreviewProps> = ({
  data,
  onApprove,
}) => {
  return (
    <div className="flex h-full flex-col space-y-5 text-white/80">
      {/* Attendance Header */}
      <div className="space-y-4 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-white/75">
              <Users2 className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-white">
                {data.className}
              </h3>
              <p className="mt-1 text-xs text-white/45">{data.date}</p>
            </div>
          </div>

          <span className="shrink-0 rounded-md border border-white/15 bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-white/65">
            Roster Reconciled
          </span>
        </div>

        {/* Attendance Statistics */}
        <div className="grid grid-cols-2 gap-2 border-t border-white/[0.08] pt-3 sm:grid-cols-4">
          <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
            <span className="block text-[10px] font-medium text-white/40">
              TOTAL
            </span>
            <span className="mt-1 block font-mono text-lg font-semibold text-white">
              {data.totalStudents}
            </span>
          </div>

          <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
            <span className="block text-[10px] font-medium text-white/40">
              PRESENT
            </span>
            <span className="mt-1 block font-mono text-lg font-semibold text-white">
              {data.presentCount}
            </span>
          </div>

          <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
            <span className="block text-[10px] font-medium text-white/40">
              ABSENT
            </span>
            <span className="mt-1 block font-mono text-lg font-semibold text-white">
              {data.absentCount}
            </span>
          </div>

          <div className="rounded-lg border border-white/[0.07] bg-white/[0.02] p-3">
            <span className="block text-[10px] font-medium text-white/40">
              FLAGGED
            </span>
            <span className="mt-1 block font-mono text-lg font-semibold text-white">
              {data.needsReviewCount}
            </span>
          </div>
        </div>

        {/* Verification Notice */}
        <div className="flex items-start gap-2 border-t border-white/[0.08] pt-3 text-[11px] leading-relaxed text-white/45">
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-white/60" />
          <span>
            Paper roster transcription verification. No biometric surveillance.
          </span>
        </div>
      </div>

      {/* Student List */}
      <div className="flex-1 space-y-3 overflow-y-auto pr-1">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-semibold text-white">
            Student Roll Log
          </h4>

          <span className="text-[10px] text-white/40">
            {data.records.length} records
          </span>
        </div>

        {data.records.map((record, index) => (
          <div
            key={`${record.rollNo}-${index}`}
            className="flex items-center justify-between gap-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-3 transition-colors hover:bg-white/[0.03]"
          >
            <div className="min-w-0 flex-1">
              <div className="flex flex-wrap items-center gap-x-2 gap-y-1">
                <span className="font-mono text-[11px] font-medium text-white/50">
                  {record.rollNo}
                </span>

                <span className="break-words text-xs font-medium text-white/90">
                  {record.studentName}
                </span>
              </div>

              {record.note && (
                <p className="mt-1 text-[11px] leading-relaxed text-white/45">
                  {record.note}
                </p>
              )}
            </div>

            {/* Attendance Status */}
            <div className="shrink-0">
              {record.status === 'Present' && (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-white/75">
                  <CheckCircle2 className="h-3 w-3" />
                  Present
                </span>
              )}

              {record.status === 'Absent' && (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-white/55">
                  <XCircle className="h-3 w-3" />
                  Absent
                </span>
              )}

              {record.status === 'Needs Review' && (
                <span className="inline-flex items-center gap-1.5 rounded-md border border-white/20 bg-white/[0.07] px-2 py-1 text-[10px] font-medium text-white">
                  <AlertCircle className="h-3 w-3" />
                  Review
                </span>
              )}
            </div>
          </div>
        ))}

        {data.records.length === 0 && (
          <div className="rounded-xl border border-white/10 bg-[#0b0b0b] p-6 text-center">
            <Users2 className="mx-auto mb-2 h-6 w-6 text-white/35" />
            <p className="text-xs text-white/50">
              No attendance records available.
            </p>
          </div>
        )}
      </div>

      {/* Approval Footer */}
      <div className="border-t border-white/10 pt-4">
        <button
          type="button"
          onClick={() =>
            onApprove('Daily attendance confirmed by course instructor.')
          }
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85"
        >
          <ThumbsUp className="h-4 w-4" />
          <span>Approve Class Attendance</span>
        </button>

        <p className="mt-2 text-center text-[10px] text-white/35">
          Attendance will be confirmed by the teacher.
        </p>
      </div>
    </div>
  );
};