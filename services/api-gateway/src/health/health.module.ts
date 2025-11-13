import { Module } from '@nestjs/common';
import { TerminusModule } from '@nestjs/terminus';
import { HealthController } from './health.controller';
import { QueueModule } from '../queue/queue.module';
import { IdempotencyModule } from '../idempotency/idempotency.module';
import { DatabaseModule } from '../database/database.module';

@Module({
  imports: [TerminusModule, QueueModule, IdempotencyModule, DatabaseModule],
  controllers: [HealthController],
})
export class HealthModule {}
