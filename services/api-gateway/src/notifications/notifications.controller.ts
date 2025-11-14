import {
  Controller,
  Post,
  Get,
  Body,
  Param,
  HttpCode,
  HttpStatus,
  BadRequestException,
  NotFoundException,
  UseGuards,
} from '@nestjs/common';
import {
  ApiTags,
  ApiOperation,
  ApiResponse as SwaggerResponse,
  ApiBadRequestResponse,
  ApiNotFoundResponse,
  ApiBearerAuth,
} from '@nestjs/swagger';
import { NotificationsService } from './notifications.service';
import {
  CreateNotificationDto,
  UpdateNotificationStatusDto,
} from './dto/create-notification.dto';
import { ApiResponse } from '../common/interfaces/api-response.interface';
import { JwtAuthGuard } from '../common/guards/jwt-auth.guard';

/**
 * NotificationsController
 * Handles all notification-related endpoints as per specification
 * All endpoints are protected with JWT authentication
 */
@ApiTags('Notifications')
@Controller('api/v1')
@UseGuards(JwtAuthGuard)
@ApiBearerAuth()
export class NotificationsController {
  constructor(private readonly notificationsService: NotificationsService) {}

  /**
   * POST /api/v1/notifications
   * Create a new notification (email or push)
   * Entry point for all notification requests
   */
  @Post('notifications')
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({
    summary: 'Create notification',
    description: 'Queue a new email or push notification for delivery',
  })
  @SwaggerResponse({
    status: 202,
    description: 'Notification queued successfully',
    schema: {
      example: {
        success: true,
        data: {
          request_id: 'unique-request-id-12345',
          notification_id: '550e8400-e29b-41d4-a716-446655440000',
          status: 'pending',
        },
        message: 'Notification queued successfully',
        meta: null,
      },
    },
  })
  @ApiBadRequestResponse({ description: 'Invalid request data' })
  async createNotification(
    @Body() dto: CreateNotificationDto,
  ): Promise<ApiResponse> {
    const result = await this.notificationsService.createNotification(dto);

    return {
      success: true,
      data: result,
      message: 'Notification queued successfully',
      meta: null,
    };
  }

  /**
   * GET /api/v1/notifications/:request_id/status
   * Get notification status by request ID
   */
  @Get('notifications/:request_id/status')
  @ApiOperation({
    summary: 'Get notification status',
    description: 'Retrieve the current status of a notification by request ID',
  })
  @SwaggerResponse({
    status: 200,
    description: 'Status retrieved successfully',
    schema: {
      example: {
        success: true,
        data: {
          request_id: 'unique-request-id-12345',
          notification_id: '550e8400-e29b-41d4-a716-446655440000',
          status: 'delivered',
          channel: 'email',
          created_at: '2025-11-13T10:00:00Z',
          updated_at: '2025-11-13T10:01:00Z',
        },
        message: 'Status retrieved successfully',
        meta: null,
      },
    },
  })
  @ApiNotFoundResponse({ description: 'Notification not found' })
  async getNotificationStatus(
    @Param('request_id') requestId: string,
  ): Promise<ApiResponse> {
    const status = await this.notificationsService.getStatus(requestId);

    if (!status) {
      throw new NotFoundException(
        `Notification with request_id ${requestId} not found`,
      );
    }

    return {
      success: true,
      data: status,
      message: 'Status retrieved successfully',
      meta: null,
    };
  }

  /**
   * POST /api/v1/{notification_preference}/status
   * Update notification status (called by worker services)
   * notification_preference can be 'email' or 'push'
   */
  @Post(':notification_preference/status')
  @HttpCode(HttpStatus.OK)
  @ApiOperation({
    summary: 'Update notification status (internal endpoint)',
    description:
      'Called by email-service and push-service to update delivery status',
  })
  @SwaggerResponse({
    status: 200,
    description: 'Status updated successfully',
    schema: {
      example: {
        success: true,
        data: {
          notification_id: '550e8400-e29b-41d4-a716-446655440000',
          status: 'delivered',
          updated_at: '2025-11-13T10:01:00Z',
        },
        message: 'Status updated successfully',
        meta: null,
      },
    },
  })
  @ApiBadRequestResponse({
    description: 'Invalid notification preference or request data',
  })
  async updateNotificationStatus(
    @Param('notification_preference') notificationPreference: string,
    @Body() dto: UpdateNotificationStatusDto,
  ): Promise<ApiResponse> {
    // Validate notification_preference
    if (!['email', 'push'].includes(notificationPreference)) {
      throw new BadRequestException(
        'Invalid notification preference. Must be "email" or "push"',
      );
    }

    const result = await this.notificationsService.updateStatus(
      notificationPreference as 'email' | 'push',
      dto,
    );

    return {
      success: true,
      data: result,
      message: 'Status updated successfully',
      meta: null,
    };
  }
}

