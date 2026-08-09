"use client";

import { useEffect, useState } from "react";
import { useRouter, usePathname } from "next/navigation";
import { hasApiKey } from "@/lib/auth";

const PUBLIC_PATHS = ["/login"];

export default function AuthGuard({ children }: { children: React.ReactNode }) {
  const router   = useRouter();
  const pathname = usePathname();
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // react-hooks/set-state-in-effect (new in eslint-plugin-react-hooks v7,
    // shipped with eslint-config-next 16) flags this whole block: it wants
    // "ready" derived during render instead of via effect+setState. But the
    // gate depends on localStorage (hasApiKey()), which doesn't exist during
    // SSR — computing it during render would mismatch the server's markup on
    // hydration. Deliberately deferring to post-mount is correct here, not
    // an accident; see https://react.dev/learn/you-might-not-need-an-effect
    // for the general guidance this rule is based on.
    /* eslint-disable react-hooks/set-state-in-effect */
    if (PUBLIC_PATHS.includes(pathname)) {
      setReady(true);
      return;
    }
    if (!hasApiKey()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
    /* eslint-enable react-hooks/set-state-in-effect */
  }, [router, pathname]);

  if (!ready) return null;
  return <>{children}</>;
}
