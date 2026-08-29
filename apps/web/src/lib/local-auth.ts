import { api } from "@/lib/api-client";
import { useActiveWorkspace } from "@/stores/use-active-workspace";

/**
 * Ask the API to establish its opt-in local development session.
 *
 * Disabled deployments deliberately answer 404. Network and disabled responses
 * both return false so the caller continues through the normal login flow.
 */
export async function establishLocalSession(): Promise<boolean> {
  try {
    const response = await api.post("/auth/local-session");
    if (response.status !== 204) return false;
    const workspaceId = response.headers["x-suitest-workspace-id"];
    if (typeof workspaceId === "string" && workspaceId.length > 0) {
      useActiveWorkspace.getState().setWorkspaceId(workspaceId);
    }
    return true;
  } catch {
    return false;
  }
}
