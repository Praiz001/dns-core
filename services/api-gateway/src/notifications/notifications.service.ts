import {
  BadRequestException,
  ConflictException,
  Injectable,
  Logger,
} from '@nestjs/common';
import { v4 as uuidv4 } from 'uuid';
import { QueueService } from '../queue/queue.service';
import {
  NotificationStatusResponse,
  NotificationStatus,
  NotificationType,
} from './dto/query-notifications.dto';
import { InjectRepository } from '@nestjs/typeorm';
import { Repository } from 'typeorm';
import { Notification } from './entities/notification.entity';
import { IdempotencyService } from '../idempotency/idempotency.service';
import { UserServiceClient } from 'src/services/user-service.client';
import { TemplateServiceClient } from 'src/services/template-service.client';
import { CreateNotificationDto } from './dto/create-notification';

/**
 * NotificationsService: Core notification processing logic
 *
 * Responsibilities:
 * 1. Idempotency checking (prevent duplicate sends)
 * 2. User info lookup (fetch email/push token from User Service)
 * 3. Template validation (verify template exists in Template Service)
 * 4. Message routing (send to correct queue based on type)
 * 5. Status tracking (store notification records)
 */

@Injectable()
export class NotificationsService {
  private readonly logger = new Logger(NotificationsService.name);

  constructor(
    private queueService: QueueService,
    @InjectRepository(Notification)
    private notificationRepository: Repository<Notification>,
    private idempotencyService: IdempotencyService,
    private userServiceClient: UserServiceClient,
    private templateServiceClient: TemplateServiceClient,
  ) {}

  /**
   * createNotification: Unified notification creation method
   *
   * Flow:
   * 1. Generate/validate request_id for idempotency
   * 2. Check for duplicate requests
   * 3. Fetch user contact info from User Service
   * 4. Validate template exists in Template Service
   * 5. Route to appropriate queue (email or push)
   * 6. Store notification record for status tracking
   * 7. Cache response for idempotency
   */

