// services/api-gateway/src/database/database.module.ts
import { Module } from '@nestjs/common';
import { TypeOrmModule } from '@nestjs/typeorm';
import { ConfigModule, ConfigService } from '@nestjs/config';
import { Notification } from 'src/notifications/entities/notification.entity';

@Module({
  imports: [
    TypeOrmModule.forRootAsync({
      imports: [ConfigModule],
      useFactory: (configService: ConfigService) => {
        // Check if Supabase connection URL is provided
        const supabaseUrl = configService.get<string>('DATABASE_URL');

        if (supabaseUrl) {
          return {
            type: 'postgres',
            url: supabaseUrl,
            entities: [Notification],
            synchronize: configService.get<string>('NODE_ENV') !== 'production',
            logging: configService.get<string>('NODE_ENV') === 'development',
            ssl: {
              rejectUnauthorized: false, // Supabase uses SSL
            },
          };
        }

        // Fallback to individual connection parameters (for local dev)
        return {
          type: 'postgres',
          host: configService.get<string>('DB_HOST', 'postgres'),
          port: configService.get<number>('DB_PORT', 5432),
          username: configService.get<string>('DB_USERNAME', 'postgres'),
          password: configService.get<string>('DB_PASSWORD', 'postgres'),
          database: configService.get<string>('DB_NAME', 'notification_db'),
          entities: [Notification],
          synchronize: configService.get<string>('NODE_ENV') !== 'production',
          logging: configService.get<string>('NODE_ENV') === 'development',
        };
      },
      inject: [ConfigService],
    }),
    TypeOrmModule.forFeature([Notification]),
  ],
  exports: [TypeOrmModule],
})
export class DatabaseModule {}
