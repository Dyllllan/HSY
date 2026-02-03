"""
AI报告解析器 - 从AI生成的文本报告中提取结构化数据
"""
import re
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ReportParser:
    """AI报告解析器"""
    
    def __init__(self, report_text: str):
        self.report_text = report_text or ""
        self.parsed_data = {}
    
    def parse(self) -> Dict:
        """
        解析报告文本，提取结构化数据
        
        Returns:
            包含解析后数据的字典
        """
        if not self.report_text:
            return self._get_empty_data()
        
        try:
            # 提取基本信息
            self.parsed_data['basic_info'] = self._parse_basic_info()
            
            # 提取技能匹配度评分
            self.parsed_data['skill_scores'] = self._parse_skill_scores()
            
            # 提取岗位推荐
            self.parsed_data['job_recommendations'] = self._parse_job_recommendations()
            
            # 提取提升建议
            self.parsed_data['improvement_suggestions'] = self._parse_improvement_suggestions()
            
            # 提取竞争力排名
            self.parsed_data['competitiveness_rank'] = self._parse_competitiveness_rank()
            
            # 提取技能优势分析
            self.parsed_data['skill_advantages'] = self._parse_skill_advantages()
            
            # 提取技能短板分析
            self.parsed_data['skill_weaknesses'] = self._parse_skill_weaknesses()
            
            return self.parsed_data
        except Exception as e:
            logger.error(f"解析报告失败: {str(e)}", exc_info=True)
            return self._get_empty_data()
    
    def _parse_basic_info(self) -> Dict:
        """解析基本信息"""
        info = {
            'education': '',
            'work_experience': '',
            'core_skills': [],
            'contact_info': ''
        }
        
        # 查找基本信息部分
        basic_section = self._extract_section('基本信息分析', '📊')
        
        if basic_section:
            # 提取教育背景
            education_match = re.search(r'教育背景[：:]\s*([^\n]+)', basic_section)
            if education_match:
                info['education'] = education_match.group(1).strip()
            
            # 提取工作经验年限
            exp_match = re.search(r'工作经验[年限]*[：:]\s*([^\n]+)', basic_section)
            if exp_match:
                info['work_experience'] = exp_match.group(1).strip()
            
            # 提取核心技能
            skills_match = re.search(r'核心技能[：:]\s*([^\n]+)', basic_section)
            if skills_match:
                skills_text = skills_match.group(1).strip()
                # 分割技能（可能是逗号、分号或换行分隔）
                info['core_skills'] = [s.strip() for s in re.split(r'[,，;；、\n]', skills_text) if s.strip()]
            
            # 提取姓名/联系方式
            contact_match = re.search(r'(姓名|联系方式)[：:]\s*([^\n]+)', basic_section)
            if contact_match:
                info['contact_info'] = contact_match.group(2).strip()
        
        return info
    
    def _parse_skill_scores(self) -> Dict:
        """解析技能匹配度评分"""
        scores = {
            'technical_skill': 0,
            'soft_skill': 0,
            'overall_match': 0
        }
        
        # 查找技能匹配度部分
        skill_section = self._extract_section('技能匹配度', '💼')
        
        if skill_section:
            # 提取技术技能评分
            tech_match = re.search(r'技术技能[：:]\s*(\d+)', skill_section)
            if tech_match:
                scores['technical_skill'] = int(tech_match.group(1))
            
            # 提取软技能评分
            soft_match = re.search(r'软技能[：:]\s*(\d+)', skill_section)
            if soft_match:
                scores['soft_skill'] = int(soft_match.group(1))
            
            # 提取综合匹配度评分
            overall_match = re.search(r'综合匹配度[：:]\s*(\d+)', skill_section)
            if overall_match:
                scores['overall_match'] = int(overall_match.group(1))
            
            # 如果没有找到，尝试其他格式
            if scores['technical_skill'] == 0:
                tech_match = re.search(r'技术[：:]\s*(\d+)', skill_section)
                if tech_match:
                    scores['technical_skill'] = int(tech_match.group(1))
            
            if scores['soft_skill'] == 0:
                soft_match = re.search(r'软技能|沟通|协作[：:]\s*(\d+)', skill_section)
                if soft_match:
                    scores['soft_skill'] = int(soft_match.group(1))
        
        return scores
    
    def _parse_job_recommendations(self) -> List[Dict]:
        """解析岗位推荐"""
        recommendations = []
        
        # 查找岗位推荐部分
        job_section = self._extract_section('岗位推荐', '🎯')
        
        if job_section:
            # 提取列表项（数字开头的行）
            lines = job_section.split('\n')
            for line in lines:
                line = line.strip()
                # 匹配 "1. 岗位名称" 或 "1、岗位名称" 格式
                match = re.match(r'^\d+[\.、]\s*(.+?)(?:\s*[-—]\s*(.+))?$', line)
                if match:
                    job_name = match.group(1).strip()
                    reason = match.group(2).strip() if match.group(2) else ''
                    
                    # 移除可能的推荐理由标记
                    if '推荐理由' in job_name:
                        job_name = job_name.replace('推荐理由', '').strip()
                    
                    recommendations.append({
                        'name': job_name,
                        'reason': reason
                    })
        
        return recommendations
    
    def _parse_improvement_suggestions(self) -> List[str]:
        """解析提升建议"""
        suggestions = []
        
        # 查找提升建议部分
        suggestion_section = self._extract_section('提升建议', '💡')
        
        if suggestion_section:
            # 提取列表项
            lines = suggestion_section.split('\n')
            for line in lines:
                line = line.strip()
                # 匹配 "1. 建议内容" 格式
                match = re.match(r'^\d+[\.、]\s*(.+)$', line)
                if match:
                    suggestions.append(match.group(1).strip())
        
        return suggestions
    
    def _parse_competitiveness_rank(self) -> str:
        """解析竞争力排名"""
        rank = ''
        
        # 查找竞争力排名部分
        rank_section = self._extract_section('竞争力排名', '📈')
        
        if rank_section:
            # 提取排名信息（如前20%、前30%等）
            rank_match = re.search(r'(前\d+%|前\d+名|top\s*\d+%)', rank_section, re.IGNORECASE)
            if rank_match:
                rank = rank_match.group(1)
            else:
                # 如果没有找到，提取整行
                lines = rank_section.split('\n')
                for line in lines:
                    if '排名' in line or '竞争力' in line:
                        rank = line.strip()
                        break
        
        return rank
    
    def _parse_skill_advantages(self) -> List[str]:
        """解析技能优势分析"""
        advantages = []
        
        skill_section = self._extract_section('技能匹配度', '💼')
        
        if skill_section:
            # 查找优势部分
            advantage_match = re.search(r'技能优势[分析]*[：:]\s*([^\n]+(?:\n[^\n]+)*?)(?=技能短板|技能匹配度|岗位推荐|提升建议|竞争力排名|$)', skill_section, re.DOTALL)
            if advantage_match:
                advantage_text = advantage_match.group(1).strip()
                # 分割成列表项
                advantages = [item.strip() for item in re.split(r'[，,；;、\n]', advantage_text) if item.strip() and len(item.strip()) > 3]
        
        return advantages
    
    def _parse_skill_weaknesses(self) -> List[str]:
        """解析技能短板分析"""
        weaknesses = []
        
        skill_section = self._extract_section('技能匹配度', '💼')
        
        if skill_section:
            # 查找短板部分
            weakness_match = re.search(r'技能短板[分析]*[：:]\s*([^\n]+(?:\n[^\n]+)*?)(?=岗位推荐|提升建议|竞争力排名|$)', skill_section, re.DOTALL)
            if weakness_match:
                weakness_text = weakness_match.group(1).strip()
                # 分割成列表项
                weaknesses = [item.strip() for item in re.split(r'[，,；;、\n]', weakness_text) if item.strip() and len(item.strip()) > 3]
        
        return weaknesses
    
    def _extract_section(self, section_name: str, emoji: str = None) -> Optional[str]:
        """提取报告中的特定部分"""
        if not self.report_text:
            return None
        
        # 构建匹配模式
        patterns = [
            rf'{emoji}\s*{section_name}[：:]*\s*\n(.*?)(?=\n[📊💼🎯💡📈]|$)',
            rf'{section_name}[：:]*\s*\n(.*?)(?=\n[📊💼🎯💡📈]|$)',
            rf'{emoji}.*?{section_name}[：:]*\s*\n(.*?)(?=\n[📊💼🎯💡📈]|$)',
        ]
        
        if emoji:
            patterns.insert(0, rf'{emoji}\s*{section_name}[：:]*\s*\n(.*?)(?=\n[📊💼🎯💡📈]|$)')
        
        for pattern in patterns:
            match = re.search(pattern, self.report_text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _get_empty_data(self) -> Dict:
        """返回空的数据结构"""
        return {
            'basic_info': {
                'education': '',
                'work_experience': '',
                'core_skills': [],
                'contact_info': ''
            },
            'skill_scores': {
                'technical_skill': 0,
                'soft_skill': 0,
                'overall_match': 0
            },
            'job_recommendations': [],
            'improvement_suggestions': [],
            'competitiveness_rank': '',
            'skill_advantages': [],
            'skill_weaknesses': []
        }


def parse_ai_report(report_text: str) -> Dict:
    """
    解析AI报告文本
    
    Args:
        report_text: AI生成的报告文本
    
    Returns:
        解析后的结构化数据字典
    """
    parser = ReportParser(report_text)
    return parser.parse()
