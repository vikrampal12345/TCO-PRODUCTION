import { Conversation } from '../types/chat';
import {
  AnswerSheetReviewData,
  QuestionPaperReviewData,
  MarksheetReviewData,
  AttendanceReviewData,
  PPTReviewData,
  AnalyticsData
} from '../types/review';

export const INITIAL_CONVERSATIONS: Conversation[] = [
  {
    id: 'conv-1',
    title: 'Check DBMS answer sheets',
    status: 'In Review',
    group: 'Today',
    lastUpdated: '10 mins ago',
    preview: 'AI completed evaluation for 35 sheets. Student STU047 flagged for teacher review.',
    activeWorkflowType: 'answer_sheet_checking',
    messages: [
      {
        id: 'm1-1',
        sender: 'teacher',
        timestamp: '10:14 AM',
        content: 'Check these answer sheets for the DBMS Mid-Term examination.',
        attachments: [
          { id: 'att-1', name: 'DBMS_Unit3_AnswerSheets_BatchA.pdf', size: '14.2 MB', type: 'application/pdf' },
          { id: 'att-2', name: 'DBMS_Marking_Scheme.pdf', size: '1.1 MB', type: 'application/pdf' },
        ],
      },
      {
        id: 'm1-2',
        sender: 'tco',
        timestamp: '10:14 AM',
        content: "I've received the answer sheets and marking scheme for the DBMS examination. TCO Master Agent has initiated the Answer Sheet Evaluation pipeline.",
        workflowProgress: {
          workflowId: 'wf-dbms-101',
          type: 'answer_sheet_checking',
          state: 'review_required',
          activeAgent: 'Answer Sheet Checking Agent',
          steps: [
            { id: 's1', agent: 'TCO Master Agent', label: 'Understanding request', description: 'Matched curriculum and assessment schema', status: 'completed' },
            { id: 's2', agent: 'Answer Sheet Checking Agent', label: 'Extracting student answers', description: 'Digitized 4 pages for Student STU047', status: 'completed' },
            { id: 's3', agent: 'Evaluation Agent', label: 'Verifying answer extraction', description: 'Cross-checked with marking scheme rubrics', status: 'completed' },
            { id: 's4', agent: 'Evaluation Agent', label: 'Provisional grading & rationale', description: 'Assigned provisional 4/5 marks with detailed reason', status: 'completed' },
            { id: 's5', agent: 'TCO Master Agent', label: 'Waiting for Teacher Review', description: 'AI assists. You make the final decision.', status: 'active' },
          ],
          approval: {
            id: 'app-dbms-1',
            title: 'Answer Sheet Ready for Teacher Review',
            summary: 'Student STU047 (Data Structures & DBMS Unit Test) has completed provisional grading. Review required before finalization.',
            metrics: [
              { label: 'Student', value: 'STU047' },
              { label: 'Pages', value: '4 Pages' },
              { label: 'Provisional Score', value: '4 / 5' },
              { label: 'Confidence', value: 'High' }
            ],
            reviewType: 'answer_sheet_checking',
            requiresReview: true
          }
        },
        reviewType: 'answer_sheet_checking',
        reviewDataId: 'review-as-stu047'
      }
    ]
  },
  {
    id: 'conv-2',
    title: 'Create OS question paper',
    status: 'Completed',
    group: 'Today',
    lastUpdated: '1 hour ago',
    preview: 'Operating Systems question paper generated with 20 questions (50 Marks).',
    activeWorkflowType: 'question_paper_generation',
    messages: [
      {
        id: 'm2-1',
        sender: 'teacher',
        timestamp: '09:05 AM',
        content: 'Create a question paper for Operating Systems covering Processes, Threads, CPU Scheduling, and Memory Management.',
      },
      {
        id: 'm2-2',
        sender: 'tco',
        timestamp: '09:06 AM',
        content: "Here is the structured 50-mark question paper for Operating Systems. It balances conceptual definitions, comparative analysis, and numerical scheduling problems according to Bloom's Taxonomy.",
        approval: {
          id: 'app-os-1',
          title: 'Question Paper Generated & Approved',
          summary: '20 questions structured across Section A (Short), Section B (Analytical), and Section C (Numerical). Total Marks: 50.',
          metrics: [
            { label: 'Total Questions', value: '20' },
            { label: 'Total Marks', value: '50' },
            { label: 'Duration', value: '90 mins' },
            { label: 'Status', value: 'Approved by Teacher' }
          ],
          reviewType: 'question_paper_generation',
        },
        reviewType: 'question_paper_generation',
        reviewDataId: 'review-qp-os'
      }
    ]
  },
  {
    id: 'conv-3',
    title: 'Class attendance',
    status: 'Completed',
    group: 'Yesterday',
    lastUpdated: 'Yesterday, 3:45 PM',
    preview: 'Attendance verified for CS-301. 38 Present, 3 Absent, 1 Flagged.',
    activeWorkflowType: 'attendance',
    messages: [
      {
        id: 'm3-1',
        sender: 'teacher',
        timestamp: 'Yesterday 3:42 PM',
        content: 'Mark attendance for today\'s CS-301 lecture based on the sign-in sheet.',
      },
      {
        id: 'm3-2',
        sender: 'tco',
        timestamp: 'Yesterday 3:44 PM',
        content: 'Processed the sign-in sheet for CS-301. 38 students marked Present, 3 marked Absent, and 1 record required teacher confirmation.',
        reviewType: 'attendance',
        reviewDataId: 'review-att-cs301'
      }
    ]
  },
  {
    id: 'conv-4',
    title: 'Generate Java PPT',
    status: 'Completed',
    group: 'Previous 7 Days',
    lastUpdated: '3 days ago',
    preview: '12-slide lecture presentation on Java Multithreading & Concurrency.',
    activeWorkflowType: 'ppt_generation',
    messages: [
      {
        id: 'm4-1',
        sender: 'teacher',
        timestamp: 'Oct 5, 11:20 AM',
        content: 'Make a PPT on Java Concurrency and Thread Lifecycle for tomorrow\'s lab class.',
      },
      {
        id: 'm4-2',
        sender: 'tco',
        timestamp: 'Oct 5, 11:22 AM',
        content: 'Generated a comprehensive 12-slide presentation structure with code snippets, thread lifecycle diagrams, and review questions.',
        reviewType: 'ppt_generation',
        reviewDataId: 'review-ppt-java'
      }
    ]
  },
  {
    id: 'conv-5',
    title: 'Analyze Unit Test results',
    status: 'Completed',
    group: 'Older',
    lastUpdated: '2 weeks ago',
    preview: 'Class average 72%. 6 students identified needing additional tutorial support.',
    activeWorkflowType: 'analytics',
    messages: [
      {
        id: 'm5-1',
        sender: 'teacher',
        timestamp: 'Sep 24, 04:10 PM',
        content: 'Analyze my class performance for the recent Data Structures Unit Test 2.',
      },
      {
        id: 'm5-2',
        sender: 'tco',
        timestamp: 'Sep 24, 04:12 PM',
        content: 'Here is the class performance diagnostic. Average score is 72%. Binary Search Trees and Graph Traversals were the primary friction points.',
        reviewType: 'analytics',
        reviewDataId: 'review-analytics-ds'
      }
    ]
  }
];

