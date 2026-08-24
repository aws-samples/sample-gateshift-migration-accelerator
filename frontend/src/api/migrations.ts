import apiClient from './client';
import type { Migration, SourcePlatform, ValidationReport } from '../types/migration';

export async function createMigration(params: {
  sourceType: SourcePlatform;
  configS3Key: string;
  fileName: string;
}): Promise<{ migrationId: string }> {
  const { data } = await apiClient.post('/migrations', params);
  return data;
}

export async function getMigration(migrationId: string): Promise<Migration> {
  const { data } = await apiClient.get(`/migrations/${migrationId}`);
  return data;
}

export async function getMigrations(): Promise<Migration[]> {
  const { data } = await apiClient.get('/migrations');
  return data.migrations;
}

export async function getValidationReport(migrationId: string): Promise<ValidationReport> {
  const { data } = await apiClient.get(`/migrations/${migrationId}/report`);
  return data;
}

export async function getDownloadUrl(migrationId: string, artifact: string): Promise<string> {
  const { data } = await apiClient.get(`/migrations/${migrationId}/download/${artifact}`);
  return data.url;
}

export interface ArtifactContent {
  artifact: string;
  filename: string;
  content: string;
}

export async function getArtifactContent(
  migrationId: string,
  artifact: string
): Promise<ArtifactContent> {
  const { data } = await apiClient.get(
    `/migrations/${migrationId}/artifact/${artifact}`
  );
  return data;
}
