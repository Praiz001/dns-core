import { Module } from '@nestjs/common';
import { AppController } from './app.controller';
import { AppService } from './app.service';
import { ConfigurationModule } from './config/config.module';
import { QueueModule } from './queue/queue.module';
import { NotificationsModule } from './notifications/notifications.module';
import { DatabaseModule } from './database/database.module';
import { ServicesModule } from './services/services.module';
import { HealthModule } from './health/health.module';

@Module({
  imports: [
    ConfigurationModule,
    QueueModule,
    NotificationsModule,
    DatabaseModule,
    ServicesModule,
    HealthModule,
  ],
  controllers: [AppController],
  providers: [AppService],
})
export class AppModule {}
