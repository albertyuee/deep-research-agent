from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from config.settings import settings


class RetryAction(Enum):
    BROADEN = "broaden"
    SWITCH_STRATEGY = "switch_strategy"
    REPHRASE = "rephrase"
    EXPAND_K = "expand_k"


@dataclass
class RetryState:
    retry_count: int = 0
    max_retries: int = 3
    history: list[dict] = field(default_factory=list)

    def can_retry(self) -> bool:
        return self.retry_count < self.max_retries

    def next_action(self) -> dict:
        """Determine the next retry action based on attempt count.

        Strategy escalation:
        - Retry 1: broaden query + increase top_k
        - Retry 2: switch retrieval strategy (semantic ↔ keyword)
        - Retry 3: rephrase query entirely
        """
        attempt = self.retry_count + 1

        if attempt == 1:
            action = {
                "type": "broaden",
                "top_k_multiplier": 2,
                "description": "扩大 top_k 并改写查询为更宽泛的版本",
            }
        elif attempt == 2:
            action = {
                "type": "switch_strategy",
                "top_k_multiplier": 2,
                "description": "切换检索策略（语义→关键词 或 关键词→语义）",
            }
        else:
            action = {
                "type": "rephrase",
                "top_k_multiplier": 3,
                "description": "重新表述查询，使用不同的关键词和角度",
            }

        return action

    def record_attempt(self, action: dict, critique_result) -> None:
        self.retry_count += 1
        self.history.append(
            {
                "attempt": self.retry_count,
                "action": action,
                "score": critique_result.composite_score,
                "reasoning": critique_result.reasoning,
            }
        )

    def exhausted(self) -> bool:
        return self.retry_count >= self.max_retries


def create_retry_state(max_retries: int | None = None) -> RetryState:
    return RetryState(max_retries=max_retries or settings.retrieval.max_retries)
