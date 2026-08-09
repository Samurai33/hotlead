import { redirect } from "next/navigation";
import { backendFetch, ServerApiError } from "@/lib/server-api";
import type { Account } from "@/lib/types";
import AccountsClient from "@/components/accounts/AccountsClient";

// Server Component initial fetch (audit AUDIT-2.md L6) — see app/page.tsx
// for the same pattern applied to the jobs list.
export default async function AccountsPage() {
  let accounts: Account[] = [];
  try {
    accounts = await backendFetch<Account[]>("/api/v1/accounts");
  } catch (err) {
    if (err instanceof ServerApiError && (err.status === 401 || err.status === 403)) {
      redirect("/login");
    }
  }

  return <AccountsClient initialAccounts={accounts} />;
}
