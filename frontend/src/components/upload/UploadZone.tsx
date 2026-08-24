import { useCallback, useState } from 'react';
import { useDropzone } from 'react-dropzone';
import { Upload, AlertCircle, FileText } from 'lucide-react';
import * as yaml from 'js-yaml';

interface KongConfig {
  _format_version?: string;
  services?: Array<{
    name?: string;
    routes?: unknown[];
    plugins?: unknown[];
  }>;
}

interface UploadZoneProps {
  onFileAccepted: (file: File, parsed: KongConfig) => void;
}

export function UploadZone({ onFileAccepted }: UploadZoneProps) {
  const [error, setError] = useState<string | null>(null);

  const onDrop = useCallback(
    (acceptedFiles: File[]) => {
      setError(null);
      const file = acceptedFiles[0];
      if (!file) return;

      if (!file.name.endsWith('.yaml') && !file.name.endsWith('.yml')) {
        setError('Please upload a YAML file (.yaml or .yml)');
        return;
      }

      if (file.size > 5 * 1024 * 1024) {
        setError('File size must be under 5MB');
        return;
      }

      const reader = new FileReader();
      reader.onload = (e) => {
        try {
          const content = e.target?.result as string;
          const parsed = yaml.load(content) as KongConfig;

          if (!parsed || typeof parsed !== 'object' || !parsed._format_version) {
            setError(
              'This does not appear to be a valid Kong declarative config (missing _format_version)'
            );
            return;
          }

          onFileAccepted(file, parsed);
        } catch {
          setError('Invalid YAML syntax. Please check your file.');
        }
      };
      reader.readAsText(file);
    },
    [onFileAccepted]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'text/yaml': ['.yaml', '.yml'] },
    maxFiles: 1,
  });

  return (
    <div
      {...getRootProps()}
      className={`cursor-pointer rounded-xl border-2 border-dashed p-12 text-center transition-colors duration-200 ${
        isDragActive
          ? 'border-blue-500 bg-blue-50'
          : 'border-gray-300 hover:border-blue-400 hover:bg-gray-50'
      }`}
    >
      <input {...getInputProps()} />
      <Upload className="mx-auto mb-4 h-12 w-12 text-gray-400" />
      <p className="text-lg font-medium text-gray-700">
        {isDragActive ? 'Drop your Kong config here' : 'Drag & drop your Kong YAML config'}
      </p>
      <p className="mt-2 text-sm text-gray-500">
        or click to browse • Supports .yaml and .yml • Max 5MB
      </p>
      {error && (
        <div className="mt-4 flex items-center justify-center gap-2 text-sm text-red-600">
          <AlertCircle className="h-4 w-4" />
          {error}
        </div>
      )}
    </div>
  );
}

interface ConfigPreviewProps {
  file: File;
  config: KongConfig;
  onConfirm: () => void;
  onCancel: () => void;
  isLoading: boolean;
}

export function ConfigPreview({ file, config, onConfirm, onCancel, isLoading }: ConfigPreviewProps) {
  const services = config.services || [];
  const routeCount = services.reduce(
    (acc, s) => acc + (s.routes?.length || 0),
    0
  );
  const pluginCount = services.reduce(
    (acc, s) => acc + (s.plugins?.length || 0),
    0
  );

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-6">
      <div className="flex items-center gap-3 mb-4">
        <FileText className="h-8 w-8 text-blue-600" />
        <div>
          <p className="font-medium text-gray-900">{file.name}</p>
          <p className="text-sm text-gray-500">
            {(file.size / 1024).toFixed(1)} KB • Kong {config._format_version}
          </p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 mb-6">
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{services.length}</p>
          <p className="text-xs text-gray-500">Services</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{routeCount}</p>
          <p className="text-xs text-gray-500">Routes</p>
        </div>
        <div className="rounded-lg bg-gray-50 p-3 text-center">
          <p className="text-2xl font-bold text-gray-900">{pluginCount}</p>
          <p className="text-xs text-gray-500">Plugins</p>
        </div>
      </div>

      <div className="flex gap-3">
        <button
          onClick={onConfirm}
          disabled={isLoading}
          className="flex-1 rounded-lg bg-blue-600 px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
        >
          {isLoading ? 'Starting Migration...' : 'Start Migration'}
        </button>
        <button
          onClick={onCancel}
          disabled={isLoading}
          className="rounded-lg border border-gray-300 px-4 py-2.5 text-sm font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          Cancel
        </button>
      </div>
    </div>
  );
}
