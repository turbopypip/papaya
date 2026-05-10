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

export interface CreateThreadRequest {
  title: string;
  categories: string[];
}

export interface CreateThreadResponse {
  error?: string;
}
