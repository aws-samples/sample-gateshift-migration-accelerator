import type { TemplateLintResult, LintLevel } from '../../types/migration';
import { CheckCircle2, XCircle, AlertTriangle, Info, MinusCircle } from 'lucide-react';

interface TemplateLintProps {
    result: TemplateLintResult;
}

const LEVEL_STYLES: Record<LintLevel, { row: string; badge: string; Icon: typeof Info }> = {
    error: { row: 'border-red-200 bg-red-50', badge: 'text-red-700', Icon: XCircle },
    warning: { row: 'border-amber-200 bg-amber-50', badge: 'text-amber-700', Icon: AlertTriangle },
    informational: { row: 'border-blue-200 bg-blue-50', badge: 'text-blue-700', Icon: Info },
};

export function TemplateLint({ result }: TemplateLintProps) {
    if (result.status === 'skipped') {
        return (
            <div className="rounded-lg border border-gray-200 bg-gray-50 p-4">
                <div className="flex items-center gap-2">
                    <MinusCircle className="h-4 w-4 text-gray-400" />
                    <p className="text-sm text-gray-600">
                        Template lint was skipped{result.reason ? `: ${result.reason}` : '.'}
                    </p>
                </div>
            </div>
        );
    }

    const { counts } = result;
    const passed = result.status === 'pass';

    return (
        <div className="space-y-3">
            {/* Summary banner */}
            <div
                className={`flex items-center justify-between rounded-lg border p-3 ${passed ? 'border-green-200 bg-green-50' : 'border-red-200 bg-red-50'
                    }`}
            >
                <div className="flex items-center gap-2">
                    {passed ? (
                        <CheckCircle2 className="h-5 w-5 text-green-600" />
                    ) : (
                        <XCircle className="h-5 w-5 text-red-600" />
                    )}
                    <p className={`text-sm font-medium ${passed ? 'text-green-800' : 'text-red-800'}`}>
                        {passed ? 'Template passed cfn-lint' : 'cfn-lint found errors in the template'}
                    </p>
                </div>
                <div className="flex items-center gap-3 text-xs font-medium">
                    <span className="text-red-700">{counts.error} errors</span>
                    <span className="text-amber-700">{counts.warning} warnings</span>
                    <span className="text-blue-700">{counts.informational} info</span>
                </div>
            </div>

            <p className="text-xs text-gray-500">
                Advisory static analysis of the generated SAM template. These findings do not affect the
                confidence score.
            </p>

            {/* Findings */}
            {result.findings.length > 0 && (
                <div className="space-y-2">
                    {result.findings.map((finding, idx) => {
                        const style = LEVEL_STYLES[finding.level] ?? LEVEL_STYLES.error;
                        const Icon = style.Icon;
                        return (
                            <div key={idx} className={`rounded-lg border p-3 ${style.row}`}>
                                <div className="flex items-start gap-2">
                                    <Icon className={`mt-0.5 h-4 w-4 shrink-0 ${style.badge}`} />
                                    <div className="min-w-0">
                                        <p className="text-sm text-gray-800">
                                            <span className={`font-mono font-medium ${style.badge}`}>{finding.id}</span>
                                            {finding.line != null && (
                                                <span className="ml-2 text-xs text-gray-400">line {finding.line}</span>
                                            )}
                                        </p>
                                        <p className="mt-1 text-sm text-gray-700">{finding.message}</p>
                                    </div>
                                </div>
                            </div>
                        );
                    })}
                    {result.truncated && (
                        <p className="text-xs text-gray-400">
                            Showing the first {result.findings.length} findings. Download the cfn-lint artifact for
                            the full list.
                        </p>
                    )}
                </div>
            )}
        </div>
    );
}
