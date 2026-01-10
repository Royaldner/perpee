/**
 * TanStack Query hooks for products.
 */

import {
  useQuery,
  useMutation,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query"
import { productsApi } from "@/lib/api"
import type {
  Product,
  ProductListItem,
  ProductCreate,
  ProductUpdate,
  ProductPriceHistory,
  ProductStats,
  PaginatedResponse,
} from "@/types/api"

// Query keys
export const productKeys = {
  all: ["products"] as const,
  lists: () => [...productKeys.all, "list"] as const,
  list: (params?: { store?: string; status?: string; page?: number; per_page?: number }) =>
    [...productKeys.lists(), params] as const,
  details: () => [...productKeys.all, "detail"] as const,
  detail: (id: number) => [...productKeys.details(), id] as const,
  history: (id: number, days?: number) =>
    [...productKeys.detail(id), "history", days] as const,
  stats: () => [...productKeys.all, "stats"] as const,
}

// List products
export function useProducts(
  params?: { store?: string; status?: string; page?: number; per_page?: number },
  options?: Omit<
    UseQueryOptions<PaginatedResponse<ProductListItem>>,
    "queryKey" | "queryFn"
  >
) {
  return useQuery({
    queryKey: productKeys.list(params),
    queryFn: () => productsApi.list(params),
    ...options,
  })
}

// Get single product
export function useProduct(
  id: number,
  options?: Omit<UseQueryOptions<Product>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: productKeys.detail(id),
    queryFn: () => productsApi.get(id),
    enabled: id > 0,
    ...options,
  })
}

// Get product price history
export function useProductHistory(
  id: number,
  days?: number,
  options?: Omit<UseQueryOptions<ProductPriceHistory>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: productKeys.history(id, days),
    queryFn: () => productsApi.getHistory(id, { days }),
    enabled: id > 0,
    ...options,
  })
}

// Get product stats
export function useProductStats(
  options?: Omit<UseQueryOptions<ProductStats>, "queryKey" | "queryFn">
) {
  return useQuery({
    queryKey: productKeys.stats(),
    queryFn: () => productsApi.getStats(),
    ...options,
  })
}

// Create product mutation
export function useCreateProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (data: ProductCreate) => productsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() })
      queryClient.invalidateQueries({ queryKey: productKeys.stats() })
    },
  })
}

// Update product mutation
export function useUpdateProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: ({ id, data }: { id: number; data: ProductUpdate }) =>
      productsApi.update(id, data),
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: productKeys.detail(variables.id) })
      queryClient.invalidateQueries({ queryKey: productKeys.lists() })
    },
  })
}

// Delete product mutation
export function useDeleteProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => productsApi.delete(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: productKeys.lists() })
      queryClient.invalidateQueries({ queryKey: productKeys.stats() })
    },
  })
}

// Refresh product mutation
export function useRefreshProduct() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (id: number) => productsApi.refresh(id),
    onSuccess: (_, id) => {
      queryClient.invalidateQueries({ queryKey: productKeys.detail(id) })
      queryClient.invalidateQueries({ queryKey: productKeys.history(id) })
    },
  })
}
