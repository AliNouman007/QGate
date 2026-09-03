import { Outlet, createFileRoute, isRedirect, redirect, useNavigate } from "@tanstack/react-router";
import { Play, ShieldCheck } from "lucide-react";
import { useEffect, useState } from "react";

import { AiPanel } from "@/components/shell/AiPanel";
import { CreateWorkspaceDialog } from "@/components/shell/CreateWorkspaceDialog";
import { Sidebar } from "@/components/shell/Sidebar";
import { Topbar } from "@/components/shell/Topbar";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { useCurrentUser, type CurrentUser } from "@/hooks/use-current-user";
import { useCreateRun } from "@/hooks/use-runs";
import { useProject } from "@/hooks/use-projects";
import { api } from "@/lib/api-client";
import { establishLocalSession } from "@/lib/local-auth";
import { useActiveProject } from "@/stores/use-active-project";
import { useActiveWorkspace } from "@/stores/use-active-workspace";
import { useCapabilities } from "@/stores/use-capabilities";
import type { components } from "@/lib/api-types";

type ProjectsPage = components["schemas"]["Page_ProjectPublic_"];

export const Route = createFileRoute("/_app")({
  beforeLoad: async ({ context, location }) => {
    try {
      await establishLocalSession();
      const me = await context.queryClient.ensureQueryData<CurrentUser>({
        queryKey: ["auth", "me"],
        queryFn: async () => (await api.get<CurrentUser>("/auth/me")).data,
      });

      if (me.must_change_password && location.pathname !== "/settings") {
        throw redirect({ to: "/settings", search: { force_password: "1" } });
      }

      const ws = useActiveWorkspace.getState();
      const validIds = new Set(me.memberships.map((m) => m.workspace_id));
      if ((ws.workspaceId === null || !validIds.has(ws.workspaceId)) && me.memberships.length > 0) {
        const first = me.memberships[0];
        if (first) {
          ws.setWorkspaceId(first.workspace_id);
        }
      }

      const activeWorkspaceId = useActiveWorkspace.getState().workspaceId;
      if (activeWorkspaceId) {
        const projects = await context.queryClient.ensureQueryData<ProjectsPage>({
          queryKey: ["projects"],
          queryFn: async () => (await api.get<ProjectsPage>("/projects")).data,
        });
        const proj = useActiveProject.getState();
        const validProjectIds = new Set(projects.items.map((p) => p.id));
        if (
          (proj.projectId === null || !validProjectIds.has(proj.projectId)) &&
          projects.items.length > 0
        ) {
          const firstProject = projects.items[0];
          if (firstProject) {
            proj.setProjectId(firstProject.id);
          }
        }
      }

      if (useCapabilities.getState().capabilities === null) {
        await useCapabilities.getState().fetch();
      }
    } catch (err) {
      if (isRedirect(err)) {
        throw err;
      }
      throw redirect({
        to: "/login",
        search: { next: location.pathname },
      });
    }
  },
  component: AppLayout,
});

