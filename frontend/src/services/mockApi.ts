import { Conversation, ChatMessage } from '../types/chat';
import { WorkflowProgress, WorkflowType } from '../types/workflow';
import {
  INITIAL_CONVERSATIONS,
  DEMO_ANSWER_SHEET,
  DEMO_QUESTION_PAPER,
  DEMO_MARKSHEET,
  DEMO_ATTENDANCE,
  DEMO_PPT,
  DEMO_ANALYTICS
} from './demoData';

// In-memory state store for session interactions
class MockApiService {
  private conversations: Conversation[] = [...INITIAL_CONVERSATIONS];
  private answerSheetReview = { ...DEMO_ANSWER_SHEET };
  private questionPaperReview = { ...DEMO_QUESTION_PAPER };
  private marksheetReview = { ...DEMO_MARKSHEET };
  private attendanceReview = { ...DEMO_ATTENDANCE };
  private pptReview = { ...DEMO_PPT };
  private analyticsReview = { ...DEMO_ANALYTICS };

  private delay(ms: number) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  async getConversations(): Promise<Conversation[]> {
    await this.delay(100);
    return [...this.conversations];
  }

  async getConversation(id: string): Promise<Conversation | null> {
    await this.delay(100);
    const conv = this.conversations.find((c) => c.id === id);
    return conv ? { ...conv } : null;
  }

  async createConversation(initialTitle?: string, initialMessage?: string): Promise<Conversation> {
    await this.delay(150);
    const newId = `conv-${Date.now()}`;
    const newConv: Conversation = {
      id: newId,
      title: initialTitle || 'New Conversation',
      status: 'Draft',
      group: 'Today',
      lastUpdated: 'Just now',
      preview: initialMessage ? initialMessage.slice(0, 60) + '...' : 'Fresh conversation with TCO Master Agent.',
      messages: [],
    };

    if (initialMessage) {
      newConv.messages.push({
        id: `msg-${Date.now()}-1`,
        sender: 'teacher',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: initialMessage,
      });
    }

    this.conversations.unshift(newConv);
    return { ...newConv };
  }

