import { Controller, Get } from '@nestjs/common';
import {
  HealthCheckService,
  HealthCheck,
  MemoryHealthIndicator,
  DiskHealthIndicator,
  HealthIndicatorResult,
} from '@nestjs/terminus';
import { QueueService } from '../queue/queue.service';
import { IdempotencyService } from '../idempotency/idempotency.service';
import { DataSource } from 'typeorm';
import { Public } from '../common/decorators/public.decorator';

@Controller('health')
export class HealthController {
  constructor(
    private health: HealthCheckService,
    private memory: MemoryHealthIndicator,
    private disk: DiskHealthIndicator,
    private queueService: QueueService,
    private idempotencyService: IdempotencyService,
    private dataSource: DataSource,
  ) {}

  @Get()
  @Public()
  // eslint-disable-next-line @typescript-eslint/no-unsafe-call
  @HealthCheck()
  check() {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-return, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    return this.health.check([
      // Database health check
      () => this.checkDatabase(),
      // RabbitMQ health check
      () => this.checkRabbitMQ(),
      // Redis health check
      () => this.checkRedis(),
      // Memory health check
      // eslint-disable-next-line @typescript-eslint/no-unsafe-return, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      () => this.memory.checkHeap('memory_heap', 300 * 1024 * 1024), // 300MB threshold
      // Disk health check
      () =>
        // eslint-disable-next-line @typescript-eslint/no-unsafe-return, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
        this.disk.checkStorage('disk', {
          path: '/',
          thresholdPercent: 0.9, // 90% threshold
        }),
    ]);
  }

  private async checkDatabase(): Promise<HealthIndicatorResult> {
    try {
      const isConnected = this.dataSource.isInitialized;
      if (isConnected) {
        // Try a simple query
        await this.dataSource.query('SELECT 1');
        return {
          database: {
            status: 'up',
            message: 'Database connection is healthy',
          },
        } as HealthIndicatorResult;
      }
      throw new Error('Database not initialized');
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      return {
        database: {
          status: 'down',
          message: `Database connection failed: ${errorMessage}`,
        },
      } as HealthIndicatorResult;
    }
  }

  private checkRabbitMQ(): Promise<HealthIndicatorResult> {
    try {
      // Check if connection exists and is connected
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
      const connection = (this.queueService as any).connection;
      if (!connection) {
        throw new Error('RabbitMQ connection not initialized');
      }

      // Try to check connection status
      // Note: amqp-connection-manager doesn't expose a direct isConnected method
      // So we'll check if channel exists as a proxy
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
      const channel = (this.queueService as any).channel;
      if (!channel) {
        throw new Error('RabbitMQ channel not initialized');
      }

      return Promise.resolve({
        rabbitmq: {
          status: 'up',
          message: 'RabbitMQ connection is healthy',
        },
      } as HealthIndicatorResult);
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      return Promise.resolve({
        rabbitmq: {
          status: 'down',
          message: `RabbitMQ connection failed: ${errorMessage}`,
        },
      } as HealthIndicatorResult);
    }
  }

  private async checkRedis(): Promise<HealthIndicatorResult> {
    try {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-member-access
      const redis = (this.idempotencyService as any).redis;
      if (!redis) {
        throw new Error('Redis connection not initialized');
      }

      // Ping Redis to check connection
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      const result = await redis.ping();
      if (result === 'PONG') {
        return {
          redis: {
            status: 'up',
            message: 'Redis connection is healthy',
          },
        } as HealthIndicatorResult;
      }
      throw new Error('Redis ping failed');
    } catch (error: unknown) {
      const errorMessage =
        error instanceof Error ? error.message : 'Unknown error';
      return {
        redis: {
          status: 'down',
          message: `Redis connection failed: ${errorMessage}`,
        },
      } as HealthIndicatorResult;
    }
  }
}
