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
    if (PUBLIC_PATHS.includes(pathname)) {
      setReady(true);
      return;
    }
    if (!hasApiKey()) {
      router.replace("/login");
    } else {
      setReady(true);
    }
  }, [router, pathname]);

  if (!ready) return null;
  return <>{children}</>;
}
