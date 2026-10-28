import React from 'react';
import { MarksheetReviewData } from '../../../types/review';
import {
  Table,
  Download,
  FileSpreadsheet,
  CheckCircle2,
  AlertCircle,
  ThumbsUp,
} from 'lucide-react';

interface MarksheetPreviewProps {
  data: MarksheetReviewData;
  onApprove: (notes?: string) => void;
}

export const MarksheetPreview: React.FC<MarksheetPreviewProps> = ({
  data,
  onApprove,
}) => {
  return (
    <div className="flex h-full flex-col space-y-5 text-white/80">
      {/* Marksheet Header */}
      <div className="space-y-3 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-white/75">
              <Table className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-white">
                {data.subject}
              </h3>

              <p className="mt-1 text-xs text-white/45">
                {data.assessmentName} · {data.classSection}
              </p>
            </div>
          </div>

          <span className="shrink-0 rounded-md border border-white/15 bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-white/65">
            Calculated
          </span>
        </div>

        <div className="flex flex-wrap items-center justify-between gap-2 border-t border-white/[0.08] pt-3 text-[11px]">
          <span className="text-white/45">Date: {data.date}</span>

          <span className="text-white/40">Demo Data</span>
        </div>
      </div>

      {/* Marksheet Table */}
      <div className="flex-1 overflow-auto rounded-xl border border-white/10 bg-[#080808]">
        <table className="w-full min-w-[520px] border-collapse text-left text-xs">
          <thead className="sticky top-0 z-10 border-b border-white/10 bg-[#111111]">
            <tr className="text-[10px] font-medium uppercase tracking-wider text-white/45">
              <th className="px-3 py-3">Roll No.</th>
              <th className="px-3 py-3">Student Name</th>
              <th className="px-3 py-3 text-center">Marks</th>
              <th className="px-3 py-3 text-center">Grade</th>
              <th className="px-3 py-3">Status</th>
            </tr>
          </thead>

          <tbody className="divide-y divide-white/[0.06]">
            {data.records.map((record) => (
              <tr
                key={record.studentId}
                className="transition-colors hover:bg-white/[0.03]"
              >
                <td className="whitespace-nowrap px-3 py-3 font-mono text-white/55">
                  {record.rollNo}
                </td>

                <td className="px-3 py-3 font-medium text-white/85">
                  {record.studentName}
                </td>

                <td className="whitespace-nowrap px-3 py-3 text-center font-mono">
                  <span className="font-semibold text-white">
                    {record.marks}
                  </span>

                  <span className="text-[10px] text-white/35">
                    {' '}/ {record.totalMarks}
                  </span>
                </td>

                <td className="px-3 py-3 text-center">
                  <span className="inline-flex rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 font-mono text-[11px] font-medium text-white/75">
                    {record.grade}
                  </span>
                </td>

                <td className="px-3 py-3">
                  {record.status === 'Verified' ? (
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[11px] text-white/65">
                      <CheckCircle2 className="h-3.5 w-3.5" />
                      Verified
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-1.5 whitespace-nowrap text-[11px] text-white/45">
                      <AlertCircle className="h-3.5 w-3.5" />
                      Needs Review
                    </span>
                  )}
                </td>
              </tr>
            ))}

            {data.records.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-10 text-center">
                  <Table className="mx-auto mb-2 h-6 w-6 text-white/30" />
                  <p className="text-xs text-white/50">
                    No marksheet records available.
                  </p>
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Actions */}
      <div className="space-y-3 border-t border-white/10 pt-4">
        <div className="grid grid-cols-2 gap-3">
          <button
            type="button"
            onClick={() =>
              alert('Demo: Exporting standard PDF Marksheet format.')
            }
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-3 text-xs font-medium text-white/75 transition-colors hover:bg-white/10 hover:text-white"
          >
            <Download className="h-4 w-4" />
            <span>Export PDF</span>
          </button>

          <button
            type="button"
            onClick={() =>
              alert('Demo: Exporting formatted Excel (.xlsx) spreadsheet.')
            }
            className="flex items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-3 text-xs font-medium text-white/75 transition-colors hover:bg-white/10 hover:text-white"
          >
            <FileSpreadsheet className="h-4 w-4" />
            <span>Export Excel</span>
          </button>
        </div>

        <button
          type="button"
          onClick={() =>
            onApprove('Marksheet compilation finalized and locked by teacher.')
          }
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85"
        >
          <ThumbsUp className="h-4 w-4" />
          <span>Approve Final Marksheet</span>
        </button>

        <p className="text-center text-[10px] text-white/35">
          Final marksheet requires teacher approval.
        </p>
      </div>
    </div>
  );
};