/**
 * TanStack Query hooks for schedules.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query"
import { schedulesApi } from "@/lib/api"
import type {
  Schedule,
  ScheduleWithDetails,
  ScheduleCreate,
  ScheduleUpdate,
  PaginatedResponse,
} from "@/types/api"

// Query keys
export const scheduleKeys = {
  all: ["schedules"] as const,
  lists: () => [...scheduleKeys.all, "list"] as const,
  list: (params?: {
    product_id?: number
    store_domain?: string
    is_active?: boolean
    page?: number
    per_page?: number
  }) => [...scheduleKeys.lists(), params] as const,
  details: () => [...scheduleKeys.all, "detail"] as const,
  detail: (id: number) => [...scheduleKeys.details(), id] as const,
}

// List schedules
export function useSchedules(
  params?: {
    product_id?: number
    store_domain?: string
    is_active?: boolean
    page?: number
    per_page?: number
  },
  options?: Omit<
    UseQueryOptions<PaginatedResponse<ScheduleWithDetails>>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: scheduleKeys.list(params),
    queryFn: () => schedulesApi.list(params),
    ...options,
  })
}

// Get single schedule
export function useSchedule(
  id: number,
  options?: Omit<UseQueryOptions<Schedule>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: scheduleKeys.detail(id),
    queryFn: () => schedulesApi.get(id),
    enabled: id > 0,
    ...options,
  })
}

// Create schedule mutation
export function useCreateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ScheduleCreate) => schedulesApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleKeys.lists() })
    },
  })
}

// Update schedule mutation
export function useUpdateSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ScheduleUpdate }) =>
      schedulesApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: scheduleKeys.detail(variables.id) })
      queryClient.invalidateQueries({ queryKey: scheduleKeys.lists() })
    },
  })
}

// Delete schedule mutation
export function useDeleteSchedule() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => schedulesApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: scheduleKeys.lists() })
    },
  })
}
