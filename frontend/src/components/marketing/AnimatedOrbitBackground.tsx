import React from 'react';

export const AnimatedOrbitBackground: React.FC = () => {
  return (
    <div className="absolute inset-0 overflow-hidden pointer-events-none z-0">

      {/* Center glow */}
      <div className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-[700px] h-[700px] rounded-full bg-white/[0.035] blur-[120px]" />

      {/* Orbit Ring 1 */}
      <div className="orbit orbit-1">

        <div className="orbit-item item-1">
          <div className="orbit-card">
            <div className="card-icon">✓</div>
            <div>
              <div className="card-title">Answer Checking</div>
              <div className="card-subtitle">AI evaluation</div>
            </div>
          </div>
        </div>

        <div className="orbit-item item-2">
          <div className="orbit-card">
            <div className="card-icon">✓</div>
            <div>
              <div className="card-title">Marks Approved</div>
              <div className="card-subtitle">Teacher review</div>
            </div>
          </div>
        </div>

        <div className="orbit-item item-3">
          <div className="orbit-card">
            <div className="card-icon">AI</div>
            <div>
              <div className="card-title">Master Agent</div>
              <div className="card-subtitle">Coordinating</div>
            </div>
          </div>
        </div>

        <div className="orbit-item item-4">
          <div className="orbit-card">
            <div className="card-icon">≡</div>
            <div>
              <div className="card-title">Question Paper</div>
              <div className="card-subtitle">Generated</div>
            </div>
          </div>
        </div>

      </div>

      {/* Orbit Ring 2 */}
      <div className="orbit orbit-2">

        <div className="orbit-item item-a">
          <div className="orbit-card orbit-card-small">
            <div className="card-icon">01</div>
            <div>
              <div className="card-title">Student 047</div>
              <div className="card-subtitle">Processing</div>
            </div>
          </div>
        </div>

        <div className="orbit-item item-b">
          <div className="orbit-card orbit-card-small">
            <div className="card-icon">✓</div>
            <div>
              <div className="card-title">Review Ready</div>
              <div className="card-subtitle">Awaiting teacher</div>
            </div>
          </div>
        </div>

        <div className="orbit-item item-c">
          <div className="orbit-card orbit-card-small">
            <div className="card-icon">AI</div>
            <div>
              <div className="card-title">OCR Active</div>
              <div className="card-subtitle">Reading answers</div>
            </div>
          </div>
        </div>

      </div>

      {/* Visible orbit lines */}
      <div className="orbit-ring ring-1" />
      <div className="orbit-ring ring-2" />

    </div>
  );
};