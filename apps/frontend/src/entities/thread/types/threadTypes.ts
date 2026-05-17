import {Attachment} from '@/entities/attachment';
import {PublicUser} from '@/entities/user/types/userTypes';

export interface Thread {
  ID: string;
  title: string;
  categories?: string[] | null;
  CreatedAt: string;
  UpdatedAt: string;
  user_id: string;
  author?: PublicUser;
  attachments?: Attachment[];
}

export interface DeletedThread {
  ID: string;
  deleted_at: string;
}

export interface GetThreadsResponse {
  error?: string;
  threads: Thread[];
}

export interface GetThreadResponse {
  error?: string;
  thread?: Thread;
  deleted_thread?: DeletedThread;
}

export interface CreateThreadRequest {
  title: string;
  categories: string[];
  attachments?: File[];
}

export interface CreateThreadResponse {
  error?: string;
  thread?: Thread;
}

export interface UpdateThreadRequest {
  id: string;
  title: string;
  categories: string[];
  keep_attachment_ids?: string[];
  attachments?: File[];
}

export interface UpdateThreadResponse {
  error?: string;
  thread?: Thread;
}

export interface DeleteThreadResponse {
  error?: string;
  thread_id?: string;
}
