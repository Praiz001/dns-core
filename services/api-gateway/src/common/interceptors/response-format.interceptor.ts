import {
  Injectable,
  NestInterceptor,
  ExecutionContext,
  CallHandler,
} from '@nestjs/common';
import { Observable } from 'rxjs';
import { map } from 'rxjs/operators';
import { ApiResponse } from '../interfaces/api-response.interface';

/**
 * Global interceptor to ensure all responses follow the required format
 * Automatically wraps responses in the standard ApiResponse structure
 */
@Injectable()
export class ResponseFormatInterceptor<T>
  implements NestInterceptor<T, ApiResponse<T>>
{
  intercept(
    context: ExecutionContext,
    next: CallHandler,
  ): Observable<ApiResponse<T>> {
    return next.handle().pipe(
      map((response) => {
        // If response already has the correct format, return as-is
        if (
          response &&
          typeof response === 'object' &&
          'success' in response &&
          'message' in response &&
          'meta' in response
        ) {
          return response as ApiResponse<T>;
        }

        // Otherwise, wrap it in the standard format
        return {
          success: true,
          data: response,
          message: 'Success',
          meta: null,
        };
      }),
    );
  }
}
