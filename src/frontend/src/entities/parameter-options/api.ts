import { chatbiPath, postJson } from "../../shared/api/http";
import type { ParameterValue } from "../chat/types";

export type ParameterOptionsResolveRequest = {
  parameterId: string;
  source: string;
  contextValues: Record<string, ParameterValue[]>;
};

export type ParameterOptionsResolveResponse = {
  options: ParameterValue[];
  defaultValue: ParameterValue[];
};

export function resolveParameterOptions(payload: ParameterOptionsResolveRequest) {
  return postJson<ParameterOptionsResolveResponse>(chatbiPath("/parameter-options/resolve"), payload);
}
