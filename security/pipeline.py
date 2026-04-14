from openai import OpenAI
from config import OPENROUTER_API_KEY, OPENROUTER_BASE_URL, JUDGE_MODEL, MAX_TOTAL_LOOPS, MAX_DUPLICATE_ACTIONS, ALLOWED_TOOLS, SENSITIVE_TOOLS, ENABLE_DLP_FILTER

from .l1_injection import L1InjectionGuard
from .l2_whitelist import L2WhitelistGuard
from .l3_circuit import L3CircuitBreaker
from .l4_dlp import L4DLPFilter
from .l5_hitl import L5HITLGuard

class SecurityPipeline:
    """Mặt tiền (Facade) điều phối 5 lớp an ninh"""
    
    def __init__(self):
        # LLM cho L1, L4
        self.llm_client = OpenAI(
            base_url=OPENROUTER_BASE_URL,
            api_key=OPENROUTER_API_KEY,
        )
        self.l1 = L1InjectionGuard(self.llm_client, JUDGE_MODEL)
        self.l2 = L2WhitelistGuard(ALLOWED_TOOLS)
        self.l3 = L3CircuitBreaker(MAX_TOTAL_LOOPS, MAX_DUPLICATE_ACTIONS)
        self.l4 = L4DLPFilter(self.llm_client, JUDGE_MODEL, ENABLE_DLP_FILTER)
        self.l5 = L5HITLGuard(SENSITIVE_TOOLS)

    def check_prompt_injection(self, text: str) -> dict:
        return self.l1.check(text)

    def is_tool_allowed(self, tool_name: str) -> dict:
        return self.l2.check(tool_name)

    def check_circuit_breaker(self, tool_name: str, parameters: dict) -> dict:
        return self.l3.check(tool_name, parameters)

    def reset_circuit_breaker(self):
        self.l3.reset()

    def dlp_filter_output(self, text: str) -> dict:
        return self.l4.filter(text)

    def require_human_approval(self, tool_name: str, parameters: dict) -> dict:
        return self.l5.check(tool_name, parameters)