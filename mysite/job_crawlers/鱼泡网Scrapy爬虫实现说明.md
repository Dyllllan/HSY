# 鱼泡网（鱼泡直聘）Scrapy 爬虫实现说明

本文说明如何在本项目 `mysite/job_crawlers` 中，用 **Scrapy** 新增一条针对鱼泡系站点（常见域名为 `yupao.com`、`www.yupao.com`、`m.yupao.com` 等，以你实际打开的为准）的爬虫。**列表页、详情页、接口 URL 与查询参数均以你在浏览器里人工核实的结果为准**，下文只给方法与模板，不写死会过期的具体路径。

> **合规提示**：爬取前请阅读目标站用户协议与 robots 规则；控制频率与并发，避免对服务器造成不当压力。本项目 `job_crawlers/settings.py` 中 `ROBOTSTXT_OBEY` 可能为 `False`，仅便于开发调试，**上线或长期运行仍应遵守站点规则与法律要求**。

---

## 一、与本项目现有结构的关系

- Scrapy 工程根目录：`mysite/job_crawlers/`（含 `scrapy.cfg`）。
- 配置：`job_crawlers/job_crawlers/settings.py`（`USER_AGENT`、`DOWNLOAD_DELAY`、`AUTOTHROTTLE` 等已与智联爬虫共用）。
- 现有示例蜘蛛：`job_crawlers/job_crawlers/spiders/zhilian.py`（含 Django/Wagtail 入库逻辑，可作「保存职位」的参考）。
- 运行方式与依赖：见同目录下 [运行爬虫指南.md](./运行爬虫指南.md)。

### 多爬虫与同目录约定（与智联共用一套 Scrapy 工程）

鱼泡爬虫 **`yupao.py` 与 `zhilian.py` 放在同一目录** 即可：`job_crawlers/job_crawlers/spiders/`。本项目在 `settings.py` 里已指定：

```python
SPIDER_MODULES = ["job_crawlers.spiders"]
NEWSPIDER_MODULE = "job_crawlers.spiders"
```

Scrapy 会**自动扫描**该包下所有蜘蛛模块，**不必**为鱼泡再建一个 Scrapy 项目。

**切换跑哪个爬虫，看的是类里的 `name`，不是文件名**：

| 文件 | 蜘蛛标识（`name`） | 启动命令 |
|------|-------------------|----------|
| `spiders/zhilian.py` | 一般为 `zhilian` | `scrapy crawl zhilian` |
| `spiders/yupao.py` | 建议 `yupao` | `scrapy crawl yupao` |

在 `mysite/job_crawlers` 下执行 **`scrapy list`** 可列出当前工程识别的全部蜘蛛，用于确认 `yupao` 已生效。

新增鱼泡时：在 `spiders/` 下新增 `yupao.py`，类中设置 `name = "yupao"`，并按实际站点调整 `allowed_domains` 与请求头。

---

## 二、人工查找 URL 与数据形态（必做）

现代招聘站多为 **前端渲染 + 接口 JSON**，因此不要假设「右键查看源代码」里就有完整职位列表。建议按下面顺序在 **Chrome/Edge 开发者工具** 中自行确认。

### 1. 固定「列表」与「详情」的入口

1. 用浏览器打开鱼泡招聘相关频道（具体路径以网站导航为准）。
2. 在列表页执行一次搜索或筛选（城市、类目、关键词），观察地址栏 **URL 是否变化**：
   - 若变化：记录「列表页」的 **完整 URL 模式**（哪些是固定段、哪些是查询参数，如 `city`、`keyword`、`page`）。
   - 若几乎不变：列表内容多半由 **XHR/Fetch** 拉取，继续第 2 步。

3. 点开一条职位进入详情页，同样记录 **详情页 URL 模式**（是否包含唯一 ID、路径规则）。

把结论写进你的蜘蛛注释或常量里，例如：

```python
# 示例：仅作结构说明，真实值必须由你在浏览器中复制
# LIST_URL_TEMPLATE = "https://www.example.com/jobs?city={city}&kw={kw}&page={page}"
# DETAIL_URL_TEMPLATE = "https://www.example.com/job/{job_id}.html"
```

### 2. 用 Network 定位真实数据接口

1. 打开 **开发者工具 → Network（网络）**，筛选 **Fetch/XHR**。
2. 刷新列表页或翻到下一页，观察新出现的请求：
   - 看 **Request URL**、**Method（GET/POST）**、**Query String / Form Data**、**Request Payload**。
   - 看 **Response**：是否为 JSON，列表字段里是否包含 `id`、`title`、`company`、`salary`、`city` 等。
3. 点开详情页，重复上述步骤，确认详情是 **独立接口** 还是 **列表接口已带全字段**（若列表已够用，可少请求详情，降低压力）。

