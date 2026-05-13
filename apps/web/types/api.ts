export type WorkforceUser = {
  user_id: string;
  organization_id: string;
  email: string;
  auth_provider: string;
  role: string;
  department_id: number | null;
  employee_id: string | null;
  mfa_enabled: boolean;
};

export type WorkforceSession = {
  session_id: string;
  login_at: string;
  last_active: string;
  refresh_expires_at: string | null;
  revoked_at: string | null;
};

export type WorkforceAuthResponse = {
  access_token: string;
  refresh_token: string;
  token_type: string;
  requires_mfa: boolean;
  user: WorkforceUser;
  session: WorkforceSession;
};

export type HealthPayload = {
  service: string;
  status: string;
  timestamp: string;
  auth_mode: string;
  version: string;
  environment: string;
};

export type EmployeeSearchResult = {
  employee_id: string;
  name: string;
  department: string;
  role: string;
  performance_score: number | null;
  status: string;
  tenure_source: string;
  relevance_score: number;
};

export type EmployeeSearchResponse = {
  query: string;
  backend: string;
  ranking: string;
  suggestion: string | null;
  results: EmployeeSearchResult[];
};

export type EmployeeProfileResponse = {
  employee_profile: {
    id: string;
    name: string;
    email: string;
    role: {
      title: string;
      level: string;
      source: string;
    };
    department: {
      id: number;
      name: string;
      source: string;
    };
    status: {
      value: string;
      source: string;
    };
    tenure: {
      years: number;
      hire_date: string;
      source: string;
    };
    manager: {
      id: string | null;
      name: string | null;
      source: string;
    };
  };
  performance: {
    latest_review: {
      score: number | null;
      period: string | null;
      reviewer_id: string | null;
      created_at: string | null;
      source: string;
    };
    trend: {
      direction: string;
      delta: number;
    };
  };
  ml_predictions:
    | {
        restricted: true;
        reason: string;
      }
    | {
        attrition_risk: PredictionPayload | null;
        performance_forecast: PredictionPayload | null;
        promotion_readiness: PredictionPayload | null;
      };
  join_logic: string[];
  formatted_summary: string;
};

export type PredictionPayload = {
  model: string;
  prediction: number;
  confidence: number;
  prediction_probability: number | null;
  top_features: string[];
  recommended_action: string;
  run_at: string;
  stale: boolean;
  warning: string | null;
  source: string;
};

export type EmployeeUpdateResponse = {
  message: string;
  employee_id: string;
  changed_fields: string[];
  audit_log_written: boolean;
};

export type AttritionReportResponse = {
  executive_summary: string[];
  grouped_by_department: Record<
    string,
    { HIGH: number; MEDIUM: number; LOW: number }
  >;
  high_risk_employees: {
    employee_id: string;
    employee_name: string;
    department: string;
    role: string;
    predicted_attrition_probability: number;
    confidence: number;
    top_features: string[];
    recommended_action: string;
    run_at: string;
    stale: boolean;
    estimated_replacement_cost: number | null;
  }[];
  financial_exposure: {
    replacement_cost_formula: string;
    total_estimated_cost: number;
    source_fields: string[];
  };
  generated_at: string;
};

export type DepartmentHealthResponse = {
  executive_summary: string[];
  department: {
    id: number;
    name: string;
    headcount_target: number | null;
    budget: number | null;
    source: string;
  };
  headcount: {
    active_count: number;
    target: number | null;
    ratio: number | null;
    source: string;
  };
  performance: {
    department_average: number | null;
    company_benchmark: number | null;
    median: number | null;
    std_deviation: number;
    source: string;
  };
  attrition_distribution: {
    HIGH: number;
    MEDIUM: number;
    LOW: number;
  };
  traffic_light_health: {
    score: number;
    label: string;
    indicator: string;
    reasons: string[];
  };
  generated_at: string;
};

export type AuditLogResponse = {
  audit_logs: {
    id: number;
    action: string;
    target_entity: string;
    target_id: string;
    timestamp: string;
    metadata: Record<string, unknown>;
    request_id: string;
  }[];
  limit: number;
};

export type ComplianceListResponse = {
  requests: ComplianceRequest[];
  limit: number;
};

export type ComplianceRequest = {
  id: number;
  organization_id: string;
  request_type: string;
  subject_employee_id: string;
  requested_by: string;
  status: string;
  created_at: string;
  completed_at: string | null;
};

export type ComplianceCreateResponse = ComplianceRequest & {
  export?: {
    employee: Record<string, unknown>;
    performance_reviews: Record<string, unknown>[];
    ml_predictions: Record<string, unknown>[];
    audit_logs: Record<string, unknown>[];
  };
};

export type FrontendSessionPayload = {
  authenticated: boolean;
  user: WorkforceUser | null;
  session: WorkforceSession | null;
};
