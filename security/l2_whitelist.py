class L2WhitelistGuard:
    def __init__(self, allowed_tools):
        self.allowed_tools = allowed_tools

    def check(self, tool_name: str) -> dict:
        if tool_name not in self.allowed_tools:
            print(f"[Security L2] CHẶN: Tool '{tool_name}' không được phép.")
            return {"status": "BLOCK", "message": "Tool not allowed by Firewall."}
        return {"status": "PASS"}