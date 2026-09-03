import { Link } from "@tanstack/react-router";
import {
  BarChart3,
  Bell,
  BookOpen,
  Brain,
  Bug,
  ChevronDown,
  ChevronRight,
  FileCode2,
  FolderKanban,
  GitPullRequest,
  Inbox,
  LayoutDashboard,
  Play,
  Plug,
  Settings,
  ShieldCheck,
  UserCheck,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { ProjectPicker } from "@/components/shell/ProjectPicker";
import { ScrollArea } from "@/components/ui/scroll-area";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

export interface SidebarProps {
  workspaceName?: string;
  inboxCount?: number;
  unreadCount?: number;
  activeRunsCount?: number;
  isSuperuser?: boolean;
  onMobileClose?: () => void;
  mobileOpen?: boolean;
  onSelectWorkspace?: (id: string) => void;
  onCreateWorkspace?: () => void;
  activeWorkspaceId?: string;
  workspaces?: Array<{ id: string; name: string }>;
  userRole?: string;
  userName?: string;
}

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  testId: string;
  liveDot?: boolean;
  badgeCount?: number;
}

export function Sidebar({
  inboxCount = 0,
  unreadCount = 0,
  activeRunsCount = 0,
  isSuperuser = false,
  onMobileClose,
}: SidebarProps = {}): React.ReactElement {
  const [moreToolsOpen, setMoreToolsOpen] = useState(false);

  const primaryNav: NavItem[] = [
    {
      to: "/dashboard",
      label: "Overview",
      icon: LayoutDashboard,
      testId: "nav-overview",
    },
    {
      to: "/gate",
      label: "QA Checks",
      icon: ShieldCheck,
      testId: "nav-qa-checks",
      liveDot: activeRunsCount > 0,
    },
    {
      to: "/project-map",
      label: "Project Knowledge",
      icon: FolderKanban,
      testId: "nav-project-knowledge",
    },
    {
      to: "/impact",
      label: "Impact & Test Plan",
      icon: GitPullRequest,
      testId: "nav-impact-test-plan",
    },
    {
      to: "/qa-memory",
      label: "QA Memory",
      icon: Brain,
      testId: "nav-qa-memory",
    },
    {
      to: "/settings",
      label: "Settings",
      icon: Settings,
      testId: "nav-settings",
    },
  ];

  const secondaryTools: NavItem[] = [
    { to: "/cases", label: "Test Cases & Suites", icon: FileCode2, testId: "nav-test-cases" },
    { to: "/defects", label: "Defects", icon: Bug, testId: "nav-defects" },
    { to: "/runs", label: "Test Runs", icon: Play, testId: "nav-test-runs" },
    { to: "/execution", label: "Browser Execution", icon: Play, testId: "nav-browser-execution" },
    { to: "/analytics", label: "Analytics", icon: BarChart3, testId: "nav-analytics" },
    { to: "/inbox", label: "Inbox", icon: Inbox, testId: "nav-inbox", badgeCount: inboxCount },
    { to: "/integrations", label: "Integrations", icon: Plug, testId: "nav-integrations" },
    { to: "/docs", label: "Docs", icon: BookOpen, testId: "nav-docs" },
    ...(isSuperuser ? [{ to: "/admin", label: "Admin", icon: UserCheck, testId: "nav-admin" }] : []),
  ];

  return (
    <TooltipProvider delayDuration={150}>
      <aside
        className="flex h-full w-[224px] shrink-0 flex-col border-r border-border-subtle bg-bg-elev-1 max-md:fixed max-md:inset-y-0 max-md:left-0 max-md:z-50 max-md:transition-transform max-md:duration-200 max-md:-translate-x-full"
        data-testid="sidebar"
      >
        {/* Section 1 — Header Wordmark */}
        <div className="flex h-[47px] shrink-0 items-center justify-between border-b border-border-subtle px-4">
          <span className="flex select-none items-center gap-2">
            <img src="/logo.svg" alt="" aria-hidden="true" className="h-6 w-6 rounded-md" />
            <span className="font-mono text-[15px] font-bold tracking-tight">
              sui<span className="text-accent">test</span>
            </span>
          </span>

          <Tooltip>
            <TooltipTrigger asChild>
              <button
                type="button"
                aria-label="Notifications"
                className="relative flex h-7 w-7 items-center justify-center rounded-md text-fg-3 hover:bg-bg-elev-2 hover:text-fg-1"
                data-testid="sidebar-bell"
              >
                <Bell className="h-4 w-4" aria-hidden="true" />
                {unreadCount > 0 ? (
                  <span
                    className="absolute right-1 top-1 h-2 w-2 rounded-full bg-red"
                    data-testid="sidebar-bell-unread"
                  />
                ) : null}
              </button>
            </TooltipTrigger>
            <TooltipContent>Notifications</TooltipContent>
          </Tooltip>
        </div>

        {/* Section 2 — Active Project Picker */}
        <div className="shrink-0 border-b border-border-subtle px-3 py-2">
          <ProjectPicker />
        </div>

        {/* Section 3 — Primary Navigation */}
        <ScrollArea className="min-h-0 flex-1">
          <nav className="px-2 py-3" aria-label="Primary">
            <div className="space-y-0.5">
              {primaryNav.map((item) => (
                <Link
                  key={item.to}
                  to={item.to}
                  onClick={onMobileClose}
                  data-testid={item.testId}
                  activeProps={{
                    className: "bg-bg-elev-2 font-semibold text-fg-1",
                  }}
                  inactiveProps={{
                    className: "text-fg-3 hover:bg-bg-elev-2 hover:text-fg-1",
                  }}
                  className="flex h-8 items-center gap-2 rounded-md px-2.5 text-[12.5px] transition-colors"
                >
                  <item.icon className="h-4 w-4 shrink-0 text-fg-3" aria-hidden="true" />
                  <span className="flex-1 truncate">{item.label}</span>
                  {item.liveDot ? (
                    <span
                      className="h-2 w-2 rounded-full bg-accent animate-pulse"
                      data-testid={`${item.testId}-live-dot`}
                    />
                  ) : null}
                </Link>
              ))}
            </div>

            {/* Collapsed Secondary Drawer */}
            <div className="mt-4 border-t border-border-subtle pt-3">
              <button
                type="button"
                onClick={() => setMoreToolsOpen((prev) => !prev)}
                className="flex w-full items-center justify-between px-2.5 py-1 text-[11px] font-medium uppercase tracking-wider text-fg-4 hover:text-fg-2"
                data-testid="nav-more-tools-toggle"
              >
                <span>More tools</span>
                {moreToolsOpen ? (
                  <ChevronDown className="h-3.5 w-3.5" aria-hidden="true" />
                ) : (
                  <ChevronRight className="h-3.5 w-3.5" aria-hidden="true" />
                )}
              </button>

              {moreToolsOpen ? (
                <div className="mt-1 space-y-0.5 border-l border-border-subtle ml-2 pl-2" data-testid="more-tools-list">
                  {secondaryTools.map((item) => (
                    <Link
                      key={item.to}
                      to={item.to}
                      onClick={onMobileClose}
                      data-testid={item.testId}
                      activeProps={{
                        className: "bg-bg-elev-2 font-medium text-fg-1",
                      }}
                      inactiveProps={{
                        className: "text-fg-4 hover:bg-bg-elev-2 hover:text-fg-2",
                      }}
                      className="flex h-7 items-center gap-2 rounded-md px-2 text-[11.5px] transition-colors"
                    >
                      <item.icon className="h-3.5 w-3.5 shrink-0 text-fg-4" aria-hidden="true" />
                      <span className="truncate">{item.label}</span>
                      {item.badgeCount && item.badgeCount > 0 ? (
                        <span
                          className="ml-auto rounded-full bg-accent/15 px-1.5 py-0.5 text-[10px] font-semibold text-accent"
                          data-testid="nav-inbox-badge"
                        >
                          {item.badgeCount}
                        </span>
                      ) : null}
                    </Link>
                  ))}
                </div>
              ) : null}
            </div>
          </nav>
        </ScrollArea>

        {/* Section 4 — Footer User Profile */}
        <div className="shrink-0 border-t border-border-subtle p-3">
          <div className="flex items-center gap-2 rounded-md bg-bg-elev-2 p-2">
            <div className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full bg-accent/20 text-[11px] font-bold text-accent">
              E2E
            </div>
            <div className="flex flex-col overflow-hidden">
              <span className="truncate text-[12px] font-medium text-fg-1">E2E Zero</span>
              <span className="truncate text-[10px] uppercase text-fg-5">OWNER</span>
            </div>
          </div>
        </div>
      </aside>
    </TooltipProvider>
  );
}
