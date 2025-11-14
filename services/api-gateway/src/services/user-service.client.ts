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

interface ApiResponse<T> {
  success: boolean;
  data: T;
  message?: string;
  error?: string;
}

export interface UserData {
  id: string;
  email: string;
  name?: string;
  preferences?: UserPreferences;
}

/**
 * UserContactInfo: Contact information for sending notifications
 * - For email: contact = user's email address
 * - For push: contact = user's device token
 */
export interface UserContactInfo {
  user_id: string;
  contact: string; // email address or device token
  notification_type: 'email' | 'push';
  preferences_enabled: boolean; // whether user has opted in
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

  /**
   * getUserContactInfo: Fetch user's contact info for a specific notification type
   *
   * This is called by API Gateway before routing to queue.
   * It retrieves either:
   * - Email address (for email notifications)
   * - Device push token (for push notifications)
   *
   * Also checks user preferences to see if they've opted in to this notification type.
   *
   * @param userId - UUID of the user
   * @param notificationType - 'email' or 'push'
   * @param correlationId - For request tracing
   * @returns UserContactInfo or null if user not found / contact not available
   */

  async getUserContactInfo(
    userId: string,
    notificationType: 'email' | 'push',
    correlationId?: string,
  ): Promise<UserContactInfo | null> {
    return this.circuitBreaker.execute(
      'user-service',
      async () => {
        return retryWithBackoff(
          async () => {
            try {
              // Call User Service endpoint: GET /api/v1/users/{userId}/contact?type={email|push}
              const response = await firstValueFrom(
                this.httpService.get<UserContactInfo>(
                  `${this.baseUrl}/api/v1/users/${userId}/contact`,
                  {
                    params: { type: notificationType },
                    headers: {
                      'X-Correlation-ID': correlationId || '',
                    },
                  },
                ),
              );
              // User Service should return:
              // {
              //   success: true,
              //   data: {
              //     user_id: "uuid",
              //     contact: "user@example.com" or "fcm_token_abc",
              //     notification_type: "email" or "push",
              //     preferences_enabled: true
              //   }
              // }

              const data = response.data;

              // If data is wrapped in response format, extract it
              if ('success' in data && 'data' in data) {
                const wrappedResponse = data as ApiResponse<UserContactInfo>;
                return wrappedResponse.data;
              }

              return data;
            } catch (error) {
              this.logger.error(
                `Failed to fetch contact info for user ${userId}`,
                error,
              );
              return null;
            }
          },
          { maxRetries: 3 },
          this.logger,
        );
      },
      { failureThreshold: 5, resetTimeout: 60000 },
    );
  }
}
