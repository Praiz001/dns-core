import {
  Controller,
  Post,
  Get,
  Body,
  Param,
  Query,
  HttpCode,
  HttpStatus,
  BadRequestException,
} from '@nestjs/common';
import { NotificationsService } from './notifications.service';
import { QueryNotificationsDto, NotificationStatus } from './dto/query-notifications.dto';
import { CreateNotificationDto } from './dto/create-notification';
import { UpdateStatusDto, StatusEnum } from './dto/update-status.dto';
import { ApiTags, ApiOperation } from '@nestjs/swagger';

/**
 * NotificationsController: API Gateway's front desk
 *
 * Responsibilities:
 * 1. Validate incoming notification requests
 * 2. Route to appropriate queue (email or push)
 * 3. Track notification status
 * 4. Provide status lookup endpoints
 */

@ApiTags('notifications')
@Controller('notifications')
export class NotificationsController {
  constructor(private readonly notificationsService: NotificationsService) {}

  /**
   * POST /api/v1/notifications/
   *
   * Unified endpoint for all notification types (email and push)
   *
   * Flow:
   * 1. Validate request (authentication, DTO validation)
   * 2. Check idempotency (prevent duplicate sends)
   * 3. Fetch user contact info from User Service
   * 4. Route to appropriate queue based on notification_type
   * 5. Return tracking ID for status lookup
   *
   * Returns: 202 Accepted (async processing)
   */
  @Post()
  @HttpCode(HttpStatus.ACCEPTED)
  @ApiOperation({
    summary: 'Create notification',
    description:
      'Unified endpoint to create email or push notifications. The notification will be queued for async processing.',
  })
  async createNotification(@Body() dto: CreateNotificationDto) {
    const result = await this.notificationsService.createNotification(dto);

    return {
      success: true,
      data: result,
      message: `${dto.notification_type} notification queued successfully`,
      meta: {
        total: 1,
        limit: 1,
        page: 1,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    };
  }

  /**
   * GET /api/v1/notifications/:id
   *
   * Get notification status by tracking ID
   *
   * Possible statuses:
   * - pending: Queued, waiting for processing
   * - processing: Currently being sent
   * - sent: Successfully sent
   * - delivered: Confirmed delivery (email opened, push received)
   * - failed: Permanent failure (moved to dead-letter queue)
   */

  @Get(':id')
  @ApiOperation({
    summary: 'Get notification status',
    description: 'Retrieve the status of a notification by its tracking ID',
  })
  async getNotificationStatus(@Param('id') id: string) {
    const notification =
      await this.notificationsService.getNotificationStatus(id);

    if (!notification) {
      return {
        success: false,
        error: 'Notification not found',
        message: 'Notification not found',
        meta: {
          total: 0,
          limit: 1,
          page: 1,
          total_pages: 0,
          has_next: false,
          has_previous: false,
        },
      };
    }

    return {
      success: true,
      data: notification,
      message: 'Notification status retrieved successfully',
      meta: {
        total: 1,
        limit: 1,
        page: 1,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    };
  }

  /**
   * GET /api/v1/notifications/
   *
   * List notifications with filtering and pagination
   *
   * Query params:
   * - page: Page number (default: 1)
   * - limit: Items per page (default: 10)
   * - status: Filter by status (optional)
   * - type: Filter by notification type (optional)
   */
  @Get()
  @ApiOperation({
    summary: 'List notifications',
    description:
      'Retrieve a paginated list of notifications with optional filtering by status and type',
  })
  async listNotifications(@Query() query: QueryNotificationsDto) {
    const result = await this.notificationsService.listNotifications(
      query.page,
      query.limit,
      query.status,
      query.type,
    );

    return {
      success: true,
      data: result.data,
      message: 'Notifications retrieved successfully',
      meta: result.meta,
    };
  }

  /**
   * POST /api/v1/:notification_preference/status
   * 
   * Internal endpoint for Email/Push services to update notification status
   * 
   * Examples:
   * - POST /api/v1/email/status
   * - POST /api/v1/push/status
   */
  @Post(':notification_preference/status')
  @ApiOperation({
    summary: 'Update notification status',
    description: 'Internal endpoint for Email/Push services to update notification status after processing',
  })
  async updateNotificationStatus(
    @Param('notification_preference') notificationPreference: string,
    @Body() updateDto: UpdateStatusDto,
  ) {
    // Validate notification_preference
    if (notificationPreference !== 'email' && notificationPreference !== 'push') {
      throw new BadRequestException(
        `Invalid notification_preference. Must be 'email' or 'push'`,
      );
    }

    // Map status strings to NotificationStatus enum
    let status: NotificationStatus;
    switch (updateDto.status) {
      case StatusEnum.DELIVERED:
        status = NotificationStatus.SENT;
        break;
      case StatusEnum.FAILED:
        status = NotificationStatus.FAILED;
        break;
      case StatusEnum.PENDING:
        status = NotificationStatus.PENDING;
        break;
      default:
        status = NotificationStatus.PENDING;
    }

    await this.notificationsService.updateNotificationStatus(
      updateDto.notification_id,
      status,
      updateDto.error,
    );

    return {
      success: true,
      message: 'Notification status updated',
      data: null,
      meta: {
        total: 1,
        limit: 1,
        page: 1,
        total_pages: 1,
        has_next: false,
        has_previous: false,
      },
    };
  }
}
