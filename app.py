import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QTabWidget, QPushButton, QTextEdit, 
                            QLabel, QFileDialog, QLineEdit, QMessageBox, QProgressBar, QGroupBox,
                            QListWidget, QListWidgetItem, QDialog)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QWaitCondition
from PyQt6.QtWidgets import QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget, QPushButton, QTextEdit, QLabel, QFileDialog, QLineEdit, QMessageBox, QProgressBar
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QMutex, QWaitCondition
from dotenv import load_dotenv
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain.text_splitter import CharacterTextSplitter
from langchain.chains import RetrievalQA
from langchain_openai import ChatOpenAI
import json
from datetime import datetime
import PyPDF2
import docx
import pdfplumber
import markdown
from PIL import Image
import pytesseract
from pdf2image import convert_from_path
import tempfile
import time

# 加载环境变量
load_dotenv()

class ResumeAssistant:
    """简历助手核心类"""
    API_BASE_URL = "https://api.deepseek.com"  # 固化的API URL
    
    def __init__(self):
        # 初始化向量数据库
        self.PERSIST_DIRECTORY = 'db'
        if not os.path.exists(self.PERSIST_DIRECTORY):
            os.makedirs(self.PERSIST_DIRECTORY)

        self.embedding = HuggingFaceEmbeddings(
            model_name="sentence-transformers/all-MiniLM-L6-v2"
        )
        self.vectordb = Chroma(
            persist_directory=self.PERSIST_DIRECTORY,
            embedding_function=self.embedding
        )
        
        # 尝试初始化LLM,但允许失败
        try:
            self.init_llm()
        except Exception:
            self.llm = None
        
    def init_llm(self):
        """初始化LLM"""
        try:
            # 从数据库获取API Key
            api_key = self.get_api_key()
            if not api_key:
                self.llm = None
                return

            os.environ["OPENAI_API_KEY"] = api_key
            os.environ["OPENAI_API_BASE"] = self.API_BASE_URL

            self.llm = ChatOpenAI(
                model_name="deepseek-chat",
                temperature=0.7,
                max_tokens=2000
            )
        except Exception as e:
            self.llm = None
            print(f"LLM初始化失败: {str(e)}")
            
    def check_llm_ready(self):
        """检查LLM是否准备就绪"""
        return self.llm is not None

    def save_api_key(self, api_key):
        """保存API Key到数据库"""
        try:
            # 检查是否已存在API Key
            collection = self.vectordb._collection
            if collection:
                results = collection.get()
                if results and 'metadatas' in results:
                    # 删除旧的API Key
                    ids_to_delete = []
                    for i, metadata in enumerate(results['metadatas']):
                        if metadata.get('type') == 'api_key':
                            ids_to_delete.append(results['ids'][i])
                    if ids_to_delete:
                        collection.delete(ids_to_delete)
            
            # 保存新的API Key
            metadata = {
                "type": "api_key",
                "timestamp": datetime.now().isoformat()
            }
            self.vectordb.add_texts([api_key], metadatas=[metadata])
            self.vectordb.persist()
            return True
        except Exception as e:
            raise Exception(f"保存API Key失败: {str(e)}")
            
    def get_api_key(self):
        """从数据库获取API Key"""
        try:
            collection = self.vectordb._collection
            if collection:
                results = collection.get()
                if results and 'metadatas' in results:
                    for i, metadata in enumerate(results['metadatas']):
                        if metadata.get('type') == 'api_key':
                            return results['documents'][i]
            return None
        except Exception:
            return None

    def chat(self, message, history):
        """对话收集信息"""
        prompt = f"""
        你是一个专业的简历顾问。请根据用户的输入提供专业的建议和指导。
        
        历史对话：
        {history}
        
        用户消息：{message}
        
        请直接回复，不要返回JSON格式。保持对话专业性和连贯性，引导用户提供更多有价值的信息。
        """
        
        try:
            qa_chain = self.get_qa_chain()
            result = qa_chain({"query": prompt})
            return result["result"]
        except Exception as e:
            raise Exception(f"对话处理失败: {str(e)}")

    def analyze_jd(self, jd_text):
        """分析职位描述"""
        prompt = f"""
        请分析以下职位描述(JD)，提取关键信息并按照指定格式返回。
        
        职位描述：
        {jd_text}

        请严格按照以下JSON格式返回，不要添加任何其他内容：
        {{
            "required_skills": ["技能1", "技能2"],
            "preferred_skills": ["技能1", "技能2"],
            "education": {{
                "degree": "学历要求",
                "major": "专业要求"
            }},
            "experience": {{
                "years": "年限要求",
                "industry": "行业要求",
                "position": "职位要求"
            }},
            "responsibilities": ["职责1", "职责2"],
            "company_info": {{
                "industry": "所属行业",
                "scale": "公司规模",
                "stage": "发展阶段"
            }}
        }}

        注意：
        1. 必须返回完全合法的JSON格式
        2. 所有字符串必须使用双引号，不能用单引号
        3. 数组至少包含一个元素
        4. 不要添加任何额外的说明或注释
        5. 不要添加任何前缀或后缀
        6. 如果信息不明确，使用合理的默认值
        """
        
        try:
            qa_chain = self.get_qa_chain()
            result = qa_chain({"query": prompt})
            response_text = result["result"].strip()
            
            # 尝试解析JSON
            try:
                jd_analysis = json.loads(response_text)
                
                # 验证并设置默认值
                required_fields = {
                    "required_skills": ["未指定"],
                    "preferred_skills": ["未指定"],
                    "education": {
                        "degree": "未指定",
                        "major": "未指定"
                    },
                    "experience": {
                        "years": "未指定",
                        "industry": "未指定",
                        "position": "未指定"
                    },
                    "responsibilities": ["未指定"],
                    "company_info": {
                        "industry": "未指定",
                        "scale": "未指定",
                        "stage": "未指定"
                    }
                }
                
                # 确保所有必要字段都存在
                for field, default_value in required_fields.items():
                    if field not in jd_analysis:
                        jd_analysis[field] = default_value
                    elif isinstance(default_value, dict):
                        for sub_field, sub_default in default_value.items():
                            if sub_field not in jd_analysis[field]:
                                jd_analysis[field][sub_field] = sub_default
                    elif isinstance(default_value, list) and not jd_analysis[field]:
                        jd_analysis[field] = default_value
                
                return jd_analysis
                
            except json.JSONDecodeError as e:
                print(f"JSON解析错误: {str(e)}")
                print(f"原始响应: {response_text}")
                # 返回默认结构
                return required_fields
                
        except Exception as e:
            raise Exception(f"JD分析失败: {str(e)}")

    def generate_resume(self, jd_analysis):
        """根据JD分析结果生成简历"""
        try:
            # 从数据库获取所有简历内容
            collection = self.vectordb._collection
            if not collection:
                raise Exception("数据库未初始化")
                
            results = collection.get()
            if not results or 'metadatas' not in results or 'documents' not in results:
                raise Exception("数据库中没有简历")
            
            # 构建简历内容列表
            resumes = []
            for i, metadata in enumerate(results['metadatas']):
                if metadata.get('type') == 'resume_info':
                    resumes.append({
                        'content': results['documents'][i],
                        'file_name': metadata.get('file_name', '未命名简历')
                    })
            
            if not resumes:
                raise Exception("没有找到可用的简历")
            
            # 分析所有简历并找到最匹配的
            prompt = f"""
            请根据以下职位要求和简历内容，生成一份最具竞争力的简历。

            职位要求：
            1. 必需技能：{', '.join(jd_analysis['required_skills'])}
            2. 加分技能：{', '.join(jd_analysis['preferred_skills'])}
            3. 教育要求：{jd_analysis['education']['degree']} ({jd_analysis['education']['major']})
            4. 经验要求：{jd_analysis['experience']['years']} ({jd_analysis['experience']['industry']})
            5. 职位要求：{jd_analysis['experience']['position']}
            6. 工作职责：{', '.join(jd_analysis['responsibilities'])}

            可用的简历内容：
            {json.dumps([{
                'file_name': r['file_name'],
                'content': r['content']
            } for r in resumes], ensure_ascii=False, indent=2)}

            要求：
            1. 直接返回纯文本的Markdown格式简历内容
            2. 不要使用代码块格式
            3. 不要解释或说明做了什么修改
            4. 不要添加任何注释
            5. 确保内容完全匹配JD要求
            6. 保持专业的简历格式和结构
            """
            
            qa_chain = self.get_qa_chain()
            result = qa_chain({"query": prompt})
            
            return {
                "resume": result["result"]
            }
        except Exception as e:
            raise Exception(f"简历生成失败: {str(e)}")

    def analyze_resume(self, text):
        """分析上传的简历内容"""
        prompt = f"""
        请详细分析以下简历内容，提取所有有用的信息：

        {text}
        
        请提取以下信息：
        1. 基本信息（姓名、邮箱、电话、所在地等）
        2. 教育背景（学校、学历、专业、时间等）
        3. 工作经验（公司、职位、时间、职责等）
        4. 项目经验（项目名称、角色、技术栈、成果等）
        5. 技能特长（技术技能、语言能力、其他技能等）
        6. 证书成就（获得的证书、奖项等）

        注意：
        1. 保持原始表述，不要主观加工
        2. 尽可能详细地提取信息
        3. 保持信息的完整性和准确性
        """

        try:
            qa_chain = self.get_qa_chain()
            result = qa_chain({"query": prompt})
            return result["result"]
        except Exception as e:
            raise Exception(f"简历分析失败: {str(e)}")

    def save_to_db(self, info):
        """保存信息到数据库"""
        try:
            # 添加元数据
            if isinstance(info, str):
                text = info
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "resume_info"
                }
            else:
                text = info.get("content", "")
                metadata = {
                    "timestamp": datetime.now().isoformat(),
                    "type": "resume_info",
                    "file_name": info.get("file_name", "未命名简历")
                }
            
            # 保存到向量数据库
            self.vectordb.add_texts([text], metadatas=[metadata])
            self.vectordb.persist()
            
            return True
        except Exception as e:
            raise Exception(f"保存到数据库失败: {str(e)}")

    def delete_from_db(self, file_names):
        """从数据库中删除指定的简历"""
        try:
            collection = self.vectordb._collection
            if collection:
                results = collection.get()
                if results and 'metadatas' in results and 'ids' in results:
                    # 找到要删除的简历索引和ID
                    ids_to_delete = []
                    for i, metadata in enumerate(results['metadatas']):
                        if (metadata.get('type') == 'resume_info' and 
                            metadata.get('file_name') in file_names):
                            ids_to_delete.append(results['ids'][i])
                    
                    if ids_to_delete:
                        collection.delete(ids_to_delete)
                        return len(ids_to_delete)
            return 0
        except Exception as e:
            print(f"删除错误详情: {str(e)}")  # 添加详细错误日志
            raise Exception(f"从数据库删除失败: {str(e)}")

    def get_qa_chain(self):
        """创建问答链"""
        retriever = self.vectordb.as_retriever(search_kwargs={"k": 3})
        qa_chain = RetrievalQA.from_chain_type(
            llm=self.llm,
            chain_type="stuff",
            retriever=retriever,
            return_source_documents=True
        )
        return qa_chain

    def calculate_match_score(self, resume_text, jd_text):
        """计算简历和JD的匹配度"""
        prompt = f"""
        请分析以下简历和职位描述的匹配程度，返回一个0-100的分数。
        
        简历内容：
        {resume_text}
        
        职位描述：
        {jd_text}
        
        请考虑以下因素：
        1. 技能匹配度
        2. 经验相关度
        3. 教育背景匹配度
        4. 职责匹配度
        
        只返回一个0-100的整数，不要返回其他内容。
        """
        
        try:
            qa_chain = self.get_qa_chain()
            result = qa_chain({"query": prompt})
            score = int(result["result"].strip())
            return max(0, min(100, score))  # 确保分数在0-100之间
        except Exception as e:
            print(f"匹配度计算失败: {str(e)}")
            return 0

    def process_document(self, file_path):
        """处理文档"""
        ext = os.path.splitext(file_path)[1].lower()
        
        try:
            if ext == '.pdf':
                with pdfplumber.open(file_path) as pdf:
                    return "\n".join(page.extract_text() for page in pdf.pages)
            elif ext in ['.docx', '.doc']:
                doc = docx.Document(file_path)
                return "\n".join(paragraph.text for paragraph in doc.paragraphs)
            elif ext == '.md':
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
            else:
                with open(file_path, 'r', encoding='utf-8') as f:
                    return f.read()
        except Exception as e:
            raise Exception(f"文件处理失败: {str(e)}")

