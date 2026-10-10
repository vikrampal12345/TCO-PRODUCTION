import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import {
  ArrowLeft,
  Save,
  ShieldCheck,
  Server,
  User,
  BookOpen,
  Check,
} from 'lucide-react';

export const Settings: React.FC = () => {
  const { user } = useAuth();
  const navigate = useNavigate();

  const [savedSuccess, setSavedSuccess] = useState(false);

  const [fastApiEndpoint, setFastApiEndpoint] = useState(() => {
    try {
      const saved = localStorage.getItem('tco_user_preferences');
      if (saved) {
        const preferences = JSON.parse(saved) as { fastApiEndpoint?: string };
        if (preferences.fastApiEndpoint) return preferences.fastApiEndpoint;
      }
    } catch { /* use configured default */ }
    return import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1';
  });

  const [rubricStandard, setRubricStandard] = useState(
    "Bloom's Taxonomy Revised"
  );

  const [confidenceThreshold, setConfidenceThreshold] = useState('85');

  const [name, setName] = useState(user?.name || '');
  const [email] = useState(user?.email || '');
  const [school, setSchool] = useState(
    user?.school || 'School of Computing & Engineering'
  );

  const [isSaving, setIsSaving] = useState(false);

  const inputClassName =
    'w-full rounded-xl border border-white/10 bg-[#080808] px-3 py-2.5 text-sm text-white outline-none transition-colors placeholder:text-white/25 focus:border-white/30 disabled:opacity-50';

  const labelClassName =
    'mb-2 block text-xs font-medium text-white/60';

  const sectionClassName =
    'space-y-5 rounded-2xl border border-white/10 bg-[#0b0b0b] p-5 sm:p-6';

  const handleSave = async (e: React.FormEvent) => {
    e.preventDefault();

    if (isSaving) return;

    setIsSaving(true);
    setSavedSuccess(false);

    try {
      // Demo: persist preferences locally.
      // Replace this with your settings API when backend persistence is ready.
      const preferences = {
        name: name.trim(),
        school: school.trim(),
        rubricStandard,
        confidenceThreshold: Number(confidenceThreshold),
        fastApiEndpoint: fastApiEndpoint.trim(),
      };

      localStorage.setItem(
        'tco_user_preferences',
        JSON.stringify(preferences)
      );

      setSavedSuccess(true);

      window.setTimeout(() => {
        setSavedSuccess(false);
      }, 3000);
    } catch {
      setSavedSuccess(false);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex min-h-screen flex-col bg-black font-sans text-white">
      {/* Header */}
      <header className="sticky top-0 z-20 flex min-h-16 items-center justify-between gap-4 border-b border-white/10 bg-black/90 px-4 backdrop-blur-xl sm:px-6">
        <div className="flex min-w-0 items-center gap-3 sm:gap-4">
          <button
            type="button"
            onClick={() => navigate('/workspace')}
            className="flex shrink-0 items-center gap-2 rounded-xl border border-white/10 bg-white/[0.04] px-3 py-2 text-xs font-medium text-white/70 transition-colors hover:bg-white/[0.08] hover:text-white"
          >
            <ArrowLeft className="h-4 w-4" />
            <span className="hidden sm:inline">Workspace</span>
          </button>

          <div className="min-w-0">
            <h1 className="truncate text-sm font-semibold text-white sm:text-base">
              Settings
            </h1>

            <p className="hidden text-[11px] text-white/40 sm:block">
              Manage your profile and workflow preferences
            </p>
          </div>
        </div>

        <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
          <ShieldCheck className="h-4 w-4 text-white/70" />
        </div>
      </header>

      {/* Main Content */}
      <main className="mx-auto w-full max-w-3xl flex-1 space-y-6 px-4 py-6 sm:px-6 sm:py-8">
        {/* Page Intro */}
        <div className="space-y-2">
          <h2 className="text-xl font-semibold tracking-tight text-white sm:text-2xl">
            Teacher & Workflow Preferences
          </h2>

          <p className="text-xs leading-relaxed text-white/45 sm:text-sm">
            Configure your instructor profile, academic evaluation
            standards, and backend connection settings.
          </p>
        </div>

        {/* Success Message */}
        {savedSuccess && (
          <div
            role="status"
            className="flex items-center gap-3 rounded-xl border border-white/15 bg-white/[0.05] p-4"
          >
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-white/10 bg-white/[0.05]">
              <Check className="h-4 w-4 text-white" />
            </div>

            <div>
              <p className="text-xs font-semibold text-white">
                Preferences saved
              </p>

              <p className="mt-1 text-[11px] text-white/45">
                Your settings have been saved in this browser.
              </p>
            </div>
          </div>
        )}

        <form onSubmit={handleSave} className="space-y-5">
          {/* Instructor Profile */}
          <section className={sectionClassName}>
            <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
                <User className="h-4 w-4 text-white/75" />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Instructor Profile
                </h3>

                <p className="mt-1 text-[11px] text-white/40">
                  Your account and institution details
                </p>
              </div>
            </div>

            <div className="grid grid-cols-1 gap-4 text-xs sm:grid-cols-2">
              <div>
                <label htmlFor="settings-name" className={labelClassName}>
                  Full Name
                </label>

                <input
                  id="settings-name"
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  placeholder="Enter your full name"
                  className={inputClassName}
                />
              </div>

              <div>
                <label htmlFor="settings-email" className={labelClassName}>
                  Email Address
                </label>

                <input
                  id="settings-email"
                  type="email"
                  value={email}
                  readOnly
                  className="w-full cursor-not-allowed rounded-xl border border-white/[0.06] bg-white/[0.02] px-3 py-2.5 text-sm text-white/40 outline-none"
                />

                <p className="mt-1.5 text-[10px] text-white/30">
                  Email cannot be changed here.
                </p>
              </div>

              <div className="sm:col-span-2">
                <label htmlFor="settings-school" className={labelClassName}>
                  Department / Institution
                </label>

                <input
                  id="settings-school"
                  type="text"
                  value={school}
                  onChange={(e) => setSchool(e.target.value)}
                  placeholder="Enter your department or institution"
                  className={inputClassName}
                />
              </div>
            </div>
          </section>

          {/* Academic Standards */}
          <section className={sectionClassName}>
            <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
                <BookOpen className="h-4 w-4 text-white/75" />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Academic & Rubric Standards
                </h3>

                <p className="mt-1 text-[11px] text-white/40">
                  Configure assessment evaluation preferences
                </p>
              </div>
            </div>

            <div className="space-y-5">
              <div>
                <label
                  htmlFor="rubric-standard"
                  className={labelClassName}
                >
                  Assessment Evaluation Benchmark
                </label>

                <select
                  id="rubric-standard"
                  value={rubricStandard}
                  onChange={(e) => setRubricStandard(e.target.value)}
                  className={`${inputClassName} appearance-none`}
                >
                  <option value="Bloom's Taxonomy Revised">
                    Bloom's Taxonomy (Cognitive Levels 1–6)
                  </option>

                  <option value="Standard Higher Ed Rubric">
                    Standard University Engineering Scale
                  </option>

                  <option value="CBSE / Board Pattern">
                    State & Central Board Standard
                  </option>
                </select>

                <p className="mt-2 text-[11px] leading-relaxed text-white/35">
                  This preference defines the evaluation framework used
                  when preparing assessments and rubrics.
                </p>
              </div>

              <div>
                <label
                  htmlFor="confidence-threshold"
                  className={labelClassName}
                >
                  OCR Confidence Threshold
                </label>

                <div className="flex flex-wrap items-center gap-3">
                  <div className="relative w-28">
                    <input
                      id="confidence-threshold"
                      type="number"
                      min={0}
                      max={100}
                      value={confidenceThreshold}
                      onChange={(e) =>
                        setConfidenceThreshold(e.target.value)
                      }
                      required
                      className={`${inputClassName} pr-8 text-center font-mono`}
                    />

                    <span className="absolute right-3 top-1/2 -translate-y-1/2 text-xs text-white/40">
                      %
                    </span>
                  </div>

                  <span className="text-[11px] text-white/40">
                    Default: 85%
                  </span>
                </div>

                <p className="mt-2 text-[11px] leading-relaxed text-white/35">
                  Answers below this confidence level can be flagged for
                  teacher verification, provided the backend applies this
                  setting.
                </p>
              </div>
            </div>
          </section>

          {/* Backend Configuration */}
          <section className={sectionClassName}>
            <div className="flex items-center gap-3 border-b border-white/[0.08] pb-4">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl border border-white/10 bg-white/[0.04]">
                <Server className="h-4 w-4 text-white/75" />
              </div>

              <div>
                <h3 className="text-sm font-semibold text-white">
                  Backend Integration
                </h3>

                <p className="mt-1 text-[11px] text-white/40">
                  FastAPI server configuration
                </p>
              </div>
            </div>

            <div>
              <label
                htmlFor="fastapi-endpoint"
                className={labelClassName}
              >
                API Base URL
              </label>

              <input
                id="fastapi-endpoint"
                type="url"
                value={fastApiEndpoint}
                onChange={(e) => setFastApiEndpoint(e.target.value)}
                placeholder="http://localhost:8000/api/v1"
                required
                className={`${inputClassName} font-mono text-xs`}
              />

              <div className="mt-3 rounded-xl border border-white/[0.08] bg-white/[0.02] p-3">
                <div className="flex items-start gap-2.5">
                  <div className="mt-0.5 h-2 w-2 shrink-0 rounded-full bg-white/50" />

                  <p className="text-[11px] leading-relaxed text-white/45">
                    Saving this URL stores it as a preference only. Your
                    frontend API client must read this setting for it to
                    change the actual backend connection. Avoid exposing
                    private API keys or credentials in frontend settings.
                  </p>
                </div>
              </div>
            </div>
          </section>

          {/* Save Button */}
          <div className="flex flex-col-reverse gap-3 border-t border-white/10 pt-5 sm:flex-row sm:items-center sm:justify-between">
            <p className="text-[10px] leading-relaxed text-white/35">
              AI assists. Teachers decide.
            </p>

            <button
              type="submit"
              disabled={isSaving}
              className="flex items-center justify-center gap-2 rounded-xl bg-white px-5 py-3 text-xs font-semibold text-black transition-colors hover:bg-white/85 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {isSaving ? (
                <div className="h-4 w-4 animate-spin rounded-full border-2 border-black/20 border-t-black" />
              ) : (
                <Save className="h-4 w-4" />
              )}

              <span>{isSaving ? 'Saving...' : 'Save Preferences'}</span>
            </button>
          </div>
        </form>
      </main>
    </div>
  );
};