记录以下信息（写入文档或代码注释，便于日后网站改版对照）：

| 项目 | 说明 |
|------|------|
| 接口 URL | 完整路径，是否带签名参数 |
| 方法 | GET / POST |
| 必要参数 | 页码、城市编码、类目 ID、关键词等 |
| 必要请求头 | `Referer`、`Origin`、`User-Agent`、自定义 token 等 |
| Cookie | 是否必须登录；若必须，需评估是否改用官方 API 或放弃自动化 |
| 翻页方式 | `page` 递增、`offset/limit`、或返回体里的 `next` 游标 |

### 3. 区分实现路线

- **路线 A：服务端直出 HTML**  
  响应体为完整 HTML，可用 `response.css()` / `xpath()` 解析列表链接，再 `Request` 跟进详情页。

- **路线 B：列表/详情均为 JSON 接口（更常见）**  
  蜘蛛的 `start_requests` 应对 **接口 URL** 发请求，在 `parse` 里 `json.loads(response.text)` 或 `response.json()`，用字典路径取字段；详情再 `yield Request` 或使用同一接口不同 `path`。

- **路线 C：强依赖浏览器环境（验证码、复杂签名）**  
  纯 Scrapy 成本陡增，需评估 **Playwright/Selenium**、官方开放平台、或人工导出等非 Scrapy 方案；本文不展开。

**结论**：鱼泡具体走 A 还是 B，以你在 Network 里看到的为准；下文 Scrapy 写法两种都覆盖。

---

## 三、Scrapy 工程内落地步骤

### 1. 新建 Spider 文件

路径：`mysite/job_crawlers/job_crawlers/spiders/yupao.py`（与 `zhilian.py` **同级同目录**，共用 `scrapy.cfg` 与 `settings.py`）。

最小骨架（**请把 URL、解析逻辑换成你人工确认的结果**）：

```python
import scrapy
from urllib.parse import urlencode, urljoin


class YupaoSpider(scrapy.Spider):
    name = "yupao"
    allowed_domains = ["www.yupao.com", "yupao.com"]  # 按实际接口域名增删

    custom_settings = {
        # 可选：鱼泡单独更保守的限速
        "DOWNLOAD_DELAY": 2,
        "CONCURRENT_REQUESTS_PER_DOMAIN": 2,
    }

    def start_requests(self):
        # 示例：关键词、城市等由你人工确认后填入
        params = {"keyword": "教师", "page": 1}
        # url = "https://api.example.com/job/list?" + urlencode(params)
        # yield scrapy.Request(url, callback=self.parse_list, meta={"page": 1})
        return []

    def parse_list(self, response):
        # JSON: data = response.json()
        # HTML: for href in response.css("a.job::attr(href)").getall():
        #     yield response.follow(href, callback=self.parse_detail)
        pass

    def parse_detail(self, response):
        # 解析详情；yield item 或调用入库逻辑
        pass
```

要点：

- **`allowed_domains`**：必须包含你实际请求的 **主机名**（含 `api.xxx.com` 若列表走独立域名）。
- **`meta`**：翻页时传入 `page`、`keyword`、列表 JSON 中的 `cursor` 等，便于下一页构造 URL。
- **`dont_filter`**：仅在确有需要时开启（例如同一 URL 因参数被去重误伤）；默认保持 `False` 以免重复轰炸接口。

### 2. 列表翻页的通用写法

- **页码型**：`page=1,2,3…`，在 `parse_list` 末尾若当前页有数据且未达上限，则 `yield scrapy.Request(next_url, callback=self.parse_list, meta=...)`。
- **offset 型**：`offset += page_size`，直到返回条数为 0 或小于 `page_size`。
- **游标型**：从 JSON 取 `next_cursor`，下一页请求带上该参数；无 `next` 则停止。

务必加 **最大页数/最大条数** 上限，避免逻辑错误导致无限请求（可参考 `zhilian.py` 中对 `page <= 10` 的限制方式）。

### 3. 请求头与 Cookie

在 `settings.py` 里已有 `DEFAULT_REQUEST_HEADERS`。若接口校验 **Referer**，可在 `Request(..., headers={"Referer": "https://www.yupao.com/..."})` 中按 Network 里复制的写。

若必须带 Cookie：

- 短期调试：可从浏览器复制 **整段 Cookie 字符串** 放到请求头（注意过期与安全，勿提交到公开仓库）。
- 长期方案：用 **Downloader Middleware** 维护登录态，或改用官方授权方式。

### 4. Item 与 Pipeline（可选）

当前项目 `items.py` 较空，智联逻辑多在蜘蛛内直接写 Wagtail 模型。你可以：