  async sendMessage(
    conversationId: string,
    content: string,
    attachments?: { name: string; size: string; type: string; file?: File }[]
  ): Promise<{ userMessage: ChatMessage; tcoMessage: ChatMessage }> {
    await this.delay(350);

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}-user`,
      sender: 'teacher',
      timestamp: nowStr,
      content,
      attachments: attachments && attachments.length > 0 ? attachments.map(({ name, size, type }, index) => ({ id: `att-${Date.now()}-${index}`, name, size, type })) : undefined,
    };

    const convIndex = this.conversations.findIndex((c) => c.id === conversationId);
    let conv = convIndex !== -1 ? this.conversations[convIndex] : null;

    if (!conv) {
      conv = await this.createConversation(content.slice(0, 30), content);
    } else {
      conv.messages.push(userMessage);
      conv.lastUpdated = 'Just now';
      conv.preview = content.slice(0, 60);
    }

    // Determine intent and workflow simulation based on message content
    const lower = content.toLowerCase();
    let tcoMessage: ChatMessage;

    if (lower.includes('check') && (lower.includes('answer') || lower.includes('sheet') || lower.includes('paper'))) {
      conv.status = 'Needs Input';
      conv.activeWorkflowType = 'answer_sheet_checking';
      conv.title = 'Check Answer Sheets';

      tcoMessage = {
        id: `msg-${Date.now()}-tco`,
        sender: 'tco',
        timestamp: nowStr,
        content:
          "To check the student answer sheets with high fidelity, I'll need to know which reference material or curriculum rubric we should evaluate against. Where should I retrieve the study material and marking scheme from?",
        clarification: {
          id: 'clarify-source-1',
          prompt: 'Where should I get the reference study material and marking rubric from?',
          contextHint: 'TCO Answer Sheet Checking Agent will cross-verify handwritten student answers against this reference standard.',
          options: [
            { id: 'opt-uploaded', label: 'Uploaded material', description: 'Batch PDFs and instructor answer key' },
            { id: 'opt-gclassroom', label: 'Google Classroom', description: 'Import active assignment & rubric' },
            { id: 'opt-websearch', label: 'Curriculum Database', description: 'Verified state & university syllabus' },
            { id: 'opt-auto', label: 'Choose for me', description: 'Use standard engineering benchmark' },
          ],
          allowCustomInput: true,
        },
      };
    } else if (lower.includes('question paper') || lower.includes('create os') || lower.includes('create a question')) {
      conv.status = 'In Review';
      conv.activeWorkflowType = 'question_paper_generation';
      conv.title = 'OS Question Paper Generation';

      tcoMessage = {
        id: `msg-${Date.now()}-tco`,
        sender: 'tco',
        timestamp: nowStr,
        content:
          "Sure. I'll prepare an Operating Systems question paper aligned with standard semester syllabus guidelines. The assessment covers process states, CPU scheduling, deadlocks, and memory management.",
        workflowProgress: {
          workflowId: `wf-qp-${Date.now()}`,
          type: 'question_paper_generation',
          state: 'review_required',
          activeAgent: 'Assessment Agent',
          steps: [
            { id: 's1', agent: 'TCO Master Agent', label: 'Understanding request', description: 'Targeting 50 marks across 3 sections', status: 'completed' },
            { id: 's2', agent: 'Assessment Agent', label: 'Preparing assessment framework', description: 'Distributing questions by Bloom\'s Taxonomy', status: 'completed' },
            { id: 's3', agent: 'Content Preparation Agent', label: 'Checking available syllabus material', description: 'Retrieved verified Operating System core concepts', status: 'completed' },
            { id: 's4', agent: 'Assessment Agent', label: 'Generating question items', description: 'Formulated 20 structured theoretical & numerical questions', status: 'completed' },
            { id: 's5', agent: 'TCO Master Agent', label: 'Waiting for Teacher Approval', description: 'AI assists. Teachers decide on final questions.', status: 'active' },
          ],
          approval: {
            id: 'app-qp-demo',
            title: 'Question Paper Ready for Review',
            summary: '20 questions structured across Section A, B, and C. Total Marks: 50.',
            metrics: [
              { label: 'Subject', value: 'Operating Systems' },
              { label: 'Total Questions', value: '20 Items' },
              { label: 'Total Marks', value: '50' },
              { label: 'Duration', value: '90 Mins' },
            ],
            reviewType: 'question_paper_generation',
            requiresReview: true,
          },
        },
        reviewType: 'question_paper_generation',
        reviewDataId: 'review-qp-os',
      };
    } else if (lower.includes('ppt') || lower.includes('presentation') || lower.includes('slide')) {
      conv.status = 'In Review';
      conv.activeWorkflowType = 'ppt_generation';
      conv.title = 'Lecture Slides Generation';

      tcoMessage = {
        id: `msg-${Date.now()}-tco`,
        sender: 'tco',
        timestamp: nowStr,
        content:
          "I've generated a 12-slide lecture presentation outline on Operating Systems & Concurrency. The slides are designed for high classroom engagement with clear technical bullet points and instructor talking notes.",
        workflowProgress: {
          workflowId: `wf-ppt-${Date.now()}`,
          type: 'ppt_generation',
          state: 'review_required',
          activeAgent: 'Presentation Agent',
          steps: [
            { id: 's1', agent: 'TCO Master Agent', label: 'Analyzing lecture topic', description: 'Structured 6 thematic lecture segments', status: 'completed' },
            { id: 's2', agent: 'Presentation Agent', label: 'Generating slide content', description: '12 slides formatted with talking notes', status: 'completed' },
            { id: 's3', agent: 'TCO Master Agent', label: 'Waiting for Teacher Approval', description: 'Ready for slide sequencing review', status: 'active' },
          ],
          approval: {
            id: 'app-ppt-demo',
            title: 'Presentation Slides Generated',
            summary: '12 interactive slides with speaker notes ready for export.',
            metrics: [
              { label: 'Slides', value: '12' },
              { label: 'Topic', value: 'Operating Systems' },
              { label: 'Format', value: '16:9 Modern' },
            ],
            reviewType: 'ppt_generation',
            requiresReview: true,
          },
        },
        reviewType: 'ppt_generation',
        reviewDataId: 'review-ppt-java',
      };
    } else if (lower.includes('attendance') || lower.includes('present') || lower.includes('absent')) {
      conv.status = 'Completed';
      conv.activeWorkflowType = 'attendance';
      conv.title = 'Class Attendance Verification';

      tcoMessage = {
        id: `msg-${Date.now()}-tco`,
        sender: 'tco',
        timestamp: nowStr,
        content:
          'Attendance reconciliation complete for CS-301. 38 students are marked Present, 3 Absent, and 1 record is flagged for teacher confirmation.',
        reviewType: 'attendance',
        reviewDataId: 'review-att-cs301',
      };
    } else if (lower.includes('analytics') || lower.includes('performance') || lower.includes('marksheet')) {
      conv.status = 'Completed';
      conv.activeWorkflowType = 'analytics';
      conv.title = 'Class Performance Diagnostic';

      tcoMessage = {
        id: `msg-${Date.now()}-tco`,
        sender: 'tco',
        timestamp: nowStr,
        content:
          'Evaluation analytics ready for 42 students. Class average is 72%. 6 students were identified who may benefit from review sessions on tree balance and indexing.',
        reviewType: 'analytics',
        reviewDataId: 'review-analytics-ds',
      };
    } else {
      conv.status = 'Running';
      tcoMessage = {
        id: `msg-${Date.now()}-tco`,
        sender: 'tco',
        timestamp: nowStr,
        content: `I've registered your request: "${content}". As your AI co-worker, I coordinate between evaluation, content preparation, and assessment workflows. AI assists you with drafts and checks, while you retain full decision authority.`,
      };
    }

    conv.messages.push(tcoMessage);
    return { userMessage, tcoMessage };
  }

  async respondToClarification(
    conversationId: string,
    optionId: string,
    customValue?: string
  ): Promise<{ userMessage: ChatMessage; tcoMessage: ChatMessage }> {
    await this.delay(400);

    const nowStr = new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    const selectedLabel =
      optionId === 'opt-uploaded'
        ? 'Uploaded material'
        : optionId === 'opt-gclassroom'
        ? 'Google Classroom'
        : optionId === 'opt-websearch'
        ? 'Curriculum Database'
        : customValue || 'Default Reference Benchmark';

    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}-user-clarify`,
      sender: 'teacher',
      timestamp: nowStr,
      content: `Use: ${selectedLabel}`,
    };

    const conv = this.conversations.find((c) => c.id === conversationId);
    if (conv) {
      conv.messages.push(userMessage);
      conv.status = 'In Review';
      conv.activeWorkflowType = 'answer_sheet_checking';
    }

    // TCO answers with full human-readable process steps and then signals Review Required
    const tcoMessage: ChatMessage = {
      id: `msg-${Date.now()}-tco-clarified`,
      sender: 'tco',
      timestamp: nowStr,
      content: `Understood. Using "${selectedLabel}". TCO Master Agent has deployed the Answer Sheet Checking Agent and Evaluation Agent to process student submission STU047.`,
      workflowProgress: {
        workflowId: `wf-as-${Date.now()}`,
        type: 'answer_sheet_checking',
        state: 'review_required',
        activeAgent: 'Answer Sheet Checking Agent',
        steps: [
          { id: 's1', agent: 'TCO Master Agent', label: 'Understanding request', description: `Using ${selectedLabel} rubric standards`, status: 'completed' },
          { id: 's2', agent: 'Answer Sheet Checking Agent', label: 'Preparing answer sheets', description: 'Digitized 4 handwritten pages for Student STU047', status: 'completed' },
          { id: 's3', agent: 'Evaluation Agent', label: 'Extracting student answers', description: 'Transcribed mathematical and theoretical statements', status: 'completed' },
          { id: 's4', agent: 'Evaluation Agent', label: 'Verifying answer extraction', description: 'Confidence check verified against handwritten scans', status: 'completed' },
          { id: 's5', agent: 'Evaluation Agent', label: 'Grading against rubric', description: 'Provisional score: 4/5 for Q1 (Complexity justification incomplete)', status: 'completed' },
          { id: 's6', agent: 'TCO Master Agent', label: 'Waiting for Teacher Review', description: 'Review the provisional grading and make your decision', status: 'active' },
        ],
        approval: {
          id: 'app-stu047-review',
          title: 'Student Answer Sheet Ready for Teacher Review',
          summary: 'Student STU047 (Data Structures Unit Test) has been evaluated. Review questions and provisional marks before finalization.',
          metrics: [
            { label: 'Student', value: 'STU047' },
            { label: 'Pages Evaluated', value: '4' },
            { label: 'Provisional Score', value: '4 / 5' },
            { label: 'Confidence', value: 'High' },
          ],
          reviewType: 'answer_sheet_checking',
          requiresReview: true,
        },
      },
      reviewType: 'answer_sheet_checking',
      reviewDataId: 'review-as-stu047',
    };

    if (conv) {
      conv.messages.push(tcoMessage);
      conv.lastUpdated = 'Just now';
    }

    return { userMessage, tcoMessage };
  }

  async approveWorkflow(
    workflowId: string,
    conversationId: string,
    reviewType: WorkflowType,
    notes?: string
  ): Promise<{ status: string; updatedWorkflow: WorkflowProgress }> {
    await this.delay(300);

    const conv = this.conversations.find((c) => c.id === conversationId);
    if (conv) {
      conv.status = 'Completed';
    }

    const updatedWorkflow: WorkflowProgress = {
      workflowId,
      type: reviewType,
      state: 'approved',
      activeAgent: 'TCO Master Agent',
      steps: [
        { id: 's-fin', agent: 'TCO Master Agent', label: 'Teacher Approved', description: notes || 'Final decision confirmed by teacher.', status: 'completed' },
      ],
      resultSummary: 'Approved by Teacher. Marksheets and student records updated.',
    };

    if (conv) {
      conv.messages.push({
        id: `msg-${Date.now()}-approved`,
        sender: 'tco',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: `Workflow approved successfully. ${notes ? `Teacher Note: "${notes}". ` : ''}All provisional recommendations have been finalized under teacher authority.`,
        workflowProgress: updatedWorkflow,
      });
    }

    return { status: 'approved', updatedWorkflow };
  }

  async rejectWorkflow(
    workflowId: string,
    conversationId: string,
    reason?: string
  ): Promise<{ status: string; updatedWorkflow: WorkflowProgress }> {
    await this.delay(300);
    const conv = this.conversations.find((c) => c.id === conversationId);
    if (conv) {
      conv.status = 'Draft';
      conv.messages.push({
        id: `msg-${Date.now()}-rejected`,
        sender: 'tco',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: `Workflow discarded as per teacher instruction. Reason: ${reason || 'Teacher requested discard'}. No academic records were altered.`,
      });
    }

    return {
      status: 'rejected',
      updatedWorkflow: {
        workflowId,
        type: 'answer_sheet_checking',
        state: 'cancelled',
        activeAgent: 'TCO Master Agent',
        steps: [],
        resultSummary: 'Cancelled by teacher',
      },
    };
  }

  async requestRevision(
    workflowId: string,
    conversationId: string,
    instructions: string
  ): Promise<{ status: string; updatedWorkflow: WorkflowProgress }> {
    await this.delay(300);
    const conv = this.conversations.find((c) => c.id === conversationId);
    if (conv) {
      conv.status = 'Running';
      conv.messages.push({
        id: `msg-${Date.now()}-revision`,
        sender: 'tco',
        timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
        content: `Applying revision instructions: "${instructions}". TCO is re-evaluating the affected criteria with updated parameters.`,
      });
    }

    return {
      status: 'revision_in_progress',
      updatedWorkflow: {
        workflowId,
        type: 'answer_sheet_checking',
        state: 'running',
        activeAgent: 'Evaluation Agent',
        steps: [
          { id: 'rev-1', agent: 'Evaluation Agent', label: 'Re-evaluating criteria', description: instructions, status: 'active' },
        ],
      },
    };
  }

  async getReviewDetails<T>(reviewType: WorkflowType, _reviewId: string): Promise<T | null> {
    await this.delay(100);
    switch (reviewType) {
      case 'answer_sheet_checking':
        return this.answerSheetReview as unknown as T;
      case 'question_paper_generation':
        return this.questionPaperReview as unknown as T;
      case 'marksheet':
        return this.marksheetReview as unknown as T;
      case 'attendance':
        return this.attendanceReview as unknown as T;
      case 'ppt_generation':
        return this.pptReview as unknown as T;
      case 'analytics':
        return this.analyticsReview as unknown as T;
      default:
        return this.answerSheetReview as unknown as T;
    }
  }

  async renameConversation(conversationId: string, newTitle: string): Promise<boolean> {
    const conv = this.conversations.find((c) => c.id === conversationId);
    if (conv) {
      conv.title = newTitle;
      return true;
    }
    return false;
  }

  async archiveConversation(conversationId: string): Promise<boolean> {
    const index = this.conversations.findIndex((c) => c.id === conversationId);
    if (index !== -1) {
      this.conversations.splice(index, 1);
      return true;
    }
    return false;
  }

  async deleteConversation(conversationId: string): Promise<boolean> {
    const index = this.conversations.findIndex((c) => c.id === conversationId);
    if (index !== -1) {
      this.conversations.splice(index, 1);
      return true;
    }
    return false;
  }
}

export const mockApi = new MockApiService();
