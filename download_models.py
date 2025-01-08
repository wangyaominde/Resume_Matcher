import os
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel

def download_model():
    print("开始下载模型...")
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    base_path = os.path.dirname(os.path.abspath(__file__))
    local_model_path = os.path.join(base_path, "models", model_name)
    
    # 创建模型目录
    os.makedirs(local_model_path, exist_ok=True)
    
    # 下载模型
    print(f"下载模型到: {local_model_path}")
    model = SentenceTransformer(model_name)
    model.save(local_model_path)
    
    print("模型下载完成！")

if __name__ == "__main__":
    download_model() 