import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { UploadZone, ConfigPreview } from '../components/upload/UploadZone';
import { getPresignedUploadUrl, uploadToS3 } from '../api/uploads';
import { createMigration } from '../api/migrations';

interface KongConfig {
  _format_version?: string;
  services?: Array<{
    name?: string;
    routes?: unknown[];
    plugins?: unknown[];
  }>;
}

export function MigratePage() {
  const navigate = useNavigate();
  const [file, setFile] = useState<File | null>(null);
  const [config, setConfig] = useState<KongConfig | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleFileAccepted = (acceptedFile: File, parsedConfig: KongConfig) => {
    setFile(acceptedFile);
    setConfig(parsedConfig);
    setError(null);
  };

  const handleConfirm = async () => {
    if (!file) return;

    setIsLoading(true);
    setError(null);

    try {
      // 1. Get presigned upload URL
      const { uploadUrl, s3Key } = await getPresignedUploadUrl(file.name);

      // 2. Upload file to S3
      await uploadToS3(uploadUrl, file);

      // 3. Create migration
      const { migrationId } = await createMigration({
        sourceType: 'kong',
        configS3Key: s3Key,
        fileName: file.name,
      });

      // 4. Navigate to migration detail page
      navigate(`/migrations/${migrationId}`);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to start migration';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCancel = () => {
    setFile(null);
    setConfig(null);
    setError(null);
  };

  return (
    <div className="mx-auto max-w-2xl">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-gray-900">New Migration</h1>
        <p className="mt-1 text-sm text-gray-500">
          Upload your Kong declarative YAML to migrate to Amazon API Gateway
        </p>
      </div>

      {/* Source Platform Indicator */}
      <div className="mb-4 flex items-center gap-2 rounded-lg bg-gray-50 p-3">
        <span className="text-sm font-medium text-gray-700">Source Platform:</span>
        <span className="inline-flex items-center rounded-full bg-blue-100 px-2.5 py-0.5 text-xs font-medium text-blue-700">
          Kong Gateway
        </span>
        <span className="text-xs text-gray-400">(more platforms coming soon)</span>
      </div>

      {!file ? (
        <UploadZone onFileAccepted={handleFileAccepted} />
      ) : (
        <ConfigPreview
          file={file}
          config={config!}
          onConfirm={handleConfirm}
          onCancel={handleCancel}
          isLoading={isLoading}
        />
      )}

      {error && (
        <div className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      )}
    </div>
  );
}
