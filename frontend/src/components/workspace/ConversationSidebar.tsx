import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Conversation, ConversationStatus } from '../../types/chat';
import { useAuth } from '../../context/AuthContext';

import {
  Plus,
  Search,
  MoreVertical,
  Edit2,
  Archive,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Settings,
  LogOut,
  Clock,
  AlertCircle,
} from 'lucide-react';

interface ConversationSidebarProps {
  conversations: Conversation[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNewChat: () => void;
  onRename: (id: string, newTitle: string) => void;
  onArchive: (id: string) => void;
  onDelete: (id: string) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
  isMobile?: boolean;
  onCloseMobile?: () => void;
}

export const ConversationSidebar: React.FC<ConversationSidebarProps> = ({
  conversations,
  activeId,
  onSelect,
  onNewChat,
  onRename,
  onArchive,
  onDelete,
  collapsed = false,
  onToggleCollapse,
  isMobile = false,
  onCloseMobile,
}) => {
  const [searchQuery, setSearchQuery] = useState('');
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');
  const [menuOpenId, setMenuOpenId] = useState<string | null>(null);

  const { user, logout } = useAuth();
  const navigate = useNavigate();

  // Search conversations without grouping them by date.
  const filtered = conversations.filter((conversation) =>
    conversation.title
      .toLowerCase()
      .includes(searchQuery.toLowerCase())
  );

  // Keep status indicators neutral and compact.
  // Completed status is intentionally not displayed.
  const getStatusBadge = (status: ConversationStatus) => {
    switch (status) {
      case 'In Review':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-300">
            <span className="w-1.5 h-1.5 rounded-full bg-gray-400" />
            In Review
          </span>
        );

      case 'Needs Input':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-300">
            <AlertCircle className="w-3 h-3 text-gray-400" />
            Needs Input
          </span>
        );

      case 'Running':
        return (
          <span className="inline-flex items-center gap-1.5 text-[10px] text-gray-300">
            <Clock className="w-3 h-3 text-gray-400" />
            Running
          </span>
        );

      case 'Completed':
        return null;

      case 'Draft':
      default:
        return null;
    }
  };

  const handleStartRename = (conversation: Conversation) => {
    setEditingId(conversation.id);
    setEditTitle(conversation.title);
    setMenuOpenId(null);
  };

  const handleSaveRename = (id: string) => {
    if (editTitle.trim()) {
      onRename(id, editTitle.trim());
    }

    setEditingId(null);
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  // Collapsed sidebar
  if (collapsed && !isMobile) {
    return (
      <div className="w-16 bg-black border-r border-white/10 flex flex-col items-center py-5 justify-between h-full select-none">

        <div className="flex flex-col items-center gap-6">

          <Link
            to="/"
            className="tco-brand-link flex h-10 w-10 items-center justify-center rounded-xl"
            title="TCO Home"
            aria-label="TCO Home"
          >
            <span className="tco-sidebar-mark" aria-hidden="true">
              <img src="/tco-monogram.png" alt="" />
            </span>
          </Link>

          <button
            type="button"
            onClick={onNewChat}
            className="
              w-10 h-10
              rounded-xl
              bg-white
              text-black
              hover:bg-gray-200
              flex
              items-center
              justify-center
              transition-colors
            "
            title="New Chat"
          >
            <Plus className="w-5 h-5" />
          </button>

        </div>

        <div className="flex flex-col items-center gap-4">

          <button
            type="button"
            onClick={onToggleCollapse}
            className="
              p-2
              rounded-lg
              text-gray-400
              hover:text-white
              hover:bg-white/10
              transition-colors
            "
            title="Expand Sidebar"
          >
            <ChevronRight className="w-5 h-5" />
          </button>

          <div
            className="
              w-8 h-8
              rounded-full
              bg-white/10
              border border-white/10
              text-white
              flex items-center justify-center
              text-xs font-semibold
            "
            title={user?.name || 'Teacher'}
          >
            {user?.name?.[0] || 'T'}
          </div>

        </div>
      </div>
    );
  }

  return (
    <aside
      className="
        w-72 sm:w-80
        bg-black
        border-r border-white/10
        flex flex-col
        h-full
        select-none
        relative
        z-20
      "
    >

      {/* Header */}
      <div className="px-4 py-4 border-b border-white/10 flex items-center justify-between">

        <Link to="/" className="tco-brand-link group flex items-center gap-2.5" aria-label="TCO Workspace home">
          <span className="tco-sidebar-mark" aria-hidden="true">
            <img src="/tco-monogram.png" alt="" />
          </span>
          <span className="tco-sidebar-wordmark">TCO</span>
          <span className="text-xs font-medium tracking-wide text-white/60">Workspace</span>
        </Link>

        {onToggleCollapse && !isMobile && (
          <button
            type="button"
            onClick={onToggleCollapse}
            className="
              p-1.5
              rounded-lg
              text-gray-500
              hover:text-white
              hover:bg-white/10
              transition-colors
            "
            title="Collapse Sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}

        {isMobile && onCloseMobile && (
          <button
            type="button"
            onClick={onCloseMobile}
            className="
              p-2
              rounded-lg
              text-gray-400
              hover:text-white
              hover:bg-white/10
              transition-colors
            "
            aria-label="Close sidebar"
          >
            <span className="text-lg leading-none">×</span>
          </button>
        )}

      </div>

      {/* New Chat & Search */}
      <div className="p-3 space-y-3">

        <button
          type="button"
          onClick={onNewChat}
          className="
            w-full
            py-2.5
            px-3.5
            rounded-xl
            bg-white
            text-black
            font-semibold
            text-sm
            hover:bg-gray-200
            transition-colors
            flex
            items-center
            justify-center
            gap-2
            group
          "
        >
          <Plus className="w-4 h-4 transition-transform group-hover:rotate-90" />
          <span>New Chat</span>
        </button>

        <div className="relative">

          <Search
            className="
              w-4 h-4
              absolute
              left-3
              top-1/2
              -translate-y-1/2
              text-gray-500
              pointer-events-none
            "
          />

          <input
            type="text"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search conversations..."
            className="
              w-full
              pl-9
              pr-3
              py-2.5
              bg-white/[0.03]
              border border-white/10
              rounded-lg
              text-sm
              text-white
              placeholder-gray-600
              focus:outline-none
              focus:border-white/30
              transition-colors
            "
          />

        </div>

      </div>

      {/* Conversation List — No Date Group Labels */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-1">

        {filtered.length === 0 ? (
          <div className="px-4 py-8 text-center">
            <div className="text-sm text-gray-400">
              {searchQuery
                ? 'No conversations found.'
                : 'No conversations yet.'}
            </div>

            {!searchQuery && (
              <p className="text-xs text-gray-600 mt-1">
                Start a new chat to get going.
              </p>
            )}
          </div>
        ) : (
          filtered.map((conversation) => {
            const isActive = conversation.id === activeId;
            const isEditing = editingId === conversation.id;

            return (
              <div
                key={conversation.id}
                className={`
                  group
                  relative
                  rounded-lg
                  border
                  transition-colors
                  ${
                    isActive
                      ? 'bg-white/[0.09] border-white/10'
                      : 'border-transparent hover:bg-white/[0.045]'
                  }
                `}
              >

                {/* Conversation */}
                <div
                  onClick={() => {
                    if (isEditing) return;

                    onSelect(conversation.id);

                    if (isMobile && onCloseMobile) {
                      onCloseMobile();
                    }
                  }}
                  className="px-3 py-3 cursor-pointer"
                >

                  <div className="flex items-center gap-2">

                    <div className="min-w-0 flex-1">

                      {isEditing ? (
                        <input
                          type="text"
                          value={editTitle}
                          onChange={(e) => setEditTitle(e.target.value)}
                          onClick={(e) => e.stopPropagation()}
                          onBlur={() => handleSaveRename(conversation.id)}
                          onKeyDown={(e) => {
                            if (e.key === 'Enter') {
                              handleSaveRename(conversation.id);
                            }

                            if (e.key === 'Escape') {
                              setEditingId(null);
                            }
                          }}
                          autoFocus
                          className="
                            w-full
                            bg-black
                            text-sm
                            px-2 py-1
                            rounded-md
                            border border-white/20
                            text-white
                            focus:outline-none
                            focus:border-white/40
                          "
                        />
                      ) : (
                        <div
                          className={`
                            text-sm
                            truncate
                            ${
                              isActive
                                ? 'text-white font-medium'
                                : 'text-gray-300'
                            }
                          `}
                        >
                          {conversation.title}
                        </div>
                      )}

                      {getStatusBadge(conversation.status) && (
                        <div className="mt-1">
                          {getStatusBadge(conversation.status)}
                        </div>
                      )}

                      <div className="text-xs text-gray-500 truncate mt-1">
                        {conversation.preview || 'New conversation'}
                      </div>

                    </div>

                    {/* Context Menu */}
                    {!isEditing && (
                      <div className="relative shrink-0">

                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();

                            setMenuOpenId(
                              menuOpenId === conversation.id
                                ? null
                                : conversation.id
                            );
                          }}
                          className="
                            p-1.5
                            rounded-md
                            text-gray-500
                            hover:text-white
                            hover:bg-white/10
                            opacity-100
                            sm:opacity-0
                            sm:group-hover:opacity-100
                            focus:opacity-100
                            transition-all
                          "
                          title="Conversation options"
                          aria-label={`Options for ${conversation.title}`}
                        >
                          <MoreVertical className="w-4 h-4" />
                        </button>

                        {menuOpenId === conversation.id && (
                          <div
                            onClick={(e) => e.stopPropagation()}
                            className="
                              absolute
                              right-0
                              top-8
                              w-36
                              bg-[#111111]
                              border border-white/10
                              rounded-xl
                              shadow-xl
                              py-1
                              z-30
                              text-sm
                              text-gray-300
                            "
                          >

                            <button
                              type="button"
                              onClick={() => handleStartRename(conversation)}
                              className="
                                w-full
                                px-3 py-2
                                text-left
                                hover:bg-white/[0.07]
                                flex items-center gap-2
                              "
                            >
                              <Edit2 className="w-3.5 h-3.5 text-gray-400" />
                              <span>Rename</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                onArchive(conversation.id);
                                setMenuOpenId(null);
                              }}
                              className="
                                w-full
                                px-3 py-2
                                text-left
                                hover:bg-white/[0.07]
                                flex items-center gap-2
                              "
                            >
                              <Archive className="w-3.5 h-3.5 text-gray-400" />
                              <span>Archive</span>
                            </button>

                            <button
                              type="button"
                              onClick={() => {
                                onDelete(conversation.id);
                                setMenuOpenId(null);
                              }}
                              className="
                                w-full
                                px-3 py-2
                                text-left
                                text-gray-300
                                hover:bg-white/[0.07]
                                flex items-center gap-2
                              "
                            >
                              <Trash2 className="w-3.5 h-3.5 text-gray-400" />
                              <span>Delete</span>
                            </button>

                          </div>
                        )}

                      </div>
                    )}

                  </div>

                </div>

              </div>
            );
          })
        )}

      </div>

      {/* User Profile & Footer */}
      <div className="p-3 border-t border-white/10 bg-[#050505]">

        <div className="flex items-center justify-between gap-2 mb-3">

          <div className="flex items-center gap-2.5 overflow-hidden min-w-0">

            <div
              className="
                w-9 h-9
                rounded-full
                bg-white/10
                border border-white/10
                text-white
                text-xs
                font-semibold
                flex items-center justify-center
                shrink-0
              "
            >
              {user?.name?.[0] || 'T'}
            </div>

            <div className="overflow-hidden min-w-0">

              <div className="text-sm font-medium text-white truncate">
                {user?.name || 'Teacher'}
              </div>

              <div className="text-xs text-gray-500 truncate">
                {user?.role || 'Educator'}
              </div>

            </div>

          </div>

          <div className="flex items-center gap-1 shrink-0">

            <Link
              to="/settings"
              className="
                p-2
                rounded-lg
                text-gray-400
                hover:text-white
                hover:bg-white/10
                transition-colors
              "
              title="Settings"
              aria-label="Settings"
            >
              <Settings className="w-4 h-4" />
            </Link>

            <button
              type="button"
              onClick={handleLogout}
              className="
                p-2
                rounded-lg
                text-gray-400
                hover:text-white
                hover:bg-white/10
                transition-colors
              "
              title="Sign Out"
              aria-label="Sign Out"
            >
              <LogOut className="w-4 h-4" />
            </button>

          </div>

        </div>

      </div>

    </aside>
  );
};