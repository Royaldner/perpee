/**
 * TanStack Query hooks for alerts.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query"
import { alertsApi } from "@/lib/api"
import type {
  Alert,
  AlertWithProduct,
  AlertCreate,
  AlertUpdate,
  PaginatedResponse,
} from "@/types/api"

// Query keys
export const alertKeys = {
  all: ["alerts"] as const,
  lists: () => [...alertKeys.all, "list"] as const,
  list: (params?: {
    product_id?: number
    is_active?: boolean
    page?: number
    per_page?: number
  }) => [...alertKeys.lists(), params] as const,
  details: () => [...alertKeys.all, "detail"] as const,
  detail: (id: number) => [...alertKeys.details(), id] as const,
}

// List alerts
export function useAlerts(
  params?: {
    product_id?: number
    is_active?: boolean
    page?: number
    per_page?: number
  },
  options?: Omit<
    UseQueryOptions<PaginatedResponse<AlertWithProduct>>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: alertKeys.list(params),
    queryFn: () => alertsApi.list(params),
    ...options,
  })
}

// Get single alert
export function useAlert(
  id: number,
  options?: Omit<UseQueryOptions<Alert>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: alertKeys.detail(id),
    queryFn: () => alertsApi.get(id),
    enabled: id > 0,
    ...options,
  })
}

// Create alert mutation
export function useCreateAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: AlertCreate) => alertsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() })
    },
  })
}

// Update alert mutation
export function useUpdateAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: AlertUpdate }) =>
      alertsApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: alertKeys.detail(variables.id) })
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() })
    },
  })
}

// Delete alert mutation
export function useDeleteAlert() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => alertsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: alertKeys.lists() })
    },
  })
}
