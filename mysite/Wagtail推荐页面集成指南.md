# Wagtail 个性化推荐页面集成指南

## 已完成的工作

### 1. 创建了 RecommendationsPage 模型
- 位置：`jobs/models.py`
- 功能：Wagtail页面模型，包含个性化推荐逻辑
- 特点：
  - 继承自 `Page` 模型
  - 重写 `get_context` 方法实现推荐逻辑
  - 支持在Wagtail后台编辑页面介绍

### 2. 创建了 Wagtail 模板
- 位置：`jobs/templates/jobs/recommendations_page.html`
- 特点：
  - 继承自 `base.html`（Wagtail基础模板）
  - 使用 `wagtailcore_tags` 标签
  - 响应式设计，适配移动端
  - 美观的卡片式布局

### 3. 创建了模板标签过滤器
- 位置：`jobs/templatetags/job_filters.py`
- 功能：提供 `split` 过滤器用于分割字符串

## 使用步骤

### 1. 创建数据库迁移

在项目根目录运行：
```bash
python manage.py makemigrations
python manage.py migrate
```

### 2. 在 Wagtail 后台创建推荐页面

1. 访问 Wagtail 管理后台：`http://localhost:8000/admin/`
2. 进入 "Pages" 菜单
3. 选择要添加推荐页面的父页面（通常是 HomePage）
4. 点击 "Add child page"
5. 选择 "个性化推荐页面" (RecommendationsPage)
6. 填写：
   - Title: "个性化推荐" 或 "为您推荐"
   - Slug: "recommendations"（这将创建 `/recommendations/` URL）
   - 页面介绍（可选）
7. 点击 "Publish" 发布页面

### 3. 更新 URL 配置（如果需要）

如果希望 `/recommendations/` 直接指向这个Wagtail页面，确保：
- Wagtail路由在 `local/urls.py` 中正确配置
- 推荐页面的slug设置为 "recommendations"

### 4. 测试页面

1. 访问：`http://localhost:8000/recommendations/`
2. 如果未登录，会显示登录提示
3. 如果已登录但没有学生档案，会显示完善档案提示
4. 如果已登录且有档案，会显示个性化推荐列表

## 功能特点

### 推荐算法
- **规则1**：按用户偏好职位类型筛选
- **规则2**：按偏好工作地点筛选
- **规则3**：按专业匹配（关键词匹配）
- **规则4**：应届生优先

### 页面特性
- ✅ 集成到Wagtail CMS
- ✅ 可在后台编辑页面内容
- ✅ 响应式设计
- ✅ 美观的UI设计
- ✅ 推荐理由显示
- ✅ 匹配度评分

## 与原有视图函数的区别

### 原有方式（Django视图）
- 使用 `@login_required` 装饰器
- 通过URL路由直接访问
- 模板继承 `jobs/base.html`

### 新方式（Wagtail页面）
- 通过Wagtail页面模型管理
- 可在后台编辑页面内容
- 模板继承 `base.html`（Wagtail基础模板）
- 更好的SEO支持
- 支持页面版本控制

## 注意事项

1. **迁移文件**：需要运行 `makemigrations` 和 `migrate` 来创建数据库表
2. **模板标签**：确保 `jobs` app 在 `INSTALLED_APPS` 中
3. **权限**：推荐页面需要用户登录，逻辑在 `get_context` 中处理
4. **URL冲突**：如果原有 `/recommendations/` URL存在，需要决定使用哪个

## 后续优化建议

1. 添加推荐算法配置选项（可在Wagtail后台配置）
2. 添加推荐数量限制配置
3. 添加推荐理由的详细说明
4. 添加用户反馈功能（推荐是否有效）
5. 添加推荐历史记录
