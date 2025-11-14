import { NestFactory } from '@nestjs/core';
import { AppModule } from './app.module';
import { ResponseInterceptor } from './common/interceptors/response.interceptor';
import { ValidationPipe, LoggerService } from '@nestjs/common';
import { CorrelationIdMiddleware } from './common/middleware/correlation-id.middleware';
import { WINSTON_MODULE_NEST_PROVIDER } from 'nest-winston';
import { SwaggerModule } from '@nestjs/swagger';
import { DocumentBuilder } from '@nestjs/swagger';

async function bootstrap() {
  const app = await NestFactory.create(AppModule);

  // Use Winston logger instead of default NestJS logger
  app.useLogger(app.get(WINSTON_MODULE_NEST_PROVIDER));
  // Apply correlation ID middleware
  app.use(
    new CorrelationIdMiddleware().use.bind(new CorrelationIdMiddleware()),
  );

  // enable CORS for cross-origin requests
  app.enableCors();
  // set global API prefix
  app.setGlobalPrefix('api/v1');

  // Swagger/OpenAPI Configuration
  const config = new DocumentBuilder()
    .setTitle('Notification System API Gateway')
    .setDescription('API Gateway for the Distributed Notification System')
    .setVersion('1.0')
    .addTag('notifications', 'Notification management endpoints')
    .addTag('health', 'Health check endpoints')
    .addBearerAuth(
      {
        type: 'http',
        scheme: 'bearer',
        bearerFormat: 'JWT',
        name: 'JWT',
        description: 'Enter JWT token',
        in: 'header',
      },
      'JWT-auth',
    )
    .build();

  const document = SwaggerModule.createDocument(app, config);
  SwaggerModule.setup('api/docs', app, document, {
    swaggerOptions: {
      persistAuthorization: true, // Keep auth token in browser
    },
  });

  // Add ValidationPipe
  app.useGlobalPipes(
    new ValidationPipe({
      whitelist: true, // Strip properties that don't have decorators
      forbidNonWhitelisted: true, // Throw error if non-whitelisted properties exist
      transform: true, // Automatically transform payloads to DTO instances
      transformOptions: {
        enableImplicitConversion: true, // Convert types automatically
      },
    }),
  );

  // Apply standardized response format globally
  app.useGlobalInterceptors(new ResponseInterceptor());

  const port = process.env.PORT || 3000;
  await app.listen(port);
  console.log(`API Gateway running on port ${port}`);

  const logger = app.get<LoggerService>(WINSTON_MODULE_NEST_PROVIDER);
  logger.log(`API Gateway running on port ${port}`, 'Bootstrap');
  logger.log(
    `Swagger documentation available at http://localhost:${port}/api/docs`,
    'Bootstrap',
  );
}
bootstrap();
