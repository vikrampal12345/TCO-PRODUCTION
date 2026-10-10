import React from 'react';
import { useNavigate } from 'react-router-dom';
import { motion } from 'framer-motion';
import {
  ArrowRight,
  Play,
  CheckCircle2,
  ShieldCheck,
  Cpu,
} from 'lucide-react';

import { AnimatedOrbitBackground } from './AnimatedOrbitBackground';
import { TCOAnimatedLogo } from './TCOAnimatedLogo';

export const Hero: React.FC = () => {
  const navigate = useNavigate();

  return (
    <section
      className="
        relative
        min-h-[760px]
        pt-32
        pb-24
        md:pt-40
        md:pb-32
        overflow-hidden
        bg-black
      "
    >

      {/* =========================================
          ORBITING TCO BACKGROUND
          ========================================= */}
      <AnimatedOrbitBackground />

      {/* =========================================
          HERO CONTENT
          ========================================= */}
      <div className="relative z-10 max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">

        <div className="text-center max-w-4xl mx-auto space-y-8">

          {/* Animated TCO chrome monogram replaces the old text badge */}
          <motion.div
            initial={{ opacity: 0, y: 18, scale: 0.96 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ duration: 0.8, ease: 'easeOut' }}
            className="flex justify-center -mb-5 sm:-mb-7"
          >
            <TCOAnimatedLogo />
          </motion.div>

          {/* =========================================
              MAIN HEADLINE
              ========================================= */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{
              duration: 0.6,
              delay: 0.1,
            }}
            className="space-y-4"
          >

            <h1
              className="
                text-4xl
                sm:text-6xl
                lg:text-7xl
                font-extrabold
                tracking-tight
                text-white
                leading-[1.1]
              "
            >
              Teach More.{' '}

              <span
                className="
                  bg-gradient-to-r
                  from-white
                  via-gray-300
                  to-gray-500
                  bg-clip-text
                  text-transparent
                "
              >
                Manage Less.
              </span>
            </h1>


            <p
              className="
                text-lg
                sm:text-xl
                lg:text-2xl
                text-gray-300
                font-normal
                max-w-2xl
                mx-auto
                leading-relaxed
              "
            >
              Your AI co-worker for the work behind the classroom.
            </p>
          </motion.div>

          {/* =========================================
              ACTION BUTTONS
              ========================================= */}
          <motion.div
            initial={{
              opacity: 0,
              y: 20,
            }}
            animate={{
              opacity: 1,
              y: 0,
            }}
            transition={{
              duration: 0.6,
              delay: 0.2,
            }}
            className="
              flex
              flex-col
              sm:flex-row
              items-center
              justify-center
              gap-4
              pt-2
            "
          >

            {/* Primary CTA */}
            <button
              onClick={() => navigate('/signup')}
              className="
                w-full
                sm:w-auto
                px-8
                py-3.5
                rounded-xl
                bg-white
                text-black
                font-semibold
                text-base
                shadow-lg
                hover:bg-gray-200
                hover:shadow-xl
                hover:scale-[1.02]
                transition-all
                duration-300
                flex
                items-center
                justify-center
                gap-2
                group
              "
            >
              <span>
                Get Started Free
              </span>

              <ArrowRight
                className="
                  w-4
                  h-4
                  transition-transform
                  group-hover:translate-x-1
                "
              />
            </button>


            {/* Secondary CTA */}
            <a
              href="#features"
              className="
                w-full
                sm:w-auto
                px-7
                py-3.5
                rounded-xl
                bg-white/[0.05]
                border
                border-white/10
                hover:bg-white/[0.08]
                hover:border-white/20
                text-gray-200
                font-medium
                text-base
                backdrop-blur-md
                transition-all
                flex
                items-center
                justify-center
                gap-2.5
              "
            >

              <div
                className="
                  w-6
                  h-6
                  rounded-full
                  bg-white/10
                  text-white
                  flex
                  items-center
                  justify-center
                "
              >
                <Play
                  className="
                    w-3
                    h-3
                    fill-current
                    ml-0.5
                  "
                />
              </div>

              <span>
                Explore TCO Features
              </span>

            </a>

          </motion.div>


          {/* =========================================
              TRUST GUARANTEES
              ========================================= */}
          <div
            className="
              flex
              flex-wrap
              items-center
              justify-center
              gap-6
              pt-4
              text-xs
              text-gray-400
            "
          >

            <span className="flex items-center gap-1.5">
              <ShieldCheck className="w-4 h-4 text-white" />
              Controlled human-in-the-loop workflows
            </span>

            <span className="flex items-center gap-1.5">
              <CheckCircle2 className="w-4 h-4 text-gray-300" />
              Zero autonomous grade finalization
            </span>

            <span className="flex items-center gap-1.5">
              <Cpu className="w-4 h-4 text-gray-400" />
              TCO Master Agent coordination
            </span>

          </div>

        </div>
      </div>

    </section>
  );
};