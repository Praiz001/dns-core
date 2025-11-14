import {
  Entity,
  Column,
  PrimaryGeneratedColumn,
  CreateDateColumn,
  UpdateDateColumn,
  Index,
} from 'typeorm';

/**
 * Notification entity - matches specification exactly
 * Stores notification records for tracking and status updates
 */
@Entity('notifications')
@Index(['request_id'], { unique: true })
@Index(['user_id'])
@Index(['status'])
@Index(['notification_type'])
@Index(['created_at'])
export class Notification {
  @PrimaryGeneratedColumn('uuid')
  id: string;

  @Column({ unique: true })
  @Index()
  request_id: string;

  @Column('uuid')
  @Index()
  user_id: string;

  @Column({
    type: 'enum',
    enum: ['email', 'push'],
  })
  notification_type: 'email' | 'push';

  @Column({
    type: 'enum',
    enum: ['pending', 'delivered', 'failed'],
    default: 'pending',
  })
  @Index()
  status: 'pending' | 'delivered' | 'failed';

  @Column()
  template_code: string;

  @Column('jsonb')
  variables: {
    name: string;
    link: string;
    meta?: Record<string, any>;
  };

  @Column('int')
  priority: number;

  @Column('jsonb', { nullable: true })
  metadata: Record<string, any>;

  @Column({ type: 'text', nullable: true })
  error_message: string;

  @Column({ type: 'timestamp', nullable: true })
  sent_at: Date;

  @CreateDateColumn()
  created_at: Date;

  @UpdateDateColumn()
  updated_at: Date;
}
