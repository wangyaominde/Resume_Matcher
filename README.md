# 智能简历助手

基于 DeepSeek 和 LangChain 的智能简历助手，帮助用户智能分析职位要求并生成匹配度最高的简历。

## 功能特点

- 📄 支持多种格式简历上传（PDF、Word、Markdown、TXT）
- 🔍 智能职位描述（JD）分析
- 🎯 简历匹配度评估
- ✨ 智能简历生成
- 💼 简历库管理
- 🔐 安全的API密钥管理

## 系统要求

- Python 3.12
- PyQt6
- 操作系统：Windows/macOS/Linux

## 安装说明

1. 克隆项目：
```bash
git clone https://github.com/wangyaominde/Resume_Matcher.git
cd Resume_Matcher
```

2. 安装依赖：
```bash
pip install -r requirements.txt
```

3. 配置 DeepSeek API：
- 在应用程序设置中配置您的 DeepSeek API Key
- API Key 将被安全加密存储

4. 配置环境变量（可选）：
```bash
pip install -r requirements.txt
```

# 激活虚拟环境
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

在首次运行前，您需要：

1. 下载模型到本地（仅需执行一次）：
```bash
python download_model.py
```


## 使用说明

1. 启动应用：
```bash
python app.py
```

2. 首次使用：
   - 点击右上角的"设置"按钮
   - 输入您的 DeepSeek API Key
   - 测试并保存配置

3. 上传简历：
   - 点击"上传简历"按钮
   - 选择一个或多个简历文件
   - 支持格式：PDF、DOCX、DOC、TXT、MD

4. 分析职位：
   - 在职位描述输入框中粘贴 JD
   - 点击"分析JD并生成简历"
   - 等待系统分析并生成匹配的简历

5. 管理简历库：
   - 查看已上传的简历列表
   - 选择并删除不需要的简历

## 主要特性说明

### 智能 JD 分析
- 自动提取关键技能要求
- 识别必需和加分技能
- 分析教育和经验要求
- 提取工作职责和公司信息

### 简历生成
- 基于 JD 智能匹配最适合的简历内容
- 自动计算匹配度评分
- 生成针对性优化的简历内容

### 简历库管理
- 集中管理所有上传的简历
- 支持批量上传和删除
- 安全的本地存储

## 技术栈

- 前端界面：PyQt6
- AI 模型：DeepSeek
- 向量数据库：Chroma
- 文档处理：
  - PDF：pdfplumber, PyPDF2
  - Word：python-docx
  - 图像：Pillow, pytesseract
  - Markdown：markdown

## 注意事项

1. API 密钥安全：
   - 请勿在公共环境泄露您的 API 密钥
   - API 密钥将被加密存储在本地数据库中

2. 文件处理：
   - 建议上传小于 10MB 的文件
   - 确保文档格式规范，避免加密或损坏的文件

3. 系统资源：
   - 处理大量简历时可能需要较多系统资源
   - 建议保持足够的磁盘空间

## 常见问题

1. Q: 为什么无法连接到 API？
   A: 请检查您的 API Key 是否正确，以及网络连接是否正常。

2. Q: 上传 PDF 失败怎么办？
   A: 确保 PDF 文件未加密，且为文本型 PDF（非扫描件）。

3. Q: 如何提高简历匹配度？
   A: 确保简历库中的简历内容完整，且与目标职位相关性高。

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交 Issue 或 Pull Request。 