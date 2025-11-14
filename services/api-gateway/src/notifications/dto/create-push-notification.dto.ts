import {
  IsString,
  IsOptional,
  IsObject,
  IsArray,
  ValidateNested,
  IsUrl,
} from 'class-validator';
import { Type } from 'class-transformer';

class PushRecipientDto {
  @IsString()
  device_token: string;

  @IsOptional()
  @IsString()
  user_id?: string;
}

/**
 * @deprecated Use CreatePushNotificationDto instead
 * This DTO will be removed soon
 */

export class CreatePushNotificationDto {
  @IsString()
  title: string;

  @IsString()
  body: string;

  @IsArray()
  @ValidateNested({ each: true })
  @Type(() => PushRecipientDto)
  recipients: PushRecipientDto[];

  @IsOptional()
  @IsString()
  template_id?: string;

  @IsOptional()
  @IsUrl()
  image_url?: string;

  @IsOptional()
  @IsUrl()
  link_url?: string;

  @IsOptional()
  @IsObject()
  data?: Record<string, any>;

  @IsOptional()
  @IsString()
  request_id?: string;

  @IsOptional()
  @IsString()
  correlation_id?: string;
}
