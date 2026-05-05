# Local settings for production environment
# This file is optional and can be used to override settings
# for local development or specific deployment environments.
# Add your local overrides here.

# AI API配置示例
# 取消下面的注释并填入你的API密钥来启用AI功能

# 方式1: 使用环境变量（推荐）
# 在系统环境变量中设置：
# - AI_PROVIDER=openai  # 或 qwen, wenxin, zhipu, deepseek
# - AI_API_KEY=your_api_key_here
# - AI_API_SECRET=your_secret_key_here  # 仅文心一言需要
# - AI_API_BASE=https://api.openai.com/v1  # 可选，自定义端点
# - AI_MODEL=gpt-3.5-turbo  # 或 qwen-turbo, glm-4, deepseek-chat 等

# 方式2: 直接在这里配置（不推荐用于生产环境）
# import os
# os.environ['AI_PROVIDER'] = 'openai'
# os.environ['AI_API_KEY'] = 'your-api-key-here'
# os.environ['AI_MODEL'] = 'gpt-3.5-turbo'

# 支持的AI提供商配置说明：
# 
# 1. OpenAI (默认)
#    AI_PROVIDER=openai
#    AI_API_KEY=sk-...
#    AI_MODEL=gpt-3.5-turbo 或 gpt-4
#    AI_API_BASE=https://api.openai.com/v1 (默认)
#
# 2. 通义千问（阿里云）
#    AI_PROVIDER=qwen 或 tongyi
#    AI_API_KEY=sk-...
#    AI_MODEL=qwen-turbo 或 qwen-plus
#    AI_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
#
# 3. 文心一言（百度）
#    AI_PROVIDER=wenxin 或 baidu
#    AI_API_KEY=your_api_key
#    AI_API_SECRET=your_secret_key
#    AI_MODEL=ernie-bot-turbo
#
# 4. 智谱AI
#    AI_PROVIDER=zhipu
#    AI_API_KEY=your_api_key
#    AI_MODEL=glm-4
#    AI_API_BASE=https://open.bigmodel.cn/api/paas/v4/chat/completions
#
# 5. DeepSeek
#    AI_PROVIDER=deepseek
#    AI_API_KEY=sk-your_deepseek_api_key
#    AI_MODEL=deepseek-chat 或 deepseek-coder
#    AI_API_BASE=https://api.deepseek.com/v1 (默认)

# This file intentionally left mostly empty
# Override settings here as needed for your local environment
import os

# ============================================
# AI API配置 - 香港可用服务
# ============================================

# 方案1: DeepSeek（推荐，香港可用，性价比高）
os.environ['AI_PROVIDER'] = 'deepseek'
os.environ['AI_API_KEY'] = 'sk-3d4c78e82ee74d218e1f42808be913e5'
os.environ['AI_API_BASE'] = 'https://api.deepseek.com/v1'  # DeepSeek API端点
os.environ['AI_MODEL'] = 'deepseek-chat'

# local.py 在 base.py 之后导入；只改 os.environ 不会回写 base.py 已经读取过的设置。
# AIService 读取的是 django.conf.settings，因此这里需要直接覆盖 Django settings。
AI_PROVIDER = os.environ['AI_PROVIDER']
AI_API_KEY = os.environ['AI_API_KEY']
AI_API_BASE = os.environ['AI_API_BASE']
AI_MODEL = os.environ['AI_MODEL']

# 方案2: 通义千问（阿里云，香港可用，备选方案）
# 如需使用通义千问，取消下面的注释并注释掉上面的DeepSeek配置
#
#os.environ['AI_API_KEY'] = ''
#os.environ['AI_PROVIDER'] = 'OPENAI'
#os.environ['AI_MODEL'] = 'gpt-5.4'
#os.environ['AI_API_BASE'] = 'https://api.mcmdo.com/v1/'

# ============================================
# 配置说明：
# 1. DeepSeek: 香港可用，价格便宜，性能优秀
#    获取API Key: https://platform.deepseek.com/api_keys
#    支持模型: deepseek-chat（通用）, deepseek-coder（代码专用）
#
# 2. 通义千问: 阿里云服务，香港可用，中文理解能力强
#    获取API Key: https://dashscope.console.aliyun.com/
#    支持模型: qwen-turbo, qwen-plus, qwen-max
# ============================================
