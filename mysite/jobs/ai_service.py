"""
AI服务模块 - 集成多种大模型API进行简历分析
支持：OpenAI、通义千问、文心一言、智谱AI、DeepSeek等
"""
import os
import json
import logging
from typing import Optional, Dict
from django.conf import settings

logger = logging.getLogger(__name__)


class AIService:
    """AI服务基类"""
    
    def __init__(self):
        self.api_key = getattr(settings, 'AI_API_KEY', None)
        self.api_base = getattr(settings, 'AI_API_BASE', None)
        self.model = getattr(settings, 'AI_MODEL', 'gpt-3.5-turbo')
        self.provider = getattr(settings, 'AI_PROVIDER', 'openai').lower()
    
    def analyze_resume(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """
        分析简历并生成报告
        
        Args:
            resume_text: 简历文本内容
            user_info: 用户信息（可选）
        
        Returns:
            AI生成的报告文本
        """
        if not self.api_key:
            logger.warning("AI API Key未配置，返回默认报告")
            return self._generate_default_report(resume_text)
        
        try:
            if self.provider == 'openai':
                return self._call_openai_api(resume_text, user_info)
            elif self.provider == 'qwen' or self.provider == 'tongyi':
                return self._call_qwen_api(resume_text, user_info)
            elif self.provider == 'wenxin' or self.provider == 'baidu':
                return self._call_wenxin_api(resume_text, user_info)
            elif self.provider == 'zhipu':
                return self._call_zhipu_api(resume_text, user_info)
            elif self.provider == 'deepseek':
                return self._call_deepseek_api(resume_text, user_info)
            else:
                logger.warning(f"不支持的AI提供商: {self.provider}，使用OpenAI")
                return self._call_openai_api(resume_text, user_info)
        except Exception as e:
            logger.error(f"AI API调用失败: {str(e)}", exc_info=True)
            return self._generate_default_report(resume_text)
    
    def _call_openai_api(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """调用OpenAI API"""
        try:
            import openai  # type: ignore[import-untyped]
            
            # 如果没有设置api_base，使用默认的OpenAI端点
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base or "https://api.openai.com/v1"
            )
            
            prompt = self._build_prompt(resume_text, user_info)
            
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "你是一位专业的职业规划顾问和简历分析专家。请根据用户的简历内容，生成一份详细的职场竞争力分析报告。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except ImportError:
            logger.error("openai库未安装，请运行: pip install openai")
            return self._generate_default_report(resume_text)
    
    def _call_qwen_api(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """调用通义千问API（阿里云）"""
        try:
            import openai  # type: ignore[import-untyped]
            
            # 通义千问使用OpenAI兼容的接口
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base or "https://dashscope.aliyuncs.com/compatible-mode/v1"
            )
            
            prompt = self._build_prompt(resume_text, user_info)
            
            response = client.chat.completions.create(
                model=self.model or "qwen-turbo",
                messages=[
                    {"role": "system", "content": "你是一位专业的职业规划顾问和简历分析专家。请根据用户的简历内容，生成一份详细的职场竞争力分析报告。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except ImportError:
            logger.error("openai库未安装，请运行: pip install openai")
            return self._generate_default_report(resume_text)
        except Exception as e:
            logger.error(f"通义千问API调用失败: {str(e)}")
            return self._generate_default_report(resume_text)
    
    def _call_wenxin_api(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """调用文心一言API（百度）"""
        try:
            import requests
            
            # 文心一言API端点
            api_url = self.api_base or "https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions"
            
            prompt = self._build_prompt(resume_text, user_info)
            
            # 获取access_token（需要先调用token接口）
            token_url = "https://aip.baidubce.com/oauth/2.0/token"
            token_params = {
                "grant_type": "client_credentials",
                "client_id": self.api_key,  # API Key
                "client_secret": getattr(settings, 'AI_API_SECRET', '')  # Secret Key
            }
            
            token_response = requests.post(token_url, params=token_params)
            access_token = token_response.json().get("access_token")
            
            if not access_token:
                raise Exception("无法获取文心一言access_token")
            
            # 调用对话接口
            headers = {"Content-Type": "application/json"}
            data = {
                "messages": [
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_output_tokens": 2000
            }
            
            response = requests.post(
                f"{api_url}?access_token={access_token}",
                headers=headers,
                json=data
            )
            
            result = response.json()
            return result.get("result", self._generate_default_report(resume_text))
        except ImportError:
            logger.error("requests库未安装，请运行: pip install requests")
            return self._generate_default_report(resume_text)
        except Exception as e:
            logger.error(f"文心一言API调用失败: {str(e)}")
            return self._generate_default_report(resume_text)
    
    def _call_zhipu_api(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """调用智谱AI API"""
        try:
            import requests
            
            api_url = self.api_base or "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            
            prompt = self._build_prompt(resume_text, user_info)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model or "glm-4",
                "messages": [
                    {"role": "system", "content": "你是一位专业的职业规划顾问和简历分析专家。请根据用户的简历内容，生成一份详细的职场竞争力分析报告。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.7,
                "max_tokens": 2000
            }
            
            response = requests.post(api_url, headers=headers, json=data)
            result = response.json()
            
            if "choices" in result and len(result["choices"]) > 0:
                return result["choices"][0]["message"]["content"]
            else:
                raise Exception(f"API返回格式错误: {result}")
        except ImportError:
            logger.error("requests库未安装，请运行: pip install requests")
            return self._generate_default_report(resume_text)
        except Exception as e:
            logger.error(f"智谱AI API调用失败: {str(e)}")
            return self._generate_default_report(resume_text)
    
    def _call_deepseek_api(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """调用DeepSeek API"""
        try:
            import openai  # type: ignore[import-untyped]
            
            # DeepSeek使用OpenAI兼容的接口
            client = openai.OpenAI(
                api_key=self.api_key,
                base_url=self.api_base or "https://api.deepseek.com/v1"
            )
            
            prompt = self._build_prompt(resume_text, user_info)
            
            response = client.chat.completions.create(
                model=self.model or "deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是一位专业的职业规划顾问和简历分析专家。请根据用户的简历内容，生成一份详细的职场竞争力分析报告。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            return response.choices[0].message.content
        except ImportError:
            logger.error("openai库未安装，请运行: pip install openai")
            return self._generate_default_report(resume_text)
        except Exception as e:
            logger.error(f"DeepSeek API调用失败: {str(e)}")
            return self._generate_default_report(resume_text)
    
    def _build_prompt(self, resume_text: str, user_info: Optional[Dict] = None) -> str:
        """构建AI提示词"""
        # 构建用户确认信息的说明
        confirmed_info = ""
        if user_info:
            confirmed_parts = []
            if user_info.get('confirmed_school'):
                confirmed_parts.append(f"学校：{user_info['confirmed_school']}")
            if user_info.get('confirmed_major'):
                confirmed_parts.append(f"专业：{user_info['confirmed_major']}")
            if user_info.get('confirmed_internship'):
                confirmed_parts.append(f"实习经历：{user_info['confirmed_internship']}")
            if user_info.get('confirmed_hobbies'):
                confirmed_parts.append(f"职业兴趣：{user_info['confirmed_hobbies']}")
            if user_info.get('confirmed_skills'):
                skills_str = ', '.join(user_info['confirmed_skills']) if isinstance(user_info['confirmed_skills'], list) else str(user_info['confirmed_skills'])
                confirmed_parts.append(f"核心技能：{skills_str}")
            
            if confirmed_parts:
                confirmed_info = "\n\n用户确认的关键信息（请重点参考）：\n" + "\n".join(confirmed_parts) + "\n"
        
        prompt = f"""请分析以下简历内容，生成一份简洁明了的职场竞争力分析报告。报告需要在一屏内完整展示，内容要精炼，避免冗长描述。

简历内容：
{resume_text[:3000]}
{confirmed_info}

【重要格式要求】请严格按照以下格式生成报告，确保内容简洁：

【AI职场竞争力报告】

☆ 匹配解析报告
【字数限制：80-120字，约2-3句话】
请用精炼的语言概括候选人的核心优势、专业背景和职业潜力，突出最关键的亮点。直接点明核心价值，避免冗长描述。
示例格式：候选人毕业于[学校][专业]，具有[核心优势1]和[核心优势2]的复合型人才潜质。通过[关键经历]，展现了[核心能力]，能够[职业价值]。

💼 核心竞争力指标评估
【必须输出】此部分必须包含4个竞争力指标的量化评分，每个指标必须给出0-100之间的具体整数分数。

【必须输出的格式】（请严格复制此格式并填写数字）：
专业深度：[数字]分
学习敏锐度：[数字]分
逻辑架构能力：[数字]分
抗压韧性：[数字]分

【评分标准】：
1. 专业深度：根据技术栈深度、项目复杂度、教育背景、专业认证等评估（0-40初级，41-70中级，71-85高级，86-100专家级）
2. 学习敏锐度：根据学习经历、新技能掌握速度、自我提升记录、跨领域学习能力等评估（0-40较慢，41-70一般，71-85较快，86-100极快）
3. 逻辑架构能力：根据项目复杂度、问题解决能力、系统设计经验、架构思维等评估（0-40基础，41-70良好，71-85优秀，86-100卓越）
4. 抗压韧性：根据工作强度、项目压力、困难克服经历、持续工作能力等评估（0-40较弱，41-70一般，71-85较强，86-100极强）

| 建议投递方向
【格式要求】仅列出3-4个岗位名称，每个岗位名称单独一行，不需要详细理由。
示例格式：
产品设计师
UI/UX设计
设计工程师
交互设计师

【总体要求】：
1. 整个报告总字数控制在300字以内
2. 匹配解析报告部分严格控制在80-120字（2-3句话）
3. 核心竞争力指标的打分必须保留，格式严格按要求（4个指标，每个0-100分）
4. 岗位推荐仅列出岗位名称，不写详细理由（3-4个岗位）
5. 省略提升建议和竞争力排名部分
6. 优先参考用户确认的关键信息（学校、专业、实习经历、职业兴趣、核心技能）"""
        
        return prompt
    
    def _generate_default_report(self, resume_text: str) -> str:
        """生成默认报告（当API不可用时）"""
        from django.utils import timezone
        
        return f"""【AI职场竞争力报告】

☆ 匹配解析报告
请配置AI API密钥以获得详细的职场竞争力分析报告。

💼 核心竞争力指标评估
专业深度: 待评估（需要AI服务支持）
学习敏锐度: 待评估（需要AI服务支持）
逻辑架构能力: 待评估（需要AI服务支持）
抗压韧性: 待评估（需要AI服务支持）

| 建议投递方向
请完善简历信息以获得更精准推荐

注：此报告为默认报告。请配置AI API密钥以获得更详细的分析。
"""


# 全局AI服务实例
_ai_service = None

def get_ai_service() -> AIService:
    """获取AI服务实例（单例模式）"""
    global _ai_service
    if _ai_service is None:
        _ai_service = AIService()
    return _ai_service
