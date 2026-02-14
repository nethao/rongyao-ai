# 模拟邮件抓取工具

## 快速使用

### 方法1: Shell脚本（推荐）

```bash
# 基本用法
./scripts/mock.sh <公众号链接> [标题]

# 示例
./scripts/mock.sh "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ" "测试文章"

# 不指定标题（默认为"测试文章"）
./scripts/mock.sh "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ"
```

### 方法2: Python脚本

```bash
# 在容器内执行
sudo docker-compose exec backend python /app/mock_email.py <链接> [标题]

# 示例
sudo docker-compose exec backend python /app/mock_email.py \
  "https://mp.weixin.qq.com/s/K1xbW7b7xB2b51rgB28UzQ" \
  "测试文章"
```

## 功能说明

- ✅ 自动抓取公众号文章内容
- ✅ 提取并上传图片到OSS
- ✅ 创建投稿记录（状态：completed）
- ✅ 不自动触发AI转换（等待编辑操作）
- ✅ 显示抓取结果统计

## 输出示例

```
🚀 开始模拟抓取...
📧 处理: 投，头，汉台区图书馆，测试文章
✅ 完成

📊 查看结果:
✅ 投稿ID: 15
📝 标题: 测试文章
📊 状态: completed
📄 草稿数: 0
🖼️  图片数: 42
```

## 后续操作

1. 刷新投稿列表页面
2. 找到新创建的投稿
3. 点击 **"AI转换"** 按钮触发AI处理
4. 或直接点击 **"详情"** 查看原文

## 文件位置

- Shell脚本: `/home/nethao/rongyao-ai/scripts/mock.sh`
- Python脚本: `/home/nethao/rongyao-ai/backend/mock_email.py`
