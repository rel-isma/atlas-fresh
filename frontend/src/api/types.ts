export type ClientMode = "EXACT" | "MINIMUM";
export type ClientStatus = "COMPLETE" | "PARTIAL" | "UNSERVED";
export type ClientReason =
  "STATION_CAPACITY_REACHED" | "INSUFFICIENT_COMPATIBLE_SEGMENT" | null;

export interface PlanKpis {
  expectedPlanT: number;
  actualReceivedT: number;
  stationCapacityT: number;
  actualBySegment: { A: number; B: number; C: number; D: number };
  exportT: number;
  exportRate: number | null;
  stationUtilization: number | null;
  localVolumeT: number;
  exportRevenueEur: number;
  localValueEur: number;
  totalValueEur: number;
  atRiskCount: number;
}

export interface PlanData {
  dataHealth: "healthy";
  kpis: PlanKpis;
  narrative: { overview: string; localResidual: string };
  segmentVariances: Array<{
    segment: string;
    expectedT: number;
    actualT: number;
    varianceT: number;
  }>;
  farmSegmentBalances: Array<{
    farmId: string;
    segment: string;
    actualT: number;
    exportedT: number;
    localT: number;
    expectedT: number;
    varianceT: number;
  }>;
  clientResults: Array<{
    clientId: string;
    name: string;
    mode: ClientMode;
    requestedSegment: string;
    priceEur: number;
    demandT: number;
    allocatedT: number;
    remainingT: number;
    status: ClientStatus;
    reason: ClientReason;
    revenueEur: number;
  }>;
  allocations: Array<{
    farmId: string;
    segment: string;
    clientId: string;
    tonnes: number;
    qualityUpgrade: number;
    unitPriceEur: number;
    revenueEur: number;
  }>;
  localResidual: Array<{
    farmId: string;
    segment: string;
    tonnesT: number;
    referencePriceEur: number;
    localPriceEur: number;
    localValueEur: number;
  }>;
}

export interface ValidationError {
  sheet: string;
  id: string | null;
  field: string | null;
  message: string;
}
export interface InvalidPlanResponse {
  dataHealth: "invalid";
  validationErrors: ValidationError[];
}
export type AssistantQuestion =
  "at_risk_clients" | "farm_gaps" | "local_residual";
export type AssistantRequest =
  { question: AssistantQuestion } | { freeText: string };
export type AssistantResponse =
  | {
      available: true;
      answer: string;
      citedIds: string[];
      source: "llm" | "fallback";
    }
  | {
      available: false;
      reason: string;
      source: "fallback";
      fallbackAnswer?: string;
    };
