// services/api-gateway/src/services/template-service.client.ts
import { Injectable, Logger } from '@nestjs/common';
import { HttpService } from '@nestjs/axios';
import { firstValueFrom } from 'rxjs';
import { ConfigService } from '@nestjs/config';
import { CircuitBreakerService } from '../circuit-breaker/circuit-breaker.service';
import { retryWithBackoff } from 'src/common/utils/retry.utils';

export interface Template {
  id: string;
  name: string;
  type: 'email' | 'push';
  content: string;
  variables: string[];
  language?: string;
}

@Injectable()
export class TemplateServiceClient {
  private readonly logger = new Logger(TemplateServiceClient.name);
  private readonly baseUrl: string;

  constructor(
    private readonly httpService: HttpService,
    private readonly configService: ConfigService,
    private readonly circuitBreaker: CircuitBreakerService,
  ) {
    this.baseUrl = this.configService.get<string>(
      'TEMPLATE_SERVICE_URL',
      'http://template-service:3000',
    );
  }

  async getTemplate(
    templateId: string,
    language?: string,
    correlationId?: string,
  ): Promise<Template> {
    return this.circuitBreaker.execute(
      'template-service',
      async () => {
        return retryWithBackoff(
          async () => {
            const params: { language?: string } = {};
            if (language) {
              params.language = language;
            }

            const response = await firstValueFrom(
              this.httpService.get<Template>(
                `${this.baseUrl}/api/templates/${templateId}`,
                {
                  params,
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

  async renderTemplate(
    templateId: string,
    variables: Record<string, string>,
    language?: string,
    correlationId?: string,
  ): Promise<string> {
    return this.circuitBreaker.execute('template-service', async () => {
      return retryWithBackoff(
        async () => {
          const response = await firstValueFrom(
            this.httpService.post<{ rendered_content: string }>(
              `${this.baseUrl}/api/templates/${templateId}/render`,
              { variables, language },
              {
                headers: {
                  'X-Correlation-ID': correlationId || '',
                },
              },
            ),
          );
          return response.data.rendered_content;
        },
        { maxRetries: 3 },
        this.logger,
      );
    });
  }
}