export const DEMO_ANSWER_SHEET: AnswerSheetReviewData = {
  id: 'review-as-stu047',
  studentId: 'STU047',
  studentName: 'Aarav Patel',
  rollNumber: 'CS-2026-047',
  assessmentTitle: 'Data Structures & DBMS Unit Test',
  subject: 'Computer Science & Engineering',
  totalPages: 4,
  currentPage: 1,
  status: 'Review Required',
  workflowPipeline: {
    extraction: 'complete',
    verification: 'complete',
    grading: 'complete',
    teacherReview: 'active',
    finalApproval: 'pending'
  },
  questions: [
    {
      questionNumber: 'Q1',
      questionText: 'Explain the working of Binary Search on an array. State its time and space complexity with justification.',
      maxMarks: 5,
      suggestedMarks: 4,
      extractedAnswer: 'Binary search works on a sorted array by repeatedly dividing the search interval in half. Beginning with an interval covering the whole array, if the target value is less than the middle element, the search continues in the left half, otherwise in the right half. Repeated until value found or interval empty.\nTime Complexity: O(log n)\nSpace Complexity: O(1)',
      rubricCriteria: [
        'Sorted array prerequisite mentioned (1 mark) - Met',
        'Divide and conquer mechanism explained (2 marks) - Met',
        'Time and space complexity stated with justification (2 marks) - Partially Met (justification brief)'
      ],
      rationale: 'Core concept is correct and algorithmic steps are well articulated. However, the theoretical derivation/justification for logarithmic time complexity is omitted.',
      confidence: 'High',
      status: 'pending'
    },
    {
      questionNumber: 'Q2',
      questionText: 'Differentiate between 2NF and 3NF with an appropriate relational schema example.',
      maxMarks: 5,
      suggestedMarks: 5,
      extractedAnswer: '2NF removes partial functional dependencies (where a non-prime attribute depends on a part of candidate key). 3NF eliminates transitive dependencies (non-prime attribute depending on another non-prime attribute). Example: Student(Roll, Course, Instructor) decomposed into Student(Roll, Course) and CourseInstructor(Course, Instructor).',
      rubricCriteria: [
        'Definition of 2NF (1.5 marks) - Met',
        'Definition of 3NF (1.5 marks) - Met',
        'Clear practical example with decomposition (2 marks) - Met'
      ],
      rationale: 'Comprehensive explanation with correct functional dependency conditions and accurate relational decomposition example.',
      confidence: 'High',
      status: 'pending'
    },
    {
      questionNumber: 'Q3',
      questionText: 'What is a B+ Tree index and why is it preferred over a binary search tree for database storage?',
      maxMarks: 5,
      suggestedMarks: 3.5,
      extractedAnswer: 'B+ Tree is a balanced search tree where all data records are stored at leaf nodes and internal nodes only contain index keys. Leaves are linked as a doubly linked list for range queries. It is preferred because disk block reads are minimized due to high fan-out.',
      rubricCriteria: [
        'B+ tree structural characteristics (2 marks) - Met',
        'Disk I/O and block read efficiency reasoning (2 marks) - Partially Met',
        'Range scan advantage (1 mark) - Met'
      ],
      rationale: 'Student correctly identifies node structure and sequential leaf pointers, but does not explicitly quantify disk seek overhead comparison against un-balanced or low-fanout BSTs.',
      confidence: 'Medium',
      status: 'pending'
    }
  ]
};

