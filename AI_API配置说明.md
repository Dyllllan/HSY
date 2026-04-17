# AI大模型API配置说明

本文档说明如何配置AI分析功能，接入大模型API进行简历分析。

## 📋 支持的AI提供商

1. **OpenAI** (GPT-3.5/GPT-4)
2. **通义千问** (阿里云)
3. **文心一言** (百度)
4. **智谱AI** (GLM)
5. **DeepSeek** (DeepSeek Chat/Coder)

## 🔧 配置方法

### 方法1: 使用环境变量（推荐）

在系统环境变量中设置以下变量：

#### OpenAI配置
```bash
export AI_PROVIDER=openai
export AI_API_KEY=sk-your-openai-api-key
export AI_MODEL=gpt-3.5-turbo
```

#### 通义千问配置
```bash
export AI_PROVIDER=qwen
export AI_API_KEY=sk-your-qwen-api-key
export AI_MODEL=qwen-turbo
export AI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

#### 文心一言配置
```bash
export AI_PROVIDER=wenxin
export AI_API_KEY=your-baidu-api-key
export AI_API_SECRET=your-baidu-secret-key
export AI_MODEL=ernie-bot-turbo
```

#### 智谱AI配置
```bash
export AI_PROVIDER=zhipu
export AI_API_KEY=your-zhipu-api-key
export AI_MODEL=glm-4
export AI_API_BASE=https://open.bigmodel.cn/api/paas/v4/chat/completions
```

#### DeepSeek配置
```bash
export AI_PROVIDER=deepseek
export AI_API_KEY=sk-your-deepseek-api-key
export AI_MODEL=deepseek-chat
export AI_API_BASE=https://api.deepseek.com/v1
```

### 方法2: 在local.py中配置

编辑 `mysite/local/settings/local.py` 文件，取消注释并填入配置：

```python
import os
os.environ['AI_PROVIDER'] = 'openai'
os.environ['AI_API_KEY'] = 'your-api-key-here'
os.environ['AI_MODEL'] = 'gpt-3.5-turbo'
```

## 📦 安装依赖

确保已安装所需的Python包：

```bash
pip install -r requirements.txt
```

主要依赖包括：
- `openai>=1.0.0` - OpenAI SDK（也用于通义千问、DeepSeek）
- `requests>=2.31.0` - HTTP请求库
- `PyPDF2>=3.0.0` - PDF解析
- `python-docx>=1.1.0` - DOCX解析
- `pdfplumber>=0.10.0` - PDF解析备选方案

## 🔑 获取API密钥

### OpenAI
1. 访问 https://platform.openai.com/
2. 注册/登录账号
3. 在 API Keys 页面创建新密钥

### 通义千问（阿里云）
1. 访问 https://dashscope.console.aliyun.com/
2. 开通DashScope服务
3. 在API-KEY管理页面创建密钥

### 文心一言（百度）
1. 访问 https://cloud.baidu.com/
2. 开通千帆大模型服务
3. 创建应用获取API Key和Secret Key

### 智谱AI
1. 访问 https://open.bigmodel.cn/
2. 注册账号并开通服务
3. 在控制台获取API Key

### DeepSeek
1. 访问 https://platform.deepseek.com/
2. 注册/登录账号
3. 在 API Keys 页面创建新密钥
4. 支持的模型：
   - `deepseek-chat` - 通用对话模型
   - `deepseek-coder` - 代码专用模型

## 🚀 使用说明

配置完成后，AI分析功能会自动启用：

1. 用户上传简历（PDF或DOCX格式）
2. 系统自动提取简历文本
3. 调用配置的大模型API进行分析
4. 生成详细的职场竞争力报告

## ⚠️ 注意事项

1. **API密钥安全**：不要将API密钥提交到代码仓库，使用环境变量或local.py（已加入.gitignore）
2. **费用控制**：注意API调用费用，建议设置使用限额
3. **文件大小**：简历文件建议不超过10MB
4. **网络连接**：确保服务器能访问对应的API端点

## 🐛 故障排查

### API调用失败
- 检查API密钥是否正确
- 确认网络连接正常
- 查看Django日志获取详细错误信息

### 简历解析失败
- 确认文件格式为PDF或DOCX
- 检查文件是否损坏
- 查看日志中的具体错误信息

### 返回默认报告
- 检查API配置是否正确
- 确认API密钥有效且有余额
- 查看日志了解失败原因

## 📝 测试配置

配置完成后，可以通过以下方式测试：

1. 登录系统
2. 进入"AI职场导航"页面
3. 上传一份测试简历
4. 点击"分析简历"按钮
5. 查看生成的报告

如果看到详细的AI分析报告，说明配置成功！
