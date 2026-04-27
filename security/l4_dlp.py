class L4DLPFilter:
    def __init__(self, llm_client, judge_model, enable_dlp):
        self.client = llm_client
        self.model = judge_model
        self.enable_dlp = enable_dlp

    def filter(self, text: str) -> dict:
        """Dùng LLM quét và che mờ thông tin nhạy cảm (PII)"""
        if not self.enable_dlp:
            return {"status": "PASS", "data": text}
            
        system_prompt = """
        You are a STRICT string-replacement script, NOT a conversational AI.
        Rule 1: Mask phone numbers, emails, and credit cards with "*********".
        Rule 2: DO NOT answer the user. DO NOT refuse. DO NOT apologize.
        Rule 3: Output the EXACT SAME text provided, just with sensitive data masked.
        Rule 4: Do not mask links, addresses, or general names unless they contain clear PII.
        If nothing needs masking, output the exact original text.
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": text}
                ],
                temperature=0.0
            )
            filtered = response.choices[0].message.content.strip()
            
            if filtered == "SAFE":
                return {"status": "PASS", "data": text}
                
            orig_words = set(text.lower().split())
            filt_words = set(filtered.lower().split())
            overlap = len(orig_words & filt_words) / max(len(orig_words), 1)
            
            # Tránh ảo giác viết lại
            if overlap < 0.3:
                print("[Security L4] DLP ngáo chữ. Bỏ qua lọc.")
                return {"status": "PASS", "data": text}
            
            # Tránh ảo giác từ chối trả lời
            refusal_keywords = ["tôi không thể", "i cannot", "xin lỗi", "không thể cung cấp", "không được phép", "as an ai", "chỉ là mô hình"]
            if any(kw in filtered.lower() for kw in refusal_keywords):
                print("[Security L4] AI có vấn đề lọc. Đã tát cảnh cáo và bỏ qua lọc.")
                return {"status": "PASS", "data": text}
                
            print("[Security L4] Đã che mờ thông tin nhạy cảm.")
            return {"status": "MODIFIED", "data": filtered}
            
        except Exception as e:
            print(f"[Security L4] Lỗi DLP: {e}")
            return {"status": "PASS", "data": text}