export const DEMO_QUESTION_PAPER: QuestionPaperReviewData = {
  id: 'review-qp-os',
  subject: 'Operating Systems (CS-402)',
  gradeOrClass: 'B.Tech CSE - 3rd Year',
  totalQuestions: 20,
  totalMarks: 50,
  durationMinutes: 90,
  instructions: [
    'Answer all questions in Section A (10 Marks).',
    'Answer any 5 questions from Section B (20 Marks).',
    'Answer any 2 questions from Section C (20 Marks).',
    'Assume standard page size of 4KB wherever numerical parameters are not explicitly given.'
  ],
  questions: [
    { id: 'qp-1', number: 1, question: 'What is a process control block (PCB)? List three primary attributes it maintains.', marks: 2, type: 'Short Answer', bloomLevel: 'Remember' },
    { id: 'qp-2', number: 2, question: 'Distinguish between preemptive and non-preemptive CPU scheduling.', marks: 2, type: 'Short Answer', bloomLevel: 'Understand' },
    { id: 'qp-3', number: 3, question: 'Explain the four necessary conditions for a deadlock to occur in an operating system.', marks: 4, type: 'Short Answer', bloomLevel: 'Understand' },
    { id: 'qp-4', number: 4, question: 'Compare First-Come First-Served (FCFS) and Shortest Job First (SJF) scheduling algorithms with average turnaround time tradeoffs.', marks: 4, type: 'Problem Solving', bloomLevel: 'Analyze' },
    { id: 'qp-5', number: 5, question: 'Describe how virtual memory is implemented using demand paging with a translation lookaside buffer (TLB).', marks: 5, type: 'Long Answer', bloomLevel: 'Understand' },
    { id: 'qp-6', number: 6, question: 'Solve the Bankers Algorithm safety check for the provided 5-process resource allocation matrix.', marks: 10, type: 'Problem Solving', bloomLevel: 'Apply' },
    { id: 'qp-7', number: 7, question: 'Illustrate the Producer-Consumer problem and solve it using POSIX counting semaphores.', marks: 10, type: 'Problem Solving', bloomLevel: 'Apply' },
  ]
};

export const DEMO_MARKSHEET: MarksheetReviewData = {
  id: 'review-marksheet-dbms',
  subject: 'Database Management Systems',
  assessmentName: 'Mid-Term Evaluation',
  classSection: 'CSE Batch 2026 - Section B',
  date: 'October 2026',
  records: [
    { studentId: 'STU047', rollNo: 'CS-047', studentName: 'Aarav Patel', marks: 44, totalMarks: 50, percentage: 88, grade: 'A+', status: 'Verified' },
    { studentId: 'STU052', rollNo: 'CS-052', studentName: 'Ananya Sharma', marks: 47, totalMarks: 50, percentage: 94, grade: 'O', status: 'Verified' },
    { studentId: 'STU061', rollNo: 'CS-061', studentName: 'Rohan Verma', marks: 32, totalMarks: 50, percentage: 64, grade: 'B', status: 'Verified' },
    { studentId: 'STU073', rollNo: 'CS-073', studentName: 'Sneha Kulkarni', marks: 39, totalMarks: 50, percentage: 78, grade: 'A', status: 'Verified' },
    { studentId: 'STU088', rollNo: 'CS-088', studentName: 'Vikramaditya Roy', marks: 26, totalMarks: 50, percentage: 52, grade: 'C', status: 'Needs Review' },
    { studentId: 'STU094', rollNo: 'CS-094', studentName: 'Divya Nambiar', marks: 41, totalMarks: 50, percentage: 82, grade: 'A', status: 'Verified' },
  ]
};

