export interface ProxyStatus {
  running: boolean;
  last_started: number | null;
  last_finished: number | null;
  stopping: boolean;
}

export interface ProxyResult {
  proxy: string;
  latency: number;
  scheme: string;
  target: string;
}

export interface LogsResponse {
  logs: string[];
}

export interface ResultsResponse {
  results: ProxyResult[];
}
