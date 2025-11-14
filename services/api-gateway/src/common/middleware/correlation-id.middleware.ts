import { Injectable, NestMiddleware, Logger } from '@nestjs/common';
import { Request, Response, NextFunction } from 'express';
import { v4 as uuidv4 } from 'uuid';

declare module 'express' {
  interface Request {
    correlationId?: string;
  }
}
@Injectable()
export class CorrelationIdMiddleware implements NestMiddleware {
  private readonly logger = new Logger(CorrelationIdMiddleware.name);

  use(req: Request, res: Response, next: NextFunction) {
    // Get correlation ID from header or generate new one
    const correlationId =
      req.headers['x-correlation-id'] ||
      req.headers['x-request-id'] ||
      uuidv4();

    // Attach to request object for use in controllers/services
    req.correlationId = correlationId as string;

    // Add to response header
    res.setHeader('X-Correlation-ID', correlationId as string);

    // Log request start
    this.logger.log(
      `${req.method} ${req.path} - Correlation ID: ${correlationId as string}`,
    );

    next();
  }
}
