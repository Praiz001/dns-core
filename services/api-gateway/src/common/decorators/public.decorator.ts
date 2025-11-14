import { SetMetadata } from '@nestjs/common';

/**
 * Public route decorator
 * Use this to mark routes that don't require authentication
 * Example: @Public() on health check endpoints
 */
export const IS_PUBLIC_KEY = 'isPublic';
export const Public = () => SetMetadata(IS_PUBLIC_KEY, true);
