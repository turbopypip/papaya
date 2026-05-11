export interface Thread {
  ID: string;
  title: string;
  categories: string[];
  CreatedAt: string;
}

export interface GetThreadsResponse {
  error?: string;
  threads: Thread[];
}

export interface GetThreadResponse {
  error?: string;
  thread: Thread;
}

export interface CreateThreadRequest {
  title: string;
  categories: string[];
}

export interface CreateThreadResponse {
  error?: string;
  thread?: Thread;
}
