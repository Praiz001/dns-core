import { ConfigService } from '@nestjs/config';

export interface RabbitMQConfig {
  url: string;
  exchange: string;
  email_queue: string;
  push_queue: string;
  failed_queue: string;
}

export const getRabbitMQConfig = (
  configService: ConfigService,
): RabbitMQConfig => ({
  url: configService.get<string>('RABBITMQ_URL', 'amqp://rabbitmq:5672'),
  exchange: configService.get<string>(
    'RABBITMQ_EXCHANGE',
    'notifications.direct',
  ),
  email_queue: configService.get<string>('RABBITMQ_EMAIL_QUEUE', 'email.queue'),
  push_queue: configService.get<string>('RABBITMQ_PUSH_QUEUE', 'push.queue'),
  failed_queue: configService.get<string>(
    'RABBITMQ_FAILED_QUEUE',
    'failed.queue',
  ),
});
