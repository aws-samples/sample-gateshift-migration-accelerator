import { useEffect, useState } from 'react';
import Editor from '@monaco-editor/react';
import { X, Download, Copy, Check, Loader2 } from 'lucide-react';
import { getArtifactContent } from '../../api/migrations';
import type { ArtifactContent } from '../../api/migrations';

interface ArtifactViewerProps {
    migrationId: string;
    artifact: string;
    label: string;
    onClose: () => void;
}

function languageFor(filename: string): string {
    if (filename.endsWith('.yaml') || filename.endsWith('.yml')) return 'yaml';
    if (filename.endsWith('.json')) return 'json';
    if (filename.endsWith('.py')) return 'python';
    if (filename.endsWith('.md')) return 'markdown';
    return 'plaintext';
}

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

export function ArtifactViewer({ migrationId, artifact, label, onClose }: ArtifactViewerProps) {
    const [data, setData] = useState<ArtifactContent | null>(null);
    const [error, setError] = useState<string | null>(null);
    const [copied, setCopied] = useState(false);

    useEffect(() => {
        let active = true;
        setData(null);
        setError(null);
        getArtifactContent(migrationId, artifact)
            .then((res) => {
                if (active) setData(res);
            })
            .catch((err) => {
                if (active) {
                    const status = err?.response?.status;
                    setError(
                        status === 404
                            ? 'This artifact was not generated for this migration.'
                            : 'Could not load this artifact.'
                    );
                }
            });
        return () => {
            active = false;
        };
    }, [migrationId, artifact]);

    // Close on Escape.
    useEffect(() => {
        const onKey = (e: KeyboardEvent) => {
            if (e.key === 'Escape') onClose();
        };
        window.addEventListener('keydown', onKey);
        return () => window.removeEventListener('keydown', onKey);
    }, [onClose]);

    const handleCopy = async () => {
        if (!data) return;
        await navigator.clipboard.writeText(data.content);
        setCopied(true);
        setTimeout(() => setCopied(false), 1500);
    };

    return (
        <div
            className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
            onClick={onClose}
        >
            <div
                className="flex h-[85vh] w-full max-w-4xl flex-col overflow-hidden rounded-xl bg-white shadow-xl"
                onClick={(e) => e.stopPropagation()}
            >
                {/* Header */}
                <div className="flex items-center justify-between border-b border-gray-200 px-4 py-3">
                    <div>
                        <h3 className="text-sm font-semibold text-gray-900">{label}</h3>
                        {data && <p className="text-xs text-gray-500">{data.filename}</p>}
                    </div>
                    <div className="flex items-center gap-2">
                        <button
                            onClick={handleCopy}
                            disabled={!data}
                            className="flex items-center gap-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50"
                        >
                            {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
                            {copied ? 'Copied' : 'Copy'}
                        </button>
                        <button
                            onClick={() => data && triggerDownload(data.filename, data.content)}
                            disabled={!data}
                            className="flex items-center gap-1 rounded-lg bg-blue-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-blue-700 disabled:opacity-50"
                        >
                            <Download className="h-3.5 w-3.5" />
                            Download
                        </button>
                        <button
                            onClick={onClose}
                            aria-label="Close"
                            className="rounded-lg p-1.5 text-gray-400 hover:bg-gray-100 hover:text-gray-600"
                        >
                            <X className="h-4 w-4" />
                        </button>
                    </div>
                </div>

                {/* Body */}
                <div className="flex-1 overflow-hidden">
                    {error ? (
                        <div className="flex h-full items-center justify-center p-6 text-sm text-gray-500">
                            {error}
                        </div>
                    ) : !data ? (
                        <div className="flex h-full items-center justify-center">
                            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
                        </div>
                    ) : (
                        <Editor
                            height="100%"
                            language={languageFor(data.filename)}
                            value={data.content}
                            options={{
                                readOnly: true,
                                minimap: { enabled: false },
                                fontSize: 13,
                                scrollBeyondLastLine: false,
                                wordWrap: 'on',
                            }}
                        />
                    )}
                </div>
            </div>
        </div>
    );
}
