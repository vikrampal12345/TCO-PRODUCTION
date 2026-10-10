import React from 'react';
import { useNavigate } from 'react-router-dom';
import { FileText, Download, ArrowLeft, Search, Upload } from 'lucide-react';

export const Files: React.FC = () => {
  const navigate = useNavigate();

  const files = [
    { name: 'DBMS_Unit3_AnswerSheets_BatchA.pdf', type: 'PDF Document', size: '14.2 MB', date: 'Today, 10:14 AM', category: 'Answer Sheets' },
    { name: 'Operating_Systems_Question_Paper_Final.pdf', type: 'PDF Document', size: '420 KB', date: 'Today, 09:06 AM', category: 'Question Papers' },
    { name: 'Midterm_Marksheet_CSE_SectionB.xlsx', type: 'Excel Spreadsheet', size: '84 KB', date: 'Yesterday', category: 'Marksheets' },
    { name: 'CS301_Attendance_Ledger_Oct8.csv', type: 'CSV Document', size: '12 KB', date: 'Yesterday', category: 'Attendance' },
    { name: 'Java_Concurrency_Architecture_Deck.pptx', type: 'PowerPoint Deck', size: '5.6 MB', date: 'Oct 5', category: 'Presentations' },
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
          <h1 className="text-sm font-bold text-white sm:text-base">Course Materials & Artifacts</h1>
        </div>

        <button
          onClick={() => alert('Simulated: Upload new physical scans or rubric PDFs.')}
          className="inline-flex shrink-0 items-center justify-center gap-1.5 self-start rounded-lg border border-white/10 bg-white/10 px-3.5 py-2 text-xs font-semibold text-white transition-colors hover:bg-white/15 sm:self-auto"
        >
          <Upload className="w-3.5 h-3.5 text-white/70" />
          <span>Upload Material</span>
        </button>
      </header>

      <main className="mx-auto w-full max-w-5xl flex-1 space-y-5 px-4 py-5 sm:space-y-6 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
          <div>
            <h2 className="text-lg font-extrabold text-white sm:text-xl">Exam Papers & Evaluated Copies</h2>
            <p className="mt-1 max-w-xl text-xs leading-relaxed text-gray-400 sm:mt-0.5">Secure academic storage for all digitized and teacher-verified files.</p>
          </div>

          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              type="text"
              placeholder="Search files..."
              className="w-full pl-9 pr-3 py-1.5 bg-[#0a0a0a] border border-white/10 rounded-lg text-xs text-white placeholder-gray-500 focus:outline-none focus:border-white/40"
            />
          </div>
        </div>

        <div className="bg-[#0b0b0b] rounded-2xl border border-white/10 overflow-hidden shadow-glass">
          <div className="divide-y divide-white/5">
            {files.map((file, idx) => (
              <div
                key={idx}
                className="flex items-start justify-between gap-3 p-3 transition-colors hover:bg-white/[0.02] sm:items-center sm:gap-4 sm:p-4"
              >
                <div className="flex min-w-0 flex-1 items-start gap-3 sm:items-center">
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/5 text-white/70 sm:h-10 sm:w-10">
                    <FileText className="w-5 h-5" />
                  </div>
                  <div className="min-w-0 flex-1">
                    <div className="break-all text-xs font-semibold text-white sm:break-normal sm:text-sm">{file.name}</div>
                    <div className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 font-mono text-[10px] leading-relaxed text-gray-400 sm:text-[11px]">
                      <span>{file.category}</span>
                      <span>•</span>
                      <span>{file.size}</span>
                      <span>•</span>
                      <span>{file.date}</span>
                    </div>
                  </div>
                </div>

                <button
                  onClick={() => alert(`Simulated download for: ${file.name}`)}
                  className="shrink-0 rounded-lg bg-white/5 p-2 text-gray-300 transition-colors hover:bg-white/10 hover:text-white"
                  title="Download File"
                >
                  <Download className="w-4 h-4" />
                </button>
              </div>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};
