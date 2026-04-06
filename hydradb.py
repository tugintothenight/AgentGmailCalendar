import os
import logging
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
logging.getLogger("sentence_transformers").setLevel(logging.ERROR)
logging.getLogger("transformers").setLevel(logging.ERROR)
logging.getLogger("huggingface_hub").setLevel(logging.ERROR)
from mcp.server.fastmcp import FastMCP
import json
import math
import numpy as np
from datetime import datetime
from sentence_transformers import SentenceTransformer

# Khởi tạo máy chủ MCP
mcp = FastMCP("memory")
DB_FILE = "hydradb_storage.json"
_embedder = None

def get_embedder():
    """Chỉ nạp Model khi thực sự cần dùng Tool, giúp Server khởi động trong 0.1s"""
    global _embedder
    if _embedder is None:
        import warnings
        warnings.filterwarnings("ignore")
        os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1"
        from sentence_transformers import SentenceTransformer
        _embedder = SentenceTransformer('all-MiniLM-L6-v2')
    return _embedder

def load_db():
    """Nạp DB với cấu trúc 3 phân vùng chuẩn Hydra"""
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "episodic": [],   # Sự kiện đã xảy ra
        "semantic": [],   # Kiến thức/Sở thích/Thói quen
        "procedural": []  # Quy tắc bất di bất dịch
    }

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def calculate_time_decay(timestamp_str, lambda_rate=0.05):
    """
    Thuật toán quên lãng (Exponential Decay).
    lambda_rate = 0.05 nghĩa là sau khoảng 14 ngày, mức độ quan trọng giảm một nửa.
    """
    past_time = datetime.fromisoformat(timestamp_str)
    delta_days = (datetime.now() - past_time).days
    return math.exp(-lambda_rate * max(0, delta_days))

def cosine_similarity(vec1, vec2):
    """Tính độ tương đồng ngữ nghĩa giữa 2 Vector"""
    return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-9)

@mcp.tool()
def hydradb_store_memory(memory_text: str, memory_type: str, tags: list[str] = []) -> str:
    """
    [BẮT BUỘC] gọi mỗi khi cần lưu vào bộ nhớ. Dùng để học thêm kiến thức mới hoặc thói quen của user.
    memory_type CHỈ ĐƯỢC CHỌN 1 trong 3: 'episodic', 'semantic', 'procedural'.
    tất cả các biến đều phải ghi bằng tiếng Anh, bao gồm cả memory_text.
    """
    valid_types = ["episodic", "semantic", "procedural"]
    if memory_type not in valid_types:
        return json.dumps({"error": f"Sai type. Phải thuộc: {valid_types}"})

    data = load_db()
    model = get_embedder()
    vector = model.encode(memory_text).tolist()
    
    entry = {
        "id": f"mem_{int(datetime.now().timestamp())}",
        "timestamp": datetime.now().isoformat(),
        "content": memory_text,
        "type": memory_type,
        "tags": [t.lower() for t in tags],
        "vector": vector,
        "access_count": 0
    }
    
    data[memory_type].append(entry)
    save_db(data)
    
    return json.dumps({
        "status": "success", 
        "action": "learned",
        "type": memory_type,
        "memory": memory_text
    }, ensure_ascii=False)

@mcp.tool()
def hydradb_retrieve_memory(query: str, top_k: int = 4) -> str:
    """
    [BẮT BUỘC] luôn luôn dùng trước khi trả lời user. 
    Dùng công cụ này để dò tìm thông tin trong não TRƯỚC KHI ra quyết định.
    Trả về context để bạn phân tích.
    """
    data = load_db()
    model = get_embedder()
    query_vector = model.encode(query).tolist()
    
    scored_results = []
    
    for mem_type in ["episodic", "semantic", "procedural"]:
        for mem in data[mem_type]:
            # Tính điểm tương đồng ngữ nghĩa
            semantic_score = cosine_similarity(query_vector, mem["vector"])
            
            # đặt ngưỡng
            if semantic_score > 0.3:
                # thuật toán decay
                # Sự kiện, Sở thích ko bao giờ được quên
                decay_factor = 1.0
                if mem_type in ["episodic", "semantic"]:
                    decay_factor = calculate_time_decay(mem["timestamp"])
                
                access_count = mem.get("access_count", 0)
                boost_score = access_count * 0.15 
                # Điểm tổng = (Ngữ nghĩa * Quên lãng) + Điểm nhắc lại ký ức
                final_score = (semantic_score * decay_factor) + boost_score
                
                scored_results.append({
                    "mem_ref": mem, # Lưu tham chiếu để cộng điểm sau
                    "score": round(final_score, 4),
                    "type": mem["type"],
                    "content": mem["content"],
                    "age_days": (datetime.now() - datetime.fromisoformat(mem["timestamp"])).days
                })
                
    # Sắp xếp theo độ quan trọng giảm dần
    scored_results.sort(key=lambda x: x["score"], reverse=True)
    top_results = scored_results[:top_k]
    output_context = []
    for item in top_results:
        # +1 điểm mỗi lần nhắc lại ký ức
        item["mem_ref"]["access_count"] = item["mem_ref"].get("access_count", 0) + 1
        
        output_context.append({
            "score": item["score"],
            "type": item["type"],
            "content": item["content"],
            "times_accessed": item["mem_ref"]["access_count"] # số lần nhắc lại
        })
    save_db(data)

    return json.dumps({
        "query": query,
        "context_injected": top_results,
        "instruction_to_agent": "Đây là ký ức của người dùng, khi tóm tắt và ra quyết định hãy để ý trường 'times_accessed' (số lần người dùng nhắc lại), số càng cao nghĩa là luật càng nghiêm ngặt, tuyệt đối không được cãi"
    }, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    mcp.run()