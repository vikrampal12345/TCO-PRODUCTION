export interface ExtractedQuestionEvaluation {
  questionNumber: string;
  questionText: string;
  maxMarks: number;
  suggestedMarks: number;
  extractedAnswer: string;
  rubricCriteria: string[];
  rationale: string;
  confidence: 'High' | 'Medium' | 'Low';
  teacherOverrideMarks?: number;
  teacherNote?: string;
  status: 'pending' | 'approved' | 'modified' | 'flagged';
}

export interface AnswerSheetReviewData {
  id: string;
  studentId: string;
  studentName: string;
  rollNumber: string;
  assessmentTitle: string;
  subject: string;
  totalPages: number;
  currentPage: number;
  status: 'Review Required' | 'Approved' | 'Flagged';
  questions: ExtractedQuestionEvaluation[];
  workflowPipeline: {
    extraction: 'complete' | 'in_progress' | 'pending';
    verification: 'complete' | 'in_progress' | 'pending';
    grading: 'complete' | 'in_progress' | 'pending';
    teacherReview: 'active' | 'complete' | 'pending';
    finalApproval: 'pending' | 'complete';
  };
}

export interface QuestionPaperItem {
  id: string;
  number: number;
  question: string;
  marks: number;
  type: 'Short Answer' | 'Long Answer' | 'MCQ' | 'Problem Solving';
  bloomLevel?: string;
}

export interface QuestionPaperReviewData {
  id: string;
  subject: string;
  gradeOrClass: string;
  totalQuestions: number;
  totalMarks: number;
  durationMinutes: number;
  instructions: string[];
  questions: QuestionPaperItem[];
}

export interface MarksheetRow {
  studentId: string;
  rollNo: string;
  studentName: string;
  marks: number;
  totalMarks: number;
  percentage: number;
  grade: string;
  status: 'Verified' | 'Needs Review' | 'Absent';
}

export interface MarksheetReviewData {
  id: string;
  subject: string;
  assessmentName: string;
  classSection: string;
  date: string;
  records: MarksheetRow[];
}

export interface AttendanceRecord {
  rollNo: string;
  studentName: string;
  status: 'Present' | 'Absent' | 'Needs Review';
  note?: string;
}

export interface AttendanceReviewData {
  id: string;
  className: string;
  date: string;
  totalStudents: number;
  presentCount: number;
  absentCount: number;
  needsReviewCount: number;
  records: AttendanceRecord[];
}

export interface PPTSlideItem {
  slideNumber: number;
  title: string;
  bullets: string[];
  speakerNotes?: string;
}

export interface PPTReviewData {
  id: string;
  topic: string;
  totalSlides: number;
  sections: string[];
  slides: PPTSlideItem[];
}

export interface AnalyticsData {
  id: string;
  classAverage: number;
  studentsEvaluated: number;
  totalQuestions: number;
  studentsNeedingAttention: number;
  questionPerformance: {
    question: string;
    topic: string;
    avgScorePercent: number;
    difficulty: 'Easy' | 'Moderate' | 'Hard';
  }[];
  scoreDistribution: {
    range: string;
    count: number;
  }[];
}
