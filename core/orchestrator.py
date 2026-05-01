import json
from config import MAX_TOTAL_LOOPS


class AgentOrchestrator:
    """Class điều phối luồng ReAct (Observe -> Think -> Act -> Reflect)"""
    
    def __init__(self, llm_engine, tool_executor, security_pipeline):
        self.llm = llm_engine
        self.tools = tool_executor
        self.security = security_pipeline

    # Vòng lặp ReAct
    def execute_loop(self, session, available_tools):
        max_steps = MAX_TOTAL_LOOPS
        step = 0
        
        while step < max_steps:
            step += 1
            print(f"\n--- [AGENT LOOP] Vòng lặp thứ {step} ---")

            # OBSERVE
            context = self.observe(session)

            # THINK
            plan = self.think(session, context, available_tools)
        
            if plan["status"] == "error":
                return plan
                
            if plan["type"] == "text_response":
                # Đã đủ thông tin hoặc cần hỏi lại User -> Dừng vòng lặp
                return self._finalize(plan["data"])
                
            elif plan["type"] == "tool_call":
                # ACT
                act_result = self.act(session, plan["tool_calls"])
                
                if "results" in act_result:
                    self.reflect(session, act_result["results"])
                else:
                    error_msg = act_result.get("message", "Lỗi thực thi công cụ.")
                    print(f"[Orchestrator] Bỏ qua Reflect do lỗi: {error_msg}")
                    session.add_message("tool", f"HỆ THỐNG TỪ CHỐI THỰC THI: {error_msg}")
                continue
                
        return {"status": "error", "message": f"Hệ thống quá tải suy nghĩ (Vượt {max_steps} bước)."}

    # Hàm xử lý các bước  
    def observe(self, session):
        """Thu thập thông tin: Lấy toàn bộ bộ nhớ và lịch sử hiện tại"""
        messages = session.get_messages().copy() 
        return messages

    def think(self, session, context, available_tools):
        """Phân tích và ra quyết định"""
        llm_result = self.llm.generate_response(context, tools=available_tools)
        
        if llm_result["status"] == "error":
            return {"status": "error", "message": llm_result["data"]}
            
        message_obj = llm_result["message_obj"]
        
        # Nếu Decide là chạy Tool -> Ép không được nhả Text, tránh trả lời ra json
        if hasattr(message_obj, 'tool_calls') and message_obj.tool_calls:
            invalid_prompt = self._validate_schedule_event_calls(message_obj.tool_calls)
            if invalid_prompt:
                session.add_message("assistant", invalid_prompt)
                return {"status": "ok", "type": "text_response", "data": invalid_prompt}

            message_obj.content = None 
            tool_calls_dict = [{
                "id": tc.id, 
                "type": "function", 
                "function": {
                    "name": tc.function.name, 
                    "arguments": tc.function.arguments
                }
            } for tc in message_obj.tool_calls
            ]
            session.add_message(message_obj.role, None, tool_calls=tool_calls_dict)   
            return {"status": "ok", "type": "tool_call", "tool_calls": message_obj.tool_calls}
        
        else:
            try:
                json.loads(message_obj.content.strip())
                message_obj.content = "vâng, em sẽ không thực hiện điều đó nữa"
            except Exception:
                # Nếu báo lỗi (tức là text bình thường), thì cho qua
                pass
            session.add_message(message_obj.role, message_obj.content)
            return {"status": "ok", "type": "text_response", "data": llm_result["data"]}

    def _validate_schedule_event_calls(self, tool_calls):
        for tc in tool_calls:
            tool_name = tc.function.name
            if tool_name != "schedule_event":
                continue
            try:
                params = json.loads(tc.function.arguments) if tc.function.arguments else {}
            except json.JSONDecodeError:
                return "Thông tin lên lịch chưa hợp lệ. Vui lòng cung cấp `title`, `start_time`, `end_time` theo định dạng ISO 8601, không được bịa đặt bất kỳ giá trị nào."
            missing = [field for field in ["title", "start_time", "end_time"] if not params.get(field)]
            if missing:
                return f"Thiếu thông tin quan trọng để tạo lịch: {', '.join(missing)}. Vui lòng cung cấp đầy đủ `title`, `start_time`, `end_time` trước khi gọi tool lập lịch. Không được tự chế thông tin thiếu."
            # Kiểm tra định dạng thời gian cơ bản
            if "T" not in params.get("start_time", "") or "T" not in params.get("end_time", ""):
                return "Định dạng thời gian chưa đúng. Hãy dùng ISO 8601, ví dụ `2026-04-30T14:00:00`."
        return None

    def act(self, session, tool_calls):
        has_pending_approval = False
        pending_tools = []
        executed_results = []
        
        for tool_call in tool_calls:
            tool_name = tool_call.function.name
            try:
                params = json.loads(tool_call.function.arguments) if tool_call.function.arguments else {}
            except json.JSONDecodeError:
                executed_results.append({
                    "id": tool_call.id, 
                    "name": tool_name, 
                    "res": json.dumps({"error": "Invalid JSON in tool arguments."})
                })
                continue

            # L2
            if self.security.is_tool_allowed(tool_name).get("status") == "BLOCK":
                executed_results.append({"id": tool_call.id, "name": tool_name, "res": json.dumps({"error": "Firewall Blocked."})})
                continue
                
            # L3
            l3 = self.security.check_circuit_breaker(tool_name, params)
            if l3.get("status") == "BLOCK":
                return {"status": "error", "message": "Đã ngắt mạch do AI kẹt vòng lặp vô hạn."}
            
            # L5
            if self.security.require_human_approval(tool_name, params).get("status") == "HOLD":
                has_pending_approval = True
                pending_tools.append({"id": tool_call.id, "name": tool_name, "params": params})
                continue
                
            # Qua hết các lớp bảo mật
            result = self.tools.execute(tool_name, params)
            executed_results.append({"id": tool_call.id, "name": tool_name, "params": params, "res": result.to_json_string()})
            
        if has_pending_approval:
            return {"status": "pending_approval", "pending_tools": pending_tools}
            
        return {"status": "completed", "results": executed_results}

    def reflect(self, session, executed_results):
        for item in executed_results:
            session.add_tool_message(item["id"], item["name"], item["res"])

            if "error" in item["res"].lower():
                # Tự động lưu vào vùng Episodic để lần sau không lặp lại
                self.tools.hydra_db.store(
                    memory_text=f"Lỗi khi chạy {item['name']}: {item['res']}. Cần rút kinh nghiệm lần sau.",
                    memory_type="episodic",
                    tags=["error_log", "lesson_learned", item["name"]]
                )

            if "error" not in item["res"].lower():
                self.tools.hydra_db.store(
                    memory_text=f"đã thực hiện {item['name']} thành công với tham số {item.get('params', '[Không có tham số]}')}",
                    memory_type="episodic", 
                    tags=["activity_log", item["name"]]
                )

    def _finalize(self, raw_text):
        # L4
        dlp_check = self.security.dlp_filter_output(raw_text)
        final_text = dlp_check.get("data", raw_text)
        return {"status": "success", "message": final_text}