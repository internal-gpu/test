import axios from "axios";

const api = axios.create({
  baseURL: "/api",
});

// ─── Types ──────────────────────────────────────────────────────────────────

export interface ReviewItem {
  id: number;
  location: string;
  original_text: string;
  suggested_text: string;
  reason: string;
  severity: "critical" | "warning" | "info";
}

export interface ContractBrief {
  id: number;
  filename: string;
  category: string;
  status: string;
  error_message: string | null;
  created_at: string;
  review_count: number;
}

export interface ContractDetail {
  id: number;
  filename: string;
  original_text: string;
  category: string;
  status: string;
  error_message: string | null;
  created_at: string;
  reviews: ReviewItem[];
}

export interface CategoryCount {
  category: string;
  count: number;
}

export type Settings = Record<string, string>;

// ─── API calls ──────────────────────────────────────────────────────────────

export const uploadContracts = (files: File[]) => {
  const form = new FormData();
  files.forEach((f) => form.append("files", f));
  return api.post<{ uploaded: { id: number; filename: string }[]; count: number }>(
    "/upload",
    form
  );
};

export const startAnalysis = (ids?: number[]) =>
  api.post<{ message: string; count: number }>("/analyze", {
    contract_ids: ids ?? null,
  });

export const listContracts = (params?: {
  category?: string;
  status?: string;
  search?: string;
}) => api.get<ContractBrief[]>("/contracts", { params });

export const getContract = (id: number) =>
  api.get<ContractDetail>(`/contracts/${id}`);

export const deleteContract = (id: number) =>
  api.delete(`/contracts/${id}`);

export const downloadReviewedDocx = (id: number) =>
  api.get(`/contracts/${id}/download`, { responseType: "blob" });

export const getCategories = () =>
  api.get<CategoryCount[]>("/categories");

export const getSettings = () =>
  api.get<Settings>("/settings");

export const updateSetting = (key: string, value: string) =>
  api.put(`/settings/${key}`, { value });
