import { useMatches, useNavigate } from "@tanstack/react-router";
import {
  BarChart3,
  BookOpen,
  Bug,
  FileCode2,
  GitPullRequest,
  Inbox,
  LayoutDashboard,
  Menu,
  Play,
  Plug,
  Search,
  ShieldCheck,
  type LucideIcon,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { LanguageSwitcher } from "@/components/shell/LanguageSwitcher";
import { ThemeToggle } from "@/components/shell/ThemeToggle";
import { TierBadge } from "@/components/shared/TierBadge";
import { Button } from "@/components/ui/button";
import {
  CommandDialog,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { cn } from "@/lib/utils";

interface CommandTarget {
  label: string;
  icon: LucideIcon;
  to: string;
}

const COMMAND_TARGETS: CommandTarget[] = [
  { label: "Go to Dashboard", icon: LayoutDashboard, to: "/dashboard" },
  { label: "Go to Test Cases", icon: FileCode2, to: "/cases" },
  { label: "Go to Test Runs", icon: Play, to: "/runs" },
  { label: "Go to Defects", icon: Bug, to: "/defects" },
  { label: "Go to Analytics", icon: BarChart3, to: "/analytics" },
  { label: "Go to Traceability", icon: GitPullRequest, to: "/trace" },
  { label: "Go to Integrations", icon: Plug, to: "/integrations" },
  { label: "Go to Docs", icon: BookOpen, to: "/docs" },
  { label: "Go to Inbox", icon: Inbox, to: "/inbox" },
];

export interface TopbarProps {
  /** External docs link opened by the help icon (preserved for interface compatibility). */
  helpHref?: string;
  /** Opens the mobile sidebar drawer (< md). Hamburger hidden when omitted. */
  onMenuClick?: () => void;
}

function IconTip({
  label,
  children,
}: {
  label: string;
  children: React.ReactElement;
}): React.ReactElement {
  return (
    <Tooltip>
      <TooltipTrigger asChild>{children}</TooltipTrigger>
      <TooltipContent>{label}</TooltipContent>
    </Tooltip>
  );
}

export function Topbar({
  onMenuClick,
}: TopbarProps = {}): React.ReactElement {
  const [commandOpen, setCommandOpen] = useState(false);
  const navigate = useNavigate();

  const breadcrumbs = useMatches({
    select: (matches) =>
      matches
        .map((m) => m.staticData.title)
        .filter((t): t is string => typeof t === "string" && t.length > 0),
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent): void => {
      if (e.key === "k" && (e.metaKey || e.ctrlKey)) {
        e.preventDefault();
        setCommandOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, []);

  const runCommand = useCallback(
    (to: string) => {
      setCommandOpen(false);
      void navigate({ to });
    },
    [navigate],
  );

  return (
    <TooltipProvider delayDuration={150}>
      <header
        className="flex h-[47px] shrink-0 items-center justify-between border-b border-border-subtle bg-bg-elev-1 px-4"
        data-testid="topbar"
      >
        {/* Mobile — sidebar drawer trigger */}
        {onMenuClick ? (
          <IconTip label="Open navigation">
            <button
              type="button"
              onClick={onMenuClick}
              aria-label="Open navigation"
              className="flex h-7 w-7 shrink-0 items-center justify-center rounded-md text-fg-3 hover:bg-bg-elev-2 hover:text-fg-1 md:hidden"
              data-testid="topbar-menu-button"
            >
              <Menu className="h-4 w-4" aria-hidden="true" />
            </button>
          </IconTip>
        ) : null}

        {/* Left — Breadcrumbs */}
        <Breadcrumbs segments={breadcrumbs} />

        <div className="ml-auto flex shrink-0 items-center gap-2">
          {/* Search palette trigger */}
          <button
            type="button"
            onClick={() => setCommandOpen(true)}
            className="hidden h-7 w-[160px] items-center gap-2 rounded-md border border-border bg-bg-elev-1 px-2 text-left text-[12.5px] text-fg-4 hover:bg-bg-elev-2 sm:inline-flex lg:w-[200px]"
            data-testid="topbar-search-trigger"
          >
            <Search className="h-3.5 w-3.5" aria-hidden="true" />
            <span className="flex-1">Search…</span>
            <kbd className="ml-auto inline-flex h-5 items-center gap-0.5 rounded border border-border bg-bg-elev-2 px-1 font-mono text-[10px] text-fg-3">
              <span className="text-[10px]">⌘</span>K
            </kbd>
          </button>
          <IconTip label="Search">
            <button
              type="button"
              onClick={() => setCommandOpen(true)}
              aria-label="Search"
              className="flex h-7 w-7 items-center justify-center rounded-md text-fg-3 hover:bg-bg-elev-2 hover:text-fg-1 sm:hidden"
              data-testid="topbar-search-trigger-mobile"
            >
              <Search className="h-4 w-4" aria-hidden="true" />
            </button>
          </IconTip>

          {/* Language switcher */}
          <LanguageSwitcher />

          {/* Dark / light theme toggle */}
          <ThemeToggle />

          {/* Tier Badge */}
          <TierBadge />

          {/* Primary Action — Start QA Check */}
          <Button
            size="sm"
            onClick={() => {
              window.dispatchEvent(new CustomEvent("open-start-qa-check"));
            }}
            className="h-7 gap-1.5 rounded-md bg-accent text-[12px] font-semibold text-accent-fg hover:bg-accent/90"
            data-testid="topbar-start-qa-check-button"
          >
            <ShieldCheck className="h-3.5 w-3.5" aria-hidden="true" />
            <span>Start QA Check</span>
          </Button>
        </div>

        <CommandDialog
          open={commandOpen}
          onOpenChange={setCommandOpen}
          title="Command palette"
          description="Jump to a screen"
        >
          <CommandInput placeholder="Type a command or search…" />
          <CommandList data-testid="topbar-command-list">
            <CommandEmpty>No results.</CommandEmpty>
            <CommandGroup heading="Navigate">
              {COMMAND_TARGETS.map((target) => {
                const Icon = target.icon;
                return (
                  <CommandItem
                    key={target.to}
                    value={target.label}
                    onSelect={() => runCommand(target.to)}
                    data-testid={`command-item-${target.to.replace(/\//g, "")}`}
                  >
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    <span>{target.label}</span>
                  </CommandItem>
                );
              })}
            </CommandGroup>
          </CommandList>
        </CommandDialog>
      </header>
    </TooltipProvider>
  );
}

function Breadcrumbs({ segments }: { segments: ReadonlyArray<string> }): React.ReactElement {
  if (segments.length === 0) {
    return <div data-testid="topbar-breadcrumbs" className="text-[13px] text-fg-3" />;
  }
  return (
    <ol
      className="flex min-w-0 items-center gap-1.5 overflow-hidden whitespace-nowrap text-[13px]"
      aria-label="Breadcrumbs"
      data-testid="topbar-breadcrumbs"
    >
      {segments.map((seg, idx) => {
        const last = idx === segments.length - 1;
        return (
          <li key={`${seg}-${idx.toString()}`} className="flex min-w-0 items-center gap-1.5">
            {idx > 0 ? (
              <span className="text-fg-5" aria-hidden="true">
                ›
              </span>
            ) : null}
            <span className={cn("truncate", last ? "font-medium text-fg-1" : "text-fg-3")}>
              {seg}
            </span>
          </li>
        );
      })}
    </ol>
  );
}
