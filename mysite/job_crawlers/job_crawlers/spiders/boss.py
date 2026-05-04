import json
import os
import re
import sys
from datetime import datetime
from urllib.parse import quote, urljoin

import django
import scrapy
from django.utils import timezone
from django.utils.text import slugify
from twisted.internet import defer, threads

# Setup Django - add parent directory to path and configure Django
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "local.settings.dev")
django.setup()

from wagtail.models import Page
from jobs.models import JobIndexPage, JobPage

try:
    from unidecode import unidecode  # type: ignore[import-untyped]
except ImportError:
    unidecode = None


class BossSpider(scrapy.Spider):
    name = "boss"
    allowed_domains = ["www.zhipin.com", "zhipin.com"]

    CITY_CODES = {
        "北京": "101010100",
        "上海": "101020100",
        "广州": "101280100",
        "深圳": "101280600",
        "杭州": "101210100",
        "成都": "101270100",
        "佛山": "101280800",
    }

    def start_requests(self):
        keywords = ["教师", "班主任", "助教", "辅导员", "教务"]
        city = "佛山"

        for keyword in keywords:
            city_code = self.CITY_CODES.get(city, "101010100")
            url = f"https://www.zhipin.com/web/geek/job?city={city_code}&query={quote(keyword)}&page=1"
            yield scrapy.Request(
                url=url,
                callback=self.parse_list,
                meta={"keyword": keyword, "city": city, "page": 1},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
                    "Referer": "https://www.zhipin.com/",
                },
                dont_filter=True,
            )

    def parse_list(self, response):
        job_links = response.css('a[href*="/job_detail/"]::attr(href)').getall()

        if not job_links:
            job_links = response.css('a[href*="/job/"]::attr(href)').getall()

        if not job_links:
            script_text = response.text
            encoded_links = re.findall(r'"jobUrl":"([^"]+)"', script_text)
            for link in encoded_links:
                decoded = link.replace("\\/", "/")
                if decoded:
                    job_links.append(decoded)

        if job_links:
            self.logger.debug(f"找到 {len(job_links)} 个职位链接")

        for link in job_links:
            if not link.startswith("http"):
                link = urljoin("https://www.zhipin.com", link)

            yield scrapy.Request(
                url=link,
                callback=self.parse_detail,
                meta={"source_url": link},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                    "Referer": response.url,
                },
                dont_filter=False,
            )

        next_page = response.css('a[ka*="page-next"]::attr(href)').get()
        if not next_page:
            next_page = response.css('a[class*="next"]::attr(href)').get()
        if not next_page:
            page = response.meta.get("page", 1)
            if page < 10:
                next_page = f"/web/geek/job?city={self.CITY_CODES.get(response.meta.get('city', ''), '101010100')}&query={quote(response.meta.get('keyword', ''))}&page={page + 1}"

        if next_page:
            if not next_page.startswith("http"):
                next_page = urljoin(response.url, next_page)

            page = response.meta.get("page", 1) + 1
            if page <= 10:
                yield scrapy.Request(
                    url=next_page,
                    callback=self.parse_list,
                    meta={
                        "keyword": response.meta.get("keyword"),
                        "city": response.meta.get("city"),
                        "page": page,
                    },
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                        "Referer": response.url,
                    },
                    dont_filter=True,
                )

    @defer.inlineCallbacks
    def parse_detail(self, response):
        source_url = response.meta.get("source_url", response.url)

        content_encoding = response.headers.get("Content-Encoding", b"").decode(
            "utf-8", errors="ignore"
        )

        try:
            response_text = response.text[:500] if len(response.text) > 500 else response.text
            has_html = "<html" in response_text.lower() or "<!DOCTYPE" in response_text.upper()
            has_title = "<title" in response_text.lower()
        except Exception as e:
            self.logger.error(f"无法解码响应文本: {str(e)}")
            self.logger.error(f"可能是压缩格式问题，Content-Encoding: {content_encoding}")
            if "br" in content_encoding.lower():
                self.logger.error("响应使用Brotli压缩，但无法解压")
            return []

        self.logger.debug(f"响应包含 <html>: {has_html}")
        self.logger.debug(f"响应包含 <title>: {has_title}")

        if not has_html and not has_title:
            self.logger.warning("响应可能不是HTML格式")
            self.logger.warning(f"Content-Encoding: {content_encoding}")
            if response.status >= 400:
                self.logger.error(f"HTTP错误状态码: {response.status}")
                return []
            if "br" in content_encoding.lower() or "brotli" in content_encoding.lower():
                self.logger.error("响应使用Brotli压缩但无法解压")
                return []

        try:
            job_title = None
            title_selectors = [
                "h1::text",
                ".job-name::text",
                ".name::text",
                '[class*="job-title"]::text',
                '[class*="position-title"]::text',
                "title::text",
            ]
            for selector in title_selectors:
                job_title = response.css(selector).get()
                if job_title:
                    job_title = re.sub(r"\s+", " ", job_title).strip()
                    if job_title:
                        break
            if job_title:
                job_title = re.sub(r"\s*-\s*BOSS直聘.*$", "", job_title, flags=re.IGNORECASE)

            company_name = None
            company_selectors = [
                ".company-info a::text",
                ".company-name::text",
                ".company a::text",
                '[class*="company"] a::text',
                '[class*="company-name"]::text',
            ]
            for selector in company_selectors:
                company_name = response.css(selector).get()
                if company_name:
                    company_name = re.sub(r"<[^>]+>", "", company_name).strip()
                    if company_name:
                        break

            location = None
            location_selectors = [
                ".job-location::text",
                ".text-city::text",
                ".location-address::text",
                '[class*="location"]::text',
                '[class*="address"]::text',
            ]
            for selector in location_selectors:
                location = response.css(selector).get()
                if location:
                    location = re.sub(r"\s+", " ", location).strip()
                    if location:
                        break

            salary = None
            salary_selectors = [
                ".salary::text",
                ".job-salary::text",
                '[class*="salary"]::text',
                '[class*="pay"]::text',
            ]
            for selector in salary_selectors:
                salary = response.css(selector).get()
                if salary:
                    salary = re.sub(r"\s+", " ", salary).strip()
                    if salary:
                        break

            description = ""
            desc_selectors = [
                ".job-sec-text",
                ".job-detail-section",
                ".detail-content",
                ".job-detail",
                '[class*="job-detail"]',
                '[class*="description"]',
            ]
            for selector in desc_selectors:
                desc_elements = response.css(selector)
                if desc_elements:
                    desc_texts = desc_elements.css("*::text").getall()
                    if desc_texts:
                        description = " ".join([t.strip() for t in desc_texts if t.strip()])
                        description = re.sub(r"\s+", " ", description).strip()
                        if description and len(description) > 20:
                            break

            if not description:
                script_json_text = response.css(
                    'script[type="application/ld+json"]::text'
                ).get()
                if script_json_text:
                    try:
                        data = json.loads(script_json_text)
                        description = re.sub(
                            r"\s+", " ", data.get("description", "") or ""
                        ).strip()
                    except json.JSONDecodeError:
                        pass

            if not description:
                description = "暂无详细描述"

            if not salary:
                salary_match = re.search(r"(\d{1,3}[-~]\d{1,3}K(?:\s*[·/]\s*\d+薪)?)", response.text, re.IGNORECASE)
                if salary_match:
                    salary = salary_match.group(1).strip()

            job_type = "fulltime"
            type_text = response.text.lower()
            if "实习" in type_text or "intern" in type_text:
                job_type = "intern"
            elif "兼职" in type_text or "parttime" in type_text:
                job_type = "parttime"

            publish_date = timezone.now()
            date_match = re.search(r"(\d{4}[-/]\d{1,2}[-/]\d{1,2})", response.text)
            if date_match:
                try:
                    publish_date = datetime.strptime(
                        date_match.group(1).replace("/", "-"), "%Y-%m-%d"
                    )
                except Exception:
                    pass

            missing_fields = []
            if not job_title:
                missing_fields.append("职位标题")
            if not company_name:
                missing_fields.append("公司名称")

            if missing_fields:
                self.logger.warning(
                    f"缺少必要字段，跳过保存: {', '.join(missing_fields)} | URL: {response.url}"
                )
                return []

            yield threads.deferToThread(
                self._process_and_save_job,
                company_name=company_name,
                job_title=job_title,
                location=location or "未知",
                salary=salary or "",
                description=description or "暂无详细描述",
                job_type=job_type,
                source_url=source_url,
                publish_date=publish_date,
            )
            return []

        except Exception as e:
            self.logger.error(f"解析职位详情失败: {response.url}, 错误: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
            return []

    def _process_and_save_job(
        self,
        company_name,
        job_title,
        location,
        salary,
        description,
        job_type,
        source_url,
        publish_date,
    ):
        from django.db import IntegrityError, transaction

        try:
            with transaction.atomic():
                existing_job = JobPage.objects.filter(source_url=source_url).first()
                if existing_job:
                    self.logger.debug(f"职位已存在，跳过: {job_title} - {company_name}")
                    return

                parent_page = JobIndexPage.objects.filter(slug="boss-jobs").first()

                if not parent_page:
                    try:
                        from wagtail.models import Site

                        default_site = Site.objects.filter(is_default_site=True).first()
                        if default_site:
                            site_root = default_site.root_page
                            parent_page = JobIndexPage(
                                title="BOSS直聘职位",
                                slug="boss-jobs",
                                intro="来自BOSS直聘的职位信息",
                            )
                            site_root.add_child(instance=parent_page)
                            parent_page.save_revision().publish()
                        else:
                            root_page = Page.objects.filter(depth=1).first()
                            if root_page:
                                parent_page = JobIndexPage(
                                    title="BOSS直聘职位",
                                    slug="boss-jobs",
                                    intro="来自BOSS直聘的职位信息",
                                )
                                root_page.add_child(instance=parent_page)
                                parent_page.save_revision().publish()
                    except Exception as e:
                        self.logger.warning(f"无法创建父页面，尝试使用默认页面: {str(e)}")
                        parent_page = Page.objects.filter(depth__gt=1).first()

                if not parent_page:
                    self.logger.error("无法找到或创建父页面，跳过保存")
                    return

                safe_company = company_name or "未知公司"
                safe_title = job_title or "未知职位"

                if unidecode:
                    safe_company = unidecode(safe_company)
                    safe_title = unidecode(safe_title)
                else:
                    safe_company = re.sub(r"[^\x00-\x7F]+", "", safe_company)
                    safe_title = re.sub(r"[^\x00-\x7F]+", "", safe_title)

                base_slug = slugify(f"{safe_company}-{safe_title}")

                if not base_slug or len(base_slug.strip()) == 0:
                    import time

                    job_id_match = re.search(r"/job_detail/([^/?]+)", source_url)
                    if job_id_match:
                        base_slug = f"boss-{job_id_match.group(1)}"
                    else:
                        base_slug = f"boss-{int(time.time())}"

                base_slug = re.sub(r"[^\w\-]", "", base_slug)
                base_slug = re.sub(r"-+", "-", base_slug).strip("-")
                if len(base_slug) > 200:
                    base_slug = base_slug[:200]

                slug = base_slug
                counter = 1
                while JobPage.objects.filter(slug=slug).exists():
                    suffix = f"-{counter}"
                    max_len = 200 - len(suffix)
                    slug = base_slug[:max_len] + suffix
                    counter += 1
                    if counter > 1000:
                        import time

                        slug = f"{base_slug[:180]}-{int(time.time())}"
                        break

                job_page = JobPage(
                    title=f"{company_name}-{job_title}",
                    slug=slug,
                    job_title=job_title,
                    company_name=company_name,
                    location=location,
                    salary=salary,
                    description=description,
                    job_type=job_type,
                    source_website="BOSS直聘",
                    source_url=source_url,
                    first_published_at=publish_date,
                )

                parent_page.add_child(instance=job_page)
                revision = job_page.save_revision()
                revision.publish()
                job_page.refresh_from_db()
                self.logger.info(f"✓ 已保存: {job_title} - {company_name} ({location})")
                self.logger.debug(f"URL路径: {job_page.url_path}")

        except IntegrityError:
            self.logger.debug(f"职位可能已存在（数据库约束冲突）: {job_title} - {company_name}")
        except Exception as e:
            self.logger.error(f"保存职位失败: {job_title} - {company_name}, 错误: {str(e)}")
            import traceback

            self.logger.error(traceback.format_exc())
