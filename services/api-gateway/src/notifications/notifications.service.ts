import {
  ConflictException,
  Injectable,
  Logger,
  NotFoundException,
} from '@nestjs/common';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { v4 as uuidv4 } from 'uuid';
import { QueueService } from '../queue/queue.service';
import { Notification } from './entities/notification.entity';
import { IdempotencyService } from '../idempotency/idempotency.service';
import {
  CreateNotificationDto,
  UpdateNotificationStatusDto,
  NotificationStatus,
} from './dto/create-notification.dto';

/**
 * NotificationsService
 * Handles business logic for notification creation and status management
 */
@Injectable()
export class NotificationsService {
  private readonly logger = new Logger(NotificationsService.name);

  constructor(
    @InjectRepository(Notification)
    private notificationRepository: Repository<Notification>,
    private queueService: QueueService,
    private idempotencyService: IdempotencyService,
  ) {}

  /**
   * Create a new notification
   * Implements idempotency checking and queue publishing
   */
  async createNotification(dto: CreateNotificationDto) {
    // Check for duplicate request (idempotency)
    const existing = await this.notificationRepository.findOne({
      where: { request_id: dto.request_id },
    });

    if (existing) {
      this.logger.log(
        `Duplicate request detected: ${dto.request_id}, returning cached response`,
      );
      return {
        request_id: existing.request_id,
        notification_id: existing.id,
        status: existing.status,
      };
    }

    // Check Redis idempotency cache
    const cachedResponse = await this.idempotencyService.checkDuplicate(
      dto.request_id,
      dto.notification_type,
    );

    if (cachedResponse) {
      this.logger.log(`Returning cached response for request: ${dto.request_id}`);
      return cachedResponse;
    }

    // Reserve request ID to prevent race conditions
    const reserved = await this.idempotencyService.reserveRequestId(
      dto.request_id,
      dto.notification_type,
    );

    if (!reserved) {
      throw new ConflictException(
        `Request ID ${dto.request_id} is already being processed`,
      );
    }

    try {
      // Generate notification ID
      const notificationId = uuidv4();

      // Create notification record in database
      const notification = this.notificationRepository.create({
        id: notificationId,
        request_id: dto.request_id,
        user_id: dto.user_id,
        notification_type: dto.notification_type,
        template_code: dto.template_code,
        variables: dto.variables,
        priority: dto.priority,
        metadata: dto.metadata || {},
        status: 'pending',
      });

      await this.notificationRepository.save(notification);

      // Publish to RabbitMQ
      const published = await this.queueService.publishNotification(
        notificationId,
        dto,
      );

      if (!published) {
        // Update status to failed if publishing fails
        await this.notificationRepository.update(notificationId, {
          status: 'failed',
          error_message: 'Failed to publish to queue',
        });

        throw new Error('Failed to publish notification to queue');
      }

      const response = {
        request_id: notification.request_id,
        notification_id: notification.id,
        status: notification.status,
      };

      // Store response for idempotency
      await this.idempotencyService.storeResponse(
        dto.request_id,
        dto.notification_type,
        response,
      );

      this.logger.log(
        `Created notification ${notificationId} with request_id ${dto.request_id}`,
      );

      return response;
    } catch (error) {
      // Release reserved request ID on error
      await this.idempotencyService.releaseRequestId(
        dto.request_id,
        dto.notification_type,
      );
      throw error;
    }
  }

  /**
   * Get notification status by request ID
   */
  async getStatus(requestId: string) {
    const notification = await this.notificationRepository.findOne({
      where: { request_id: requestId },
    });

    if (!notification) {
      return null;
    }

    return {
      request_id: notification.request_id,
      notification_id: notification.id,
      status: notification.status,
      channel: notification.notification_type,
      created_at: notification.created_at.toISOString(),
      updated_at: notification.updated_at.toISOString(),
      error_message: notification.error_message,
      sent_at: notification.sent_at?.toISOString(),
    };
  }

  /**
   * Update notification status
   * Called by worker services (email-service, push-service)
   */
  async updateStatus(
    channel: 'email' | 'push',
    dto: UpdateNotificationStatusDto,
  ) {
    const notification = await this.notificationRepository.findOne({
      where: { id: dto.notification_id },
    });

    if (!notification) {
      throw new NotFoundException(
        `Notification ${dto.notification_id} not found`,
      );
    }

    // Validate channel matches notification type
    if (notification.notification_type !== channel) {
      throw new ConflictException(
        `Channel mismatch: notification is ${notification.notification_type} but update is for ${channel}`,
      );
    }

    // Update status
    const updateData: Partial<Notification> = {
      status: dto.status,
      error_message: dto.error || undefined,
    };

    // Set sent_at timestamp if status is delivered
    if (dto.status === NotificationStatus.DELIVERED && !notification.sent_at) {
      updateData.sent_at = dto.timestamp || new Date();
    }

    await this.notificationRepository.update(dto.notification_id, updateData);

    // Fetch updated notification
    const updated = await this.notificationRepository.findOne({
      where: { id: dto.notification_id },
    });

    this.logger.log(
      `Updated notification ${dto.notification_id} status to ${dto.status}`,
    );

    return {
      notification_id: updated.id,
      status: updated.status,
      updated_at: updated.updated_at.toISOString(),
    };
  }
}