export const DEMO_ATTENDANCE: AttendanceReviewData = {
  id: 'review-att-cs301',
  className: 'CS-301 Database Systems',
  date: 'October 8, 2026',
  totalStudents: 42,
  presentCount: 38,
  absentCount: 3,
  needsReviewCount: 1,
  records: [
    { rollNo: 'CS-001', studentName: 'Aaditya Sen', status: 'Present' },
    { rollNo: 'CS-002', studentName: 'Akash Mehra', status: 'Present' },
    { rollNo: 'CS-003', studentName: 'Bhavna Rao', status: 'Absent', note: 'Medical leave submitted' },
    { rollNo: 'CS-047', studentName: 'Aarav Patel', status: 'Present' },
    { rollNo: 'CS-052', studentName: 'Ananya Sharma', status: 'Present' },
    { rollNo: 'CS-088', studentName: 'Vikramaditya Roy', status: 'Needs Review', note: 'Signature ambiguity on physical roster' },
  ]
};

export const DEMO_PPT: PPTReviewData = {
  id: 'review-ppt-java',
  topic: 'Operating Systems & Concurrency Architecture',
  totalSlides: 12,
  sections: [
    '1. Introduction & Objectives',
    '2. Process States & Context Switching',
    '3. CPU Scheduling Mechanics',
    '4. Memory Management & Paging',
    '5. File Systems & Virtualization',
    '6. Summary & Review Exercise'
  ],
  slides: [
    {
      slideNumber: 1,
      title: 'Operating Systems: Architecture & Core Abstractions',
      bullets: [
        'Bridging hardware execution with application isolation',
        'Kernel mode vs. User mode privilege boundaries',
        'Key learning objectives for Unit 2'
      ],
      speakerNotes: 'Introduce the core mission of OS as both a resource allocator and an extended virtual machine.'
    },
    {
      slideNumber: 2,
      title: 'Process Lifecycle & State Transitions',
      bullets: [
        'New, Ready, Running, Waiting, and Terminated states',
        'Role of the Process Control Block (PCB)',
        'Context switch latency and register state preservation'
      ],
      speakerNotes: 'Draw emphasis on the difference between CPU switching overhead and pure compute execution.'
    },
    {
      slideNumber: 3,
      title: 'CPU Scheduling Algorithms Comparison',
      bullets: [
        'Preemptive vs Non-Preemptive policies',
        'FCFS, Round Robin, and Multi-Level Feedback Queues',
        'Tradeoffs between response time and system throughput'
      ],
      speakerNotes: 'Engage class with numerical example showing convoy effect in FCFS.'
    }
  ]
};

export const DEMO_ANALYTICS: AnalyticsData = {
  id: 'review-analytics-ds',
  classAverage: 72,
  studentsEvaluated: 42,
  totalQuestions: 20,
  studentsNeedingAttention: 6,
  questionPerformance: [
    { question: 'Q1: Binary Search Logic', topic: 'Searching', avgScorePercent: 88, difficulty: 'Easy' },
    { question: 'Q2: Normalization (2NF/3NF)', topic: 'DBMS', avgScorePercent: 78, difficulty: 'Moderate' },
    { question: 'Q3: B+ Tree Indexing', topic: 'Indexing', avgScorePercent: 54, difficulty: 'Hard' },
    { question: 'Q4: Bankers Algorithm', topic: 'Deadlock', avgScorePercent: 61, difficulty: 'Hard' },
    { question: 'Q5: Page Fault Replacement', topic: 'Virtual Memory', avgScorePercent: 74, difficulty: 'Moderate' },
  ],
  scoreDistribution: [
    { range: '90-100%', count: 8 },
    { range: '80-89%', count: 14 },
    { range: '70-79%', count: 11 },
    { range: '60-69%', count: 3 },
    { range: '< 60%', count: 6 }
  ]
};
