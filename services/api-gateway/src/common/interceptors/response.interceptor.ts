import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { PaginationMeta } from '../interfaces/pagination-meta.interface';

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message: string;
  meta: PaginationMeta;
}

@Injectable()
export class ResponseInterceptor<T>
  implements NestInterceptor<T, ApiResponse<T>>
{
  intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Observable<ApiResponse<T>> {
    return next.handle().pipe(
      map((data: T | ApiResponse<T>): ApiResponse<T> => {
        // If response already has the correct format, return as is
        if (data && typeof data === 'object' && 'success' in data) {
          return data;
        }

        // Default pagination meta for non-paginated responses
        const defaultMeta: PaginationMeta = {
          total: 1,
          limit: 1,
          page: 1,
          total_pages: 1,
          has_next: false,
          has_previous: false,
        };

        return {
          success: true,
          data,
          message: 'Success',
          meta: defaultMeta,
        };
      }),
    );
  }
}
