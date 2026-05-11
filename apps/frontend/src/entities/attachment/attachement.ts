export type AttachmentOwnerType = 'thread' | 'post' | 'comment';

export interface Attachment {
  ID: string;
  url: string;
  file_name: string;
  content_type: string;
  size: number;
  owner_type: AttachmentOwnerType;
  owner_id: string;
  CreatedAt: string;
}
