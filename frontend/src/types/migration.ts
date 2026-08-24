export type MigrationStatus =
  | 'PENDING'
  | 'PARSING'
  | 'ANALYZING'
  | 'GENERATING'
  | 'VALIDATING'
  | 'COMPLETE'
  | 'FAILED'
  | 'NEEDS_REVIEW';

export type SourcePlatform = 'kong' | 'apigee' | 'ibm';
export type TargetApiType = 'REST' | 'HTTP';
export type MappingType = 'direct' | 'lambda' | 'alternative' | 'gap';

export interface Migration {
  migration_id: string;
  source_type: SourcePlatform;
  status: MigrationStatus;
  created_at: string;
  updated_at: string;
  file_name: string;
  confidence_score?: number;
  target_api_type?: TargetApiType;
  summary?: MigrationSummary;
  error_message?: string;
}

export interface MigrationSummary {
  direct_count: number;
  lambda_count: number;
  alternative_count: number;
  gap_count: number;
  estimated_effort_hours: number;
}

export interface FeatureMapping {
  source_feature: string;
  source_plugin_name: string;
  aws_equivalent: string;
  mapping_type: MappingType;
  implementation_notes: string;
}

export interface GapItem {
  source_feature: string;
  source_plugin_name: string;
  category: string;
  severity: 'low' | 'medium' | 'high' | 'critical';
  recommendation: string;
  effort_estimate_hours: number;
}

export interface CoverageResult {
  total: number;
  covered: number;
  percentage: number;
  details: string[];
}

export type LintLevel = 'error' | 'warning' | 'informational';

export interface TemplateLintFinding {
  id: string;
  level: LintLevel;
  message: string;
  line?: number | null;
}

export interface TemplateLintResult {
  status: 'pass' | 'fail' | 'skipped';
  reason?: string;
  counts: { error: number; warning: number; informational: number };
  findings: TemplateLintFinding[];
  truncated?: boolean;
}

export interface ValidationReport {
  migration_id: string;
  confidence_score: number;
  target_api_type: TargetApiType;
  target_api_type_reasoning: string;
  route_coverage: CoverageResult;
  auth_coverage: CoverageResult;
  plugin_coverage: CoverageResult;
  feature_mappings: FeatureMapping[];
  gaps: GapItem[];
  warnings: string[];
  summary: MigrationSummary;
  template_lint?: TemplateLintResult;
}
