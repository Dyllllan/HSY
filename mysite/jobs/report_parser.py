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
            
            # 提取核心竞争力指标评分
            self.parsed_data['competency_scores'] = self._parse_competency_scores()
            
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
    
    def _parse_competency_scores(self) -> Dict:
        """解析核心竞争力指标评分"""
        scores = {
            'professional_depth': 0,        # 专业深度
            'learning_acuity': 0,           # 学习敏锐度
            'logical_architecture': 0,      # 逻辑架构能力
            'resilience': 0                 # 抗压韧性
        }
        
        # 首先尝试查找新格式：核心竞争力指标
        competency_section = self._extract_section('核心竞争力指标', '💼')
        
        if competency_section:
            # 提取专业深度评分（支持多种格式：95分、95、专业深度：95等）
            depth_patterns = [
                r'专业深度[：:]\s*(\d+)',
                r'专业深度[：:]\s*(\d+)\s*分',
                r'专业深度[：:]\s*(\d+)\s*%',
                r'[Pp]rofessional\s*[Dd]epth[：:]\s*(\d+)',
            ]
            for pattern in depth_patterns:
                depth_match = re.search(pattern, competency_section)
                if depth_match:
                    scores['professional_depth'] = int(depth_match.group(1))
                    break
            
            # 提取学习敏锐度评分
            learning_patterns = [
                r'学习敏锐度[：:]\s*(\d+)',
                r'学习敏锐度[：:]\s*(\d+)\s*分',
                r'学习敏锐度[：:]\s*(\d+)\s*%',
                r'[Ll]earning\s*[Aa]cuity[：:]\s*(\d+)',
            ]
            for pattern in learning_patterns:
                learning_match = re.search(pattern, competency_section)
                if learning_match:
                    scores['learning_acuity'] = int(learning_match.group(1))
                    break
            
            # 提取逻辑架构能力评分
            logical_patterns = [
                r'逻辑架构能力[：:]\s*(\d+)',
                r'逻辑架构能力[：:]\s*(\d+)\s*分',
                r'逻辑架构能力[：:]\s*(\d+)\s*%',
                r'[Ll]ogical\s*[Aa]rchitecture[：:]\s*(\d+)',
            ]
            for pattern in logical_patterns:
                logical_match = re.search(pattern, competency_section)
                if logical_match:
                    scores['logical_architecture'] = int(logical_match.group(1))
                    break
            
            # 提取抗压韧性评分
            resilience_patterns = [
                r'抗压韧性[：:]\s*(\d+)',
                r'抗压韧性[：:]\s*(\d+)\s*分',
                r'抗压韧性[：:]\s*(\d+)\s*%',
                r'[Rr]esilience[：:]\s*(\d+)',
            ]
            for pattern in resilience_patterns:
                resilience_match = re.search(pattern, competency_section)
                if resilience_match:
                    scores['resilience'] = int(resilience_match.group(1))
                    break
        
        # 如果新格式没有找到数据，尝试兼容旧格式：技能匹配度评估
        if scores['professional_depth'] == 0 and scores['learning_acuity'] == 0 and \
           scores['logical_architecture'] == 0 and scores['resilience'] == 0:
            skill_section = self._extract_section('技能匹配度', '💼')
            if not skill_section:
                skill_section = self.report_text
            
            # 从旧格式中提取技术技能、软技能、综合匹配度
            tech_match = re.search(r'技术技能[评分]*[：:]\s*(\d+)', skill_section)
            soft_match = re.search(r'软技能[评分]*[：:]\s*(\d+)', skill_section)
            overall_match = re.search(r'综合匹配度[评分]*[：:]\s*(\d+)', skill_section)
            
            tech_score = int(tech_match.group(1)) if tech_match else 0
            soft_score = int(soft_match.group(1)) if soft_match else 0
            overall_score = int(overall_match.group(1)) if overall_match else 0
            
            # 将旧格式映射到新格式
            if tech_score > 0 or soft_score > 0 or overall_score > 0:
                # 技术技能 -> 专业深度
                scores['professional_depth'] = tech_score
                # 软技能 -> 学习敏锐度
                scores['learning_acuity'] = soft_score
                # 综合匹配度 -> 逻辑架构能力
                scores['logical_architecture'] = overall_score
                # 抗压韧性：如果综合匹配度较高，可以设置为综合匹配度的90%
                scores['resilience'] = int(overall_score * 0.9) if overall_score > 0 else 0
        
        # 如果仍然没有找到，尝试在整个报告中搜索（支持更多格式变体）
        if scores['professional_depth'] == 0:
            depth_patterns = [
                r'专业深度[：:]\s*(\d+)',
                r'专业深度[：:]\s*(\d+)\s*分',
                r'专业深度[：:]\s*(\d+)\s*%',
                r'[Pp]rofessional\s*[Dd]epth[：:]\s*(\d+)',
            ]
            for pattern in depth_patterns:
                depth_match = re.search(pattern, self.report_text)
                if depth_match:
                    scores['professional_depth'] = int(depth_match.group(1))
                    break
        
        if scores['learning_acuity'] == 0:
            learning_patterns = [
                r'学习敏锐度[：:]\s*(\d+)',
                r'学习敏锐度[：:]\s*(\d+)\s*分',
                r'学习敏锐度[：:]\s*(\d+)\s*%',
                r'[Ll]earning\s*[Aa]cuity[：:]\s*(\d+)',
            ]
            for pattern in learning_patterns:
                learning_match = re.search(pattern, self.report_text)
                if learning_match:
                    scores['learning_acuity'] = int(learning_match.group(1))
                    break
        
        if scores['logical_architecture'] == 0:
            logical_patterns = [
                r'逻辑架构能力[：:]\s*(\d+)',
                r'逻辑架构能力[：:]\s*(\d+)\s*分',
                r'逻辑架构能力[：:]\s*(\d+)\s*%',
                r'[Ll]ogical\s*[Aa]rchitecture[：:]\s*(\d+)',
            ]
            for pattern in logical_patterns:
                logical_match = re.search(pattern, self.report_text)
                if logical_match:
                    scores['logical_architecture'] = int(logical_match.group(1))
                    break
        
        if scores['resilience'] == 0:
            resilience_patterns = [
                r'抗压韧性[：:]\s*(\d+)',
                r'抗压韧性[：:]\s*(\d+)\s*分',
                r'抗压韧性[：:]\s*(\d+)\s*%',
                r'[Rr]esilience[：:]\s*(\d+)',
            ]
            for pattern in resilience_patterns:
                resilience_match = re.search(pattern, self.report_text)
                if resilience_match:
                    scores['resilience'] = int(resilience_match.group(1))
                    break
        
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
            'competency_scores': {
                'professional_depth': 0,
                'learning_acuity': 0,
                'logical_architecture': 0,
                'resilience': 0
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
