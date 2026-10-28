import React from 'react';
import { Navbar } from '../components/marketing/Navbar';
import { Hero } from '../components/marketing/Hero';
import { WorkflowTimeline } from '../components/marketing/WorkflowTimeline';
import { TeacherFirstPhilosophy } from '../components/marketing/TeacherFirstPhilosophy';
import { SecuritySection } from '../components/marketing/SecuritySection';
import { Footer } from '../components/marketing/Footer';

export const Home: React.FC = () => {
  return (
    <div className="min-h-screen bg-black text-gray-100 flex flex-col selection:bg-white/20 selection:text-white">
      <Navbar />
      <main className="flex-1">
        <Hero />
        <TeacherFirstPhilosophy />
        <WorkflowTimeline />
        <SecuritySection />
      </main>
      <Footer />
    </div>
  );
};