  async createNotification(dto: CreateNotificationDto) {
    // Step 1: Generate unique IDs
    const requestId = dto.request_id || uuidv4();
    const correlationId = uuidv4();

    this.logger.log(
      `Processing notification request: ${requestId} for user: ${dto.user_id}`,
    );

    // Step 2: Check for duplicate request (Idempotency)
    if (dto.request_id) {
      const cachedResponse = await this.idempotencyService.checkDuplicate(
        requestId,
        dto.notification_type,
      );

      if (cachedResponse) {
        this.logger.log(`Returning cached response for request: ${requestId}`);
        return cachedResponse;
      }

      // Reserve request ID to prevent race conditions
      const reserved = await this.idempotencyService.reserveRequestId(
        requestId,
        dto.notification_type,
      );

      if (!reserved) {
        throw new ConflictException(
          `Request ID ${requestId} is already being processed`,
        );
      }
    }
    try {
      // Step 3: Fetch user contact information from User Service
      this.logger.log(`Fetching user info for user: ${dto.user_id}`);
      // const userInfo = await this.userServiceClient.getUserContactInfo(
      //   dto.user_id,
      //   dto.notification_type,
      // );

      // if (!userInfo) {
      //   throw new BadRequestException(
      //     `User ${dto.user_id} not found or has no contact info for ${dto.notification_type}`,
      //   );
      // }

      // // Step 4: Validate template exists (optional - can skip if Template Service handles this)
      this.logger.log(`Validating template: ${dto.template_code}`);
      // const templateExists = await this.templateServiceClient.getTemplate(
      //   dto.template_code,
      // );

      // if (!templateExists) {
      //   throw new BadRequestException(
      //     `Template ${dto.template_code} not found`,
      //   );
      // }

      // Step 5: Build message payload for queue
      // const messageX = {
      //   request_id: requestId,
      //   correlation_id: correlationId,
      //   type: dto.notification_type,
      //   user_id: dto.user_id,
      //   // user_contact: userInfo.contact, // email address or device token
      //   template_code: dto.template_code,
      //   variables: dto.variables,
      //   priority: dto.priority || 5, // Default to medium priority
      //   metadata: dto.metadata || {},
      //   created_at: new Date().toISOString(),
      // };

      // req by for email service
      const message = {
        correlation_id: correlationId,
        template_id: dto.template_code,
        variables: {
          user_name: dto.variables.name,
          verification_link: dto.variables.link,
          app_name: (dto.metadata?.app_name as string) || 'My Awesome App',
        },
        priority: dto.priority || 5, // Default to medium priority
        retry_count: 0,
        created_at: new Date().toISOString(),
        metadata: {
          ...dto.metadata,
          user_id: dto.user_id,
          source: 'api_gateway',
          request_ip: '137.184.7.214',
        },
        request_id: requestId,
        type: dto.notification_type,
      };

      // Step 6: Create notification record in database for tracking
      const notification = this.notificationRepository.create({
        id: requestId,
        type: dto.notification_type, // Use directly, no mapping needed
        status: NotificationStatus.PENDING,
        correlation_id: correlationId,
      });
      await this.notificationRepository.save(notification);

      // Step 7: Route to appropriate queue based on notification type
      let published = false;

      if (dto.notification_type === NotificationType.EMAIL) {
        this.logger.log(`Publishing to email queue: ${requestId}`);
        published = await this.queueService.publishToEmailQueue(message);
      } else if (dto.notification_type === NotificationType.PUSH) {
        this.logger.log(`Publishing to push queue: ${requestId}`);
        published = await this.queueService.publishToPushQueue(message);
      } else {
        throw new BadRequestException(
          `Unsupported notification type: ${dto.notification_type as string}`,
        );
      }

      // Step 8: Handle queue publishing failure
      if (!published) {
        await this.notificationRepository.update(requestId, {
          status: NotificationStatus.FAILED,
          error: 'Failed to publish to queue',
        });
        throw new Error(
          `Failed to publish ${dto.notification_type} notification to queue`,
        );
      }

      // Step 9: Build response
      const response = {
        id: requestId,
        correlation_id: correlationId,
        status: 'pending',
        type: dto.notification_type,
        user_id: dto.user_id,
        priority: dto.priority || 5,
      };

      // Step 10: Cache response for idempotency
      if (dto.request_id) {
        await this.idempotencyService.storeResponse(
          requestId,
          dto.notification_type,
          response,
        );
      }

      this.logger.log(
        `${dto.notification_type} notification created successfully: ${requestId}`,
      );
      return response;
    } catch (error) {
      // Release reserved request ID on error
      if (dto.request_id) {
        await this.idempotencyService.releaseRequestId(
          requestId,
          dto.notification_type,
        );
      }
      const errorMessage =
        error instanceof Error ? error.message : String(error);
      this.logger.error(`Failed to create notification: ${errorMessage}`);
      throw error;
    }
  }

  async getNotificationStatus(
    id: string,
  ): Promise<NotificationStatusResponse | null> {
    const notification = await this.notificationRepository.findOne({
      where: { id },
    });

    if (!notification) {
      return null;
    }

    return this.mapToStatusResponse(notification);
  }

  async listNotifications(
    page: number = 1,
    limit: number = 10,
    status?: NotificationStatus,
    type?: NotificationType,
  ) {
    const queryBuilder =
      this.notificationRepository.createQueryBuilder('notification');

    if (status) {
      queryBuilder.andWhere('notification.status = :status', { status });
    }

    if (type) {
      queryBuilder.andWhere('notification.type = :type', { type });
    }

    const total = await queryBuilder.getCount();

    const notifications = await queryBuilder
      .orderBy('notification.created_at', 'DESC')
      .skip((page - 1) * limit)
      .take(limit)
      .getMany();

    const totalPages = Math.ceil(total / limit);
    return {
      data: notifications.map((n) => this.mapToStatusResponse(n)),
      meta: {
        total,
        limit,
        page,
        total_pages: totalPages,
        has_next: page < totalPages,
        has_previous: page > 1,
      },
    };
  }

