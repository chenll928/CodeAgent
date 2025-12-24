"""
Logging and monitoring for AI Coding Agent.

Provides structured logging, metrics tracking, and performance monitoring.
"""

import logging
import time
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class LogLevel(str, Enum):
    """Log levels."""
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"


@dataclass
class OperationMetrics:
    """Metrics for a single operation."""
    operation: str
    start_time: float
    end_time: Optional[float] = None
    duration: Optional[float] = None
    token_usage: int = 0
    success: bool = True
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class AgentLogger:
    """
    Structured logger for AI Coding Agent.
    
    Features:
    - Structured logging with context
    - Performance metrics tracking
    - Token usage monitoring
    - Error tracking
    """

    def __init__(
        self,
        name: str = "intentgraph.agent",
        log_file: Optional[Path] = None,
        level: LogLevel = LogLevel.INFO
    ):
        """Initialize logger."""
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, level.value.upper()))
        
        # Console handler
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)
        
        # File handler
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_handler.setFormatter(formatter)
            self.logger.addHandler(file_handler)
        
        # Metrics storage
        self._metrics: List[OperationMetrics] = []
        self._current_operation: Optional[OperationMetrics] = None

    def start_operation(self, operation: str, **metadata):
        """Start tracking an operation."""
        self._current_operation = OperationMetrics(
            operation=operation,
            start_time=time.time(),
            metadata=metadata
        )
        self.logger.info(f"Starting operation: {operation}")

    def end_operation(self, success: bool = True, error: Optional[str] = None, token_usage: int = 0):
        """End tracking current operation."""
        if not self._current_operation:
            return
        
        self._current_operation.end_time = time.time()
        self._current_operation.duration = (
            self._current_operation.end_time - self._current_operation.start_time
        )
        self._current_operation.success = success
        self._current_operation.error = error
        self._current_operation.token_usage = token_usage
        
        self._metrics.append(self._current_operation)
        
        if success:
            self.logger.info(
                f"Completed operation: {self._current_operation.operation} "
                f"({self._current_operation.duration:.2f}s, {token_usage} tokens)"
            )
        else:
            self.logger.error(
                f"Failed operation: {self._current_operation.operation} - {error}"
            )
        
        self._current_operation = None

    def log_llm_call(self, prompt_tokens: int, completion_tokens: int, model: str):
        """Log LLM API call."""
        total_tokens = prompt_tokens + completion_tokens
        self.logger.debug(
            f"LLM call: {model} - {prompt_tokens} prompt + {completion_tokens} completion = {total_tokens} total"
        )

    def log_cache_hit(self, key: str):
        """Log cache hit."""
        self.logger.debug(f"Cache hit: {key}")

    def log_cache_miss(self, key: str):
        """Log cache miss."""
        self.logger.debug(f"Cache miss: {key}")

    def get_metrics_summary(self) -> Dict[str, Any]:
        """Get summary of all metrics."""
        if not self._metrics:
            return {}
        
        total_operations = len(self._metrics)
        successful_operations = sum(1 for m in self._metrics if m.success)
        total_duration = sum(m.duration for m in self._metrics if m.duration)
        total_tokens = sum(m.token_usage for m in self._metrics)
        
        return {
            "total_operations": total_operations,
            "successful_operations": successful_operations,
            "failed_operations": total_operations - successful_operations,
            "success_rate": successful_operations / total_operations if total_operations > 0 else 0,
            "total_duration": total_duration,
            "average_duration": total_duration / total_operations if total_operations > 0 else 0,
            "total_tokens": total_tokens,
            "average_tokens": total_tokens / total_operations if total_operations > 0 else 0
        }

    def get_operation_metrics(self, operation: str) -> List[OperationMetrics]:
        """Get metrics for specific operation."""
        return [m for m in self._metrics if m.operation == operation]

    def export_metrics(self, output_file: Path):
        """Export metrics to JSON file."""
        import json
        
        metrics_data = {
            "summary": self.get_metrics_summary(),
            "operations": [
                {
                    "operation": m.operation,
                    "duration": m.duration,
                    "token_usage": m.token_usage,
                    "success": m.success,
                    "error": m.error,
                    "timestamp": datetime.fromtimestamp(m.start_time).isoformat(),
                    "metadata": m.metadata
                }
                for m in self._metrics
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(metrics_data, f, indent=2)
        
        self.logger.info(f"Metrics exported to {output_file}")


# Global logger instance
_global_logger: Optional[AgentLogger] = None


def get_logger() -> AgentLogger:
    """Get global logger instance."""
    global _global_logger
    if _global_logger is None:
        _global_logger = AgentLogger()
    return _global_logger


def configure_logger(
    log_file: Optional[Path] = None,
    level: LogLevel = LogLevel.INFO
):
    """Configure global logger."""
    global _global_logger
    _global_logger = AgentLogger(log_file=log_file, level=level)

