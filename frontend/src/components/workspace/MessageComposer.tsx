
import React, { useState, useRef, useEffect } from 'react';
import type { MessageAttachmentInput } from '../../services/api';
import {
  ArrowUp,
  Paperclip,
  Mic,
  Square,
  FileText,
  X,
  Database,
  Globe,
  GraduationCap,
  Brain,
} from 'lucide-react';

export type WorkspaceSourceMode =
  | 'general_knowledge'
  | 'teacher_file'
  | 'classroom'
  | 'web_search';

interface MessageComposerProps {
  onSend: (
    message: string,
    attachments?: MessageAttachmentInput[],
    sourceMode?: WorkspaceSourceMode,
  ) => void;
  isProcessing: boolean;
  onStop: () => void;
  disabled?: boolean;
}

const SOURCE_OPTIONS: {
  value: WorkspaceSourceMode;
  label: string;
  description: string;
}[] = [
  {
    value: 'general_knowledge',
    label: 'General Knowledge',
    description: 'Use general AI knowledge without a reference source',
  },
  {
    value: 'teacher_file',
    label: 'Teacher File + RAG',
    description: 'Ground the response in your uploaded reference files',
  },
  {
    value: 'classroom',
    label: 'Google Classroom + RAG',
    description: 'Use relevant content from Google Classroom',
  },
  {
    value: 'web_search',
    label: 'Web Search + RAG',
    description: 'Find relevant web sources for the task',
  },
];

