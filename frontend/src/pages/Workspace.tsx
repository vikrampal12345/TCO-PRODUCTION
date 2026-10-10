import React, { useEffect, useState } from 'react';
import { ConversationSidebar } from '../components/workspace/ConversationSidebar';
import { ChatWindow } from '../components/workspace/ChatWindow';
import { ContextPanel } from '../components/workspace/ContextPanel';
import { useChat } from '../hooks/useChat';

export const Workspace: React.FC = () => {
  const {
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
    openReviewPanel,
    closeReviewPanel,
    stopProcessing,
    renameConversation,
    archiveConversation,
    deleteConversation,
  } = useChat();

  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileSidebarOpen, setMobileSidebarOpen] = useState(false);
  const [isMobileViewport, setIsMobileViewport] = useState(
    () => typeof window !== 'undefined' && window.innerWidth < 1024
  );

  useEffect(() => {
    const updateViewport = () => setIsMobileViewport(window.innerWidth < 1024);
    window.addEventListener('resize', updateViewport);
    return () => window.removeEventListener('resize', updateViewport);
  }, []);

  return (
    <div className="flex h-[100dvh] min-h-[100svh] w-full max-w-full overflow-hidden bg-black font-sans text-gray-100 selection:bg-white/20 selection:text-white">
      {/* Desktop Sidebar */}
      <div className="hidden lg:block h-full shrink-0">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeConversationId}
          onSelect={selectConversation}
          onNewChat={createNewChat}
          onRename={renameConversation}
          onArchive={archiveConversation}
          onDelete={deleteConversation}
          collapsed={sidebarCollapsed}
          onToggleCollapse={() => setSidebarCollapsed(!sidebarCollapsed)}
        />
      </div>

      {/* Mobile Sidebar Overlay Drawer */}
      {mobileSidebarOpen && (
        <div className="lg:hidden fixed inset-0 z-50 flex">
          <div
            className="fixed inset-0 bg-black/70 backdrop-blur-sm"
            onClick={() => setMobileSidebarOpen(false)}
          />
          <div className="relative w-80 max-w-[85vw] h-full z-10">
            <ConversationSidebar
              conversations={conversations}
              activeId={activeConversationId}
              onSelect={selectConversation}
              onNewChat={createNewChat}
              onRename={renameConversation}
              onArchive={archiveConversation}
              onDelete={deleteConversation}
              isMobile={true}
              onCloseMobile={() => setMobileSidebarOpen(false)}
            />
          </div>
        </div>
      )}

      {/* Center Chat Workspace */}
      <main className="flex-1 flex flex-col h-full min-w-0 overflow-hidden relative">
        {error && (
          <div role="alert" className="absolute left-3 right-3 top-3 z-40 mx-auto flex max-w-3xl items-start justify-between gap-3 rounded-xl border border-white/15 bg-[#111111] px-4 py-3 text-xs text-gray-100 shadow-xl">
            <span className="min-w-0 break-words">{error}</span>
            <button type="button" onClick={clearError} className="shrink-0 rounded px-2 py-1 text-gray-200 hover:bg-white/10" aria-label="Dismiss error">Dismiss</button>
          </div>
        )}
        <ChatWindow
          conversation={activeConversation}
          isProcessing={isProcessing}
          onSendMessage={sendMessage}
          onClarification={handleClarification}
          onApprove={handleApprove}
          onRequestRevision={handleRequestRevision}
          onOpenReview={openReviewPanel}
          onStopProcessing={stopProcessing}
          isReviewPanelOpen={isReviewPanelOpen}
          onToggleReviewPanel={() => {
            if (isReviewPanelOpen) {
              closeReviewPanel();
            } else {
              openReviewPanel(activeReviewType || 'answer_sheet_checking');
            }
          }}
          onOpenMobileSidebar={() => setMobileSidebarOpen(true)}
        />
      </main>

      {/* Right Review Panel Drawer */}
      <ContextPanel
        isOpen={isReviewPanelOpen}
        onClose={closeReviewPanel}
        reviewType={activeReviewType}
        reviewId={activeReviewId}
        onApprove={handleApprove}
        onReject={handleReject}
        onRequestRevision={handleRequestRevision}
        isMobile={isMobileViewport}
      />
    </div>
  );
};