- **简单**：在 `parse_detail` 里组装 `dict`，再交给与 `zhilian` 相同的保存函数；或  
- **规范**：定义 `scrapy.Item` 字段，用 `pipelines.py` 统一校验、去重、入库。

### 5. 与 Django/Wagtail 入库对齐（可选）

若需像 `zhilian` 一样写入 `JobPage`，通常需要：

1. 在蜘蛛头部做与 `zhilian.py` 相同的 `sys.path` 与 `django.setup()`（注意 `DJANGO_SETTINGS_MODULE` 与本地 `local.settings.dev` / `local.settings.local` 一致）。
2. 在 `parse_detail` 中映射字段：`title`、`company_name`、`location`、`salary`、`body`（职位描述）、`source_url` 等，与 `jobs.models.JobPage` 字段一致。
3. 父页面、去重策略、slug 生成等可直接对照 `zhilian.py` 中已有逻辑改写，避免重复造轮子。

**建议**：第一版先 `scrapy crawl yupao -o yupao.json` 验证字段齐全，再接入数据库。

---

## 四、运行与调试

在 `mysite/job_crawlers` 目录下：

```bash
cd mysite/job_crawlers
scrapy list          # 确认已注册 zhilian、yupao 等
scrapy crawl yupao   # 只跑鱼泡；智联则为 scrapy crawl zhilian
```

导出样本：

```bash
scrapy crawl yupao -o yupao_sample.json
```

调试单条响应：

```bash
scrapy shell "https://你确认的列表或接口URL"
```

在 shell 里尝试 `response.text[:500]`、`response.json()`、`view(response)`（若已配置）等。

日志级别：

```bash
scrapy crawl yupao -L DEBUG
```

若响应为乱码或解压失败，参见同目录 [安装brotli库说明.md](./安装brotli库说明.md) 与智联爬虫中对 Brotli 的说明。

---

## 五、与 `run_crawlers` 管理命令的衔接（可选）

Django 命令 `mysite/jobs/management/commands/run_crawlers.py` 当前将 `sys.argv` 固定为 `scrapy crawl zhilian`，因此 **`python manage.py run_crawlers` 只会启动智联**，不会自动切到鱼泡。

若希望 **与管理命令一致地「按指令选爬虫」**，在保持 `os.chdir` 到 `job_crawlers` 的前提下，把最后一档改成传入的蜘蛛名即可，例如：

- `python manage.py run_crawlers yupao`
- `python manage.py run_crawlers zhilian`（与现状等价）

实现思路：`add_arguments` 里增加位置参数 `spider`（默认值可为 `zhilian` 以兼容旧用法），在 `handle` 里执行：

```python
spider = options["spider"]  # 或 args[0]，视你定义的参数而定
sys.argv = ["scrapy", "crawl", spider]
execute()
```

**注意**：这与在爬虫目录直接执行 `scrapy crawl yupao` 效果相同，只是多了一层从 Django 侧调用的入口。

---

## 六、常见问题（鱼泡场景）

1. **列表为空但浏览器有数据**  
   几乎一定是 **数据来自 XHR**，应用接口 URL 发请求，而不是爬静态 HTML。

2. **401/403 或空 JSON**  
   检查 **Referer、Origin、Cookie、Token** 是否与浏览器一致；是否触发 **风控/验证码**。

3. **频率限制**  
   增大 `DOWNLOAD_DELAY`、降低 `CONCURRENT_REQUESTS_PER_DOMAIN`、启用 `AUTOTHROTTLE`（项目里已部分配置）。

4. **字段改版**  
   站点改版后优先重新走一遍第二节的 Network 记录，再改解析路径，而不是盲目改 CSS。

---

## 七、自检清单

- [ ] `yupao.py` 已放在 `spiders/` 与 `zhilian.py` 同目录，`scrapy list` 能看到 `yupao`。
- [ ] 已在浏览器中确认列表与详情的数据来源（HTML 或 JSON 接口）。
- [ ] 已记录完整 URL、方法、必要参数与请求头（可附在团队 Wiki，勿含隐私 token）。
- [ ] `allowed_domains` 与实际请求主机一致。
- [ ] 翻页有终止条件，避免死循环。
- [ ] 已用 `-o json` 或日志验证字段正确，再考虑入库。
- [ ] 已评估合规与频率，避免对目标站造成不当负载。
- [ ] （可选）已按需扩展 `run_crawlers`，避免误以为改 `yupao.py` 后 `manage.py run_crawlers` 会自动跑鱼泡。

按上述步骤，你可以在不依赖本文给出「固定鱼泡 URL」的前提下，独立完成鱼泡网 Scrapy 爬虫的实现与维护；**URL 结构以你人工查找为准**，代码中一律使用你自己记录的常量与解析逻辑即可。
