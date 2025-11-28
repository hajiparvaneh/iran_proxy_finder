import { CommonModule } from '@angular/common';
import { Component, DestroyRef, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { finalize, interval, tap } from 'rxjs';
import { ApiService, StartPayload } from './services/api.service';
import { ProxyResult, ProxyStatus } from './models/proxy.models';

const DEFAULT_TARGETS = [
  'https://api.ipify.org?format=json',
  'https://httpbin.org/get'
].join('\n');

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [CommonModule, ReactiveFormsModule],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.scss']
})
export class AppComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly fb = inject(FormBuilder);
  private readonly destroyRef = inject(DestroyRef);

  status = signal<ProxyStatus | null>(null);
  logs = signal<string[]>([]);
  results = signal<ProxyResult[]>([]);
  statusMessage = signal<string>('');
  isStarting = signal(false);
  isStopping = signal(false);
  lastUpdated = signal<Date | null>(null);

  readonly form = this.fb.group({
    targets: this.fb.control<string>(DEFAULT_TARGETS, [Validators.required]),
    maxProxies: this.fb.control<number | null>(null, [Validators.min(1)]),
    maxPerTarget: this.fb.control<number | null>(null, [Validators.min(1)])
  });

  readonly statusLabel = computed(() => {
    const current = this.status();
    if (!current) {
      return 'Idle';
    }
    if (current.stopping) {
      return 'Stopping';
    }
    return current.running ? 'Running' : 'Idle';
  });

  readonly statusClass = computed(() => {
    const label = this.statusLabel();
    if (label === 'Running') return 'running';
    if (label === 'Stopping') return 'stopping';
    return 'idle';
  });

  ngOnInit(): void {
    this.refreshStatus();
    this.refreshLogs();
    this.refreshResults();

    interval(4000)
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe(() => {
        this.refreshStatus();
        this.refreshLogs();
        this.refreshResults(false);
      });
  }

  refreshStatus(): void {
    this.api
      .getStatus()
      .pipe(tap(() => this.markUpdated()))
      .subscribe({
        next: (data) => this.status.set(data),
        error: () => this.statusMessage.set('Unable to load status. Check the server connection.')
      });
  }

  refreshLogs(): void {
    this.api
      .getLogs()
      .pipe(tap(() => this.markUpdated()))
      .subscribe({ next: (data) => this.logs.set(data.logs ?? []) });
  }

  refreshResults(resetUpdate: boolean = true): void {
    this.api
      .getResults()
      .pipe(tap(() => resetUpdate && this.markUpdated()))
      .subscribe({ next: (data) => this.results.set(data.results ?? []) });
  }

  startScan(): void {
    if (this.form.invalid || this.isStarting()) {
      this.form.markAllAsTouched();
      return;
    }

    const payload: StartPayload = this.buildPayload();

    this.isStarting.set(true);
    this.statusMessage.set('');
    this.api
      .startScan(payload)
      .pipe(finalize(() => this.isStarting.set(false)))
      .subscribe({
        next: () => {
          this.statusMessage.set('Scan started. Watching for updates...');
          this.refreshStatus();
        },
        error: (err) => {
          this.statusMessage.set(err?.error || 'Scan is already running.');
        }
      });
  }

  stopScan(): void {
    if (this.isStopping()) {
      return;
    }
    this.isStopping.set(true);
    this.statusMessage.set('');
    this.api
      .stopScan()
      .pipe(finalize(() => this.isStopping.set(false)))
      .subscribe({
        next: () => {
          this.statusMessage.set('Stopping scan...');
          this.refreshStatus();
        },
        error: (err) => {
          this.statusMessage.set(err?.error || 'No scan is currently running.');
        }
      });
  }

  copyProxy(proxy: string): void {
    if (!navigator?.clipboard) {
      this.statusMessage.set('Clipboard not available in this browser.');
      return;
    }
    navigator.clipboard
      .writeText(proxy)
      .then(() => this.statusMessage.set(`Copied ${proxy}`))
      .catch(() => this.statusMessage.set('Unable to copy right now.'));
  }

  formatTimestamp(value: number | null): string {
    if (!value) return '—';
    const date = new Date(value * 1000);
    return date.toLocaleString();
  }

  trackByProxy(_: number, item: ProxyResult): string {
    return `${item.proxy}-${item.target}`;
  }

  private buildPayload(): StartPayload {
    const { targets, maxPerTarget, maxProxies } = this.form.getRawValue();
    const cleanedTargets = (targets || '')
      .split(/\n|,/)
      .map((t) => t.trim())
      .filter(Boolean);

    return {
      targets: cleanedTargets.length ? cleanedTargets : undefined,
      max_per_target: maxPerTarget && maxPerTarget > 0 ? maxPerTarget : null,
      max_proxies: maxProxies && maxProxies > 0 ? maxProxies : null
    };
  }

  private markUpdated(): void {
    this.lastUpdated.set(new Date());
  }
}
