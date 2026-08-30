import json
import time
from typing import Any, AsyncGenerator
from uuid import UUID

import httpx

from app.core.database import AsyncSessionLocal
from app.models.execution_log import ExecutionLog
from app.models.provider import Provider
from app.models.provider_model import ProviderModel
from app.repositories.execution_log_repository import ExecutionLogRepository
from app.repositories.provider_model_repository import ProviderModelRepository
from app.repositories.provider_repository import ProviderRepository


class LLMGatewayError(Exception):
    pass


class ProviderNotFoundError(LLMGatewayError):
    pass


class ModelNotFoundError(LLMGatewayError):
    pass


class ProviderExecutionError(LLMGatewayError):
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        self.message = message
        super().__init__(f"Provider returned error {status_code}: {message}")


class LLMGatewayService:
    def __init__(
        self,
        provider_repo: ProviderRepository,
        model_repo: ProviderModelRepository,
        execution_log_repo: ExecutionLogRepository,
        http_client: httpx.AsyncClient | None = None,
    ):
        self._provider_repo = provider_repo
        self._model_repo = model_repo
        self._execution_log_repo = execution_log_repo
        self._http_client = http_client

    async def _save_log_safely(self, log: ExecutionLog) -> None:
        """Save an ExecutionLog safely using a fresh DB session or fallback repository."""
        try:
            async with AsyncSessionLocal() as session:
                repo = ExecutionLogRepository(session)
                await repo.create(log)
        except Exception:
            # Fallback to injected repository (e.g. for mock repositories in tests)
            try:
                await self._execution_log_repo.create(log)
            except Exception:
                pass

    async def resolve_provider_and_model(
        self, organization_id: UUID, model_identifier: str
    ) -> tuple[Provider, ProviderModel | None]:
        """
        Resolve an active provider and model for the organization.
        Returns (Provider, ProviderModel | None).
        Raises ProviderNotFoundError or ModelNotFoundError if unavailable or inactive.
        """
        providers = await self._provider_repo.list_by_organization(organization_id)
        active_providers = [p for p in providers if p.is_active]

        if not active_providers:
            raise ProviderNotFoundError("No active provider found for this organization.")

        # Check ProviderModel records across active providers
        for provider in active_providers:
            model_record = await self._model_repo.get_duplicate(provider.id, model_identifier)
            if model_record and model_record.is_active:
                return provider, model_record

        # Check fallback match on provider's default_model
        for provider in active_providers:
            if provider.default_model == model_identifier:
                return provider, None

        raise ModelNotFoundError(
            f"Model '{model_identifier}' is not configured or active for this organization."
        )

    def _get_provider_base_url(self, provider: Provider) -> str:
        """Resolve the base URL for the provider API requests."""
        if provider.base_url:
            return provider.base_url.rstrip("/")

        # Defaults for known provider types
        defaults = {
            "openai": "https://api.openai.com/v1",
            "anthropic": "https://api.anthropic.com/v1",
            "gemini": "https://generativelanguage.googleapis.com/v1beta",
            "groq": "https://api.groq.com/openai/v1",
            "openrouter": "https://openrouter.ai/api/v1",
            "azure_openai": "https://api.openai.com/v1",
            "ollama": "http://localhost:11434/v1",
            "lmstudio": "http://localhost:1234/v1",
        }
        pt_str = getattr(provider.provider_type, "value", str(provider.provider_type))
        return defaults.get(pt_str, "https://api.openai.com/v1")

    async def execute_chat_completion(
        self,
        organization_id: UUID,
        api_key_id: UUID | None,
        model_identifier: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream: bool = False,
    ) -> tuple[dict[str, Any], ExecutionLog]:
        """
        Execute a non-streaming chat completion request through the resolved provider and log the execution.
        """
        if stream:
            raise LLMGatewayError("Use stream_chat_completion for streaming requests.")

        start_time = time.perf_counter()
        provider = None
        model_record = None
        status_code = 500
        error_message = None
        prompt_tokens = None
        completion_tokens = None
        total_tokens = None
        response_json: dict[str, Any] = {}

        try:
            provider, model_record = await self.resolve_provider_and_model(
                organization_id, model_identifier
            )

            base_url = self._get_provider_base_url(provider)
            endpoint_url = f"{base_url}/chat/completions"

            headers = {
                "Authorization": f"Bearer {provider.api_key}",
                "Content-Type": "application/json",
            }

            payload: dict[str, Any] = {
                "model": model_identifier,
                "messages": messages,
            }
            if temperature is not None:
                payload["temperature"] = temperature
            if max_tokens is not None:
                payload["max_tokens"] = max_tokens

            client = self._http_client or httpx.AsyncClient(timeout=60.0)
            close_client = self._http_client is None

            try:
                response = await client.post(endpoint_url, json=payload, headers=headers)
                status_code = response.status_code

                if response.status_code >= 400:
                    error_message = response.text
                    raise ProviderExecutionError(response.status_code, response.text)

                response_json = response.json()
                usage = response_json.get("usage", {})
                prompt_tokens = usage.get("prompt_tokens")
                completion_tokens = usage.get("completion_tokens")
                total_tokens = usage.get("total_tokens")

            finally:
                if close_client:
                    await client.aclose()

        except LLMGatewayError as e:
            if not isinstance(e, ProviderExecutionError):
                status_code = 404 if isinstance(e, (ProviderNotFoundError, ModelNotFoundError)) else 400
                error_message = str(e)
            raise e

        except Exception as e:
            status_code = 500
            error_message = str(e)
            raise ProviderExecutionError(500, str(e)) from e

        finally:
            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)

            execution_log = ExecutionLog(
                organization_id=organization_id,
                api_key_id=api_key_id,
                provider_id=provider.id if provider else None,
                model_id=model_record.id if model_record else None,
                model_name=model_identifier,
                status_code=status_code,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                latency_ms=latency_ms,
                error_message=error_message,
            )

            await self._save_log_safely(execution_log)

        return response_json, execution_log

    async def stream_chat_completion(
        self,
        organization_id: UUID,
        api_key_id: UUID | None,
        model_identifier: str,
        messages: list[dict[str, Any]],
        temperature: float | None = None,
        max_tokens: int | None = None,
        stream_options: dict[str, Any] | None = None,
    ) -> AsyncGenerator[str, None]:
        """
        Stream a chat completion request through the resolved provider and log the execution upon completion or failure.
        """
        start_time = time.perf_counter()
        provider, model_record = await self.resolve_provider_and_model(
            organization_id, model_identifier
        )

        base_url = self._get_provider_base_url(provider)
        endpoint_url = f"{base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {provider.api_key}",
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {
            "model": model_identifier,
            "messages": messages,
            "stream": True,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens
        if stream_options is not None:
            payload["stream_options"] = stream_options
        else:
            payload["stream_options"] = {"include_usage": True}

        client = self._http_client or httpx.AsyncClient(timeout=60.0)
        close_client = self._http_client is None

        # Step 1: Open the HTTP stream and check for initial provider error before yielding chunks
        req_context = client.stream("POST", endpoint_url, json=payload, headers=headers)
        response = await req_context.__aenter__()

        if response.status_code >= 400:
            error_bytes = await response.aread()
            error_text = error_bytes.decode("utf-8", errors="replace")
            await req_context.__aexit__(None, None, None)
            if close_client:
                await client.aclose()

            end_time = time.perf_counter()
            latency_ms = int((end_time - start_time) * 1000)

            execution_log = ExecutionLog(
                organization_id=organization_id,
                api_key_id=api_key_id,
                provider_id=provider.id,
                model_id=model_record.id if model_record else None,
                model_name=model_identifier,
                status_code=response.status_code,
                latency_ms=latency_ms,
                error_message=error_text,
            )
            await self._save_log_safely(execution_log)
            raise ProviderExecutionError(response.status_code, error_text)

        # Step 2: Generator yielding SSE chunks and recording execution log in finally block
        async def sse_generator() -> AsyncGenerator[str, None]:
            status_code = response.status_code
            error_message = None
            prompt_tokens = None
            completion_tokens = None
            total_tokens = None

            try:
                async for line in response.aiter_lines():
                    if not line:
                        continue
                    yield f"{line}\n\n"

                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk_json = json.loads(line[6:])
                            usage = chunk_json.get("usage")
                            if usage:
                                prompt_tokens = usage.get("prompt_tokens")
                                completion_tokens = usage.get("completion_tokens")
                                total_tokens = usage.get("total_tokens")
                        except Exception:
                            pass

            except BaseException as e:
                status_code = 500
                error_message = str(e) or e.__class__.__name__
                raise e
            finally:
                await req_context.__aexit__(None, None, None)
                if close_client:
                    await client.aclose()

                end_time = time.perf_counter()
                latency_ms = int((end_time - start_time) * 1000)

                execution_log = ExecutionLog(
                    organization_id=organization_id,
                    api_key_id=api_key_id,
                    provider_id=provider.id,
                    model_id=model_record.id if model_record else None,
                    model_name=model_identifier,
                    status_code=status_code,
                    prompt_tokens=prompt_tokens,
                    completion_tokens=completion_tokens,
                    total_tokens=total_tokens,
                    latency_ms=latency_ms,
                    error_message=error_message,
                )
                await self._save_log_safely(execution_log)

        return sse_generator()
