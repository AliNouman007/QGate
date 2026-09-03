import { useQuery } from "@tanstack/react-query";
import { Check, ChevronDown, FolderKanban, Plus } from "lucide-react";
import { useState } from "react";

import { CreateProjectDialog } from "@/components/cases/CreateProjectDialog";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { api } from "@/lib/api-client";
import type { components } from "@/lib/api-types";
import { cn } from "@/lib/utils";
import { useActiveProject } from "@/stores/use-active-project";

type Project = components["schemas"]["ProjectPublic"];
type ProjectsPage = { items: Project[] };

export function ProjectPicker(): React.ReactElement | null {
  const [open, setOpen] = useState(false);
  const [dialogOpen, setDialogOpen] = useState(false);
  const projectId = useActiveProject((s) => s.projectId);
  const setProjectId = useActiveProject((s) => s.setProjectId);

  const { data } = useQuery({
    queryKey: ["projects"] as const,
    queryFn: async () => (await api.get<ProjectsPage>("/projects")).data,
  });
  const projects = data?.items ?? [];
  const active = projects.find((p) => p.id === projectId) ?? projects[0];

  return (
    <>
      <div className="shrink-0 border-b border-border-subtle px-3 py-2">
        <Popover open={open} onOpenChange={setOpen}>
          <PopoverTrigger asChild>
            <button
              type="button"
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-left hover:bg-bg-elev-2"
              data-testid="project-picker"
            >
              <FolderKanban className="h-3.5 w-3.5 shrink-0 text-fg-4" aria-hidden="true" />
              <span className="flex flex-col overflow-hidden">
                <span className="text-[9.5px] uppercase tracking-wide text-fg-5">Project</span>
                <span className="truncate text-[12px] font-medium text-fg-1">
                  {active?.name ?? "Select project"}
                </span>
              </span>
              <ChevronDown className="ml-auto h-3.5 w-3.5 shrink-0 text-fg-4" aria-hidden="true" />
            </button>
          </PopoverTrigger>
          <PopoverContent
            align="start"
            className="w-[220px] border-border bg-bg-elev-1 p-1 text-fg-1"
          >
            <ul className="space-y-0.5" data-testid="project-picker-list">
              {projects.map((p) => {
                const isActive = p.id === active?.id;
                return (
                  <li key={p.id}>
                    <button
                      type="button"
                      data-testid="project-picker-item"
                      data-active={isActive ? "true" : "false"}
                      onClick={() => {
                        setOpen(false);
                        if (!isActive) setProjectId(p.id);
                      }}
                      className={cn(
                        "flex w-full items-center gap-2 rounded-sm px-2 py-1.5 text-left text-[12.5px] hover:bg-bg-elev-2",
                        isActive ? "bg-bg-elev-2 text-fg-1" : "text-fg-3",
                      )}
                    >
                      <span className="flex-1 truncate">{p.name}</span>
                      {isActive ? (
                        <Check className="h-3.5 w-3.5 shrink-0 text-accent" aria-hidden="true" />
                      ) : null}
                    </button>
                  </li>
                );
              })}
              <li>
                <button
                  type="button"
                  data-testid="add-project-button"
                  onClick={() => {
                    setOpen(false);
                    setDialogOpen(true);
                  }}
                  className="flex w-full items-center gap-2 rounded-sm border-t border-border-subtle px-2 py-1.5 text-left text-[12.5px] font-medium text-accent hover:bg-bg-elev-2"
                >
                  <Plus className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                  <span>New Project</span>
                </button>
              </li>
            </ul>
          </PopoverContent>
        </Popover>
      </div>
      <CreateProjectDialog open={dialogOpen} onClose={() => setDialogOpen(false)} />
    </>
  );
}
