import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatNumber(n: number): string {
  return new Intl.NumberFormat("pt-BR").format(n);
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat("pt-BR", {
    day: "2-digit",
    month: "2-digit",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(iso));
}

export function progressPct(scraped: number, total: number): number {
  if (total === 0) return 0;
  return Math.min(100, Math.round((scraped / total) * 100));
}

export const STATUS_LABELS: Record<string, string> = {
  pending: "Aguardando",
  running: "Executando",
  paused:  "Pausado",
  done:    "Concluído",
  error:   "Erro",
};
