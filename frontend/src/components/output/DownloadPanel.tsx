import { useState } from 'react';
import { Download, FileText, Code, ClipboardList, Eye, Loader2 } from 'lucide-react';
import { getArtifactContent } from '../../api/migrations';
import { ArtifactViewer } from './ArtifactViewer';

interface DownloadPanelProps {
  migrationId: string;
}

const ARTIFACTS = [
  { key: 'template', label: 'SAM Template', icon: FileText, description: 'template.yaml' },
  { key: 'openapi', label: 'OpenAPI Spec', icon: FileText, description: 'openapi.yaml' },
  { key: 'report', label: 'Validation Report', icon: ClipboardList, description: 'validation-report.json' },
  { key: 'cfn-lint', label: 'Template Lint', icon: ClipboardList, description: 'cfn-lint.json' },
  { key: 'migration-report', label: 'Migration Report', icon: FileText, description: 'migration-report.md' },
  { key: 'authorizer', label: 'Lambda Authorizer', icon: Code, description: 'authorizer/index.py' },
];

function triggerDownload(filename: string, content: string) {
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}

export function DownloadPanel({ migrationId }: DownloadPanelProps) {
  const [viewing, setViewing] = useState<{ key: string; label: string } | null>(null);
  const [downloading, setDownloading] = useState<string | null>(null);

  const handleDownload = async (artifact: string) => {
    setDownloading(artifact);
    try {
      const { filename, content } = await getArtifactContent(migrationId, artifact);
      triggerDownload(filename, content);
    } catch {
      // Artifact may not exist (e.g., no Lambda authorizer for this migration).
    } finally {
      setDownloading(null);
    }
  };

  return (
    <div className="space-y-2">
      <h4 className="text-sm font-medium text-gray-900">Artifacts</h4>
      <p className="text-xs text-gray-500">Click an artifact to preview it, or download directly.</p>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
        {ARTIFACTS.map((artifact) => {
          const Icon = artifact.icon;
          return (
            <div
              key={artifact.key}
              className="flex items-center gap-3 rounded-lg border border-gray-200 p-3 transition hover:border-blue-300"
            >
              <button
                onClick={() => setViewing({ key: artifact.key, label: artifact.label })}
                className="flex min-w-0 flex-1 items-center gap-3 text-left"
                title="Preview"
              >
                <Icon className="h-5 w-5 shrink-0 text-gray-400" />
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-gray-900">{artifact.label}</p>
                  <p className="truncate text-xs text-gray-500">{artifact.description}</p>
                </div>
                <Eye className="h-4 w-4 shrink-0 text-gray-300" />
              </button>
              <button
                onClick={() => handleDownload(artifact.key)}
                disabled={downloading === artifact.key}
                aria-label={`Download ${artifact.label}`}
                title="Download"
                className="shrink-0 rounded-lg p-2 text-gray-400 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-50"
              >
                {downloading === artifact.key ? (
                  <Loader2 className="h-4 w-4 animate-spin" />
                ) : (
                  <Download className="h-4 w-4" />
                )}
              </button>
            </div>
          );
        })}
      </div>

      {viewing && (
        <ArtifactViewer
          migrationId={migrationId}
          artifact={viewing.key}
          label={viewing.label}
          onClose={() => setViewing(null)}
        />
      )}
    </div>
  );
}
