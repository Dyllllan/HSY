import scrapy
import json
import re
from datetime import datetime
from urllib.parse import urljoin, urlencode, quote
import os
import sys
import django

# Setup Django - add parent directory to path and configure Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'local.settings.dev')
django.setup()

from wagtail.models import Page
from jobs.models import JobPage, JobIndexPage
from django.utils import timezone
from twisted.internet import threads, defer

class ZhilianSpider(scrapy.Spider):
    name = 'zhilian'
    allowed_domains = ['www.zhaopin.com', 'sou.zhaopin.com']
    
    # 城市代码映射（北京=530，上海=538，深圳=765等）
    CITY_CODES = {
        '北京': '530',
        '上海': '538',
        '深圳': '765',
        '广州': '763',
        '杭州': '653',
        '成都': '801',
    }
    
    def start_requests(self):
        keywords = ['Python', 'Java', '前端', '后端', '算法']
        city = '广州'  
        
        for keyword in keywords:
            # 使用智联招聘的搜索URL
            # 方式1: 使用新的搜索页面
            url = f'https://sou.zhaopin.com/?jl={self.CITY_CODES.get(city, "530")}&kw={quote(keyword)}&p=1'
            
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta={'keyword': keyword, 'city': city, 'page': 1},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
                    'Referer': 'https://www.zhaopin.com/',
                },
                dont_filter=True
            )
    
    def parse_list(self, response):
        job_links = response.css('a[href*="/job_detail/"]::attr(href)').getall()
        
        # 方式2: 查找包含职位ID的链接
        if not job_links:
            job_links = response.css('a[href*="job"]::attr(href)').getall()
        
        # 方式3: 从页面中提取所有可能的职位链接
        if not job_links:
            # 尝试从JavaScript数据中提取
            script_text = response.text
            # 查找包含jobId或positionId的模式
            job_ids = re.findall(r'job[Ii]d["\']?\s*[:=]\s*["\']?(\d+)', script_text)
            for job_id in job_ids:
                job_links.append(f'https://www.zhaopin.com/job_detail/{job_id}.html')
        
        if job_links:
            self.logger.debug(f"找到 {len(job_links)} 个职位链接")
        
        for link in job_links:
            # 确保链接是完整的URL
            if not link.startswith('http'):
                link = urljoin('https://www.zhaopin.com', link)
            
            # 直接yield请求，在parse_detail中进行去重检查
            yield scrapy.Request(
                url=link,
                callback=self.parse_detail,
                meta={'source_url': link},
                headers={
                    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                    'Referer': response.url,
                },
                dont_filter=False
            )
        
        # 翻页逻辑
        next_page = response.css('a.next-page::attr(href)').get()
        if not next_page:
            # 尝试其他翻页选择器
            next_page = response.css('a[class*="next"]::attr(href)').get()
        
        if next_page:
            if not next_page.startswith('http'):
                next_page = urljoin(response.url, next_page)
            
            page = response.meta.get('page', 1) + 1
            if page <= 10:  # 限制最多爬取10页
                yield scrapy.Request(
                    url=next_page,
                    callback=self.parse_list,
                    meta={'keyword': response.meta.get('keyword'), 'city': response.meta.get('city'), 'page': page},
                    headers={
                        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                        'Referer': response.url,
                    },
                    dont_filter=True
                )
    
    @defer.inlineCallbacks
    def parse_detail(self, response):
        """解析职位详情页面"""
        source_url = response.meta.get('source_url', response.url)
        
        # 检查响应状态和内容类型
        content_type = response.headers.get('Content-Type', b'').decode('utf-8', errors='ignore')
        content_encoding = response.headers.get('Content-Encoding', b'').decode('utf-8', errors='ignore')
        
        # 检查响应是否包含HTML
        try:
            response_text = response.text[:500] if len(response.text) > 500 else response.text
            has_html = '<html' in response_text.lower() or '<!DOCTYPE' in response_text.upper()
            has_title = '<title' in response_text.lower()
        except Exception as e:
            self.logger.error(f"无法解码响应文本: {str(e)}")
            self.logger.error(f"可能是压缩格式问题，Content-Encoding: {content_encoding}")
            # 尝试手动解压（如果需要）
            if 'br' in content_encoding.lower():
                self.logger.error("⚠️  响应使用Brotli压缩，但无法解压！")
                self.logger.error("   解决方案：安装 brotli 或 brotlicffi 库")
                self.logger.error("   命令：pip install brotli 或 pip install brotlicffi")
            return []  # 返回空列表而不是None
        
        self.logger.debug(f"响应包含 <html>: {has_html}")
        self.logger.debug(f"响应包含 <title>: {has_title}")
        
        # 如果响应不是HTML，记录警告
        if not has_html and not has_title:
            self.logger.warning(f"⚠️  响应可能不是HTML格式！")
            self.logger.warning(f"   Content-Encoding: {content_encoding}")
            self.logger.warning(f"   响应前200字符: {response_text[:200]}")
            
            # 检查是否是JSON响应
            try:
                import json
                json_data = json.loads(response.text)
                self.logger.warning(f"   响应是JSON格式: {type(json_data)}")
                self.logger.warning(f"   JSON内容预览: {str(json_data)[:200]}")
            except:
                pass
            
            # 检查是否是错误页面
            if response.status >= 400:
                self.logger.error(f"   HTTP错误状态码: {response.status}")
                return []  # 返回空列表而不是None
            
            # 如果是压缩问题
            if 'br' in content_encoding.lower() or 'brotli' in content_encoding.lower():
                self.logger.error("⚠️  响应使用Brotli压缩但无法解压！")
                self.logger.error("   请安装 brotli 库: pip install brotli")
                return []  # 返回空列表而不是None
        
        try:
            # 提取职位信息（这些操作是同步的，不需要在线程中执行）
            # 职位标题 - 根据实际HTML结构：<h1 class="summary-plane__title">职位名称<img ...></h1>
            # 需要排除img标签，只提取文本内容
            job_title = None
            
            # 方法1：使用XPath获取h1的直接文本内容（自动排除img等子元素）
            h1_element = response.css('h1.summary-plane__title')
            if h1_element:
                # XPath的text()只获取直接文本节点，不包括子元素的文本
                job_title = h1_element.xpath('text()').get()
                if job_title:
                    job_title = job_title.strip()
            
            # 方法2：如果方法1失败，尝试CSS选择器
            if not job_title:
                title_selectors = [
                    'h1.summary-plane__title::text',  # 优先使用实际的结构
                    '.summary-plane__title::text',
                    'h1.job-title::text',
                    'h1::text',
                    '.job-title::text',
                    '.position-title::text',
                    '[class*="job-title"]::text',
                    '[class*="position-title"]::text',
                    '[class*="summary-plane"] h1::text',
                    'title::text'
                ]
                for selector in title_selectors:
                    job_title = response.css(selector).get()
                    if job_title:
                        job_title = job_title.strip()
                        if job_title:
                            break
            
            # 方法3：如果还是失败，从h1元素HTML中提取并清理标签
            if not job_title:
                h1_element = response.css('h1.summary-plane__title')
                if h1_element:
                    h1_html = h1_element.get()
                    if h1_html:
                        # 移除所有HTML标签（包括img）
                        job_title = re.sub(r'<[^>]+>', '', h1_html)
                        job_title = job_title.strip()
            
            # 清理标题
            if job_title:
                job_title = job_title.strip()
                # 清理标题中的网站名称和多余空白
                job_title = re.sub(r'[-_]\s*智联招聘.*$', '', job_title, flags=re.IGNORECASE)
                job_title = re.sub(r'\s*-\s*智联招聘.*$', '', job_title, flags=re.IGNORECASE)
                job_title = re.sub(r'\s+', ' ', job_title).strip()  # 清理多余空白
            
            # 如果CSS选择器都失败，尝试从title标签提取
            if not job_title:
                title_text = response.css('title::text').get() or ''
                # 从title中提取职位名称（通常在"-"之前）
                title_match = re.search(r'^([^-]+)', title_text)
                if title_match:
                    job_title = title_match.group(1).strip()
                    job_title = re.sub(r'[-_]\s*智联招聘.*$', '', job_title, flags=re.IGNORECASE)
            
            # 公司名称 - 根据实际HTML结构：
            # <li class="company-info">
            #   <strong class="company-info__title">入职公司:</strong>
            #   <span class="company-info__description">北京智谱华章科技股份有限公司</span>
            # </li>
            # 或者：<a href="..." class="company__title">公司名称</a>
            company_name = None
            
            # 方法1：从 join-company__content 中提取（优先）
            company_info = response.css('.join-company__content')
            if company_info:
                # 查找包含"入职公司"的li
                company_li = company_info.css('li.company-info')
                for li in company_li:
                    title = li.css('strong.company-info__title::text').get() or ''
                    if '入职公司' in title or '公司' in title:
                        company_name = li.css('span.company-info__description::text').get()
                        if company_name:
                            company_name = company_name.strip()
                            break
            
            # 方法2：如果方法1失败，尝试 company__title
            if not company_name:
                company_selectors = [
                    'a.company__title::text',  # 优先使用实际的结构
                    '.company__title::text',  # 备用：不指定标签
                    'a.company__title',  # 获取整个a元素
                    '.summary-plane__company::text',  # 备用：summary-plane结构
                    '.summary-plane__company a::text',
                    'a[href*="/company/"]::text',
                    'a[href*="companydetail"]::text',  # 匹配公司详情页链接
                    '.company-name::text',
                    '.company-name a::text',
                    '[class*="company-name"]::text',
                    '[class*="company"] a::text',
                    '.job-company::text',
                    '.company::text',
                    '[class*="summary-plane"][class*="company"]::text'
                ]
                for selector in company_selectors:
                    company_name = response.css(selector).get()
                    if company_name:
                        company_name = company_name.strip()
                        # 清理可能的HTML标签残留
                        company_name = re.sub(r'<[^>]+>', '', company_name).strip()
                        if company_name:
                            break
            
            # 方法3：如果直接获取文本失败，尝试获取a元素然后提取文本
            if not company_name:
                company_element = response.css('a.company__title')
                if company_element:
                    company_name = ''.join(company_element.css('*::text').getall())
                    if not company_name:
                        company_name = company_element.get()
                        if company_name:
                            company_name = re.sub(r'<[^>]+>', '', company_name)
                    if company_name:
                        company_name = company_name.strip()
            
            # 如果CSS选择器都失败，尝试从页面文本中提取
            if not company_name:
                # 查找包含"公司"的文本模式
                page_text = response.text
                company_match = re.search(r'入职公司[：:]\s*([^\s<]+)', page_text)
                if not company_match:
                    company_match = re.search(r'公司[名称]?[：:]\s*([^\s<]+)', page_text)
                if company_match:
                    company_name = company_match.group(1).strip()
            
            # 工作地点 - 根据实际HTML结构：
            # <ul class="summary-plane__info">
            #   <li><a href="//www.zhaopin.com/beijing/" target="_blank">北京</a><span>海淀区</span></li>
            # </ul>
            # 或者：<span class="job-address__content-text">北京海淀区搜狐网络大厦9</span>
            location = None
            
            # 方法1：从 summary-plane__info 的第一个li中提取（城市+区域）
            info_list = response.css('ul.summary-plane__info')
            if info_list:
                first_li_list = info_list.css('li')
                if first_li_list:
                    first_li = first_li_list[0]  # 使用索引获取第一个元素
                    # 获取li内的所有文本（包括a和span标签的文本）
                    city_text = first_li.css('a::text').get() or ''
                    area_text = first_li.css('span::text').get() or ''
                    if city_text or area_text:
                        location = (city_text.strip() + area_text.strip()).strip()
            
            # 方法2：如果方法1失败，尝试 job-address__content-text
            if not location:
                location_selectors = [
                    'span.job-address__content-text::text',  # 优先使用实际的结构
                    '.job-address__content-text::text',  # 备用：不指定标签
                    'span.job-address__content-text',  # 获取整个span元素
                    '.summary-plane__location::text',  # 备用：summary-plane结构
                    '.summary-plane__area::text',
                    '.summary-plane__city::text',
                    '.job-location::text',
                    '.workplace::text',
                    '.location::text',
                    '[class*="location"]::text',
                    '[class*="workplace"]::text',
                    '[class*="area"]::text',
                    '[class*="address"]::text',
                    '.job-area::text',
                    '[class*="summary-plane"][class*="location"]::text'
                ]
                for selector in location_selectors:
                    location = response.css(selector).get()
                    if location:
                        location = location.strip()
                        # 清理可能的HTML标签残留和图标文本
                        location = re.sub(r'<[^>]+>', '', location).strip()
                        # 移除可能的图标字符或空白
                        location = re.sub(r'^\s*[📍🔍]\s*', '', location).strip()
                        if location:
                            break
            
            # 方法3：如果直接获取文本失败，尝试获取span元素然后提取文本（排除图标）
            if not location:
                location_element = response.css('span.job-address__content-text')
                if location_element:
                    # 获取所有文本节点，但排除图标内的文本
                    all_texts = location_element.css('*::text').getall()
                    # 过滤掉可能是图标的内容（通常很短或包含特殊字符）
                    location = ''.join([t.strip() for t in all_texts if t.strip() and len(t.strip()) > 1])
                    if not location:
                        # 如果还是没有，获取整个元素内容并清理
                        location = location_element.get()
                        if location:
                            # 移除HTML标签
                            location = re.sub(r'<[^>]+>', '', location)
                            # 移除可能的图标字符
                            location = re.sub(r'[📍🔍]', '', location).strip()
                    if location:
                        location = location.strip()
            
            # 如果CSS选择器都失败，尝试从页面文本中提取
            if not location:
                page_text = response.text
                location_match = re.search(r'工作[地点|城市][：:]\s*([^\s<]+)', page_text)
                if location_match:
                    location = location_match.group(1).strip()
            
            # 薪资 - 根据实际HTML结构：<span class="summary-plane__salary">1.5-1.8万</span>
            salary = None
            salary_selectors = [
                'span.summary-plane__salary::text',  # 优先使用实际的结构
                '.summary-plane__salary::text',  # 备用：不指定标签
                'span.summary-plane__salary',  # 获取整个span元素
                '.summary-plane__pay::text',
                '.salary::text',
                '.job-salary::text',
                '[class*="salary"]::text',
                '.pay::text',
                '.wage::text',
                '[class*="summary-plane"][class*="salary"]::text'
            ]
            for selector in salary_selectors:
                salary = response.css(selector).get()
                if salary:
                    salary = salary.strip()
                    # 清理可能的HTML标签残留
                    salary = re.sub(r'<[^>]+>', '', salary).strip()
                    if salary:
                        break
            
            # 如果直接获取文本失败，尝试获取span元素然后提取文本
            if not salary:
                salary_element = response.css('span.summary-plane__salary')
                if salary_element:
                    salary = ''.join(salary_element.css('*::text').getall())
                    if not salary:
                        salary = salary_element.get()
                        if salary:
                            salary = re.sub(r'<[^>]+>', '', salary)
                    if salary:
                        salary = salary.strip()
            
            # 如果CSS选择器都失败，尝试从页面文本中提取薪资
            if not salary:
                page_text = response.text
                # 查找薪资模式：如"8-12K"、"10K-15K"、"面议"等
                salary_match = re.search(r'(薪资|工资|待遇)[：:]\s*([^\s<]+)', page_text)
                if salary_match:
                    salary = salary_match.group(2).strip()
            
            # 如果关键字段缺失，尝试从页面中的JSON数据提取
            if (not job_title or not company_name) and '<script' in response.text:
                try:
                    # 查找页面中的JSON数据
                    json_matches = re.findall(r'<script[^>]*type=["\']application/json["\'][^>]*>(.*?)</script>', response.text, re.DOTALL)
                    for json_str in json_matches:
                        try:
                            data = json.loads(json_str)
                            # 递归搜索JSON中的职位信息
                            def find_in_dict(d, keys):
                                if isinstance(d, dict):
                                    for k, v in d.items():
                                        if any(key in k.lower() for key in keys):
                                            if isinstance(v, str) and v:
                                                return v
                                        if isinstance(v, (dict, list)):
                                            result = find_in_dict(v, keys)
                                            if result:
                                                return result
                                elif isinstance(d, list):
                                    for item in d:
                                        result = find_in_dict(item, keys)
                                        if result:
                                            return result
                                return None
                            
                            if not job_title:
                                job_title = find_in_dict(data, ['title', 'jobname', 'position', 'name'])
                            if not company_name:
                                company_name = find_in_dict(data, ['company', 'companyname', 'employer'])
                            if not location:
                                location = find_in_dict(data, ['location', 'city', 'workplace', 'area'])
                            if not salary:
                                salary = find_in_dict(data, ['salary', 'pay', 'wage'])
                            
                            if job_title and company_name:
                                break
                        except json.JSONDecodeError:
                            continue
                except Exception:
                    pass
            
            # 职位描述 - 根据实际HTML结构：
            # <div class="describtion__detail-content">
            #   <div>职位描述</div>
            #   <div>1、负责与客户沟通...</div>
            #   <div>职位要求</div>
            #   <div>1、本科及以上学历...</div>
            # </div>
            description = ''
            
            # 方法1：从 describtion__detail-content 中提取（优先）
            detail_content = response.css('.describtion__detail-content')
            if detail_content:
                # 获取所有div内的文本内容
                desc_divs = detail_content.css('div')
                desc_parts = []
                for div in desc_divs:
                    div_text = ''.join(div.css('*::text').getall())
                    if not div_text:
                        div_html = div.get()
                        if div_html:
                            div_text = re.sub(r'<[^>]+>', ' ', div_html)
                    if div_text:
                        div_text = re.sub(r'\s+', ' ', div_text).strip()
                        # 跳过标题行（如"职位描述"、"职位要求"）
                        if div_text and div_text not in ['职位描述', '职位要求', '岗位职责', '工作内容']:
                            desc_parts.append(div_text)
                
                if desc_parts:
                    description = '\n'.join(desc_parts)
            
            # 方法2：如果方法1失败，尝试其他选择器
            if not description:
                desc_selectors = [
                    '.describtion__detail-content',  # 使用实际的结构
                    '.job-description',  # 常见的职位描述类
                    '.position-detail',
                    '.job-detail',
                    '.job-des',
                    '.description',
                    '[class*="description"]',
                    '[class*="detail"]',
                    '[class*="job-desc"]',
                    '.position-content',
                    '.job-content',
                    '[class*="summary-plane"][class*="description"]',  # 可能在summary-plane中
                    '.detail-content',
                    '.job-intro'
                ]
                for selector in desc_selectors:
                    desc_elements = response.css(selector)
                    if desc_elements:
                        # 尝试获取所有文本内容
                        desc_texts = desc_elements.css('*::text').getall()
                        if desc_texts:
                            description = ' '.join([t.strip() for t in desc_texts if t.strip()])
                            if description and len(description) > 20:  # 确保有足够的内容
                                break
            
            # 方法3：如果CSS选择器都失败，尝试从页面HTML中提取
            if not description:
                page_text = response.text
                # 查找包含"职位描述"、"岗位职责"、"工作内容"的部分
                desc_patterns = [
                    r'<div[^>]*class[^>]*describtion__detail-content[^>]*>(.*?)</div>',  # 优先匹配实际结构
                    r'(职位描述|岗位职责|工作内容|岗位要求)[：:]\s*([^<]*?)(任职要求|公司介绍|职位要求|$)',
                    r'<div[^>]*class[^>]*description[^>]*>(.*?)</div>',
                    r'<div[^>]*class[^>]*detail[^>]*>(.*?)</div>',
                ]
                for pattern in desc_patterns:
                    desc_match = re.search(pattern, page_text, re.DOTALL | re.IGNORECASE)
                    if desc_match:
                        desc_text = desc_match.group(1) if desc_match.lastindex >= 1 else desc_match.group(0)
                        # 清理HTML标签
                        desc_text = re.sub(r'<[^>]+>', ' ', desc_text)
                        desc_text = re.sub(r'\s+', ' ', desc_text).strip()
                        if desc_text and len(desc_text) > 20:  # 确保有足够的内容
                            description = desc_text
                            break
            
            # 如果还是没有描述，至少设置一个默认值
            if not description:
                description = '暂无详细描述'
            
            # 职位类型（全职/实习/兼职）
            job_type = 'fulltime'  # 默认全职
            type_text = response.text.lower()
            if '实习' in type_text or 'intern' in type_text:
                job_type = 'intern'
            elif '兼职' in type_text or 'parttime' in type_text:
                job_type = 'parttime'
            
            # 发布时间
            publish_date = timezone.now()
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2})', response.text)
            if date_match:
                try:
                    publish_date = datetime.strptime(date_match.group(1).replace('/', '-'), '%Y-%m-%d')
                except:
                    pass
            
            # 验证必要字段
            missing_fields = []
            if not job_title:
                missing_fields.append("职位标题")
            if not company_name:
                missing_fields.append("公司名称")
            
            if missing_fields:
                self.logger.warning(f"缺少必要字段，跳过保存: {', '.join(missing_fields)} | URL: {response.url}")
                return []  # 返回空列表而不是None
            
            # 使用deferToThread在线程中执行数据库操作（包括检查和保存）
            yield threads.deferToThread(
                self._process_and_save_job,
                company_name=company_name,
                job_title=job_title,
                location=location or '未知',
                salary=salary or '',
                description=description or '暂无详细描述',
                job_type=job_type,
                source_url=source_url,
                publish_date=publish_date
            )
            # 返回空列表，表示没有新的请求需要处理
            return []
        
        except Exception as e:
            self.logger.error(f"解析职位详情失败: {response.url}, 错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            # 返回空列表而不是None，避免迭代错误
            return []
    
    def job_exists_sync(self, source_url):
        """同步版本的职位存在检查（用于在异步上下文中调用）"""
        if not source_url:
            return False
        
        # 提取职位ID（如果URL中包含）
        job_id_match = re.search(r'/(\d+)\.html', source_url)
        if job_id_match:
            job_id = job_id_match.group(1)
            return JobPage.objects.filter(source_url__contains=job_id).exists()
        
        # 否则检查完整URL
        return JobPage.objects.filter(source_url=source_url).exists()
    
    def _process_and_save_job(self, company_name, job_title, location, salary, 
                               description, job_type, source_url, publish_date):
        """在线程中处理并保存职位（包括去重检查和保存）"""
        from django.db import transaction, IntegrityError
        
        try:
            # 使用数据库事务确保原子性操作，防止并发重复保存
            with transaction.atomic():
                # 检查是否已存在（在事务中检查，防止并发问题）
                existing_job = JobPage.objects.filter(source_url=source_url).first()
                if existing_job:
                    self.logger.debug(f"职位已存在，跳过: {job_title} - {company_name}")
                    return
                
                # 获取或创建父页面
                parent_page = JobIndexPage.objects.filter(slug='zhilian-jobs').first()
                
                if not parent_page:
                    # 尝试查找根页面
                    try:
                        root_page = Page.objects.filter(depth=1).first()
                        if root_page:
                            # 创建JobIndexPage
                            parent_page = JobIndexPage(
                                title='智联招聘职位',
                                slug='zhilian-jobs',
                                intro='来自智联招聘的职位信息'
                            )
                            root_page.add_child(instance=parent_page)
                            parent_page.save_revision().publish()
                            self.logger.debug("创建了新的职位索引页")
                    except Exception as e:
                        self.logger.warning(f"无法创建父页面，尝试使用默认页面: {str(e)}")
                        # 使用第一个可用的页面
                        parent_page = Page.objects.filter(depth__gt=1).first()
                
                if not parent_page:
                    self.logger.error("无法找到或创建父页面，跳过保存")
                    return
                
                # 创建JobPage实例
                job_page = JobPage(
                    title=f"{company_name}-{job_title}",
                    job_title=job_title,
                    company_name=company_name,
                    location=location,
                    salary=salary,
                    description=description,
                    job_type=job_type,
                    source_website='智联招聘',
                    source_url=source_url,
                    first_published_at=publish_date
                )
                
                # 添加到页面树并发布（在事务中执行）
                parent_page.add_child(instance=job_page)
                job_page.save_revision().publish()
                self.logger.info(f"✓ 已保存: {job_title} - {company_name} ({location})")
            
        except IntegrityError:
            # 数据库唯一约束冲突（如果设置了唯一约束）
            self.logger.debug(f"职位可能已存在（数据库约束冲突）: {job_title} - {company_name}")
        except Exception as e:
            self.logger.error(f"保存职位失败: {job_title} - {company_name}, 错误: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
