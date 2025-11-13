// services/api-gateway/src/queue/queue.service.ts
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

  // private async setupQueues() {
  //   try {
  //     // Setup email queue with dead-letter queue
  //     await this.channel.assertQueue(this.config.email_queue, {
  //       durable: true,
  //       arguments: {
  //         'x-dead-letter-exchange': this.config.exchange,
  //         'x-dead-letter-routing-key': this.config.failed_queue,
  //       },
  //     });
  //     await this.channel.bindQueue(
  //       this.config.email_queue,
  //       this.config.exchange,
  //       'email',
  //     );

  //     // Setup push queue with dead-letter queue
  //     await this.channel.assertQueue(this.config.push_queue, {
  //       durable: true,
  //       arguments: {
  //         'x-dead-letter-exchange': this.config.exchange,
  //         'x-dead-letter-routing-key': this.config.failed_queue,
  //       },
  //     });
  //     await this.channel.bindQueue(
  //       this.config.push_queue,
  //       this.config.exchange,
  //       'push',
  //     );

  //     // Setup failed queue (dead-letter queue)
  //     await this.channel.assertQueue(this.config.failed_queue, {
  //       durable: true,
  //     });
  //     await this.channel.bindQueue(
  //       this.config.failed_queue,
  //       this.config.exchange,
  //       'failed',
  //     );

  //     this.logger.log('Queues and exchange setup completed');
  //   } catch (error) {
  //     this.logger.error('Failed to setup queues', error);
  //     throw error;
  //   }
  // }

  private async setupQueuesOnChannel(channel: amqp.Channel) {
    try {
      // Setup email queue with dead-letter queue
      await channel.assertQueue(this.config.email_queue, {
        durable: true,
        arguments: {
          'x-dead-letter-exchange': this.config.exchange,
          'x-dead-letter-routing-key': this.config.failed_queue,
        },
      });
      await channel.bindQueue(
        this.config.email_queue,
        this.config.exchange,
        'email',
      );

      // Setup push queue with dead-letter queue
      await channel.assertQueue(this.config.push_queue, {
        durable: true,
        arguments: {
          'x-dead-letter-exchange': this.config.exchange,
          'x-dead-letter-routing-key': this.config.failed_queue,
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
        this.config.exchange,
        'failed',
      );

      this.logger.log('Queues and exchange setup completed');
    } catch (error) {
      this.logger.error('Failed to setup queues', error);
      throw error;
    }
  }

  async publishToEmailQueue(message: {
    request_id?: string;
    [key: string]: unknown;
  }): Promise<boolean> {
    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const published = await this.channel.publish(
        this.config.exchange,
        'email',
        messageBuffer,
        {
          persistent: true,
          messageId: message.request_id || this.generateMessageId(),
          timestamp: Date.now(),
        },
      );

      if (published) {
        this.logger.log(
          `Message published to email queue: ${message.request_id || 'unknown'}`,
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

  async publishToPushQueue(message: {
    request_id?: string;
    [key: string]: unknown;
  }): Promise<boolean> {
    try {
      const messageBuffer = Buffer.from(JSON.stringify(message));
      const published = await this.channel.publish(
        this.config.exchange,
        'push',
        messageBuffer,
        {
          persistent: true,
          messageId: message.request_id || this.generateMessageId(),
          timestamp: Date.now(),
        },
      );

      if (published) {
        this.logger.log(
          `Message published to push queue: ${message.request_id || 'unknown'}`,
        );
        return true;
      } else {
        this.logger.warn('Message not published to push queue (buffer full)');
        return false;
      }
    } catch (error) {
      this.logger.error('Failed to publish to push queue', error);
      throw error;
    }
  }

  private generateMessageId(): string {
    return `msg_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  isConnected(): boolean {
    return !!(this.connection && this.channel);
  }
}
