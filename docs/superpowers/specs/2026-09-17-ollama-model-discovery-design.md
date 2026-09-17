# Ollama Model Discovery Design

## Goal

Remove the need to type an Ollama model name while retaining explicit model selection when several installed models are available.

## User Experience

When the user selects Ollama, the app queries the configured endpoint and displays installed models in a dropdown. The configured `OLLAMA_MODEL` is selected when it is installed; otherwise, the first returned model is selected. A refresh control repeats discovery after an endpoint or local model change.

If the endpoint is unavailable or has no installed models, the app displays a concise warning and exposes a manual model field. Deterministic comparison remains available in every state.

## Architecture

Model discovery belongs to the Ollama adapter and uses `GET /api/tags`. It returns model names as a plain list and raises a provider-safe error when discovery fails. The Streamlit sidebar consumes that provider-neutral result to render the dropdown or fallback field. Comparison and semantic-matching services remain unchanged.

Streamlit caches discovery briefly by endpoint. The refresh control clears that cached result before rerunning the app.

## Selection Rules

1. Use `OLLAMA_MODEL` if it appears in the discovered list.
2. Otherwise use the first discovered model in Ollama's response order.
3. Never silently submit an arbitrary model when discovery returned no models.
4. Manual fallback is available only when automatic discovery cannot provide a selection.

## Error Handling

- Unreachable or invalid endpoint: show that discovery failed and allow manual entry.
- Empty model list: tell the user to install a model and allow manual entry.
- Malformed `/api/tags` response: treat it as discovery failure without exposing an internal traceback.
- A model removed after discovery: the existing connection test reports it as unavailable.

## Testing

- Adapter tests cover multiple models, an empty response, and malformed/unavailable endpoints.
- Sidebar tests verify automatic selection and ensure deterministic mode remains usable.
- The complete test suite and a real local Ollama smoke test verify the integration.
