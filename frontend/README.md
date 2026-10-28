# TCO — Teacher Co-Worker (Frontend MVP)

> **"Teach More. Manage Less."**  
> *Your AI co-worker for the work behind the classroom.*  
> **Core Philosophy:** *"AI assists. Teachers decide."*

---

## 1. Project Overview

**TCO (Teacher Co-Worker)** is an AI-powered conversational workspace and co-worker for teachers, educators, and professors. It automates repetitive, mechanical non-teaching work:

- **Checking Student Answer Sheets** (Handwriting OCR transcription + verified rubric alignment + provisional scoring with explicit teacher rationale)
- **Question Paper & Exam Generation** (Curriculum-aligned across Bloom's Taxonomy cognitive levels, section distributions, and mark limits)
- **Class Marksheet Compilations** (Totaling, grading tiers, error-free exports to PDF and Excel)
- **Attendance Ledger Reconciliation** (Physical sign-in roster reconciliation with zero invasive biometric surveillance)
- **Lecture PPT Generation** (12-slide structured classroom decks with instructor talking notes)
- **Diagnostic Class Analytics** (Question-wise mastery diagnostics, score distributions, and student support signals)

### What TCO is NOT
- **NOT an AI teacher replacement**
- **NOT a generic chatbot**
- **NOT a traditional bloated ERP dashboard**
- **NOT an autonomous grading system that finalizes academic records without human approval**

---

## 2. Tech Stack

- **React 18** (Functional components, hooks, custom state orchestrators)
- **TypeScript** (Strict types, no implicit any, robust interfaces)
- **Vite** (Lightning-fast development & production bundling)
- **Tailwind CSS** (Custom dark cinematic theme, glassmorphism, glowing ambient accents)
- **Framer Motion** (Smooth transitions, right review panel drawer, process timelines)
- **Lucide React** (Consistent modern icon system)
- **React Router v6** (Stateful multi-route client navigation)

---

## 3. Project Structure

```text
├── index.html                     # HTML5 entry with dark theme & web fonts
├── package.json                   # Dependencies & npm scripts
├── postcss.config.js              # PostCSS Tailwind integration
├── tailwind.config.js             # Tailwind design tokens & cinematic dark theme
├── tsconfig.json                  # TypeScript compiler settings
├── tsconfig.node.json             # TypeScript node config
├── vite.config.ts                 # Vite bundler & path alias configuration
├── src/
│   ├── App.tsx                    # Root component with providers & routing
│   ├── main.tsx                   # DOM mount entry
│   ├── routes.tsx                 # Route declarations (/, /login, /signup, /workspace, etc.)
│   ├── index.css                  # Global styles, glassmorphism utilities & scrollbars
│   ├── context/
│   │   └── AuthContext.tsx        # Simulated authentication provider (JWT-ready)
│   ├── hooks/
│   │   ├── useAuth.ts             # Auth hook shortcut
│   │   └── useChat.ts             # Stateful chat & workflow orchestration hook
│   ├── types/
│   │   ├── auth.ts                # User, Role, and Auth credentials types
│   │   ├── chat.ts                # Message, Conversation, QuickAction types
│   │   ├── workflow.ts            # Central workflow state machine & agent types
│   │   └── review.ts              # Answer Sheet, Question Paper, Marksheet data contracts
│   ├── services/
│   │   ├── api.ts                 # Clean API contract interface
│   │   ├── mockApi.ts             # Stateful in-memory mock service layer
│   │   └── demoData.ts            # Realistic demo evaluations & test data
│   ├── components/
│   │   ├── auth/
│   │   │   └── AuthLayout.tsx     # Cinematic container for login & signup
│   │   ├── marketing/
│   │   │   ├── Navbar.tsx         # Responsive header with branding & CTAs
│   │   │   ├── Hero.tsx           # Cinematic hero with live workflow preview
│   │   │   ├── FeatureShowcase.tsx# 8 core capability cards
│   │   │   ├── WorkflowTimeline.tsx # "How TCO Works" 5-step flow
│   │   │   ├── AgentNetwork.tsx   # Master Agent + 7 specialized agents visualizer
│   │   │   ├── CopyCheckingDemo.tsx # Flagship Answer Sheet Checking split-screen demo
│   │   │   ├── TeacherFirstPhilosophy.tsx # "What TCO is vs is NOT" contrast
│   │   │   ├── SchoolBenefits.tsx # Institutional impact & burnout reduction
│   │   │   ├── SecuritySection.tsx# Controlled guardrails & review enforcement
│   │   │   ├── Testimonials.tsx   # Simulated educator evaluation feedback
│   │   │   ├── FinalCTA.tsx       # Bottom conversion section
│   │   │   └── Footer.tsx         # Comprehensive site footer
│   │   └── workspace/
│   │       ├── ConversationSidebar.tsx # Collapsible 280px history & new chat sidebar
│   │       ├── ChatWindow.tsx     # Conversational center pane with quick action chips
│   │       ├── ChatMessageItem.tsx # Rich cards, attachments & timeline rendering
│   │       ├── MessageComposer.tsx # Auto-expanding bottom composer with stop control
│   │       ├── ClarificationBar.tsx # Contextual choice card above composer
│   │       ├── ApprovalBar.tsx    # Contextual approval card above composer
│   │       ├── ProcessTimeline.tsx # Human-readable agent execution steps
│   │       ├── ContextPanel.tsx   # 520px slide-in right review drawer
│   │       └── reviews/
│   │           ├── AnswerSheetReview.tsx   # Student STU047 handwriting review
│   │           ├── QuestionPaperReview.tsx # OS 20-question review & editing
│   │           ├── MarksheetPreview.tsx    # Student grade ledger & export
│   │           ├── AttendancePreview.tsx   # Roster reconciliation & checks
│   │           ├── PPTPreview.tsx          # 12-slide lecture deck viewer
│   │           └── AnalyticsPreview.tsx    # Diagnostic class performance
│   └── pages/
│       ├── Home.tsx               # Marketing landing page
│       ├── Login.tsx              # Teacher sign in
│       ├── Signup.tsx             # Account creation & role configuration
│       ├── Workspace.tsx          # Authenticated conversational co-worker
│       ├── Tasks.tsx              # Academic workflow ledger
│       ├── Files.tsx              # Scanned and generated course artifacts
│       ├── Analytics.tsx          # Class diagnostics overview
│       └── Settings.tsx           # Profile, rubric standards & FastAPI URL
```

---

## 4. Getting Started & Installation

### Prerequisites
- Node.js version 18.x or higher
- npm, pnpm, or yarn

### 1. Install Dependencies
```bash
npm install
```

### 2. Run Local Development Server
```bash
npm run dev
```
The application will launch at `http://localhost:5173/`.

### 3. Build for Production Deployment
```bash
npm run build
```
This generates a production-ready, minified bundle in the `dist/` directory.

### 4. Preview Production Build
```bash
npm run preview
```

---

## 5. Required Routes

| Route | View | Description |
|---|---|---|
| `/` | `Home.tsx` | Public dark cinematic marketing landing page with interactive demos |
| `/login` | `Login.tsx` | Teacher sign-in page with simulated Google SSO and instant redirect to `/workspace` |
| `/signup` | `Signup.tsx` | Educator onboarding with Role selection (Teacher, Educator, Administrator) |
| `/workspace` | `Workspace.tsx` | Main 3-pane conversational AI co-worker workspace |
| `/tasks` | `Tasks.tsx` | Academic task tracking ledger |
| `/files` | `Files.tsx` | Course repository of student answer scans and generated exams |
| `/analytics` | `Analytics.tsx` | Diagnostic class performance and question mastery rates |
| `/settings` | `Settings.tsx` | Teacher preferences, rubric benchmarks, and FastAPI backend configuration |

---

## 6. How the Mock API Works

The project adheres strictly to **Clean Architecture & Separation of Concerns**:

```text
React UI Components
        ↓
   services/api.ts (ITCOApiService Contract)
        ↓
 services/mockApi.ts (In-Memory Stateful Service)
        ↓
  services/demoData.ts (Demo Evaluation Scenarios)
```

1. **Decoupled Contract (`api.ts`)**: UI components never import `mockApi` directly; they only communicate through the `ITCOApiService` interface exported by `api.ts`.
2. **Stateful Interaction Loop**: When you type or click quick actions such as *"Check Answer Sheets"* or *"Create a question paper for OS"*:
   - `sendMessage()` creates an active workflow and returns a contextual clarification or approval request.
   - If TCO needs clarification (e.g., *"Where should I get the reference material from?"*), `ClarificationBar` renders directly **above the message composer**.
   - When the teacher selects an option (e.g. *"Uploaded material"*), TCO advances the workflow to `review_required` and opens the **Right Context Panel**.
   - Clicking **Approve** commits the evaluation, updates the conversation status to `Completed`, and records the result.
3. **Safe Demo Grounding**: All student identities (`STU047`, `STU052`, etc.) and metrics are clearly labeled as demo data, respecting ethical educational guidelines.

---

## 7. FastAPI Connection

The real API client and auth adapter are included in this frontend. Use the `.env` switch and follow [`README_BACKEND_INTEGRATION.md`](./README_BACKEND_INTEGRATION.md) for the exact endpoint contract and test procedure. The frontend archive does not include backend source, so match the adapter to the existing backend routes before switching demo mode off.

## 8. Real Backend Integration

The app defaults to mock/demo data so the frontend can be previewed without a running API. Copy `.env.example` to `.env`, set `VITE_USE_MOCK_API=false`, and set `VITE_API_BASE_URL` to the actual FastAPI route prefix to use the backend adapter. The paperclip now selects actual files and sends multipart form data when files are attached.

See [`README_BACKEND_INTEGRATION.md`](./README_BACKEND_INTEGRATION.md) for the expected endpoint contract, authentication token handling, CORS setup, file-upload requirements, and backend smoke-test command. The supplied ZIP contains frontend code only, so endpoint names must be verified against the real backend router code.

## 9. Deployment Guide for Hackathon URL

You can deploy this frontend directly to any static web hosting provider:

### Deploying to Vercel (Recommended)
1. Push this repository to GitHub or GitLab.
2. Visit [Vercel](https://vercel.com/) and click **"Add New Project"**.
3. Select your repository. Vercel automatically detects Vite + React.
4. Click **Deploy**. Your public production URL will be live in under 60 seconds!

### Deploying to Netlify
1. Create a `netlify.toml` file in the root:
   ```toml
   [build]
     command = "npm run build"
     publish = "dist"

   [[redirects]]
     from = "/*"
     to = "/index.html"
     status = 200
   ```
2. Connect your Git repository on Netlify and deploy.

---

## 10. Design System Summary
- **Background**: Deep Navy / Obsidian `#05070f`, Surfaces `#090d1a`, Cards `#0b1021`
- **Accents**: Cyan `#06b6d4`, Blue `#3b82f6`, Indigo `#6366f1`, Emerald `#10b981` (Approvals)
- **Glassmorphism**: `backdrop-blur-md`, subtle `border-white/10`, `shadow-glow-cyan`
- **Typography**: Inter (Body & Headers), JetBrains Mono (Codes, Marks, Student IDs)
