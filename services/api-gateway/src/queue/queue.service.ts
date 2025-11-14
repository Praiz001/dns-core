import {
  Injectable,
  OnModuleInit,
  OnModuleDestroy,
  Logger,
} from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import * as amqp from 'amqplib';
import { connect } from 'amqp-connection-manager';
import { getRabbitMQConfig, RabbitMQConfig } from './queue.config';

@Injectable()
export class QueueService implements OnModuleInit, OnModuleDestroy {
  private readonly logger = new Logger(QueueService.name);
  private connection!: ReturnType<typeof connect>;
  private channel!: Awaited<
    ReturnType<ReturnType<typeof connect>['createChannel']>
  >;
  private config: RabbitMQConfig;

  constructor(private configService: ConfigService) {
    this.config = getRabbitMQConfig(configService);
  }

  onModuleInit() {
    this.connect();
    // await this.setupQueues();
  }

  async onModuleDestroy() {
    if (this.channel) {
      await this.channel.close();
    }
    if (this.connection) {
      await this.connection.close();
    }
  }

  private connect() {
    try {
      this.connection = connect([this.config.url], {
        reconnectTimeInSeconds: 5,
      });

      this.connection.on('connect', () => {
        this.logger.log('Connected to RabbitMQ');
      });

      this.connection.on('disconnect', (err) => {
        this.logger.error('Disconnected from RabbitMQ', err);
      });

      this.channel = this.connection.createChannel({
        setup: async (channel: amqp.Channel) => {
          // Assert exchange
          await channel.assertExchange(this.config.exchange, 'direct', {
            durable: true,
          });

          // Setup queues here - this runs when channel is ready
          await this.setupQueuesOnChannel(channel);
        },
      });

      this.logger.log('RabbitMQ channel created');
    } catch (error) {
      this.logger.error('Failed to connect to RabbitMQ', error);
      throw error;
    }
  }

  private async setupQueuesOnChannel(channel: amqp.Channel) {
    try {
      // Assert main exchange
      await channel.assertExchange(this.config.exchange, 'direct', {
        durable: true,
      });

      // Assert dead-letter exchange
      await channel.assertExchange(this.config.dlx_exchange, 'direct', {
        durable: true,
      });

      // Setup email queue with dead-letter queue AND priority support
      await channel.assertQueue(this.config.email_queue, {
        durable: true,
        arguments: {
          // 'x-dead-letter-exchange': this.config.exchange,
          // 'x-dead-letter-routing-key': this.config.failed_queue,
          'x-dead-letter-exchange': this.config.dlx_exchange,
          'x-dead-letter-routing-key': 'failed',
          'x-max-priority': 10,
        },
      });
      await channel.bindQueue(
        this.config.email_queue,
        this.config.exchange,
        'email',
      );

      // Setup push queue with dead-letter queue AND priority support
      await channel.assertQueue(this.config.push_queue, {
        durable: true,
        arguments: {
          // 'x-dead-letter-exchange': this.config.exchange,
          // 'x-dead-letter-routing-key': this.config.failed_queue,
          'x-dead-letter-exchange': this.config.dlx_exchange,
          'x-dead-letter-routing-key': 'failed',
          'x-max-priority': 10,
        },
      });
      await channel.bindQueue(
        this.config.push_queue,
        this.config.exchange,
        'push',
      );

      // Setup failed queue (dead-letter queue)
      await channel.assertQueue(this.config.failed_queue, {
        durable: true,
      });
      await channel.bindQueue(
        this.config.failed_queue,
        // this.config.exchange,
        this.config.dlx_exchange,
        'failed',
      );

      this.logger.log('Queues and exchange setup completed');
    } catch (error) {
      this.logger.error('Failed to setup queues', error);
      throw error;
    }
  }

  /**
   * publishToEmailQueue: Send message to email queue
   *
   * @param message - Notification payload
   * @param priority - Optional priority (1-10, default 5)
   *                   Higher priority messages are processed first
   * @returns true if published successfully
   */

  async publishToEmailQueue(
    message: {
      request_id?: string;
      priority?: number;
      [key: string]: unknown;
    },
    priority?: number,
  ): Promise<boolean> {
    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));

      // Use priority from message or parameter (default to 5)
      const messagePriority = priority || message.priority || 5;

      const published = await this.channel.publish(
        this.config.exchange,
        'email',
        messageBuffer,
        {
          persistent: true,
          messageId: message.request_id || this.generateMessageId(),
          timestamp: Date.now(),
          priority: messagePriority,
        },
      );
      if (published) {
        this.logger.log(
          `Message published to email queue (priority ${messagePriority}): ${message.request_id || 'unknown'}`,
        );
        return true;
      } else {
        this.logger.warn('Message not published to email queue (buffer full)');
        return false;
      }
    } catch (error) {
      this.logger.error('Failed to publish to email queue', error);
      throw error;
    }
  }

  /**
   * publishToPushQueue: Send message to push queue
   *
   * @param message - Notification payload
   * @param priority - Optional priority (1-10, default 5)
   *                   Higher priority messages are processed first
   * @returns true if published successfully
   */

  async publishToPushQueue(
    message: {
      request_id?: string;
      priority?: number;
      [key: string]: unknown;
    },
    priority?: number,
  ): Promise<boolean> {
    try {
      // Check if connected before attempting to publish
      if (!this.isConnected()) {
        this.logger.error('RabbitMQ not connected, cannot publish message');
        return false;
      }

      const messageBuffer = Buffer.from(JSON.stringify(message));
      // Use priority from message or parameter (default to 5)
      const messagePriority = priority || message.priority || 5;

      // Add timeout to prevent indefinite hanging
      const publishPromise = this.channel.publish(
        this.config.exchange,
        'push',
        messageBuffer,
        {
          persistent: true,
          messageId: message.request_id || this.generateMessageId(),
          timestamp: Date.now(),
          priority: messagePriority,
        },
      );

      // Wait max 5 seconds for publish
      const timeoutPromise = new Promise<boolean>((_, reject) =>
        setTimeout(() => reject(new Error('Publish timeout after 5s')), 5000),
      );

      const published = await Promise.race([publishPromise, timeoutPromise]);

      // const published = await this.channel.publish(
      //   this.config.exchange,
      //   'push',
      //   messageBuffer,
      //   {
      //     persistent: true,
      //     messageId: message.request_id || this.generateMessageId(),
      //     timestamp: Date.now(),
      //     // ADD: Set message priority
      //     priority: messagePriority,
      //   },
      // );

      if (published) {
        this.logger.log(
          `Message published to push queue (priority ${messagePriority}): ${message.request_id || 'unknown'}`,
        );
        return true;
      } else {
        this.logger.warn('Message not published to push queue (buffer full)');
        return false;
      }
    } catch (error) {
      this.logger.error('Failed to publish to push queue', error);
      return false;
      // throw error;
    }
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  isConnected(): boolean {
    return !!(this.connection && this.channel && this.connection.isConnected());
  }
}
