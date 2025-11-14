import { IsString, IsEnum, IsOptional, IsUUID } from 'class-validator';
import { ApiProperty } from '@nestjs/swagger';

export enum StatusEnum {
  DELIVERED = 'delivered',
  PENDING = 'pending',
  FAILED = 'failed',
}

export class UpdateStatusDto {
  @ApiProperty({
    description: 'Notification ID to update',
    example: '550e8400-e29b-41d4-a716-446655440000',
  })
  @IsUUID()
  notification_id: string;

  @ApiProperty({
    description: 'Notification status',
    enum: StatusEnum,
    example: 'delivered',
  })
  @IsEnum(StatusEnum)
  status: StatusEnum;

  @ApiProperty({
    description: 'Timestamp of status change',
    example: '2025-11-14T19:47:09Z',
    required: false,
  })
  @IsOptional()
  @IsString()
  timestamp?: string;

  @ApiProperty({
    description: 'Error message if status is failed',
    example: 'SMTP connection timeout',
    required: false,
  })
  @IsOptional()
  @IsString()
  error?: string;
}
