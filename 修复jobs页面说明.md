# 修复 /jobs/ 页面 404 错误

## 问题说明
访问 `/jobs/` 路径时返回 404 错误，是因为 Wagtail 中缺少 slug 为 "jobs" 的 JobIndexPage 页面。

## 解决方案

### 方法1：运行管理命令（推荐）

在项目根目录的 `mysite` 文件夹下运行：

```bash
cd mysite
python manage.py fix_job_index
```

这个命令会：
1. 检查是否存在 slug='jobs' 的 JobIndexPage
2. 如果不存在，会自动创建并发布
3. 如果存在但位置不对，会自动移动到正确位置
4. 确保页面已发布

### 方法2：在 Wagtail 管理后台手动创建

1. 访问 `http://localhost:8000/admin/`
2. 登录管理后台
3. 进入 "页面" (Pages)
4. 找到根页面（通常是 "Home"）
5. 点击 "添加子页面" (Add child page)
6. 选择 "职位索引页面" (JobIndexPage)
7. 设置：
   - 标题：职位列表
   - Slug：jobs
   - 导语：浏览所有职位信息
8. 点击 "发布" (Publish)

## 验证

创建完成后，访问 `http://localhost:8000/jobs/` 应该可以正常显示职位列表页面。

## 注意事项

- 确保页面已发布（live 状态）
- 确保页面在 Site 的 root_page 下
- 如果页面已存在但 slug 不是 "jobs"，需要修改 slug 或运行修复命令
