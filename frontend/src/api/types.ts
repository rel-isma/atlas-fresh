export type ClientMode = "EXACT" | "MINIMUM";
export type Segment = "A" | "B" | "C" | "D";
export type ClientStatus = "COMPLETE" | "PARTIAL" | "UNSERVED";
export type ClientReason =
  "STATION_CAPACITY_REACHED" | "INSUFFICIENT_COMPATIBLE_SEGMENT" | null;
export type VarianceDirection = "BELOW" | "ON_PLAN" | "ABOVE";

export interface PlanKpis {
  expectedPlanT: number;
  actualReceivedT: number;
  stationCapacityT: number;
  localMarketRatio: number;
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

export interface ClientStatusSummary {
  clientCount: number;
  completeCount: number;
  partialCount: number;
  unservedCount: number;
  completePct: number;
  partialPct: number;
  unservedPct: number;
  partialEndPct: number;
}

export interface PlanData {
  dataHealth: "healthy";
  kpis: PlanKpis;
  clientStatusSummary: ClientStatusSummary;
  narrative: { overview: string; localResidual: string };
  segmentVariances: Array<{
    segment: Segment;
    expectedT: number;
    actualT: number;
    varianceT: number;
  }>;
  farmSegmentBalances: Array<{
    farmId: string;
    segment: Segment;
    actualT: number;
    exportedT: number;
    localT: number;
    expectedT: number;
    varianceT: number;
    varianceDirection: VarianceDirection;
  }>;
  farmSummaries: Array<{
    farmId: string;
    expectedT: number;
    actualT: number;
    localT: number;
    varianceT: number;
    belowPlan: boolean;
  }>;
  clientResults: Array<{
    clientId: string;
    name: string;
    mode: ClientMode;
    requestedSegment: Segment;
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
    segment: Segment;
    clientId: string;
    tonnes: number;
    qualityUpgrade: number;
    unitPriceEur: number;
    revenueEur: number;
  }>;
  localResidual: Array<{
    farmId: string;
    segment: Segment;
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
  | { question: AssistantQuestion; freeText?: never }
  | { freeText: string; question?: never };
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
      fallbackAnswer: string | null;
    };
