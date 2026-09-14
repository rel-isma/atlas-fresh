import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { getPlan } from "../api/client";
import type { PlanData, ValidationError } from "../api/types";

type PlanState = {
  status: "loading" | "error" | "invalid" | "ready";
  data: PlanData | null;
  validationErrors: ValidationError[];
  refetch: () => Promise<void>;
};
const PlanContext = createContext<PlanState | null>(null);

export function PlanProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<PlanState["status"]>("loading");
  const [data, setData] = useState<PlanData | null>(null);
  const [validationErrors, setValidationErrors] = useState<ValidationError[]>(
    [],
  );
  const refetch = useCallback(async () => {
    setStatus("loading");
    setValidationErrors([]);
    try {
      const response = await getPlan();
      if (response.dataHealth === "invalid") {
        setData(null);
        setValidationErrors(response.validationErrors);
        setStatus("invalid");
      } else {
        setData(response);
        setStatus("ready");
      }
    } catch {
      setData(null);
      setStatus("error");
    }
  }, []);
  useEffect(() => {
    void refetch();
  }, [refetch]);
  return (
    <PlanContext.Provider value={{ status, data, validationErrors, refetch }}>
      {children}
    </PlanContext.Provider>
  );
}
export function usePlan() {
  const value = useContext(PlanContext);
  if (!value) throw new Error("usePlan must be used within PlanProvider");
  return value;
}
