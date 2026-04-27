import os
import json
import math
import numpy as np
from datetime import datetime

class HydraMemoryDB:
    """Class quản lý trí nhớ 3 phân vùng + Graph"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._embedder = None
        
    def _get_embedder(self):
        """Lazy load model nhúng"""
        if self._embedder is None:
            os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "1" # tắt thanh tiến trình tải
            import warnings
            warnings.filterwarnings("ignore") # tắt cảnh báo linh tinh
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer('all-MiniLM-L6-v2')
        return self._embedder

    def _load_db(self):
        default_db = {"episodic": [], "semantic": [], "procedural": [], "graph_relations": []}
        if os.path.exists(self.db_path):
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if not content: return default_db
                    data = json.loads(content)
                    if "graph_relations" not in data: data["graph_relations"] = []
                    return data
            except Exception as e:
                print(f"[HydraDB] Warning: {e}")
        return default_db

    def _save_db(self, data):
        with open(self.db_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _cosine_similarity(self, vec1, vec2):
        return np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2) + 1e-9)

    def _calculate_time_decay(self, timestamp_str, lambda_rate=0.05):
        past_time = datetime.fromisoformat(timestamp_str)
        delta_days = (datetime.now() - past_time).days
        return math.exp(-lambda_rate * max(0, delta_days))

    def store(self, memory_text: str, memory_type: str, tags: list = [], triplets: list = []) -> str:
        """Lưu trí nhớ"""
        if memory_type not in ["episodic", "semantic", "procedural"]:
            return json.dumps({"error": "Sai type."})

        data = self._load_db()
        model = self._get_embedder()
        vector = model.encode(memory_text).tolist()
        
        mem_id = f"mem_{int(datetime.now().timestamp())}"
        entry = {
            "id": mem_id, "timestamp": datetime.now().isoformat(),
            "content": memory_text, "type": memory_type,
            "tags": [t.lower() for t in tags], "vector": vector, "access_count": 0
        }
        data[memory_type].append(entry)
        
        if triplets:
            for t in triplets:
                if isinstance(t, dict) and all(k in t for k in ["subject", "predicate", "object"]):
                    data["graph_relations"].append({
                        "source": t["subject"], "edge": t["predicate"], 
                        "target": t["object"], "linked_memory_id": mem_id
                    })
        self._save_db(data)
        return json.dumps({"status": "success", "action": "learned", "type": memory_type})

    def retrieve(self, query: str, top_k: int = 4) -> str:
        """Trích xuất trí nhớ"""
        data = self._load_db()
        model = self._get_embedder()
        query_vector = model.encode(query).tolist()
        
        scored_results = []
        for mem_type in ["episodic", "semantic", "procedural"]:
            for mem in data[mem_type]:
                semantic_score = self._cosine_similarity(query_vector, mem["vector"])
                if semantic_score > 0.3:
                    decay = self._calculate_time_decay(mem["timestamp"]) if mem_type != "procedural" else 1.0
                    boost = mem.get("access_count", 0) * 0.15 
                    scored_results.append({
                        "mem_ref": mem,
                        "score": round((semantic_score * decay) + boost, 4),
                        "type": mem["type"], "content": mem["content"]
                    })
                    
        top_results = sorted(scored_results, key=lambda x: x["score"], reverse=True)[:top_k]
        
        output_context, extracted_ids = [], []
        for item in top_results:
            item["mem_ref"]["access_count"] = item["mem_ref"].get("access_count", 0) + 1
            extracted_ids.append(item["mem_ref"]["id"])
            output_context.append({"score": item["score"], "type": item["type"], "content": item["content"]})
            
        graph_context = [f"{r['source']} --[{r['edge']}]--> {r['target']}" for r in data.get("graph_relations", []) if r.get("linked_memory_id") in extracted_ids]

        self._save_db(data)
        return json.dumps({
            "query": query, "vector_context": output_context, "graph_context": graph_context
        }, ensure_ascii=False)

HYDRADB_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "hydradb_store",
            "description": "Store user memories, facts, or rules. You MUST TO provide triplets for Graph context. All parameters must be in English.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_text": {"type": "string"},
                    "memory_type": {"type": "string", "enum": ["episodic", "semantic", "procedural"]},
                    "tags": {"type": "array", "items": {"type": "string"}},
                    "triplets": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "subject": {"type": "string"},
                                "predicate": {"type": "string"},
                                "object": {"type": "string"}
                            }
                        }
                    }
                },
                "required": ["memory_text", "memory_type"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "hydradb_retrieve",
            "description": "Retrieve memories before answering any personal questions. query by english text. Returns relevant memories with time decay and access boost, plus related graph context. All parameters must be in English.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}}
            }
        }
    }
]