import {
  Controller,
  Post,
  Get,
  Body,
  Param,
  Query,
  HttpCode,
  HttpStatus,
} from '@nestjs/common';
import { NotificationsService } from './notifications.service';
import { CreateEmailNotificationDto } from './dto/create-email-notification.dto';
import { CreatePushNotificationDto } from './dto/create-push-notification.dto';
import { QueryNotificationsDto } from './dto/query-notifications.dto';

@Controller('notifications')
export class NotificationsController {
  constructor(private readonly notificationsService: NotificationsService) {}

  @Post('email')
  @HttpCode(HttpStatus.ACCEPTED)
  async createEmailNotification(@Body() dto: CreateEmailNotificationDto) {
    const result = await this.notificationsService.createEmailNotification(dto);
    return {
      success: true,
      data: result,
      message: 'Email notification queued successfully',
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

  @Post('push')
  @HttpCode(HttpStatus.ACCEPTED)
  async createPushNotification(@Body() dto: CreatePushNotificationDto) {
    const result = await this.notificationsService.createPushNotification(dto);
    return {
      success: true,
      data: result,
      message: 'Push notification queued successfully',
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

  @Get(':id')
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

  @Get()
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
}