function GlobalStartQaCheckModal({ open, onOpenChange }: { open: boolean; onOpenChange: (open: boolean) => void }): React.ReactElement {
  const navigate = useNavigate();
  const projectId = useActiveProject((s) => s.projectId);
  const { data: project } = useProject(projectId);
  const createRunMutation = useCreateRun();
  const [isRunning, setIsRunning] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  useEffect(() => {
    if (open) setErrorMessage(null);
  }, [open]);

  const handleStartRun = () => {
    if (!projectId) {
      setErrorMessage("No active project selected. Please select a project first.");
      return;
    }
    setIsRunning(true);
    setErrorMessage(null);

    createRunMutation.mutate(
      {
        projectId,
        name: `QGate Automated QA Check - ${new Date().toLocaleTimeString()}`,
        selection: [],
        env: "staging",
        trigger: "MANUAL",
      },
      {
        onSuccess: () => {
          setIsRunning(false);
          onOpenChange(false);
          void navigate({ to: "/gate" });
        },
        onError: (err) => {
          setIsRunning(false);
          const msg = err instanceof Error ? err.message : "Failed to trigger QA check.";
          setErrorMessage(msg);
        },
      },
    );
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="border-border bg-bg-elev-1 sm:max-w-[500px]" data-testid="start-qa-check-dialog">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2 text-fg-1">
            <ShieldCheck className="h-5 w-5 text-accent" aria-hidden="true" />
            <span>Start QA Check</span>
          </DialogTitle>
          <DialogDescription className="text-fg-4 text-[13px]">
            Target Project: <strong className="font-mono text-fg-1">{project?.name ?? "D:\\QGate\\qgate-test-shop"}</strong>
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 py-2 text-[12.5px] leading-relaxed text-fg-3">
          {errorMessage ? (
            <div className="rounded-md border border-red/30 bg-red/10 p-3 text-[12px] text-red font-medium" data-testid="start-qa-check-error">
              {errorMessage}
            </div>
          ) : null}

          <p>
            QGate will automatically index code changes, calculate risk scores, synthesize baseline assertions, execute Playwright browser scenarios, and issue a <strong>PASS</strong> or <strong>BLOCK</strong> verdict.
          </p>
          <div className="rounded-md border border-border-subtle bg-bg-elev-2 p-3 text-[12px] text-fg-2">
            <strong className="text-fg-1">Pipeline Steps:</strong> Project Intelligence → Impact Analysis → Scenario Synthesis → Browser Execution → Gate Verdict.
          </div>
        </div>

        <DialogFooter className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={() => onOpenChange(false)}>
            Close
          </Button>
          <Button
            size="sm"
            disabled={isRunning}
            onClick={handleStartRun}
            className="gap-1.5 bg-accent text-accent-fg hover:bg-accent/90"
            data-testid="confirm-run-qa-check-button"
          >
            <Play className="h-3.5 w-3.5" aria-hidden="true" />
            <span>{isRunning ? "Launching Pipeline..." : "Run QA Check Now"}</span>
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function AppLayout(): React.ReactElement {
  const tier = useCapabilities((s) => s.capabilities?.tier);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [qaModalOpen, setQaModalOpen] = useState(false);

  const { data: user } = useCurrentUser();
  const activeWorkspaceId = useActiveWorkspace((s) => s.workspaceId);
  const setWorkspaceId = useActiveWorkspace((s) => s.setWorkspaceId);
  const setProjectId = useActiveProject((s) => s.setProjectId);

  const [workspaceDialogOpen, setWorkspaceDialogOpen] = useState(user.memberships.length === 0);
  const memberships = user.memberships;
  const activeMembership =
    memberships.find((m) => m.workspace_id === activeWorkspaceId) ?? memberships[0];
  const workspaceName = activeMembership?.workspace.name;
  const workspaces = memberships.map((m) => ({
    id: m.workspace.id,
    name: m.workspace.name,
  }));
  const userName = user.name ?? user.email.split("@")[0] ?? "Account";
  const userRole = activeMembership?.role;

  useEffect(() => {
    const handleOpenModal = () => setQaModalOpen(true);
    window.addEventListener("open-start-qa-check", handleOpenModal);
    return () => window.removeEventListener("open-start-qa-check", handleOpenModal);
  }, []);

  const handleSwitchWorkspace = (id: string): void => {
    setWorkspaceId(id);
    setProjectId(null);
    window.location.assign("/dashboard");
  };

  return (
    <div className="flex h-dvh overflow-hidden" data-testid="app-shell">
      <Sidebar
        {...(workspaceName !== undefined ? { workspaceName } : {})}
        userName={userName}
        {...(userRole !== undefined ? { userRole } : {})}
        {...(workspaces.length > 0 ? { workspaces } : {})}
        {...(activeWorkspaceId ? { activeWorkspaceId } : {})}
        onSelectWorkspace={handleSwitchWorkspace}
        onCreateWorkspace={() => {
          setWorkspaceDialogOpen(true);
        }}
        isSuperuser={user.is_superuser === true}
        mobileOpen={mobileNavOpen}
        onMobileClose={() => {
          setMobileNavOpen(false);
        }}
      />
      <CreateWorkspaceDialog
        open={workspaceDialogOpen}
        onClose={() => {
          setWorkspaceDialogOpen(false);
        }}
      />
      <GlobalStartQaCheckModal open={qaModalOpen} onOpenChange={setQaModalOpen} />
      <div className="flex min-w-0 flex-1 flex-col">
        <Topbar
          onMenuClick={() => {
            setMobileNavOpen(true);
          }}
        />
        <main className="min-w-0 flex-1 overflow-y-auto px-4 py-4 sm:px-6 sm:py-6">
          <Outlet />
        </main>
      </div>
      {tier !== "ZERO" ? <AiPanel /> : null}
    </div>
  );
}
