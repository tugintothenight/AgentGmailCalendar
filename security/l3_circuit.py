class L3CircuitBreaker:
    def __init__(self, max_loops, max_duplicates):
        self.max_loops = max_loops
        self.max_duplicates = max_duplicates
        self.history_actions = []

    def check(self, tool_name: str, parameters: dict) -> dict:
        if len(self.history_actions) >= self.max_loops:
            return {"status": "BLOCK", "message": "HARD_STOP: Too many tool calls."}
        
        if tool_name == "schedule_event":
            critical_params = {
                "start_time": parameters.get("start_time", ""),
                "end_time": parameters.get("end_time", "")
            }
            current_action = f"{tool_name}_{str(critical_params)}"
        else:
            current_action = f"{tool_name}_{str(parameters)}"
        
        self.history_actions.append(current_action)
        
        if len(self.history_actions) >= 2:
            recent = self.history_actions[-self.max_duplicates:]            
            # Nếu gọi liên tục max_duplicates lần -> Ngắt luồng
            if len(recent) == self.max_duplicates and len(set(recent)) == 1:
                print(f"[Security L3] AI kẹt vòng lặp -> buộc dừng!")
                return {"status": "BLOCK", "message": "HARD_STOP: Infinite loop detected."}
            # Nếu gọi lại tool y hệt 2 lần liên tiếp -> Cảnh cáo
            if len(recent) >= 2 and len(set(self.history_actions[-2:])) == 1:
                print(f"[Security L3] AI lặp lại hành động: {current_action}")
                return {"status": "WARNING", "message": "Mày vừa gọi tool này rồi. Đổi cách đi!"}    
        return {"status": "PASS"}

    def reset(self):
        self.history_actions = []