
import { useState, useCallback, useEffect } from 'react';
import type { Conversation, ChatMessage, QuickActionItem } from '../types/chat';
import type { WorkflowType } from '../types/workflow';
import { api } from '../services/api';
import type { MessageAttachmentInput, WorkspaceSourceMode } from '../services/api';
import { errorMessage } from '../services/http';

export function useChat(initialConversationId?: string) {
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [activeConversationId, setActiveConversationId] = useState<string | null>(
    initialConversationId || null,
  );
  const [activeConversation, setActiveConversation] =
    useState<Conversation | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [activeReviewType, setActiveReviewType] =
    useState<WorkflowType | null>(null);
  const [activeReviewId, setActiveReviewId] = useState<string | null>(null);
  const [isReviewPanelOpen, setIsReviewPanelOpen] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Load the conversation list without automatically selecting an old chat.
  const refreshConversations = useCallback(async () => {
    try {
      const list = await api.getConversations();
      setConversations(list);
    } catch (err) {
      console.error('Failed to load conversations:', err);
      setError(errorMessage(err));
    }
  }, []);

  useEffect(() => {
    void refreshConversations();
  }, [refreshConversations]);

  // Load the selected conversation and discard state belonging to the old one.
  useEffect(() => {
    let isMounted = true;

    setActiveConversation(null);
    setActiveReviewType(null);
    setActiveReviewId(null);
    setIsReviewPanelOpen(false);

    if (!activeConversationId) {
      return () => {
        isMounted = false;
      };
    }

    api
      .getConversation(activeConversationId)
      .then((conversation) => {
        if (!isMounted) return;

        if (!conversation) {
          setActiveConversation(null);
          return;
        }

        setActiveConversation(conversation);

        const lastMessage =
          conversation.messages[conversation.messages.length - 1];

        if (lastMessage?.reviewType) {
          setActiveReviewType(lastMessage.reviewType);
          setActiveReviewId(lastMessage.reviewDataId || null);

          const state = lastMessage.workflowProgress?.state;
          const reviewPending = [
            'review_required',
            'assessment_ready_for_teacher',
            'assessment_ready_for_review',
          ].includes(String(state || ''));

          setIsReviewPanelOpen(reviewPending);
        } else {
          setActiveReviewType(null);
          setActiveReviewId(null);
          setIsReviewPanelOpen(false);
        }
      })
      .catch((err) => {
        if (!isMounted) return;
        console.error('Failed to load conversation:', err);
        setError(errorMessage(err));
      });

    return () => {
      isMounted = false;
    };
  }, [activeConversationId]);

  const selectConversation = useCallback((id: string) => {
    setError(null);
    setActiveReviewType(null);
    setActiveReviewId(null);
    setIsReviewPanelOpen(false);
    setActiveConversation(null);
    setActiveConversationId(id);
  }, []);

  const createNewChat = useCallback(async () => {
    setIsProcessing(true);
    setError(null);
    setActiveReviewType(null);
    setActiveReviewId(null);
    setIsReviewPanelOpen(false);

    try {
      const newConversation = await api.createConversation('New Conversation');

      // Switch to the new conversation immediately.
      setActiveConversationId(newConversation.id);
      setActiveConversation(newConversation);
      setConversations((previous) => [
        newConversation,
        ...previous.filter((item) => item.id !== newConversation.id),
      ]);
    } catch (err) {
      console.error('Failed to create conversation:', err);
      setError(errorMessage(err));
    } finally {
      setIsProcessing(false);
    }
  }, []);

  const sendMessage = useCallback(
    async (content: string, attachments?: MessageAttachmentInput[], sourceMode?: WorkspaceSourceMode) => {
      if (!content.trim() && (!attachments || attachments.length === 0)) {
        return;
      }

      setError(null);
      // Start the workspace TCO activity animation immediately when a task is submitted,
      // including the initial conversation-creation request.
      setIsProcessing(true);

      let targetConversationId = activeConversationId;

      try {
        if (!targetConversationId) {
          const newConversation = await api.createConversation(
            content.trim().slice(0, 30) || 'New Conversation',
          );

          targetConversationId = newConversation.id;
          setActiveConversationId(newConversation.id);
          setActiveConversation(newConversation);
          setConversations((previous) => [
            newConversation,
            ...previous.filter((item) => item.id !== newConversation.id),
          ]);
        }

        const optimisticMessage: ChatMessage = {
          id: `optimistic-${Date.now()}`,
          sender: 'teacher',
          timestamp: new Date().toLocaleTimeString([], {
            hour: '2-digit',
            minute: '2-digit',
          }),
          content,
          attachments: attachments?.map((attachment, index) => ({
            id: `upload-${Date.now()}-${index}`,
            name: attachment.name,
            size: attachment.size,
            type: attachment.type,
          })),
        };

        setActiveConversation((previous) => {
          if (!previous || previous.id !== targetConversationId) {
            return previous;
          }

          return {
            ...previous,
            messages: [...previous.messages, optimisticMessage],
          };
        });

        const { tcoMessage } = await api.sendMessage(
          targetConversationId,
          content,
          attachments,
          sourceMode,
        );

        setActiveConversation((previous) => {
          if (!previous || previous.id !== targetConversationId) {
            return previous;
          }

          const cleanMessages = previous.messages.filter(
            (message) => message.id !== optimisticMessage.id,
          );

          return {
            ...previous,
            messages: [...cleanMessages, optimisticMessage, tcoMessage],
            status:
              tcoMessage.workflowProgress?.state === 'review_required'
                ? 'In Review'
                : previous.status,
          };
        });

        if (tcoMessage.reviewType) {
          setActiveReviewType(tcoMessage.reviewType);
          setActiveReviewId(tcoMessage.reviewDataId || null);

          const state = tcoMessage.workflowProgress?.state;
          const reviewPending = [
            'review_required',
            'assessment_ready_for_teacher',
            'assessment_ready_for_review',
          ].includes(String(state || ''));

          setIsReviewPanelOpen(reviewPending);
        } else {
          setActiveReviewType(null);
          setActiveReviewId(null);
          setIsReviewPanelOpen(false);
        }

        await refreshConversations();
      } catch (err) {
        console.error('Failed to send message:', err);
        setError(errorMessage(err));
      } finally {
        setIsProcessing(false);
      }
    },
    [activeConversationId, refreshConversations],
  );

  const handleClarification = useCallback(
    async (optionId: string, customValue?: string) => {
      if (!activeConversationId) return;

      setIsProcessing(true);
      setError(null);

      try {
        const { userMessage, tcoMessage } = await api.respondToClarification(
          activeConversationId,
          optionId,
          customValue,
        );

        setActiveConversation((previous) => {
          if (!previous || previous.id !== activeConversationId) {
            return previous;
          }

          return {
            ...previous,
            messages: [...previous.messages, userMessage, tcoMessage],
            status: 'In Review',
          };
        });

        if (tcoMessage.reviewType) {
          setActiveReviewType(tcoMessage.reviewType);
          setActiveReviewId(tcoMessage.reviewDataId || null);
          setIsReviewPanelOpen(true);
        }

        await refreshConversations();
      } catch (err) {
        console.error('Clarification error:', err);
        setError(errorMessage(err));
      } finally {
        setIsProcessing(false);
      }
    },
    [activeConversationId, refreshConversations],
  );

  // Prefer the ID associated with the currently selected review.
  // Fall back to the latest workflow/review ID in this conversation.
  const getCurrentReviewId = useCallback(() => {
    if (activeReviewId && activeReviewId !== 'default') {
      return activeReviewId;
    }

    const messages = activeConversation?.messages || [];

    for (let index = messages.length - 1; index >= 0; index -= 1) {
      const message = messages[index];

      if (
        message.reviewDataId &&
        message.reviewDataId !== 'default'
      ) {
        return message.reviewDataId;
      }

      if (message.workflowProgress?.workflowId) {
        return message.workflowProgress.workflowId;
      }
    }

    return null;
  }, [activeConversation, activeReviewId]);

  const handleApprove = useCallback(
    async (notes?: string) => {
      if (!activeConversation || !activeConversationId || !activeReviewType) {
        setError('Select an assessment review before approving it.');
        return;
      }

      const reviewId = getCurrentReviewId();

      if (!reviewId) {
        setError(
          'Assessment ID is missing. Open the assessment review again before approving.',
        );
        return;
      }

      setIsProcessing(true);
      setError(null);

      try {
        await api.approveWorkflow(
          reviewId,
          activeConversationId,
          activeReviewType,
          notes,
        );

        setActiveConversation((previous) => {
          if (!previous || previous.id !== activeConversationId) {
            return previous;
          }

          return {
            ...previous,
            status: 'Completed',
          };
        });

        setIsReviewPanelOpen(false);
        setActiveReviewType(null);
        setActiveReviewId(null);

        await refreshConversations();
      } catch (err) {
        console.error('Approval failed:', err);
        setError(errorMessage(err));
      } finally {
        setIsProcessing(false);
      }
    },
    [
      activeConversation,
      activeConversationId,
      activeReviewType,
      getCurrentReviewId,
      refreshConversations,
    ],
  );

  const handleReject = useCallback(
    async (reason?: string) => {
      if (!activeConversationId) return;

      const reviewId = getCurrentReviewId();

      if (!reviewId) {
        setError('Assessment ID is missing. Open the assessment review again.');
        return;
      }

      setIsProcessing(true);
      setError(null);

      try {
        await api.rejectWorkflow(reviewId, activeConversationId, reason);

        setIsReviewPanelOpen(false);
        setActiveReviewType(null);
        setActiveReviewId(null);

        await refreshConversations();
      } catch (err) {
        console.error('Rejection failed:', err);
        setError(errorMessage(err));
      } finally {
        setIsProcessing(false);
      }
    },
    [activeConversationId, getCurrentReviewId, refreshConversations],
  );

  const handleRequestRevision = useCallback(
    async (instructions: string) => {
      if (!activeConversationId) return;

      const reviewId = getCurrentReviewId();

      if (!reviewId) {
        setError('Assessment ID is missing. Open the assessment review again.');
        return;
      }

      setIsProcessing(true);
      setError(null);

      try {
        await api.requestRevision(
          reviewId,
          activeConversationId,
          instructions,
        );

        setIsReviewPanelOpen(false);
        setActiveReviewType(null);
        setActiveReviewId(null);

        await refreshConversations();
      } catch (err) {
        console.error('Revision request failed:', err);
        setError(errorMessage(err));
      } finally {
        setIsProcessing(false);
      }
    },
    [activeConversationId, getCurrentReviewId, refreshConversations],
  );

  const handleQuickAction = useCallback(
    (action: QuickActionItem) => {
      void sendMessage(action.prompt);
    },
    [sendMessage],
  );

  const openReviewPanel = useCallback(
    (type?: WorkflowType, id?: string) => {
      if (type) setActiveReviewType(type);
      if (id) setActiveReviewId(id);
      setError(null);
      setIsReviewPanelOpen(true);
    },
    [],
  );

  const closeReviewPanel = useCallback(() => {
    setIsReviewPanelOpen(false);
  }, []);

  const stopProcessing = useCallback(() => {
    setIsProcessing(false);
  }, []);

  const clearError = useCallback(() => {
    setError(null);
  }, []);

  const renameConversation = useCallback(
    async (id: string, newTitle: string) => {
      try {
        await api.renameConversation(id, newTitle);
        await refreshConversations();
      } catch (err) {
        setError(errorMessage(err));
      }
    },
    [refreshConversations],
  );

  const archiveConversation = useCallback(
    async (id: string) => {
      try {
        await api.archiveConversation(id);
        await refreshConversations();

        if (activeConversationId === id) {
          setActiveConversationId(null);
          setActiveConversation(null);
          setActiveReviewType(null);
          setActiveReviewId(null);
          setIsReviewPanelOpen(false);
          setError(null);
        }
      } catch (err) {
        setError(errorMessage(err));
      }
    },
    [activeConversationId, refreshConversations],
  );

  const deleteConversation = useCallback(
    async (id: string) => {
      try {
        await api.deleteConversation(id);
        await refreshConversations();

        if (activeConversationId === id) {
          setActiveConversationId(null);
          setActiveConversation(null);
          setActiveReviewType(null);
          setActiveReviewId(null);
          setIsReviewPanelOpen(false);
          setError(null);
        }
      } catch (err) {
        setError(errorMessage(err));
      }
    },
    [activeConversationId, refreshConversations],
  );

  return {
    conversations,
    activeConversation,
    activeConversationId,
    isProcessing,
    isReviewPanelOpen,
    error,
    clearError,
    activeReviewType,
    activeReviewId,
    selectConversation,
    createNewChat,
    sendMessage,
    handleClarification,
    handleApprove,
    handleReject,
    handleRequestRevision,
    handleQuickAction,
    openReviewPanel,
    closeReviewPanel,
    stopProcessing,
    renameConversation,
    archiveConversation,
    deleteConversation,
  };
}

