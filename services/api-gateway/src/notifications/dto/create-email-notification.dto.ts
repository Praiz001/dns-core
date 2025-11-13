import {
  IsString,
  IsEmail,
  IsOptional,
  IsObject,
  IsArray,
  ValidateNested,
} from 'class-validator';
import { Type } from 'class-transformer';

class EmailRecipientDto {
  @IsEmail()
  email: string;

  @IsOptional()
  @IsString()
  name?: string;
}

export class CreateEmailNotificationDto {
  @IsString()
  template_id: string;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => EmailRecipientDto)
  recipients: EmailRecipientDto[];

  @IsOptional()
  @IsString()
  subject?: string;

  @IsOptional()
  @IsObject()
  variables?: Record<string, string>;

  @IsOptional()
  @IsString()
  request_id?: string; // For idempotency

  @IsOptional()
  @IsString()
  correlation_id?: string; // For tracking
}
