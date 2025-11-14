import {
  IsEnum,
  IsUUID,
  IsString,
  IsInt,
  IsOptional,
  IsObject,
  ValidateNested,
  Min,
  Max,
  IsUrl,
} from 'class-validator';
import { Type } from 'class-transformer';
import { NotificationType } from './query-notifications.dto';

/**
 * UserData: Contains user-specific variables for template substitution
 * Example: { name: "John Doe", link: "https://example.com/verify", meta: { order_id: "123" } }
 */
export class UserDataDto {
  @IsString()
  name: string;

  @IsUrl()
  link: string;

  @IsOptional()
  @IsObject()
  meta?: Record<string, any>;
}

/**
 * CreateNotificationDto: Unified DTO for all notification types
 *
 * This DTO handles both email and push notifications through a single endpoint.
 * The API Gateway will route to the appropriate queue based on notification_type.
 *
 * Flow:
 * 1. Client sends notification request with user_id and template_code
 * 2. Gateway validates request and checks idempotency (request_id)
 * 3. Gateway queries User Service to get contact info (email/push token)
 * 4. Gateway routes to appropriate queue (email.queue or push.queue)
 * 5. Worker service (Email/Push) processes from queue
 */
export class CreateNotificationDto {
  /**
   * notification_type: Determines routing queue
   * - 'email' -> email.queue -> Email Service
   * - 'push' -> push.queue -> Push Service
   */
  @IsEnum(NotificationType)
  notification_type: NotificationType;

  /**
   * user_id: UUID of the recipient user
   * Gateway will fetch user's contact info (email/device_token) from User Service
   */
  @IsUUID()
  user_id: string;

  /**
   * template_code: Identifier for the notification template
   * Can be a code (e.g., "welcome_email") or path (e.g., "templates/welcome.html")
   * Gateway will fetch template from Template Service
   */
  @IsString()
  template_code: string;

  /**
   * variables: User-specific data for template substitution
   * Example: { name: "John", link: "https://app.com/verify?token=abc", meta: { order_id: "456" } }
   */
  @ValidateNested()
  @Type(() => UserDataDto)
  variables: UserDataDto;

  /**
   * request_id: Unique identifier for idempotency
   * If provided, duplicate requests with same ID will return cached response
   * If not provided, system generates one automatically
   */
  @IsOptional()
  @IsString()
  request_id?: string;

  /**
   * priority: Message priority for queue processing (1-10)
   * Higher priority = processed first
   * Default: 5 (medium priority)
   * - 1-3: Low priority (marketing, newsletters)
   * - 4-6: Medium priority (general notifications)
   * - 7-10: High priority (security alerts, password resets)
   */
  @IsOptional()
  @IsInt()
  @Min(1)
  @Max(10)
  priority?: number;

  /**
   * metadata: Additional context for tracking/logging
   * Not used in message content, but logged for debugging
   * Example: { source: "checkout_flow", campaign_id: "summer_sale" }
   */
  @IsOptional()
  @IsObject()
  metadata?: Record<string, any>;
}
