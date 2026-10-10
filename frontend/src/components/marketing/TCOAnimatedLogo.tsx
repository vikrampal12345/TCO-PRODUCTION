import React from 'react';

interface TCOAnimatedLogoProps {
  /** Start the task-in-progress motion when true. */
  active?: boolean;
  /** Compact, state-driven presentation for the teacher workspace. */
  variant?: 'hero' | 'workspace';
  className?: string;
}

const particles = [
  { left: '13%', top: '22%', delay: '0s', duration: '3.8s', size: 2 },
  { left: '82%', top: '19%', delay: '0.8s', duration: '4.2s', size: 2 },
  { left: '8%', top: '58%', delay: '1.4s', duration: '3.4s', size: 1.5 },
  { left: '89%', top: '52%', delay: '0.4s', duration: '4.4s', size: 2 },
  { left: '22%', top: '84%', delay: '1.1s', duration: '3.7s', size: 1.5 },
  { left: '73%', top: '86%', delay: '2s', duration: '4.1s', size: 2 },
  { left: '50%', top: '7%', delay: '1.7s', duration: '3.9s', size: 1.5 },
  { left: '94%', top: '37%', delay: '2.2s', duration: '4.3s', size: 1.5 },
  { left: '4%', top: '40%', delay: '0.6s', duration: '3.6s', size: 2 },
  { left: '58%', top: '94%', delay: '1.9s', duration: '4.5s', size: 1.5 },
];

/** Animated chrome TCO monogram adapted from the supplied animation HTML. */
export const TCOAnimatedLogo: React.FC<TCOAnimatedLogoProps> = ({
  active = false,
  variant = 'hero',
  className = '',
}) => {
  const logoClassName = [
    'tco-animated-logo',
    variant === 'workspace' ? 'tco-animated-logo-workspace' : '',
    active ? 'is-active' : '',
    className,
  ].filter(Boolean).join(' ');

  return (
    <div
      className={logoClassName}
      role="img"
      aria-label="TCO animated chrome monogram — Teacher Co-Worker"
    >
      <div className="tco-logo-aura" aria-hidden="true" />

      <div className="tco-logo-stage" aria-hidden="true">
        {particles.map((particle, index) => (
          <span
            key={index}
            className="tco-logo-particle"
            style={{
              left: particle.left,
              top: particle.top,
              animationDelay: particle.delay,
              animationDuration: particle.duration,
              width: `${particle.size}px`,
              height: `${particle.size}px`,
            }}
          />
        ))}

        <img
          src="/tco-logo-t.png"
          alt=""
          draggable={false}
          className="tco-logo-layer tco-logo-layer-t"
        />
        <img
          src="/tco-logo-c.png"
          alt=""
          draggable={false}
          className="tco-logo-layer tco-logo-layer-c"
        />
        <img
          src="/tco-logo-o.png"
          alt=""
          draggable={false}
          className="tco-logo-layer tco-logo-layer-o"
        />

        <span className="tco-logo-shimmer" />
      </div>
    </div>
  );
};
