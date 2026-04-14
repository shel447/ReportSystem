# Dynamic Parameter Source Interface Design (Draft)

## 1. Background

Current dynamic parameter options are resolved by local demo mapping (`source -> table/column`) and returned as plain string lists.

Current gaps:

- No formal external source request contract.
- No unified request/response schema for platform-to-source calls.
- No explicit limits (count, body size, timeout).
- No standardized error semantics for dynamic option fetch failures.

## 2. Goals

- Define a stable v1 protocol for dynamic parameter option fetch.
- Keep frontend only calling platform APIs; platform proxies external sources.
- Standardize method, request body, response body, and limits.
- Keep failures non-blocking for chat flow (empty options + retry hint).

## 3. API Contract (Frontend -> Platform)

### 3.1 Endpoint

- Method: `POST`
- Path: `/rest/chatbi/v1/parameter-options/resolve`

### 3.2 Request Body

```json
{
  "template_id": "tpl_xxx",
  "param_id": "device_scope",
  "source": "api:/devices/list",
  "query": "华东",
  "selected_params": {
    "region": "east"
  },
  "limit": 10
}
```

Field rules:

- `template_id`: optional but recommended for audit and routing.
- `param_id`: required.
- `source`: required source identifier in template parameter.
- `query`: optional keyword for fuzzy option search.
- `selected_params`: optional resolved parameters used as source context.
- `limit`: optional, default `10`, max `50`.

### 3.3 Response Body

```json
{
  "items": [
    { "label": "华东一大区", "value": "EAST_1", "query": "EAST_1" },
    { "label": "华东二大区", "value": "EAST_2", "query": ["E2A", "E2B"] }
  ],
  "meta": {
    "source": "api:/devices/list",
    "limit": 10,
    "returned": 2,
    "has_more": false,
    "truncated": false
  }
}
```

## 4. API Contract (Platform -> External Source)

### 4.1 Method and Body

- Method: `POST` (uniform for v1)

```json
{
  "request_id": "req_xxx",
  "source": "api:/devices/list",
  "query": "华东",
  "context": {
    "template_id": "tpl_xxx",
    "param_id": "device_scope",
    "selected_params": {
      "region": "east"
    }
  },
  "limit": 10
}
```

### 4.2 External Response

```json
{
  "items": [
    { "label": "华东一大区", "value": "EAST_1", "query": "EAST_1" }
  ],
  "total": 1,
  "has_more": false
}
```

Normalization rules:

- Platform accepts only `items[].label/value/query`.
- `value` supports scalar only in v1 (`string | number | boolean`).
- `query` supports scalar or scalar array in v1 (`scalar | scalar[]`).
- Platform truncates to internal max limit.

## 5. Limits and Runtime Spec

- Default `limit`: `10`
- Max `limit`: `50`
- Request body max size: `32 KB`
- Response item max count: `50`
- Item field length:
  - `label <= 64`
  - `value <= 128` (after string conversion for validation)
  - `query <= 128` for scalar; arrays should keep each element within the same limit
- Upstream timeout: `3s`
- Retry: none in v1

## 6. Failure Handling and Error Semantics

Failure policy for chat flow:

- Return empty `items` and attach retryable error info.
- Do not hard-break current report conversation turn.

Suggested error codes:

- `PARAM_SOURCE_INVALID`
- `PARAM_SOURCE_TIMEOUT`
- `PARAM_SOURCE_UPSTREAM_ERROR`
- `PARAM_SOURCE_RESPONSE_INVALID`
- `PARAM_SOURCE_LIMIT_EXCEEDED`

## 7. Compatibility

- Keep existing template field: `TemplateParameter.source`.
- Keep existing UI action payload compatibility:
  - Existing: `param.options: string[]`
  - Target: `param.choices: [{label,value,query}]`
- Transitional rule:
  - If `choices` exists, UI renders by `choices`.
  - Else fallback to `options`.

## 8. Scope Boundary

Included in this draft:

- Protocol and limits.
- Response normalization rules.
- Error semantics baseline.

Not included in this draft:

- Provider registry management UI.
- Cache/TTL strategy.
- Auth signature specification per external provider.
