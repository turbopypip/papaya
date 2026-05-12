import {Attachment} from '@/entities/attachment';

export interface Thread {
  ID: string;
  title: string;
  categories?: string[] | null;
  CreatedAt: string;
  user_id: string;
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
