import { chatbiPath, postJson } from "../../shared/api/http";
import type { TrioValue } from "../chat/types";

export type ParameterOptionsResolveRequest = {
  parameterId: string;
  openSource: {
    url: string;
  };
  contextValues: Record<string, TrioValue[]>;
};

export type ParameterOptionsResolveResponse = {
  options: TrioValue[];
  defaultValue: TrioValue[];
};

export function resolveParameterOptions(payload: ParameterOptionsResolveRequest) {
  return postJson<ParameterOptionsResolveResponse>(chatbiPath("/parameter-options/resolve"), payload);
}
