#!/bin/bash

# 设置颜色输出
GREEN='\033[0;32m'
BLUE='\033[0;34m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# 检查Python3是否安装
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}错误: 请先安装 Python3${NC}"
    return 1
fi

# 检查是否存在venv目录
if [ ! -d "venv" ]; then
    echo -e "${BLUE}首次运行，正在创建虚拟环境...${NC}"
    python3 -m venv venv
    if [ $? -ne 0 ]; then
        echo -e "${RED}创建虚拟环境失败${NC}"
        return 1
    fi
    source venv/bin/activate || return 1
    echo -e "${BLUE}正在安装依赖...${NC}"
    pip install -r requirements.txt
    if [ $? -ne 0 ]; then
        echo -e "${RED}安装依赖失败${NC}"
        return 1
    fi
    echo -e "${GREEN}环境配置完成！${NC}"
else
    echo -e "${BLUE}使用已存在的虚拟环境${NC}"
    source venv/bin/activate || return 1
fi

# 运行应用
echo -e "${GREEN}启动应用...${NC}"
python app.py 