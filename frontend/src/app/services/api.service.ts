import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { LogsResponse, ProxyResult, ProxyStatus, ResultsResponse } from '../models/proxy.models';

export interface StartPayload {
  targets?: string[];
  max_proxies?: number | null;
  max_per_target?: number | null;
}

@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  getStatus(): Observable<ProxyStatus> {
    return this.http.get<ProxyStatus>('/status');
  }

  getLogs(): Observable<LogsResponse> {
    return this.http.get<LogsResponse>('/logs');
  }

  getResults(): Observable<ResultsResponse> {
    return this.http.get<ResultsResponse>('/results');
  }

  startScan(payload: StartPayload): Observable<string> {
    return this.http.post('/start', payload, { responseType: 'text' });
  }

  stopScan(): Observable<string> {
    return this.http.post('/stop', {}, { responseType: 'text' });
  }
}
