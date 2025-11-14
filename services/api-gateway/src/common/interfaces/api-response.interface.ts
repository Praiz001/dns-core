/**
 * Pagination metadata interface
 * Follows snake_case convention as per task requirements
 */
export interface PaginationMeta {
  total: number;
  limit: number;
  page: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
}

/**
 * Standard API response interface
 * All endpoints must return this format
 */
export interface ApiResponse<T = any> {
  success: boolean;
  data?: T;
  error?: string;
  message: string;
  meta: PaginationMeta | null;
}
