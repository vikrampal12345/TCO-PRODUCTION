import React, { useState } from 'react';
import { PPTReviewData } from '../../../types/review';
import {
  Presentation,
  RefreshCw,
  ThumbsUp,
} from 'lucide-react';

interface PPTPreviewProps {
  data: PPTReviewData;
  onApprove: (notes?: string) => void;
  onRequestRevision: (instructions: string) => void;
}

export const PPTPreview: React.FC<PPTPreviewProps> = ({
  data,
  onApprove,
  onRequestRevision,
}) => {
  const [selectedSlide, setSelectedSlide] = useState<number>(0);

  const currentSlide = data.slides[selectedSlide];

  return (
    <div className="flex h-full flex-col space-y-5 text-white/80">
      {/* Header */}
      <div className="space-y-4 rounded-xl border border-white/10 bg-[#0b0b0b] p-4">
        <div className="flex items-center justify-between gap-3">
          <div className="flex min-w-0 items-center gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05] text-white/75">
              <Presentation className="h-4 w-4" />
            </div>

            <div className="min-w-0">
              <h3 className="truncate text-sm font-semibold text-white">
                {data.topic}
              </h3>

              <p className="mt-1 text-xs text-white/45">
                {data.totalSlides} Slides · 16:9 Presentation Format
              </p>
            </div>
          </div>

          <span className="shrink-0 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-[10px] font-medium text-white/65">
            Structured
          </span>
        </div>

        {/* Section Tags */}
        {data.sections.length > 0 && (
          <div className="flex flex-wrap gap-1.5 border-t border-white/[0.06] pt-3">
            {data.sections.map((section, index) => (
              <span
                key={`${section}-${index}`}
                className="rounded-md border border-white/[0.08] bg-white/[0.03] px-2 py-1 text-[10px] text-white/50"
              >
                {section}
              </span>
            ))}
          </div>
        )}
      </div>

      {/* Slide Preview */}
      <div className="space-y-3">
        <div className="flex items-center justify-between gap-2">
          <span className="text-xs font-medium text-white/75">
            Slide Preview
          </span>

          <span className="font-mono text-[10px] text-white/45">
            {currentSlide
              ? `Slide ${selectedSlide + 1} of ${data.slides.length}`
              : 'No slides available'}
          </span>
        </div>

        {currentSlide ? (
          <div className="group relative flex aspect-video flex-col justify-between overflow-hidden rounded-xl border border-white/15 bg-[#080808] p-5 sm:p-7">
            {/* Subtle decorative background */}
            <div className="pointer-events-none absolute right-0 top-0 h-32 w-32 rounded-full bg-white/[0.025] blur-3xl" />

            <div className="relative z-10 space-y-4">
              <div className="flex items-center gap-2 text-[9px] font-medium uppercase tracking-[0.2em] text-white/40 sm:text-[10px]">
                <Presentation className="h-3.5 w-3.5" />
                TCO Presentation Agent
              </div>

              <h4 className="max-w-2xl text-base font-semibold leading-tight text-white sm:text-xl">
                {currentSlide.title}
              </h4>

              {currentSlide.bullets.length > 0 ? (
                <ul className="list-disc space-y-2 pl-4 text-[11px] leading-relaxed text-white/65 sm:text-xs">
                  {currentSlide.bullets.map((bullet, index) => (
                    <li key={`${bullet}-${index}`}>{bullet}</li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-white/40">
                  No slide content available.
                </p>
              )}
            </div>

            {currentSlide.speakerNotes && (
              <div className="relative z-10 mt-4 border-t border-white/10 pt-3 text-[10px] italic leading-relaxed text-white/45 sm:text-[11px]">
                <span className="mr-1 font-semibold not-italic text-white/70">
                  Speaker Notes:
                </span>
                {currentSlide.speakerNotes}
              </div>
            )}

            {/* Slide Number */}
            <span className="absolute bottom-3 right-4 font-mono text-[9px] text-white/25">
              {currentSlide.slideNumber}
            </span>
          </div>
        ) : (
          <div className="flex aspect-video flex-col items-center justify-center rounded-xl border border-dashed border-white/10 bg-[#080808] p-6 text-center">
            <Presentation className="mb-3 h-8 w-8 text-white/25" />
            <p className="text-sm font-medium text-white/65">
              No slides available
            </p>
            <p className="mt-1 text-xs text-white/40">
              Slide content will appear here once it is generated.
            </p>
          </div>
        )}
      </div>

      {/* Slide Selector */}
      {data.slides.length > 0 && (
        <div className="space-y-2">
          <div className="text-[11px] font-medium text-white/50">
            All Slides
          </div>

          <div className="flex items-center gap-2 overflow-x-auto pb-2">
            {data.slides.map((slide, index) => (
              <button
                key={`${slide.slideNumber}-${index}`}
                type="button"
                onClick={() => setSelectedSlide(index)}
                aria-pressed={selectedSlide === index}
                className={`w-28 shrink-0 rounded-lg border p-2.5 text-left transition-colors ${
                  selectedSlide === index
                    ? 'border-white/35 bg-white/[0.09] text-white'
                    : 'border-white/[0.08] bg-[#0b0b0b] text-white/50 hover:border-white/20 hover:bg-white/[0.04] hover:text-white/80'
                }`}
              >
                <div className="font-mono text-[9px] text-white/40">
                  SLIDE {slide.slideNumber}
                </div>

                <div className="mt-1 truncate text-[11px] font-medium">
                  {slide.title}
                </div>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Action Footer */}
      <div className="space-y-3 border-t border-white/10 pt-4">
        <button
          type="button"
          onClick={() =>
            onApprove(
              `${data.totalSlides}-slide lecture deck approved for PowerPoint export.`
            )
          }
          disabled={data.slides.length === 0}
          className="flex w-full items-center justify-center gap-2 rounded-xl bg-white px-4 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-40"
        >
          <ThumbsUp className="h-4 w-4" />
          <span>Approve & Export PowerPoint (.pptx)</span>
        </button>

        <button
          type="button"
          onClick={() =>
            onRequestRevision(
              'Add more diagram placeholders to illustrate process states.'
            )
          }
          className="flex w-full items-center justify-center gap-2 rounded-xl border border-white/10 bg-white/[0.03] py-3 text-[11px] font-medium text-white/55 transition-colors hover:bg-white/[0.07] hover:text-white"
        >
          <RefreshCw className="h-3.5 w-3.5" />
          Regenerate Slide Sequence
        </button>

        <p className="text-center text-[10px] text-white/35">
          AI assists. Teachers decide.
        </p>
      </div>
    </div>
  );
};