  async updateNotificationStatus(
    id: string,
    status: NotificationStatus,
    error?: string,
  ): Promise<void> {
    await this.notificationRepository.update(id, { status, error });
  }

  private mapToStatusResponse(
    notification: Notification,
  ): NotificationStatusResponse {
    return {
      id: notification.id,
      type: notification.type,
      status: notification.status,
      created_at: notification.created_at.toISOString(),
      correlation_id: notification.correlation_id,
      error: notification.error,
    };
  }
}

// @Injectable()
// export class NotificationsService {
//   private readonly logger = new Logger(NotificationsService.name);
//   constructor(
//     private queueService: QueueService,
//     @InjectRepository(Notification)
//     private notificationRepository: Repository<Notification>,
//     private idempotencyService: IdempotencyService,
//   ) {}

//   async createEmailNotification(dto: CreateEmailNotificationDto) {
//     // eslint-disable-next-line @typescript-eslint/no-unsafe-call
//     const requestId = (dto.request_id || uuidv4()) as string;
//     // eslint-disable-next-line @typescript-eslint/no-unsafe-call
//     const correlationId = (dto.correlation_id || uuidv4()) as string;

//     // Check for duplicate request (idempotency)
//     if (dto.request_id) {
//       const cachedResponse = await this.idempotencyService.checkDuplicate(
//         requestId,
//         'email',
//       );

//       if (cachedResponse) {
//         this.logger.log(`Returning cached response for request: ${requestId}`);
//         return cachedResponse;
//       }

//       // Reserve request ID to prevent race conditions
//       const reserved = await this.idempotencyService.reserveRequestId(
//         requestId,
//         'email',
//       );

//       if (!reserved) {
//         throw new ConflictException(
//           `Request ID ${requestId} is already being processed`,
//         );
//       }
//     }
//     try {
//       const message = {
//         request_id: requestId,
//         correlation_id: correlationId,
//         type: 'email',
//         template_id: dto.template_id,
//         recipients: dto.recipients,
//         subject: dto.subject,
//         variables: dto.variables || {},
//         created_at: new Date().toISOString(),
//       };

//       // Create notification record in database
//       const notification = this.notificationRepository.create({
//         id: requestId,
//         type: NotificationType.EMAIL,
//         status: NotificationStatus.PENDING,
//         correlation_id: correlationId,
//       });
//       await this.notificationRepository.save(notification);

//       // Publish to email queue
//       const published = await this.queueService.publishToEmailQueue(message);

//       if (!published) {
//         // Update status to failed
//         await this.notificationRepository.update(requestId, {
//           status: NotificationStatus.FAILED,
//           error: 'Failed to publish to queue',
//         });
//         throw new Error('Failed to publish email notification to queue');
//       }
//       const response = {
//         id: requestId,
//         correlation_id: correlationId,
//         status: 'pending',
//         type: 'email',
//       };

//       // Store response for idempotency
//       if (dto.request_id) {
//         await this.idempotencyService.storeResponse(
//           requestId,
//           'email',
//           response,
//         );
//       }

//       this.logger.log(`Email notification created: ${requestId}`);
//       return response;
//     } catch (error) {
//       // Release reserved request ID on error
//       if (dto.request_id) {
//         await this.idempotencyService.releaseRequestId(requestId, 'email');
//       }
//       throw error;
//     }
//   }

//   async createPushNotification(dto: CreatePushNotificationDto) {
//     // eslint-disable-next-line @typescript-eslint/no-unsafe-call
//     const requestId = (dto.request_id || uuidv4()) as string;
//     // eslint-disable-next-line @typescript-eslint/no-unsafe-call
//     const correlationId = (dto.correlation_id || uuidv4()) as string;

//     // Check for duplicate request (idempotency)
//     if (dto.request_id) {
//       const cachedResponse = await this.idempotencyService.checkDuplicate(
//         requestId,
//         'push',
//       );

