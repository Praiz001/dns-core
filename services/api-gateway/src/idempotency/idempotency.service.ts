import { Injectable, Logger, OnModuleDestroy } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { Redis, RedisOptions } from 'ioredis';

@Injectable()
export class IdempotencyService implements OnModuleDestroy {
  private readonly logger = new Logger(IdempotencyService.name);
  private readonly redis: Redis;
  private readonly ttl: number; // Time to live in seconds

  constructor(private configService: ConfigService) {
    const redisHost =
      this.configService.get<string>('REDIS_HOST', 'redis') ?? 'redis';
    const redisPort =
      this.configService.get<number>('REDIS_PORT', 6379) ?? 6379;
    const ttl = this.configService.get<number>('REDIS_TTL', 3600) ?? 3600; // 1 hour default

    const redisOptions: RedisOptions = {
      host: redisHost,
      port: redisPort,
      retryStrategy: (times) => {
        const delay = Math.min(times * 50, 2000);
        return delay;
      },
    };

    // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call
    this.redis = new Redis(redisOptions) as Redis;
    this.ttl = ttl;

    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    this.redis.on('connect', () => {
      this.logger.log('Connected to Redis');
    });

    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    this.redis.on('error', (error) => {
      this.logger.error('Redis connection error', error);
    });
  }

  /**
   * Generate idempotency key from request ID
   */
  private getKey(requestId: string, type: 'email' | 'push'): string {
    return `idempotency:${type}:${requestId}`;
  }

  /**
   * Check if request ID already exists (duplicate request)
   * Returns cached response if exists, null if new request
   */
  async checkDuplicate(
    requestId: string,
    type: 'email' | 'push',
  ): Promise<Record<string, unknown> | null> {
    try {
      const key = this.getKey(requestId, type);
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      const cached = await this.redis.get(key);

      if (cached) {
        this.logger.log(`Duplicate request detected: ${requestId}`);
        return JSON.parse(cached as string) as Record<string, unknown>;
      }

      return null;
    } catch (error) {
      this.logger.error(`Error checking idempotency for ${requestId}`, error);
      // Don't fail the request if Redis is down, just log and continue
      return null;
    }
  }

  /**
   * Store request ID and response for idempotency
   */
  async storeResponse(
    requestId: string,
    type: 'email' | 'push',
    response: Record<string, unknown>,
  ): Promise<void> {
    try {
      const key = this.getKey(requestId, type);
      // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      await this.redis.setex(key, this.ttl, JSON.stringify(response));
      this.logger.log(`Stored idempotency key: ${requestId}`);
    } catch (error) {
      this.logger.error(`Error storing idempotency for ${requestId}`, error);
      // Don't fail the request if Redis is down
    }
  }

  /**
   * Reserve request ID (for optimistic locking)
   * Returns true if reserved, false if already exists
   */
  async reserveRequestId(
    requestId: string,
    type: 'email' | 'push',
  ): Promise<boolean> {
    try {
      const key = this.getKey(requestId, type);
      // Use SET with NX (only set if not exists) and EX (expiration)
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      const result = await this.redis.set(
        key,
        'processing',
        'EX',
        this.ttl,
        'NX',
      );

      if (result === 'OK' || result === null) {
        this.logger.log(`Reserved idempotency key: ${requestId}`);
        return true;
      }

      // Key already exists
      this.logger.warn(`Request ID already in use: ${requestId}`);
      return false;
    } catch (error) {
      this.logger.error(`Error reserving idempotency for ${requestId}`, error);
      // If Redis is down, allow the request to proceed
      return true;
    }
  }

  /**
   * Clean up reserved key (if processing failed)
   */
  async releaseRequestId(
    requestId: string,
    type: 'email' | 'push',
  ): Promise<void> {
    try {
      const key = this.getKey(requestId, type);
      // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      await this.redis.del(key);
      this.logger.log(`Released idempotency key: ${requestId}`);
    } catch (error) {
      this.logger.error(`Error releasing idempotency for ${requestId}`, error);
    }
  }

  async isConnected(): Promise<boolean> {
    try {
      // eslint-disable-next-line @typescript-eslint/no-unsafe-assignment, @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
      const result = await this.redis.ping();
      return result === 'PONG';
    } catch {
      return false;
    }
  }

  /**
   * On module destroy, close Redis connection
   */
  async onModuleDestroy(): Promise<void> {
    // eslint-disable-next-line @typescript-eslint/no-unsafe-call, @typescript-eslint/no-unsafe-member-access
    await this.redis.quit();
  }
}
