# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_all

block_cipher = None

# 收集所有需要的数据文件和模块
datas = []
binaries = []
hiddenimports = []

# 收集 chromadb 的所有相关文件和模块
chromadb_datas, chromadb_binaries, chromadb_hiddenimports = collect_all('chromadb')
datas.extend(chromadb_datas)
binaries.extend(chromadb_binaries)
hiddenimports.extend(chromadb_hiddenimports)

# 添加模型文件
model_path = os.path.join('models', 'sentence-transformers')
if os.path.exists(model_path):
    datas.extend([(model_path, 'models/sentence-transformers')])

# 添加其他资源文件
datas.extend([('logo.png', '.')])

# 收集其他相关的数据文件
datas += collect_data_files('pydantic')
datas += collect_data_files('onnxruntime')

# 添加额外的 chromadb 模块
extra_chromadb_imports = [
    'chromadb.api',
    'chromadb.config',
    'chromadb.utils',
    'chromadb.utils.embedding_functions',
    'chromadb.db',
    'chromadb.segment',
    'chromadb.telemetry',
    'chromadb.types',
    'chromadb.errors',
    'chromadb.migrations',
    'chromadb.execution',
    'chromadb.execution.executor',
    'chromadb.execution.executor.local',
    'chromadb.api.models',
    'chromadb.api.types',
    'chromadb.api.client',
    'chromadb.api.segment',
    'chromadb.api.fastapi',
    'chromadb.server',
    'chromadb.store',
]

# 基础隐藏导入
base_hiddenimports = [
    'sentence_transformers',
    'transformers',
    'torch',
    'numpy',
    'tqdm',
    'regex',
    'requests',
    'packaging',
    'filelock',
    'yaml',
    'typing_extensions',
    'importlib_metadata',
    'huggingface_hub',
    'pydantic',
    'pydantic.deprecated',
    'pydantic.deprecated.decorator',
    'pydantic.json',
    'pydantic.dataclasses',
    'pydantic.class_validators',
    'pydantic.error_wrappers',
    'pydantic.utils',
    'pydantic.typing',
    'pydantic.types',
    'pydantic.fields',
    'pydantic.schema',
    'pydantic.networks',
    'pydantic.datetime_parse',
    'pydantic.color',
    'langchain',
    'langchain.chains',
    'langchain.prompts',
    'langchain.schema',
    'langchain_core',
    'langchain_core.prompts',
    'langchain_core.messages',
    'langchain_core.language_models',
    'langchain_core.callbacks',
    'langchain_core.outputs',
    'langchain_openai',
    'langchain_community',
    'langchain_huggingface',
    'langchain_chroma',
    'onnxruntime',
    'tokenizers',
]

# 合并所有隐藏导入
hiddenimports.extend(base_hiddenimports)
hiddenimports.extend(extra_chromadb_imports)
hiddenimports.extend(collect_submodules('pydantic'))
hiddenimports.extend(collect_submodules('chromadb'))

# 需要排除的目录和文件
excludes = [
    'db',  # 排除数据库目录
    '__pycache__',  # 排除 Python 缓存
    '*.pyc',  # 排除编译的 Python 文件
    '*.pyo',  # 排除优化的 Python 文件
    '*.pyd',  # 排除 Python DLL 文件
    '.DS_Store',  # 排除 macOS 系统文件
    'Thumbs.db',  # 排除 Windows 系统文件
    '.git',  # 排除 git 目录
    '.env',  # 排除环境变量文件
    '*.log',  # 排除日志文件
    'temp',  # 排除临时目录
    'tmp',  # 排除临时目录
]

a = Analysis(
    ['app.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,  # 添加排除列表
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

# 添加缺失的模块文件
def add_files(a):
    import os
    import pydantic
    import chromadb
    
    # 添加 pydantic 文件
    pydantic_path = os.path.dirname(pydantic.__file__)
    a.datas += [(os.path.join('pydantic', 'deprecated', 'decorator.py'), 
                 os.path.join(pydantic_path, 'deprecated', 'decorator.py'), 
                 'DATA')]
    
    # 添加 chromadb 文件
    chromadb_path = os.path.dirname(chromadb.__file__)
    executor_path = os.path.join(chromadb_path, 'execution', 'executor')
    if os.path.exists(executor_path):
        for root, dirs, files in os.walk(executor_path):
            # 排除不需要的目录
            dirs[:] = [d for d in dirs if d not in ['__pycache__']]
            for file in files:
                if file.endswith('.py') and not file.startswith('__'):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, chromadb_path)
                    a.datas += [(os.path.join('chromadb', rel_path), full_path, 'DATA')]

add_files(a)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='Resume_Matcher',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # 临时改为 True 以查看错误信息
    icon='logo.png',
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
) 