//       if (cachedResponse) {
//         this.logger.log(`Returning cached response for request: ${requestId}`);
//         return cachedResponse;
//       }

//       // Reserve request ID to prevent race conditions
//       const reserved = await this.idempotencyService.reserveRequestId(
//         requestId,
//         'push',
//       );

//       if (!reserved) {
//         throw new ConflictException(
//           `Request ID ${requestId} is already being processed`,
//         );
//       }
//     }
//     try {
//       const message = {
//         request_id: requestId,
//         correlation_id: correlationId,
//         type: 'push',
//         title: dto.title,
//         body: dto.body,
//         recipients: dto.recipients,
//         template_id: dto.template_id,
//         image_url: dto.image_url,
//         link_url: dto.link_url,
//         data: dto.data || {},
//         created_at: new Date().toISOString(),
//       };

//       // Create notification record in database
//       const notification = this.notificationRepository.create({
//         id: requestId,
//         type: NotificationType.PUSH,
//         status: NotificationStatus.PENDING,
//         correlation_id: correlationId,
//       });
//       await this.notificationRepository.save(notification);

//       // Publish to push queue
//       const published = await this.queueService.publishToPushQueue(message);

//       if (!published) {
//         // Update status to failed
//         await this.notificationRepository.update(requestId, {
//           status: NotificationStatus.FAILED,
//           error: 'Failed to publish to queue',
//         });
//         throw new Error('Failed to publish push notification to queue');
//       }
//       const response = {
//         id: requestId,
//         correlation_id: correlationId,
//         status: 'pending',
//         type: 'push',
//       };

//       // Store response for idempotency
//       if (dto.request_id) {
//         await this.idempotencyService.storeResponse(
//           requestId,
//           'push',
//           response,
//         );
//       }

//       this.logger.log(`Push notification created: ${requestId}`);
//       return response;
//     } catch (error) {
//       // Release reserved request ID on error
//       if (dto.request_id) {
//         await this.idempotencyService.releaseRequestId(requestId, 'push');
//       }
//       throw error;
//     }
//   }

//   async getNotificationStatus(
//     id: string,
//   ): Promise<NotificationStatusResponse | null> {
//     const notification = await this.notificationRepository.findOne({
//       where: { id },
//     });

//     if (!notification) {
//       return null;
//     }

//     return this.mapToStatusResponse(notification);
//   }

//   async listNotifications(
//     page: number = 1,
//     limit: number = 10,
//     status?: NotificationStatus,
//     type?: NotificationType,
//   ) {
//     const queryBuilder =
//       this.notificationRepository.createQueryBuilder('notification');

//     // Apply filters
//     if (status) {
//       queryBuilder.andWhere('notification.status = :status', { status });
//     }

//     if (type) {
//       queryBuilder.andWhere('notification.type = :type', { type });
//     }
//     // Get total count
//     const total = await queryBuilder.getCount();

//     // Apply pagination and sorting
//     const notifications = await queryBuilder
//       .orderBy('notification.created_at', 'DESC')
//       .skip((page - 1) * limit)
//       .take(limit)
//       .getMany();

//     const totalPages = Math.ceil(total / limit);

//     return {
//       data: notifications.map((n) => this.mapToStatusResponse(n)),
//       meta: {
//         total,
//         limit,
//         page,
//         total_pages: totalPages,
//         has_next: page < totalPages,
//         has_previous: page > 1,
//       },
//     };
//   }

//   // Helper method to update notification status (for use by other services)
//   async updateNotificationStatus(
//     id: string,
//     status: NotificationStatus,
//     error?: string,
//   ): Promise<void> {
//     await this.notificationRepository.update(id, { status, error });
//   }

//   private mapToStatusResponse(
//     notification: Notification,
//   ): NotificationStatusResponse {
//     return {
//       id: notification.id,
//       type: notification.type,
//       status: notification.status,
//       created_at: notification.created_at.toISOString(),
//       correlation_id: notification.correlation_id,
//       error: notification.error,
//     };
//   }
// }