class AITask:
    """AI任务类"""
    def __init__(self, task_type, params, callback, timeout=120):  # 默认120秒超时
        self.task_type = task_type  # 任务类型：'chat', 'analyze_resume', 'analyze_jd'
        self.params = params        # 任务参数
        self.callback = callback    # 完成后的回调函数
        self.timeout = timeout      # 超时时间（秒）
        self.start_time = None     # 任务开始时间

class AIWorker(QThread):
    """AI工作线程"""
    finished = pyqtSignal(str, object)  # 任务类型, 结果
    error = pyqtSignal(str, str)      # 任务类型, 错误信息
    progress = pyqtSignal(int)        # 进度信号
    match_score = pyqtSignal(float)   # 匹配度信号
    status_message = pyqtSignal(str)  # 状态栏消息信号
    timeout = pyqtSignal(str)         # 超时信号

    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.tasks = []
        self.running = True
        self.mutex = QMutex()
        self.condition = QWaitCondition()
        self.current_task = None

    def add_task(self, task):
        """添加任务到队列"""
        self.mutex.lock()
        self.tasks.append(task)
        self.condition.wakeOne()
        self.mutex.unlock()

    def stop(self):
        """停止工作线程"""
        self.running = False
        self.condition.wakeOne()

    def check_timeout(self):
        """检查当前任务是否超时"""
        if self.current_task and self.current_task.start_time:
            elapsed_time = time.time() - self.current_task.start_time
            return elapsed_time > self.current_task.timeout
        return False

    def run(self):
        """运行工作线程"""
        while self.running:
            self.mutex.lock()
            if not self.tasks:
                self.condition.wait(self.mutex)
            if not self.running:
                self.mutex.unlock()
                break
            self.current_task = self.tasks.pop(0) if self.tasks else None
            self.mutex.unlock()

            if self.current_task:
                try:
                    self.current_task.start_time = time.time()
                    
                    if self.current_task.task_type == 'chat':
                        self.progress.emit(30)
                        self.status_message.emit("正在处理对话...")
                        result = self.assistant.chat(self.current_task.params['message'], 
                                                   self.current_task.params['history'])
                        if self.check_timeout():
                            raise TimeoutError("对话处理超时")
                        self.progress.emit(100)
                        self.finished.emit('chat', result)
                        
                    elif self.current_task.task_type == 'analyze_jd':
                        self.progress.emit(30)
                        self.status_message.emit("正在分析职位要求...")
                        result = self.assistant.analyze_jd(self.current_task.params['text'])
                        if self.check_timeout():
                            raise TimeoutError("职位分析超时")
                        self.progress.emit(100)
                        self.finished.emit('analyze_jd', result)
                        
                    elif self.current_task.task_type == 'generate_resume':
                        self.progress.emit(30)
                        self.status_message.emit("正在生成简历...")
                        result = self.assistant.generate_resume(self.current_task.params['jd_analysis'])
                        if self.check_timeout():
                            raise TimeoutError("简历生成超时")
                        self.progress.emit(90)
                        if isinstance(result, dict) and "resume" in result:
                            score = self.assistant.calculate_match_score(
                                result["resume"], 
                                self.current_task.params.get('jd_text', '')
                            )
                            if self.check_timeout():
                                raise TimeoutError("匹配度计算超时")
                            self.match_score.emit(score)
                        self.progress.emit(100)
                        self.finished.emit('generate_resume', result)
                    
                    self.status_message.emit("处理完成")
                    
                except TimeoutError as e:
                    self.timeout.emit(self.current_task.task_type)
                    self.error.emit(self.current_task.task_type, str(e))
                    self.status_message.emit("处理超时")
                except Exception as e:
                    self.error.emit(self.current_task.task_type, str(e))
                    self.status_message.emit("处理失败")
                finally:
                    self.progress.emit(100)
                    self.current_task = None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("智能简历助手")
        self.setGeometry(100, 100, 1200, 800)
        self.assistant = ResumeAssistant()
        self.chat_history = []
        
        # 创建AI工作线程
        self.ai_worker = AIWorker(self.assistant)
        self.ai_worker.finished.connect(self.handle_ai_result)
        self.ai_worker.error.connect(self.handle_ai_error)
        self.ai_worker.progress.connect(self.update_progress)
        self.ai_worker.match_score.connect(self.update_match_score)
        self.ai_worker.status_message.connect(self.update_status)
        self.ai_worker.timeout.connect(self.handle_timeout)
        self.ai_worker.start()
        
        self.setup_ui()
        self.load_resume_count()
        
        # 检查API Key
        if not self.assistant.check_llm_ready():
            QMessageBox.information(self, "提示", "请先在设置中配置API Key")
            self.show_settings()

    def handle_timeout(self, task_type):
        """处理任务超时"""
        timeout_messages = {
            'chat': "对话处理超时，请重试",
            'analyze_resume': "简历分析超时，请重试",
            'analyze_jd': "职位分析超时，请重试",
            'generate_resume': "简历生成超时，请重试"
        }
        
        message = timeout_messages.get(task_type, "处理超时，请重试")
        QMessageBox.warning(self, "超时提醒", message)
        
        # 重新启用所有按钮
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(True)

    def handle_ai_result(self, task_type, result):
        """处理AI任务结果"""
        try:
            if task_type == 'chat':
                self.append_message("AI", result)
                self.chat_input.setEnabled(True)
            elif task_type == 'analyze_resume':
                self.resume_analysis.setText(result)
                self.assistant.save_to_db({"content": result})
                QMessageBox.information(self, "成功", "简历分析完成")
            elif task_type == 'analyze_jd':
                self.handle_jd_analysis(result)
            elif task_type == 'generate_resume':
                self.handle_resume_generation(result)
        except Exception as e:
            self.handle_ai_error(task_type, str(e))

    def handle_ai_error(self, task_type, error_msg):
        """处理AI任务错误"""
        error_messages = {
            'chat': "对话处理失败",
            'analyze_resume': "简历分析失败",
            'analyze_jd': "JD分析失败",
            'generate_resume': "简历生成失败"
        }
        
        error_title = error_messages.get(task_type, "处理失败")
        QMessageBox.critical(self, error_title, f"{error_title}: {error_msg}")
        
        # 重新启用所有按钮
        for btn in self.findChildren(QPushButton):
            btn.setEnabled(True)

    def setup_ui(self):
        """设置UI界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 顶部工具栏
        toolbar_layout = QHBoxLayout()
        toolbar_layout.addStretch()
        
        # 设置按钮
        settings_btn = QPushButton("⚙️ 设置")
        settings_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #666;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 4px 8px;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #f0f0f0;
                color: #333;
            }
        """)
        settings_btn.clicked.connect(self.show_settings)
        toolbar_layout.addWidget(settings_btn)
        
        layout.addLayout(toolbar_layout)
        
        # 设置整体样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QWidget {
                font-family: 'Microsoft YaHei', Arial;
                font-size: 12pt;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 100px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QTextEdit {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px;
            }
            QLabel {
                color: #333;
                font-weight: bold;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
        """)
        
        # 简历上传区域
        resume_group = QGroupBox("简历库")
        resume_layout = QVBoxLayout(resume_group)
        
        upload_layout = QHBoxLayout()
        upload_btn = QPushButton("上传简历")
        upload_btn.clicked.connect(self.upload_resumes)
        upload_layout.addWidget(upload_btn)
        
        delete_layout = QHBoxLayout()
        delete_btn = QPushButton("删除选中简历")
        delete_btn.clicked.connect(self.delete_resume)
        delete_btn.setStyleSheet("background-color: #d83b01;")
        delete_layout.addWidget(delete_btn)
        delete_layout.addStretch()
        resume_layout.addLayout(delete_layout)
        
        self.resume_count_label = QLabel("已上传简历：0 份")
        upload_layout.addWidget(self.resume_count_label)
        upload_layout.addStretch()
        resume_layout.addLayout(upload_layout)
        
        # 简历列表
        self.resume_list = QListWidget()
        self.resume_list.setMaximumHeight(150)
        resume_layout.addWidget(self.resume_list)
        
        layout.addWidget(resume_group)
        
        # JD分析区域
        jd_group = QGroupBox("职位描述分析")
        jd_layout = QVBoxLayout(jd_group)
        
        jd_layout.addWidget(QLabel("请输入职位描述 (JD)："))
        self.jd_input = QTextEdit()
        self.jd_input.setPlaceholderText("在此输入职位描述...")
        jd_layout.addWidget(self.jd_input)
        
        analyze_btn = QPushButton("分析JD并生成简历")
        analyze_btn.clicked.connect(self.analyze_and_generate)
        jd_layout.addWidget(analyze_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(jd_group)
        
        # 结果显示区域
        results_group = QGroupBox("分析结果")
        results_layout = QHBoxLayout(results_group)
        
        # JD分析结果
        jd_result_layout = QVBoxLayout()
        jd_result_layout.addWidget(QLabel("职位要求分析："))
        self.jd_result = StreamTextEdit()
        jd_result_layout.addWidget(self.jd_result)
        results_layout.addLayout(jd_result_layout)
        
        # 生成的简历
        resume_result_layout = QVBoxLayout()
        resume_result_layout.addWidget(QLabel("生成的简历："))
        self.resume_result = StreamTextEdit()
        resume_result_layout.addWidget(self.resume_result)
        results_layout.addLayout(resume_result_layout)
        
        layout.addWidget(results_group)
        
        # 底部状态区域
        bottom_layout = QHBoxLayout()
        
        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximumWidth(200)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        bottom_layout.addWidget(self.progress_bar)
        
        # 匹配度显示
        self.match_score_label = QLabel("匹配度：--")
        self.match_score_label.setStyleSheet("""
            QLabel {
                color: #0078d4;
                font-size: 14pt;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }
        """)
        bottom_layout.addWidget(self.match_score_label)
        
        layout.addLayout(bottom_layout)
        
        # 状态栏
        self.statusBar().setStyleSheet("""
            QStatusBar {
                background-color: #f0f0f0;
                color: #666;
                padding: 4px;
            }
        """)
        self.statusBar().showMessage("就绪")

        # 连接信号
        self.ai_worker.progress.connect(self.update_progress)
        self.ai_worker.match_score.connect(self.update_match_score)
        self.ai_worker.status_message.connect(self.update_status)

    def update_progress(self, value):
        """更新进度条"""
        self.progress_bar.setValue(value)

    def update_match_score(self, score):
        """更新匹配度显示"""
        self.match_score_label.setText(f"匹配度：{score}%")
        # 根据匹配度设置不同的颜色
        if score >= 80:
            color = "#107c10"  # 绿色
        elif score >= 60:
            color = "#ff8c00"  # 橙色
        else:
            color = "#d83b01"  # 红色
        self.match_score_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 14pt;
                font-weight: bold;
                padding: 5px;
                border: 1px solid #ddd;
                border-radius: 4px;
                background: white;
            }}
        """)

    def update_status(self, message):
        """更新状态栏消息"""
        self.statusBar().showMessage(message)

    def delete_resume(self):
        """删除选中的简历"""
        checked_items = []
        for i in range(self.resume_list.count()):
            item = self.resume_list.item(i)
            if item.checkState() == Qt.CheckState.Checked:
                checked_items.append(item.text())
        
        if not checked_items:
            QMessageBox.warning(self, "提示", "请先选择要删除的简历")
            return

        reply = QMessageBox.question(
            self, 
            "确认删除", 
            f"确定要删除选中的 {len(checked_items)} 份简历吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # 从数据库中删除
                deleted_count = self.assistant.delete_from_db(checked_items)
                if deleted_count > 0:
                    # 更新显示
                    self.load_resume_count()
                    QMessageBox.information(self, "成功", f"已删除 {deleted_count} 份简历")
                else:
                    raise Exception("未找到指定的简历")
            except Exception as e:
                QMessageBox.critical(self, "错误", f"删除失败: {str(e)}")

    def process_document(self, file_path):
        """处理文档"""
        return self.assistant.process_document(file_path)

    def upload_resumes(self):
        """上传多个简历"""
        file_names, _ = QFileDialog.getOpenFileNames(
            self,
            "选择简历文件",
            "",
            "简历文件 (*.pdf *.docx *.doc *.txt *.md)"
        )
        
        if not file_names:
            return
            
        success_count = 0
        failed_files = []
        
        for file_name in file_names:
            try:
                self.statusBar().showMessage(f"正在处理：{os.path.basename(file_name)}...")
                
                # 读取文件内容
                text = self.process_document(file_name)
                if not text:
                    raise Exception("无法读取文件内容")
                
                # 直接保存原始内容到数据库
                info = {
                    "content": text,  # 保存原始文本
                    "file_name": os.path.basename(file_name),
                    "upload_time": datetime.now().isoformat(),
                    "file_type": os.path.splitext(file_name)[1].lower()
                }
                self.assistant.save_to_db(info)
                
                success_count += 1
                
            except Exception as e:
                failed_files.append((os.path.basename(file_name), str(e)))
        
        # 更新显示
        self.load_resume_count()
        
        # 显示结果
        if success_count > 0:
            success_msg = f"成功上传 {success_count} 份简历"
            if failed_files:
                failed_msg = "\n\n上传失败的文件：\n" + "\n".join(
                    f"- {name}: {error}" for name, error in failed_files
                )
                QMessageBox.warning(self, "上传完成", success_msg + failed_msg)
            else:
                QMessageBox.information(self, "上传成功", success_msg)
        elif failed_files:
            failed_msg = "所有文件上传失败：\n" + "\n".join(
                f"- {name}: {error}" for name, error in failed_files
            )
            QMessageBox.critical(self, "上传失败", failed_msg)
        
        self.statusBar().showMessage("就绪")

    def append_message(self, sender, message):
        """添加消息到对话显示区域"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        formatted_message = f"[{timestamp}] {sender}：{message}\n"
        self.chat_display.append(formatted_message)
        self.chat_history.append({
            "sender": sender,
            "message": message,
            "timestamp": timestamp
        })

    def format_chat_history(self):
        """格式化对话历史"""
        return "\n".join([
            f"[{msg['timestamp']}] {msg['sender']}：{msg['message']}"
            for msg in self.chat_history[-10:]
        ])

    def analyze_and_generate(self):
        """分析JD并生成简历"""
        if not self.assistant.check_llm_ready():
            QMessageBox.warning(self, "提示", "请先在设置中配置API Key")
            self.show_settings()
            return
            
        jd_text = self.jd_input.toPlainText()
        if not jd_text:
            QMessageBox.warning(self, "提示", "请输入职位描述")
            return
        
        # 禁用按钮，防止重复提交
        self.sender().setEnabled(False)
        self.statusBar().showMessage("正在分析JD...")
        self.jd_result.clear()
        self.resume_result.clear()
        
        # 创建任务（设置60秒超时）
        task = AITask(
            task_type='analyze_jd',
            params={'text': jd_text},
            callback=self.handle_jd_analysis,
            timeout=60  # 60秒超时
        )
        
        # 添加到工作队列
        self.ai_worker.add_task(task)

    def handle_jd_analysis(self, jd_analysis):
        """处理JD分析结果"""
        try:
            # 流式显示分析结果
            formatted_analysis = self.format_jd_analysis(jd_analysis)
            self.jd_result.stream_text(formatted_analysis)
            
            # 生成简历
            self.statusBar().showMessage("正在生成简历...")
            
            # 创建生成简历的任务
            task = AITask(
                task_type='generate_resume',
                params={'jd_analysis': jd_analysis},
                callback=self.handle_resume_generation
            )
            
            # 添加到工作队列
            self.ai_worker.add_task(task)
            
        except Exception as e:
            self.statusBar().showMessage("处理失败")
            QMessageBox.critical(self, "错误", str(e))
        finally:
            # 重新启用按钮
            for btn in self.findChildren(QPushButton):
                if btn.text() == "分析JD并生成简历":
                    btn.setEnabled(True)

    def handle_resume_generation(self, result):
        """处理简历生成结果"""
        try:
            if isinstance(result, dict) and "resume" in result:
                self.resume_result.stream_text(result["resume"])
                self.statusBar().showMessage("简历生成完成")
            else:
                raise Exception("简历生成结果格式错误")
        except Exception as e:
            self.statusBar().showMessage("处理失败")
            QMessageBox.critical(self, "错误", str(e))

    def format_jd_analysis(self, jd_analysis):
        """格式化JD分析结果"""
        formatted = "职位要求分析：\n\n"
        
        # 必需技能
        formatted += "📌 必需技能：\n"
        for skill in jd_analysis["required_skills"]:
            formatted += f"  • {skill}\n"
        formatted += "\n"
        
        # 加分技能
        formatted += "✨ 加分技能：\n"
        for skill in jd_analysis["preferred_skills"]:
            formatted += f"  • {skill}\n"
        formatted += "\n"
        
        # 教育背景
        formatted += "🎓 教育要求：\n"
        formatted += f"  • 学历：{jd_analysis['education']['degree']}\n"
        formatted += f"  • 专业：{jd_analysis['education']['major']}\n\n"
        
        # 经验要求
        formatted += "💼 经验要求：\n"
        formatted += f"  • 年限：{jd_analysis['experience']['years']}\n"
        formatted += f"  • 行业：{jd_analysis['experience']['industry']}\n"
        formatted += f"  • 职位：{jd_analysis['experience']['position']}\n\n"
        
        # 工作职责
        formatted += "📋 工作职责：\n"
        for resp in jd_analysis["responsibilities"]:
            formatted += f"  • {resp}\n"
        formatted += "\n"
        
        # 公司信息
        formatted += "🏢 公司信息：\n"
        formatted += f"  • 行业：{jd_analysis['company_info']['industry']}\n"
        formatted += f"  • 规模：{jd_analysis['company_info']['scale']}\n"
        formatted += f"  • 阶段：{jd_analysis['company_info']['stage']}\n"
        
        return formatted

    def load_resume_count(self):
        """加载已有简历数量"""
        try:
            collection = self.assistant.vectordb._collection
            if collection:
                results = collection.get()
                if results and 'metadatas' in results:
                    # 只统计简历类型的文档
                    resume_metadatas = [m for m in results['metadatas'] 
                                      if m.get('type') == 'resume_info']
                    count = len(resume_metadatas)
                    self.resume_count_label.setText(f"已上传简历：{count} 份")
                    
                    # 更新简历列表
                    self.resume_list.clear()
                    for metadata in resume_metadatas:
                        file_name = metadata.get('file_name', '未命名简历')
                        item = QListWidgetItem(file_name)
                        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                        item.setCheckState(Qt.CheckState.Unchecked)
                        self.resume_list.addItem(item)
        except Exception as e:
            print(f"加载简历数量失败: {str(e)}")
            self.resume_count_label.setText("已上传简历：0 份")

    def closeEvent(self, event):
        """窗口关闭事件"""
        self.ai_worker.stop()
        self.ai_worker.wait()
        event.accept()

    def show_settings(self):
        """显示设置对话框"""
        dialog = QDialog(self)
        dialog.setWindowTitle("设置")
        dialog.setFixedWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        # API设置组
        api_group = QGroupBox("API 设置")
        api_layout = QVBoxLayout(api_group)
        
        # API Key输入
        key_layout = QHBoxLayout()
        key_layout.addWidget(QLabel("DeepSeek API Key:"))
        key_input = QLineEdit()
        key_input.setEchoMode(QLineEdit.EchoMode.Password)
        
        # 从数据库获取API Key
        current_key = self.assistant.get_api_key()
        if current_key:
            key_input.setText(current_key)
        
        key_layout.addWidget(key_input)
        
        # 测试按钮
        test_btn = QPushButton("测试")
        test_btn.setFixedWidth(60)
        test_btn.setStyleSheet("""
            QPushButton {
                background-color: #107c10;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 60px;
            }
            QPushButton:hover {
                background-color: #0b590b;
            }
        """)
        key_layout.addWidget(test_btn)
        
        api_layout.addLayout(key_layout)
        
        # 显示当前设置状态
        status_label = QLabel()
        if current_key:
            status_label.setText("✅ API配置已设置")
            status_label.setStyleSheet("color: #107c10;")
        else:
            status_label.setText("❌ 未设置API配置")
            status_label.setStyleSheet("color: #d83b01;")
        api_layout.addWidget(status_label)
        
        layout.addWidget(api_group)
        
        # 按钮区域
        button_layout = QHBoxLayout()
        save_btn = QPushButton("保存")
        cancel_btn = QPushButton("取消")
        
        save_btn.setStyleSheet("""
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
        """)
        
        cancel_btn.setStyleSheet("""
            QPushButton {
                background-color: #f0f0f0;
                color: #333;
                border: 1px solid #ddd;
                border-radius: 4px;
                padding: 8px 16px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e0e0e0;
            }
        """)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)
        
        def test_api():
            """测试API连接"""
            api_key = key_input.text().strip()
            if not api_key:
                QMessageBox.warning(dialog, "提示", "请先输入API Key")
                return
                
            test_btn.setEnabled(False)
            test_btn.setText("测试中...")
            
            try:
                # 临时设置环境变量
                os.environ["OPENAI_API_KEY"] = api_key
                os.environ["OPENAI_API_BASE"] = self.assistant.API_BASE_URL
                
                # 创建测试用的LLM实例
                llm = ChatOpenAI(
                    model_name="deepseek-chat",
                    temperature=0.7,
                    max_tokens=10
                )
                
                # 发送测试请求
                response = llm.invoke("测试")
                
                QMessageBox.information(dialog, "成功", "API连接测试成功!")
                status_label.setText("✅ API配置已验证")
                status_label.setStyleSheet("color: #107c10;")
                
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"API连接测试失败: {str(e)}")
                status_label.setText("❌ API配置验证失败")
                status_label.setStyleSheet("color: #d83b01;")
                
            finally:
                test_btn.setEnabled(True)
                test_btn.setText("测试")
        
        def save_settings():
            """保存设置"""
            try:
                api_key = key_input.text().strip()
                if not api_key:
                    QMessageBox.warning(dialog, "提示", "请输入API Key")
                    return
                
                # 保存到数据库
                self.assistant.save_api_key(api_key)
                
                # 更新环境变量
                os.environ["OPENAI_API_KEY"] = api_key
                os.environ["OPENAI_API_BASE"] = self.assistant.API_BASE_URL
                
                # 重新初始化LLM
                self.assistant.init_llm()
                
                QMessageBox.information(dialog, "成功", "设置已保存")
                dialog.accept()
            except Exception as e:
                QMessageBox.critical(dialog, "错误", f"保存设置失败: {str(e)}")
        
        test_btn.clicked.connect(test_api)
        save_btn.clicked.connect(save_settings)
        cancel_btn.clicked.connect(dialog.reject)
        
        dialog.exec()

class StreamTextEdit(QTextEdit):
    """支持流式输出的文本编辑器"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.current_text = ""
        
    def stream_text(self, text):
        """直接显示文本"""
        self.setText(text)

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec()) 