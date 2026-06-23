import useSWR from "swr";
import { jobsApi, type Job, type JobSummary } from "@/lib/api";

export function useJob(id: string | null) {
  const { data, error, mutate } = useSWR<Job>(
    id ? `job-${id}` : null,
    () => jobsApi.get(id!),
    {
      refreshInterval(data) {
        // Poll every 3s while running, stop when terminal
        if (!data) return 3000;
        return ["done", "error", "paused"].includes(data.status) ? 0 : 3000;
      },
      revalidateOnFocus: false,
    },
  );

  return {
    job: data,
    isLoading: !error && !data,
    isError: !!error,
    mutate,
  };
}

export function useJobs() {
  const { data, error, mutate } = useSWR<JobSummary[]>(
    "jobs-list",
    jobsApi.list,
    { refreshInterval: 5000 },
  );

  return {
    jobs: data ?? [],
    isLoading: !error && !data,
    isError: !!error,
    mutate,
  };
}
