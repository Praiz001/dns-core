import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '@nestjs/config';
import { CircuitBreakerService } from '../circuit-breaker/circuit-breaker.service';
import { retryWithBackoff } from 'src/common/utils/retry.utils';

export interface UserPreferences {
  email_enabled: boolean;
  push_enabled: boolean;
  email?: string;
  push_tokens?: string[];
}

export interface UserData {
  id: string;
  email: string;
  name?: string;
  preferences?: UserPreferences;
}

@Injectable()
export class UserServiceClient {
  private readonly logger = new Logger(UserServiceClient.name);
  private readonly baseUrl: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
    private readonly circuitBreaker: CircuitBreakerService,
  ) {
    this.baseUrl = this.configService.get<string>(
      'USER_SERVICE_URL',
      'http://user-service:3000',
    );
  }

  async getUserPreferences(
    userId: string,
    correlationId?: string,
  ): Promise<UserPreferences> {
    return this.circuitBreaker.execute(
      'user-service',
      async () => {
        return retryWithBackoff(
          async () => {
            const response = await firstValueFrom(
              this.httpService.get<UserPreferences>(
                `${this.baseUrl}/api/users/${userId}/preferences`,
                {
                  headers: {
                    'X-Correlation-ID': correlationId || '',
                  },
                },
              ),
            );
            return response.data;
          },
          { maxRetries: 3 },
          this.logger,
        );
      },
      { failureThreshold: 5, resetTimeout: 60000 },
    );
  }

  async getUserData(userId: string, correlationId?: string): Promise<UserData> {
    return this.circuitBreaker.execute(
      'user-service',
      async () => {
        return retryWithBackoff(
          async () => {
            const response = await firstValueFrom(
              this.httpService.get<UserData>(
                `${this.baseUrl}/api/users/${userId}`,
                {
                  headers: {
                    'X-Correlation-ID': correlationId || '',
                  },
                },
              ),
            );
            return response.data;
          },
          { maxRetries: 3 },
          this.logger,
        );
      },
      { failureThreshold: 5, resetTimeout: 60000 },
    );
  }

  async validateUserToken(token: string): Promise<UserData | null> {
    try {
      return await this.circuitBreaker.execute('user-service', async () => {
        return retryWithBackoff(
          async () => {
            const response = await firstValueFrom(
              this.httpService.get<UserData>(
                `${this.baseUrl}/api/users/validate`,
                {
                  headers: {
                    Authorization: `Bearer ${token}`,
                  },
                },
              ),
            );
            return response.data;
          },
          { maxRetries: 2 },
          this.logger,
        );
      });
    } catch (error) {
      this.logger.error('Failed to validate user token', error);
      return null;
    }
  }
}
