class L5HITLGuard:
    def __init__(self, sensitive_tools):
        self.sensitive_tools = sensitive_tools

    def check(self, tool_name: str, parameters: dict) -> dict:
        """Kiểm tra tool có nằm trong danh sách cần Sếp duyệt không"""
        if tool_name in self.sensitive_tools:
            print(f"[Security L5] Yêu cầu duyệt thủ công (HITL) cho: {tool_name}")
            return {"status": "HOLD", "message": "Awaiting human approval."}
        return {"status": "PASS"}