import { Module } from '@nestjs/common';
import { NotificationsController } from './notifications.controller';
import { NotificationsService } from './notifications.service';
import { QueueModule } from '../queue/queue.module';
import { Notification } from './entities/notification.entity';
import { TypeOrmModule } from '@nestjs/typeorm';
import { IdempotencyModule } from '../idempotency/idempotency.module';
import { ServicesModule } from '../services/services.module';

@Module({
  imports: [
    QueueModule,
    TypeOrmModule.forFeature([Notification]),
    IdempotencyModule,
    ServicesModule,
  ],
  controllers: [NotificationsController],
  providers: [NotificationsService],
  exports: [NotificationsService],
})
export class NotificationsModule {}
