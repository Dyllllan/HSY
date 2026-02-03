"""
简历初步信息提取器 - 使用AI提取学校、专业、实习经历、爱好等基本信息
"""
import logging
from typing import Dict, List, Optional
from django.conf import settings

logger = logging.getLogger(__name__)


class ResumeExtractor:
    """简历信息提取器"""
    
    def __init__(self):
        from .ai_service import get_ai_service
        self.ai_service = get_ai_service()
    
    def extract_basic_info(self, resume_text: str) -> Dict:
        """
        从简历文本中提取基本信息
        
        Args:
            resume_text: 简历文本内容
        
        Returns:
            包含提取信息的字典
        """
        if not resume_text:
            return self._get_empty_info()
        
        try:
            # 构建提取提示词
            prompt = self._build_extraction_prompt(resume_text)
            
            # 调用AI提取
            if self.ai_service.api_key:
                extracted_text = self._call_ai_extraction(prompt)
                return self._parse_extraction_result(extracted_text)
            else:
                # 如果没有配置AI，尝试简单的正则提取
                return self._simple_extract(resume_text)
        except Exception as e:
            logger.error(f"提取简历信息失败: {str(e)}", exc_info=True)
            return self._simple_extract(resume_text)
    
    def _build_extraction_prompt(self, resume_text: str) -> str:
        """构建AI提取提示词"""
        prompt = f"""请从以下简历文本中提取关键信息，并以JSON格式返回：

简历文本：
{resume_text[:2000]}

请提取以下信息并返回JSON格式：
{{
    "school": "学校名称（如：北京邮电大学）",
    "major": "专业名称（如：数字媒体技术）",
    "internship_summary": "实习经历总结（简要描述主要实习经历，如：字节跳动实习经历，参与过某金融App视觉升级）",
    "hobbies": "爱好和职业兴趣（如：喜欢互联网大厂氛围）",
    "skills": ["技能1", "技能2", "技能3"]  // 核心技能列表，如：["Figma", "React", "UI设计"]
}}

要求：
1. 如果某项信息无法提取，返回空字符串或空数组
2. 技能列表最多提取5-8个核心技能
3. 实习经历总结要简洁，控制在100字以内
4. 直接返回JSON，不要添加其他说明文字
"""
        return prompt
    
    def _call_ai_extraction(self, prompt: str) -> str:
        """调用AI进行信息提取"""
        try:
            import openai
            
            client = openai.OpenAI(
                api_key=self.ai_service.api_key,
                base_url=self.ai_service.api_base or "https://api.openai.com/v1"
            )
            
            response = client.chat.completions.create(
                model=self.ai_service.model or "gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "你是一个专业的简历信息提取助手。请严格按照JSON格式返回提取的信息，不要添加任何其他文字说明。"},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"AI提取调用失败: {str(e)}")
            return ""
    
    def _parse_extraction_result(self, extracted_text: str) -> Dict:
        """解析AI返回的提取结果"""
        import json
        import re
        
        try:
            # 尝试直接解析JSON
            # 移除可能的markdown代码块标记
            extracted_text = re.sub(r'```json\s*', '', extracted_text)
            extracted_text = re.sub(r'```\s*', '', extracted_text)
            extracted_text = extracted_text.strip()
            
            # 尝试提取JSON对象
            json_match = re.search(r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}', extracted_text, re.DOTALL)
            if json_match:
                extracted_text = json_match.group(0)
            
            data = json.loads(extracted_text)
            
            return {
                'school': data.get('school', '').strip(),
                'major': data.get('major', '').strip(),
                'internship_summary': data.get('internship_summary', '').strip(),
                'hobbies': data.get('hobbies', '').strip(),
                'skills': data.get('skills', []) if isinstance(data.get('skills'), list) else []
            }
        except json.JSONDecodeError as e:
            logger.warning(f"JSON解析失败，尝试简单提取: {str(e)}")
            return self._simple_extract_from_text(extracted_text)
        except Exception as e:
            logger.error(f"解析提取结果失败: {str(e)}")
            return self._get_empty_info()
    
    def _simple_extract_from_text(self, text: str) -> Dict:
        """从文本中简单提取信息（备用方案）"""
        import re
        
        info = self._get_empty_info()
        
        # 提取学校（常见模式）
        school_patterns = [
            r'([\u4e00-\u9fa5]+大学)',
            r'([\u4e00-\u9fa5]+学院)',
            r'([\u4e00-\u9fa5]+科技大学)',
        ]
        for pattern in school_patterns:
            match = re.search(pattern, text)
            if match:
                info['school'] = match.group(1)
                break
        
        # 提取专业（通常在"专业"、"专业方向"等关键词后）
        major_match = re.search(r'专业[：:方向]*[：:]\s*([^\n，,；;]+)', text)
        if major_match:
            info['major'] = major_match.group(1).strip()
        
        # 提取技能（常见技能关键词）
        skill_keywords = ['Python', 'Java', 'JavaScript', 'React', 'Vue', 'Figma', 'UI设计', '前端', '后端', '数据库']
        found_skills = []
        for keyword in skill_keywords:
            if keyword in text:
                found_skills.append(keyword)
        info['skills'] = found_skills[:5]  # 最多5个
        
        return info
    
    def _simple_extract(self, resume_text: str) -> Dict:
        """简单提取（不使用AI）"""
        import re
        
        info = self._get_empty_info()
        
        # 提取学校
        school_match = re.search(r'([\u4e00-\u9fa5]+(?:大学|学院|科技大学))', resume_text)
        if school_match:
            info['school'] = school_match.group(1)
        
        # 提取专业
        major_match = re.search(r'专业[：:方向]*[：:]\s*([^\n，,；;]+)', resume_text)
        if not major_match:
            major_match = re.search(r'([\u4e00-\u9fa5]+(?:工程|技术|科学|管理|设计|艺术))', resume_text)
        if major_match:
            info['major'] = major_match.group(1).strip()
        
        # 提取实习经历关键词
        internship_keywords = ['实习', 'internship', '字节跳动', '腾讯', '阿里', '百度', '美团', '滴滴']
        internship_found = False
        for keyword in internship_keywords:
            if keyword in resume_text:
                internship_found = True
                # 尝试提取相关句子
                sentences = re.split(r'[。！？\n]', resume_text)
                for sentence in sentences:
                    if keyword in sentence and len(sentence) < 100:
                        info['internship_summary'] = sentence.strip()
                        break
                if info['internship_summary']:
                    break
        
        # 提取技能
        skill_keywords = ['Python', 'Java', 'JavaScript', 'React', 'Vue', 'Angular', 'Node.js', 
                         'Figma', 'Sketch', 'UI设计', 'UX设计', '前端', '后端', '全栈',
                         'MySQL', 'MongoDB', 'Redis', 'Docker', 'Kubernetes']
        found_skills = []
        for keyword in skill_keywords:
            if keyword in resume_text:
                found_skills.append(keyword)
        info['skills'] = list(set(found_skills))[:8]  # 去重并限制数量
        
        return info
    
    def _get_empty_info(self) -> Dict:
        """返回空的信息结构"""
        return {
            'school': '',
            'major': '',
            'internship_summary': '',
            'hobbies': '',
            'skills': []
        }


def extract_resume_info(resume_text: str) -> Dict:
    """
    提取简历基本信息
    
    Args:
        resume_text: 简历文本内容
    
    Returns:
        包含提取信息的字典
    """
    extractor = ResumeExtractor()
    return extractor.extract_basic_info(resume_text)
