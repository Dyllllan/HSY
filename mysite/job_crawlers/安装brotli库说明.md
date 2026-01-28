# 安装Brotli库解决压缩问题

## 问题描述

爬虫遇到以下错误：
```
HttpCompressionMiddleware cannot decode the response for ... from unsupported encoding(s) 'br'. 
You need to install brotli or brotlicffi >= 1.2.0 to decode 'br'.
```

这是因为智联招聘网站使用了Brotli压缩（br），但Scrapy无法解压。

## 解决方案

### 方法1：安装brotli库（推荐）

```bash
pip install brotli
```

或者：

```bash
pip install brotlicffi
```

### 方法2：使用requirements.txt安装

已在 `mysite/requirements.txt` 中添加了 `brotli>=1.0.0`，运行：

```bash
cd mysite
pip install -r requirements.txt
```

## 验证安装

安装后，重新运行爬虫：

```bash
cd mysite/job_crawlers
scrapy crawl zhilian -L INFO
```

如果安装成功，应该不会再看到Brotli压缩警告，并且能够正确提取字段。

## 临时解决方案

如果暂时不想安装brotli库，我已经修改了设置文件，移除了请求头中的 `br`，只使用 `gzip, deflate`。但这可能导致某些页面无法正常访问。

## 注意事项

- `brotli` 和 `brotlicffi` 功能相同，安装其中一个即可
- `brotlicffi` 是纯Python实现，兼容性更好
- `brotli` 是C扩展，性能更好