export const MessageComposer: React.FC<MessageComposerProps> = ({
  onSend,
  isProcessing,
  onStop,
  disabled = false,
}) => {
  const [content, setContent] = useState('');
  const [attachments, setAttachments] = useState<MessageAttachmentInput[]>([]);
  const [sourceMode, setSourceMode] =
    useState<WorkspaceSourceMode>('general_knowledge');

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!textareaRef.current) return;

    textareaRef.current.style.height = 'auto';
    const scrollHeight = textareaRef.current.scrollHeight;

    textareaRef.current.style.height = `${Math.min(
      scrollHeight,
      180,
    )}px`;
  }, [content]);

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLTextAreaElement>,
  ) => {
    if (
      event.key === 'Enter' &&
      !event.shiftKey &&
      !event.nativeEvent.isComposing
    ) {
      event.preventDefault();
      handleSubmit();
    }
  };

  const handleSubmit = () => {
    if (
      (!content.trim() && attachments.length === 0) ||
      isProcessing ||
      disabled
    ) {
      return;
    }

    // Pass the selected source mode through the callback.
    // The next integration step connects it to the FastAPI request.
    onSend(content.trim(), attachments, sourceMode);

    setContent('');
    setAttachments([]);

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) {
      return `${(bytes / 1024).toFixed(1)} KB`;
    }
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const handleFilesSelected = (
    event: React.ChangeEvent<HTMLInputElement>,
  ) => {
    const selected = Array.from(event.target.files || []);

    if (selected.length > 0) {
      setAttachments((previous) => [
        ...previous,
        ...selected.map((file) => ({
          name: file.name,
          size: formatFileSize(file.size),
          type: file.type || 'application/octet-stream',
          file,
        })),
      ]);
    }

    // Allow selecting the same file after removing it.
    event.target.value = '';
  };

  const removeAttachment = (index: number) => {
    setAttachments((previous) =>
      previous.filter((_, itemIndex) => itemIndex !== index),
    );
  };

  const canSend =
    (content.trim().length > 0 || attachments.length > 0) &&
    !isProcessing &&
    !disabled;

  const selectedSource = SOURCE_OPTIONS.find(
    (option) => option.value === sourceMode,
  );

  const getSourceIcon = () => {
    switch (sourceMode) {
      case 'teacher_file':
        return <FileText className="h-4 w-4" />;
      case 'classroom':
        return <GraduationCap className="h-4 w-4" />;
      case 'web_search':
        return <Globe className="h-4 w-4" />;
      default:
        return <Brain className="h-4 w-4" />;
    }
  };

  return (
    <div className="relative z-10 border-t border-white/[0.06] bg-black px-3 py-3 sm:px-4 sm:py-4">
      <div className="mx-auto max-w-4xl">
        <input
          ref={fileInputRef}
          type="file"
          multiple
          accept=".pdf,.doc,.docx,.txt,.png,.jpg,.jpeg,.webp,.xlsx,.csv"
          className="hidden"
          onChange={handleFilesSelected}
        />

        {/* Attachment chips */}
        {attachments.length > 0 && (
          <div className="mb-3 flex flex-wrap gap-2 px-1">
            {attachments.map((attachment, index) => (
              <div
                key={`${attachment.name}-${index}`}
                className="flex max-w-full items-center gap-2 rounded-lg border border-white/10 bg-[#111111] px-3 py-2 text-xs text-white/80"
              >
                <FileText className="h-4 w-4 shrink-0 text-white/60" />

                <span className="max-w-[180px] truncate">
                  {attachment.name}
                </span>

                <span className="shrink-0 text-[10px] text-white/40">
                  ({attachment.size})
                </span>

                <button
                  type="button"
                  onClick={() => removeAttachment(index)}
                  disabled={disabled || isProcessing}
                  className="ml-1 rounded p-0.5 text-white/40 transition-colors hover:bg-white/10 hover:text-white disabled:opacity-40"
                  aria-label={`Remove ${attachment.name}`}
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Composer */}
        <div className="rounded-2xl border border-white/10 bg-[#0c0c0c] p-2 transition-colors focus-within:border-white/25">
          {/* Source selection */}
          <div className="flex flex-col gap-2 border-b border-white/[0.07] px-2 pb-3 pt-1 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex min-w-0 items-center gap-2">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.04] text-white/70">
                {getSourceIcon()}
              </div>

              <div className="min-w-0">
                <label
                  htmlFor="tco-source-mode"
                  className="block text-[11px] font-medium text-white/80"
                >
                  Knowledge source
                </label>

                <p className="mt-0.5 text-[10px] text-white/40">
                  {selectedSource?.description}
                </p>
              </div>
            </div>

            <select
              id="tco-source-mode"
              value={sourceMode}
              onChange={(event) =>
                setSourceMode(event.target.value as WorkspaceSourceMode)
              }
              disabled={disabled || isProcessing}
              className="w-full rounded-lg border border-white/10 bg-[#151515] px-3 py-2 text-xs text-white outline-none transition-colors focus:border-white/30 disabled:cursor-not-allowed disabled:opacity-50 sm:max-w-[230px]"
            >
              {SOURCE_OPTIONS.map((option) => (
                <option
                  key={option.value}
                  value={option.value}
                  className="bg-[#151515] text-white"
                >
                  {option.label}
                </option>
              ))}
            </select>
          </div>

          {/* Message input */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled || isProcessing}
            placeholder="Message TCO..."
            className="max-h-[180px] min-h-[44px] w-full resize-none bg-transparent px-3 pb-2 pt-3 text-sm leading-relaxed text-white outline-none placeholder:text-white/35 disabled:cursor-not-allowed"
          />

          {/* Bottom controls */}
          <div className="mt-1 flex items-center justify-between border-t border-white/[0.07] px-1 pt-2">
            <div className="flex min-w-0 items-center gap-1">
              <button
                type="button"
                onClick={() => fileInputRef.current?.click()}
                disabled={disabled || isProcessing}
                className="rounded-lg p-2 text-white/50 transition-colors hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                title="Attach exam materials"
                aria-label="Attach exam materials"
              >
                <Paperclip className="h-4 w-4" />
              </button>

              <button
                type="button"
                onClick={() =>
                  setContent((previous) =>
                    previous
                      ? `${previous} (voice command)`
                      : 'Check these answer sheets',
                  )
                }
                disabled={disabled || isProcessing}
                className="rounded-lg p-2 text-white/50 transition-colors hover:bg-white/10 hover:text-white disabled:cursor-not-allowed disabled:opacity-40"
                title="Voice dictation (simulated)"
                aria-label="Voice dictation"
              >
                <Mic className="h-4 w-4" />
              </button>

              <span className="ml-2 hidden text-[11px] text-white/35 sm:inline">
                Shift + Enter for new line
              </span>
            </div>

            {/* Send / Stop */}
            <div className="flex shrink-0 items-center gap-2">
              {isProcessing ? (
                <button
                  type="button"
                  onClick={onStop}
                  className="flex items-center gap-2 rounded-lg border border-white/15 bg-white/10 px-3 py-2 text-xs font-medium text-white transition-colors hover:bg-white/15"
                >
                  <Square className="h-3 w-3 fill-current" />
                  <span>Stop</span>
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSubmit}
                  disabled={!canSend}
                  className={`flex h-9 w-9 items-center justify-center rounded-xl transition-colors ${
                    canSend
                      ? 'bg-white text-black hover:bg-white/85'
                      : 'cursor-not-allowed bg-white/[0.06] text-white/25'
                  }`}
                  title="Send message"
                  aria-label="Send message"
                >
                  <ArrowUp className="h-4 w-4" />
                </button>
              )}
            </div>
          </div>
        </div>

        <p className="mt-2 text-center text-[10px] text-white/30">
          AI assists. Teachers decide.
        </p>
      </div>
    </div>
  );
};
