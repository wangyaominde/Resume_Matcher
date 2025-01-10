import os
from langchain_community.embeddings import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModel

def download_model():
    """下载并保存模型到本地"""
    print("开始下载模型...")
    
    # 设置模型目录
    model_name = "sentence-transformers/all-MiniLM-L6-v2"
    model_directory = os.path.join('models', 'sentence-transformers', 'all-MiniLM-L6-v2')
    
    # 创建模型目录
    os.makedirs(model_directory, exist_ok=True)
    
    try:
        # 下载模型和tokenizer
        print("下载embedding模型...")
        embedding = HuggingFaceEmbeddings(
            model_name=model_name,
            cache_folder=model_directory
        )
        
        # 强制下载模型文件
        tokenizer = AutoTokenizer.from_pretrained(model_name, cache_dir=model_directory)
        model = AutoModel.from_pretrained(model_name, cache_dir=model_directory)
        
        # 保存模型和tokenizer
        print(f"保存模型到: {model_directory}")
        model.save_pretrained(model_directory)
        tokenizer.save_pretrained(model_directory)
        
        print("模型下载完成！")
        return True
        
    except Exception as e:
        print(f"模型下载失败: {str(e)}")
        return False

if __name__ == "__main__":
    download_model() 