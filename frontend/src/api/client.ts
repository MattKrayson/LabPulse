export interface HealthResponse {
  status: string;
  app: string;
  version: string;
  database: string;
  timestamp: string;
}

export class UnauthorizedError extends Error {
  constructor() {
    super("Unauthorized");
    this.name = "UnauthorizedError";
  }
}

export interface Host {
  id: number;
  name: string;
  hostname: string | null;
  is_local: boolean;
  created_at: string;
  connection_url: string | null;
  status: "connected" | "error" | "unknown";
  last_error: string | null;
  last_checked_at: string | null;
}

export interface ContainerSummary {
  id: number;
  host_id: number;
  container_id: string;
  name: string;
  image: string;
  image_id: string;
  created_at: string | null;
  state: string;
  status: string;
  health_status: string | null;
  restart_count: number;
  started_at: string | null;
  is_present: boolean;
  first_seen_at: string;
  last_seen_at: string;
}

export type Severity = "INFO" | "WARNING" | "ERROR" | "CRITICAL";

export interface EventSummary {
  id: number;
  timestamp: string;
  severity: Severity;
  category: string;
  source_type: string;
  source_id: string;
  source_name: string;
  title: string;
  description: string | null;
  event_metadata: Record<string, unknown> | null;
  created_at: string;
}

export interface StatsResponse {
  total_containers: number;
  healthy: number;
  warning: number;
  critical: number;
  recent_errors: number;
  recent_incidents: number;
}

export type MetricType =
  | "cpu_percent"
  | "memory_percent"
  | "network_rx_bytes"
  | "network_tx_bytes";

export interface MetricPoint {
  id: number;
  timestamp: string;
  container_id: string;
  metric_type: MetricType;
  value: number;
  created_at: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`/api${path}`, { credentials: "include", ...init });
  if (response.status === 401) {
    throw new UnauthorizedError();
  }
  if (!response.ok) {
    throw new Error(`Request to ${path} failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

export function getHosts(): Promise<Host[]> {
  return request<Host[]>("/hosts");
}

export function createHost(name: string, connectionUrl: string): Promise<Host> {
  return request<Host>("/hosts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ name, connection_url: connectionUrl }),
  });
}

export function testHost(hostId: number): Promise<Host> {
  return request<Host>(`/hosts/${hostId}/test`, { method: "POST" });
}

export function deleteHost(hostId: number): Promise<void> {
  return request<void>(`/hosts/${hostId}`, { method: "DELETE" });
}

export function getContainers(): Promise<ContainerSummary[]> {
  return request<ContainerSummary[]>("/containers");
}

export function getContainer(containerId: string): Promise<ContainerSummary> {
  return request<ContainerSummary>(`/containers/${containerId}`);
}

export function getStats(): Promise<StatsResponse> {
  return request<StatsResponse>("/stats");
}

export function getEvents(): Promise<EventSummary[]> {
  return request<EventSummary[]>("/events?limit=20");
}

export function getEventsForSource(sourceId: string, limit = 50): Promise<EventSummary[]> {
  const params = new URLSearchParams({ source_id: sourceId, limit: String(limit) });
  return request<EventSummary[]>(`/events?${params.toString()}`);
}

export function getMetrics(
  containerId: string,
  metricType: MetricType,
  sinceMinutes = 30,
  limit = 500
): Promise<MetricPoint[]> {
  const since = new Date(Date.now() - sinceMinutes * 60_000).toISOString();
  const params = new URLSearchParams({
    container_id: containerId,
    metric_type: metricType,
    since,
    limit: String(limit),
  });
  return request<MetricPoint[]>(`/metrics?${params.toString()}`);
}

export interface ChangeEntry {
  type: string;
  container_id: string;
  container_name: string;
  description: string;
  detail: string | null;
}

export function getChanges(sinceHours = 24): Promise<ChangeEntry[]> {
  return request<ChangeEntry[]>(`/changes?since_hours=${sinceHours}`);
}

export type IncidentStatus = "OPEN" | "RESOLVED";

export interface IncidentSummary {
  id: number;
  source_type: string;
  source_id: string;
  source_name: string;
  title: string;
  severity: Severity;
  status: IncidentStatus;
  started_at: string;
  ended_at: string;
  event_count: number;
}

export interface IncidentDetail extends IncidentSummary {
  events: EventSummary[];
}

export function getIncidents(status?: IncidentStatus): Promise<IncidentSummary[]> {
  const params = new URLSearchParams({ limit: "50" });
  if (status) params.set("status", status);
  return request<IncidentSummary[]>(`/incidents?${params.toString()}`);
}

export function getIncident(incidentId: number): Promise<IncidentDetail> {
  return request<IncidentDetail>(`/incidents/${incidentId}`);
}

export type WebhookFormat = "generic" | "discord" | "slack" | "ntfy";

export interface Webhook {
  id: number;
  name: string;
  url: string;
  format: WebhookFormat;
  enabled: boolean;
  notify_on_open: boolean;
  notify_on_resolve: boolean;
  created_at: string;
  last_triggered_at: string | null;
  last_error: string | null;
}

export function getWebhooks(): Promise<Webhook[]> {
  return request<Webhook[]>("/webhooks");
}

export function createWebhook(body: {
  name: string;
  url: string;
  format: WebhookFormat;
  notify_on_open: boolean;
  notify_on_resolve: boolean;
}): Promise<Webhook> {
  return request<Webhook>("/webhooks", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

export function deleteWebhook(webhookId: number): Promise<void> {
  return request<void>(`/webhooks/${webhookId}`, { method: "DELETE" });
}

export function testWebhook(webhookId: number): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/webhooks/${webhookId}/test`, { method: "POST" });
}

export interface AuthUser {
  username: string;
}

export function getMe(): Promise<AuthUser> {
  return request<AuthUser>("/auth/me");
}

export function login(username: string, password: string): Promise<AuthUser> {
  return request<AuthUser>("/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
}

export function logout(): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/auth/logout", { method: "POST" });
}

export interface SetupStatus {
  configured: boolean;
  database_url_masked: string | null;
}

export type DatabaseMode = "internal" | "custom";

export class SetupError extends Error {}

async function setupRequest<T>(path: string, mode: DatabaseMode, databaseUrl?: string): Promise<T> {
  const response = await fetch(`/api/setup${path}`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ mode, database_url: databaseUrl }),
  });
  if (response.status === 401) {
    throw new UnauthorizedError();
  }
  if (!response.ok) {
    const body = await response.json().catch(() => null);
    throw new SetupError(body?.detail ?? `Request failed with status ${response.status}`);
  }
  return response.json() as Promise<T>;
}

export function getSetupStatus(): Promise<SetupStatus> {
  return request<SetupStatus>("/setup/status");
}

export function testDatabaseConfig(mode: DatabaseMode, databaseUrl?: string): Promise<{ ok: boolean }> {
  return setupRequest<{ ok: boolean }>("/test", mode, databaseUrl);
}

export function applyDatabaseConfig(
  mode: DatabaseMode,
  databaseUrl?: string
): Promise<{ ok: boolean; restarting?: boolean }> {
  return setupRequest<{ ok: boolean; restarting?: boolean }>("/configure", mode, databaseUrl);
}
