"""
LLM Provider Interface and Implementations.

This module provides a unified interface for different LLM providers
(OpenAI, Anthropic, etc.) to be used with the AI Coding Agent.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass


@dataclass
class LLMResponse:
    """Response from LLM provider."""
    content: str
    tokens_used: int
    model: str
    finish_reason: str = "stop"


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    @abstractmethod
    def chat(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """
        Send a chat completion request.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Response text from the LLM
        """
        pass
    
    @abstractmethod
    def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """
        Send a completion request.
        
        Args:
            prompt: The prompt to send
            max_tokens: Maximum tokens in response
            **kwargs: Additional provider-specific parameters
            
        Returns:
            Completion text from the LLM
        """
        pass
    
    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for text.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4


class OpenAIProvider(LLMProvider):
    """OpenAI LLM provider implementation."""
    
    def __init__(self, api_key: str, model: str = "gpt-4", **kwargs):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
            model: Model to use (gpt-4, gpt-3.5-turbo, etc.)
            **kwargs: Additional configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of OpenAI client."""
        if self._client is None:
            try:
                import openai
                openai.api_key = self.api_key
                self._client = openai
            except ImportError:
                raise ImportError("openai package not installed. Install with: pip install openai")
        return self._client
    
    def chat(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Send chat completion request to OpenAI."""
        client = self._get_client()
        
        try:
            response = client.ChatCompletion.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a helpful coding assistant."},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=kwargs.get("temperature", 0.7),
                **{k: v for k, v in kwargs.items() if k != "temperature"}
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"OpenAI API error: {e}")
            return "{}"
    
    def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Send completion request to OpenAI."""
        # For newer models, use chat completion
        return self.chat(prompt, max_tokens, **kwargs)


class AnthropicProvider(LLMProvider):
    """Anthropic (Claude) LLM provider implementation."""
    
    def __init__(self, api_key: str, model: str = "claude-3-sonnet-20240229", **kwargs):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
            model: Model to use (claude-3-opus, claude-3-sonnet, etc.)
            **kwargs: Additional configuration
        """
        self.api_key = api_key
        self.model = model
        self.config = kwargs
        self._client = None
    
    def _get_client(self):
        """Lazy initialization of Anthropic client."""
        if self._client is None:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except ImportError:
                raise ImportError("anthropic package not installed. Install with: pip install anthropic")
        return self._client
    
    def chat(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Send message to Claude."""
        client = self._get_client()
        
        try:
            message = client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=kwargs.get("temperature", 0.7)
            )
            return message.content[0].text
        except Exception as e:
            print(f"Anthropic API error: {e}")
            return "{}"
    
    def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Send completion request (uses chat for Claude)."""
        return self.chat(prompt, max_tokens, **kwargs)


class MockLLMProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, responses: Optional[Dict[str, str]] = None):
        """
        Initialize mock provider.

        Args:
            responses: Dictionary mapping prompt keywords to responses
        """
        self.responses = responses or {}
        self.call_count = 0

    def chat(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Return mock response."""
        self.call_count += 1

        # Check for keyword matches
        for keyword, response in self.responses.items():
            if keyword.lower() in prompt.lower():
                return response

        # Default mock response
        return '{"result": "mock response"}'

    def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Return mock completion."""
        return self.chat(prompt, max_tokens, **kwargs)


class DeepSeekProvider(LLMProvider):
    """DeepSeek LLM provider implementation."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        **kwargs
    ):
        """
        Initialize DeepSeek provider.

        Args:
            api_key: DeepSeek API key
            base_url: API base URL (default: https://api.deepseek.com)
            model: Model to use (deepseek-chat, deepseek-coder)
            **kwargs: Additional configuration
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.config = kwargs
        self._client = None

    def _get_client(self):
        """Lazy initialization of OpenAI-compatible client for DeepSeek."""
        if self._client is None:
            try:
                import openai
                # DeepSeek API is OpenAI-compatible
                self._client = openai.OpenAI(
                    api_key=self.api_key,
                    base_url=self.base_url
                )
            except ImportError:
                raise ImportError(
                    "openai package not installed. "
                    "Install with: pip install openai"
                )
        return self._client

    def chat(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Send chat completion request to DeepSeek."""
        client = self._get_client()

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a helpful coding assistant."
                    },
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=kwargs.get("temperature", 0.7),
                stream=False
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"DeepSeek API error: {e}")
            return "{}"

    def complete(self, prompt: str, max_tokens: int = 1000, **kwargs) -> str:
        """Send completion request (uses chat for DeepSeek)."""
        return self.chat(prompt, max_tokens, **kwargs)

    def get_token_count(self, text: str) -> int:
        """
        Estimate token count for DeepSeek.

        DeepSeek uses similar tokenization to GPT models.
        """
        # Simple estimation: ~4 characters per token
        return len(text) // 4

