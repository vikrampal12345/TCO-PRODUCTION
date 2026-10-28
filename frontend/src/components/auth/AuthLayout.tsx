import React from 'react';
import { Link } from 'react-router-dom';
import { motion, useReducedMotion } from 'framer-motion';
import { ShieldCheck } from 'lucide-react';

interface AuthLayoutProps {
  children: React.ReactNode;
  title: string;
  subtitle: string;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  title,
  subtitle,
}) => {
  const reduceMotion = useReducedMotion();

  const enterTransition = reduceMotion
    ? { duration: 0 }
    : { duration: 0.55, ease: [0.22, 1, 0.36, 1] as const };

  return (
    <div className="relative isolate flex min-h-[100svh] w-full flex-col items-center justify-center overflow-x-hidden bg-black px-4 py-8 sm:px-6 sm:py-10">
      {/* Animated monochrome background */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden" aria-hidden="true">
        <motion.div
          className="auth-glow auth-glow-center absolute left-1/2 top-1/2 h-[min(700px,120vw)] w-[min(700px,120vw)] rounded-full bg-white/[0.035] blur-[110px]"
          animate={reduceMotion ? undefined : {
            x: ['-50%', '-46%', '-50%'],
            y: ['-50%', '-54%', '-50%'],
            scale: [1, 1.08, 1],
            opacity: [0.55, 0.9, 0.55],
          }}
          transition={{ duration: 16, repeat: Infinity, ease: 'easeInOut' }}
          style={{ translateX: '-50%', translateY: '-50%' }}
        />
        <motion.div
          className="auth-glow absolute -top-64 left-1/2 h-[500px] w-[min(800px,130vw)] rounded-full bg-white/[0.04] blur-[120px]"
          animate={reduceMotion ? undefined : { x: ['-50%', '-46%', '-50%'], opacity: [0.45, 0.75, 0.45] }}
          transition={{ duration: 19, repeat: Infinity, ease: 'easeInOut' }}
          style={{ translateX: '-50%' }}
        />
        <motion.div
          className="auth-glow absolute -left-64 top-[20%] h-[420px] w-[420px] rounded-full bg-gray-300/[0.025] blur-[115px]"
          animate={reduceMotion ? undefined : { x: [0, 30, 0], y: [0, -20, 0] }}
          transition={{ duration: 21, repeat: Infinity, ease: 'easeInOut' }}
        />
        <motion.div
          className="auth-glow absolute -right-64 bottom-[5%] h-[440px] w-[440px] rounded-full bg-white/[0.025] blur-[120px]"
          animate={reduceMotion ? undefined : { x: [0, -28, 0], y: [0, 22, 0] }}
          transition={{ duration: 23, repeat: Infinity, ease: 'easeInOut' }}
        />

        <div className="auth-orbit auth-orbit-one absolute left-1/2 top-1/2 h-[850px] w-[850px] rounded-full border border-white/[0.035]" />
        <div className="auth-orbit auth-orbit-two absolute left-1/2 top-1/2 h-[1100px] w-[1100px] rounded-full border border-white/[0.022]" />
        <div className="auth-orbit auth-orbit-three absolute left-1/2 top-1/2 h-[1350px] w-[1350px] rounded-full border border-white/[0.014]" />

        <div className="absolute inset-0 opacity-[0.025] [background-image:linear-gradient(rgba(255,255,255,0.5)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.5)_1px,transparent_1px)] [background-size:80px_80px]" />
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,transparent_15%,rgba(0,0,0,0.55)_65%,rgba(0,0,0,0.92)_100%)]" />
        <div className="absolute inset-0 bg-[linear-gradient(to_bottom,rgba(0,0,0,0.3),transparent_25%,transparent_75%,rgba(0,0,0,0.45))]" />
      </div>

      {/* Brand and page title */}
      <motion.header
        initial={reduceMotion ? false : { opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={enterTransition}
        className="relative z-10 mx-auto w-full max-w-md space-y-4 text-center"
      >
        <Link to="/" className="group inline-flex items-center justify-center gap-3 rounded-xl focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-white/70">
          <motion.div
            whileHover={reduceMotion ? undefined : { scale: 1.06, rotate: -2 }}
            whileTap={reduceMotion ? undefined : { scale: 0.97 }}
            className="flex h-11 w-11 items-center justify-center rounded-xl bg-white p-0.5 shadow-[0_0_35px_rgba(255,255,255,0.08)] transition-shadow group-hover:shadow-[0_0_42px_rgba(255,255,255,0.16)]"
          >
            <div className="flex h-full w-full items-center justify-center rounded-[10px] bg-black">
              <span className="text-xl font-extrabold tracking-wider text-white">TCO</span>
            </div>
          </motion.div>
        </Link>

        <div className="space-y-2">
          <h1 className="text-2xl font-extrabold tracking-tight text-white sm:text-3xl">
            {title}
          </h1>
          <p className="mx-auto max-w-sm text-xs leading-relaxed text-gray-400 sm:text-sm">
            {subtitle}
          </p>
        </div>
      </motion.header>

      {/* Animated responsive form card */}
      <motion.div
        initial={reduceMotion ? false : { opacity: 0, y: 22, scale: 0.985 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={reduceMotion ? { duration: 0 } : { ...enterTransition, delay: 0.08 }}
        className="relative z-10 mt-6 w-full max-w-md sm:mt-8"
      >
        <div className="relative rounded-2xl border border-white/[0.10] bg-[#0a0a0a]/90 px-5 py-6 shadow-[0_25px_80px_rgba(0,0,0,0.65)] backdrop-blur-xl sm:px-8 sm:py-8 lg:px-10">
          <div className="pointer-events-none absolute left-1/2 top-0 h-px w-32 -translate-x-1/2 bg-gradient-to-r from-transparent via-white/25 to-transparent" />
          {children}
        </div>

        <motion.div
          initial={reduceMotion ? false : { opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={reduceMotion ? { duration: 0 } : { duration: 0.6, delay: 0.35 }}
          className="mt-5 flex items-center justify-center gap-2 px-2 text-center text-[11px] text-gray-500 sm:mt-6 sm:text-xs"
        >
          <ShieldCheck className="h-3.5 w-3.5 shrink-0 text-gray-400" />
          <span>Teacher Co-Worker</span>
        </motion.div>
      </motion.div>
    </div>
  );
};
