import { useEffect, useState } from "react";

import { fetchRunSignedUrl } from "@/lib/api-client";

export function useRunArtifactUrl(runId: string | null, artifactId: string | null): string | null {
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!runId || !artifactId) {
      setUrl(null);
      return;
    }
    let cancelled = false;
    void fetchRunSignedUrl(runId, artifactId).then((signed) => {
      if (!cancelled) setUrl(signed.url);
    });
    return () => {
      cancelled = true;
    };
  }, [artifactId, runId]);

  return url;
}
