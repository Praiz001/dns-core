import {
  IsString,
  IsUUID,
  IsOptional,
  IsObject,
  IsInt,
  IsEnum,
  IsUrl,
  ValidateNested,
  Min,
  Max,
} from 'class-validator';
import { Type } from 'class-transformer';
import { ApiProperty } from '@nestjs/swagger';

export enum NotificationType {
  EMAIL = 'email',
  PUSH = 'push',
}

export enum NotificationStatus {
  DELIVERED = 'delivered',
  PENDING = 'pending',
  FAILED = 'failed',
}

/**
 * UserData class as per specification
 * Contains the template variables that will be passed to the template service
 */
export class UserData {
  @ApiProperty({
    description: 'User name for template rendering',
    example: 'John Doe',
  })
  @IsString()
  name: string;

  @ApiProperty({
    description: 'Link URL for template rendering',
    example: 'https://example.com/verify',
  })
  @IsUrl()
  link: string;

  @ApiProperty({
    description: 'Additional metadata for template rendering',
    required: false,
    example: { order_id: 'ORD-12345', product: 'Premium Plan' },
  })
  @IsOptional()
  @IsObject()
  meta?: Record<string, any>;
}

/**
 * Main DTO for creating notifications
 * Matches the specification exactly
 */
export class CreateNotificationDto {
  @ApiProperty({
    description: 'Type of notification to send',
    enum: NotificationType,
    example: NotificationType.EMAIL,
  })
  @IsEnum(NotificationType)
  notification_type: NotificationType;

  @ApiProperty({
    description: 'UUID of the user to send notification to',
    example: '550e8400-e29b-41d4-a716-446655440000',
  })
  @IsUUID('4')
  user_id: string;

  @ApiProperty({
    description: 'Template code or path identifier',
    example: 'welcome_email',
  })
  @IsString()
  template_code: string;

  @ApiProperty({
    description: 'Template variables (strongly typed UserData)',
    type: UserData,
  })
  @ValidateNested()
  @Type(() => UserData)
  variables: UserData;

  @ApiProperty({
    description: 'Unique request ID for idempotency checking',
    example: 'unique-request-id-12345',
  })
  @IsString()
  request_id: string;

  @ApiProperty({
    description: 'Priority level (0-10, higher number = higher priority)',
    example: 1,
    minimum: 0,
    maximum: 10,
  })
  @IsInt()
  @Min(0)
  @Max(10)
  priority: number;

  @ApiProperty({
    description: 'Additional metadata for the notification',
    required: false,
    example: { source: 'api', campaign_id: 'camp_123' },
  })
  @IsOptional()
  @IsObject()
  metadata?: Record<string, any>;
}

/**
 * DTO for updating notification status
 * Used by worker services (email-service, push-service)
 */
export class UpdateNotificationStatusDto {
  @ApiProperty({
    description: 'UUID of the notification to update',
    example: '550e8400-e29b-41d4-a716-446655440000',
  })
  @IsString()
  notification_id: string;

  @ApiProperty({
    description: 'New status of the notification',
    enum: NotificationStatus,
    example: NotificationStatus.DELIVERED,
  })
  @IsEnum(NotificationStatus)
  status: NotificationStatus;

  @ApiProperty({
    description: 'Timestamp of the status update (ISO 8601 format)',
    required: false,
    example: '2025-11-13T10:30:00Z',
  })
  @IsOptional()
  timestamp?: Date;

  @ApiProperty({
    description: 'Error message if status is failed',
    required: false,
    example: 'SMTP connection timeout after 3 retries',
  })
  @IsOptional()
  @IsString()
  error?: string;
}
