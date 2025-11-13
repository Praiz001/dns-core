import { Module } from '@nestjs/common';
import { HttpModule } from '@nestjs/axios';
import { UserServiceClient } from './user-service.client';
import { TemplateServiceClient } from './template-service.client';
import { CircuitBreakerModule } from '../circuit-breaker/circuit-breaker.module';

@Module({
  imports: [
    HttpModule.register({
      timeout: 5000, // 5 second timeout
      maxRedirects: 3,
    }),
    CircuitBreakerModule,
  ],
  providers: [UserServiceClient, TemplateServiceClient],
  exports: [UserServiceClient, TemplateServiceClient],
})
export class ServicesModule {}
