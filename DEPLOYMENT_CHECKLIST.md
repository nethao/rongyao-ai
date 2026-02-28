# 荣耀AI审核发布系统 - 部署准备清单

> 📅 创建日期: 2024年
> 🎯 目标: 协助完成服务器部署的前期准备工作
> ⏱️ 预计部署时间: 30-40分钟

---

## 📋 目录

- [第一部分：服务器基本信息](#第一部分服务器基本信息)
- [第二部分：API密钥和配置](#第二部分api密钥和配置)
- [第三部分：安全配置](#第三部分安全配置)
- [第四部分：代码准备](#第四部分代码准备)
- [第五部分：信息填写模板](#第五部分信息填写模板)
- [第六部分：部署流程预览](#第六部分部署流程预览)

---

## 第一部分：服务器基本信息

### 1.1 服务器访问信息 ⭐ 必需

| 项目 | 说明 | 示例 | 状态 |
|------|------|------|------|
| 服务器IP地址 | 公网IP地址 | `123.456.789.012` | ☐ 未准备 |
| SSH端口 | SSH服务端口 | `22` (默认) | ☐ 未准备 |
| SSH用户名 | 登录用户名 | `root` 或 `ubuntu` | ☐ 未准备 |
| SSH认证方式 | 密码或密钥 | 密码 / SSH私钥 | ☐ 未准备 |
| SSH密码/密钥 | 登录凭证 | `********` | ☐ 未准备 |

**注意事项:**
- 建议使用root用户或具有sudo权限的用户
- 如使用密钥认证,请准备好私钥文件(.pem或.key)
- 确保SSH服务已启动且可以远程访问

### 1.2 服务器配置确认 ⭐ 必需

| 配置项 | 最低要求 | 推荐配置 | 实际配置 | 状态 |
|--------|----------|----------|----------|------|
| 操作系统 | Ubuntu 20.04+ / CentOS 8+ | Ubuntu 22.04 LTS | _________ | ☐ 未确认 |
| CPU核心数 | 4核 | 8核 | ___核 | ☐ 未确认 |
| 内存大小 | 8GB | 16GB | ___GB | ☐ 未确认 |
| 磁盘空间 | 50GB | 100GB | ___GB | ☐ 未确认 |
| 网络带宽 | 10Mbps | 100Mbps | ___Mbps | ☐ 未确认 |

| RAR/7Z 解压依赖 | 需安装 p7zip-full、unrar | 已安装 | _________ | ☐ 未确认 |

**检查命令:**
```bash
# 查看操作系统版本
cat /etc/os-release

# 查看CPU信息
lscpu | grep "CPU(s)"

# 查看内存
free -h

# 查看磁盘空间
df -h

# 查看网络
ip addr show
1.3 域名配置 (可选)
项目	说明	示例	状态
域名	访问域名	glory-ai.example.com	☐ 无域名 / ☐ 已准备
DNS解析	A记录指向服务器IP	已解析 / 未解析	☐ 未配置
SSL证书	HTTPS证书	Let's Encrypt / 自有证书	☐ 未配置
如果没有域名:

可以使用IP地址访问: http://服务器IP:8000
后期可以随时添加域名
第二部分：API密钥和配置
2.1 OpenAI API配置 ⭐ 必需
项目	说明	示例	状态
API密钥	OpenAI API Key	sk-proj-xxxxxxxxxxxxx	☐ 未准备
模型选择	使用的模型	gpt-4 / gpt-3.5-turbo	☐ 未选择
API额度	账户余额	至少$10	☐ 未确认
Base URL	API端点(可选)	https://api.openai.com/v1	☐ 使用默认
获取方式:

访问: https://platform.openai.com/api-keys
登录OpenAI账号
点击"Create new secret key"
复制并保存密钥(只显示一次)
测试命令:

curl https://api.openai.com/v1/models \
  -H "Authorization: Bearer YOUR_API_KEY"
2.2 阿里云OSS配置 (图片上传功能需要)
项目	说明	示例	状态
Access Key ID	访问密钥ID	LTAI5t...	☐ 未准备
Access Key Secret	访问密钥Secret	abc123...	☐ 未准备
Endpoint	OSS区域端点	oss-cn-hangzhou.aliyuncs.com	☐ 未准备
Bucket名称	存储桶名称	glory-ai-images	☐ 未准备
Bucket权限	读写权限	公共读 / 私有	☐ 未配置
获取方式:

登录阿里云控制台
访问"访问控制" > "用户" > "创建用户"
勾选"OpenAPI调用访问"
保存Access Key ID和Secret
创建OSS Bucket并授权
注意:

如果暂时不需要图片上传功能,可以跳过此配置
后期可以通过系统配置界面添加
2.3 IMAP邮箱配置 (邮件抓取功能需要)
项目	说明	示例	状态
IMAP服务器	邮件服务器地址	imap.gmail.com	☐ 未准备
IMAP端口	服务端口	993 (SSL)	☐ 未准备
邮箱账号	完整邮箱地址	your-email@gmail.com	☐ 未准备
邮箱密码	密码或应用专用密码	********	☐ 未准备
SSL/TLS	是否启用加密	true	☐ 未配置
常见邮箱IMAP配置:

邮箱服务商	IMAP服务器	端口	说明
Gmail	imap.gmail.com	993	需要开启IMAP并使用应用专用密码
QQ邮箱	imap.qq.com	993	需要开启IMAP服务
163邮箱	imap.163.com	993	需要开启IMAP并获取授权码
企业邮箱	咨询管理员	993	根据企业配置
注意:

Gmail需要开启"不够安全的应用访问权限"或使用应用专用密码
如果暂时不需要邮件抓取功能,可以跳过此配置
2.4 WordPress站点配置 (发布功能需要,可后期配置)
项目	说明	示例	状态
站点URL	WordPress站点地址	https://blog.example.com	☐ 未准备
用户名	管理员用户名	admin	☐ 未准备
应用密码	REST API密码	xxxx xxxx xxxx xxxx	☐ 未准备
站点名称	站点标识	A站 / B站	☐ 未准备
获取WordPress应用密码:

登录WordPress后台
用户 > 个人资料
滚动到"应用密码"部分
输入名称(如"Glory AI")并点击"添加新应用密码"
复制生成的密码
注意:

可以配置多个WordPress站点(A/B/C/D站)
此配置可以在系统部署后通过管理界面添加
第三部分：安全配置
3.1 密码和密钥生成 ⭐ 必需
以下密钥我会帮您生成,或者您可以自己准备:

项目	要求	用途	状态
JWT密钥	32字符以上随机字符串	用户认证令牌加密	☐ 需要生成
数据库密码	强密码(字母+数字+符号)	PostgreSQL数据库密码	☐ 需要生成
加密密钥	32字符固定长度	配置信息加密	☐ 需要生成
生成命令(Linux/Mac):

# 生成JWT密钥(64字符)
openssl rand -hex 32

# 生成加密密钥(32字符)
openssl rand -hex 16

# 生成强密码
openssl rand -base64 24
生成命令(Windows PowerShell):

# 生成随机密钥
-join ((48..57) + (65..90) + (97..122) | Get-Random -Count 32 | % {[char]$_})
3.2 防火墙配置
需要开放的端口:

端口	服务	说明	状态
22	SSH	远程管理	☐ 未配置
80	HTTP	Web访问	☐ 未配置
443	HTTPS	安全Web访问	☐ 未配置
8000	Backend API	后端API(可选)	☐ 未配置
3000	Frontend	前端(可选)	☐ 未配置
注意:

如果使用Nginx反向代理,只需开放80和443端口
8000和3000端口可以不对外开放
3.3 SSL证书配置 (如果有域名)
选项	说明	推荐	状态
Let's Encrypt	免费自动续期证书	✅ 推荐	☐ 未配置
自有证书	已购买的SSL证书	如果已有	☐ 未配置
暂不配置	先使用HTTP	测试环境可以	☐ 暂不配置
第四部分：代码准备
4.1 代码获取方式
请选择一种方式:

方式A: Git仓库克隆 (推荐)

项目	说明	示例	状态
仓库地址	Git仓库URL	https://github.com/user/repo.git	☐ 未准备
分支名称	使用的分支	main / master	☐ 未准备
访问凭证	用户名/密码或Token	如果是私有仓库	☐ 未准备
方式B: 本地代码打包上传

项目	说明	状态
代码打包	将项目打包为.zip或.tar.gz	☐ 未准备
上传方式	SCP/SFTP上传到服务器	☐ 未准备
打包命令:

# 在项目根目录执行
tar -czf glory-ai-system.tar.gz \
  --exclude=node_modules \
  --exclude=__pycache__ \
  --exclude=.git \
  --exclude=*.pyc \
  .
第五部分：信息填写模板
5.1 快速配置模板 (复制并填写)
# ============================================
# 荣耀AI审核发布系统 - 部署配置信息
# ============================================

# 【第一部分：服务器信息】⭐ 必需
server:
  ip: "___.___.___.___ "              # 服务器IP地址
  ssh_port: 22                         # SSH端口
  ssh_user: "root"                     # SSH用户名
  ssh_auth_method: "password"          # 认证方式: password 或 key
  ssh_password: "________"             # SSH密码(如使用密码认证)
  ssh_key_path: "/path/to/key.pem"    # SSH密钥路径(如使用密钥认证)
  os: "Ubuntu 22.04"                   # 操作系统
  cpu_cores: 4                         # CPU核心数
  memory_gb: 8                         # 内存大小(GB)
  disk_gb: 50                          # 磁盘空间(GB)

# 【第二部分：域名配置】(可选)
domain:
  enabled: false                       # 是否使用域名: true 或 false
  name: "glory-ai.example.com"        # 域名(如果enabled=true)
  ssl_enabled: false                   # 是否配置SSL: true 或 false
  ssl_method: "letsencrypt"           # SSL方式: letsencrypt 或 custom

# 【第三部分：OpenAI配置】⭐ 必需
openai:
  api_key: "sk-proj-________________" # OpenAI API密钥
  model: "gpt-4"                       # 模型: gpt-4 或 gpt-3.5-turbo
  base_url: "https://api.openai.com/v1"  # API端点(通常不需要改)

# 【第四部分：阿里云OSS配置】(可选,图片上传功能需要)
oss:
  enabled: false                       # 是否启用: true 或 false
  access_key_id: "________________"    # Access Key ID
  access_key_secret: "________________" # Access Key Secret
  endpoint: "oss-cn-hangzhou.aliyuncs.com"  # OSS端点
  bucket_name: "________________"      # Bucket名称

# 【第五部分：IMAP邮箱配置】(可选,邮件抓取功能需要)
imap:
  enabled: false                       # 是否启用: true 或 false
  host: "imap.example.com"            # IMAP服务器
  port: 993                            # IMAP端口
  user: "your-email@example.com"      # 邮箱账号
  password: "________________"         # 邮箱密码
  use_ssl: true                        # 是否使用SSL

# 【第六部分：代码获取方式】
code:
  method: "git"                        # 获取方式: git 或 upload
  git_repository: "https://github.com/user/repo.git"  # Git仓库地址
  git_branch: "main"                   # Git分支
  git_username: ""                     # Git用户名(私有仓库需要)
  git_password: ""                     # Git密码或Token(私有仓库需要)

# 【第七部分：管理员账号】
admin:
  username: "admin"                    # 管理员用户名
  password: "________________"         # 管理员密码(强密码)
  email: "admin@example.com"          # 管理员邮箱

# 【第八部分：部署选项】
deployment:
  mode: "quick"                        # 部署模式: quick(快速) 或 full(完整)
  auto_start: true                     # 是否自动启动服务
  run_tests: false                     # 是否运行测试
  setup_nginx: false                   # 是否配置Nginx
  setup_ssl: false                     # 是否配置SSL

# ============================================
# 填写完成后请保存此文件
# ============================================
5.2 最小化配置模板 (快速开始)
如果您想快速看到效果,只需填写以下最基本信息:

# 最小化配置 - 快速开始
server:
  ip: "___.___.___.___ "
  ssh_user: "root"
  ssh_password: "________"

openai:
  api_key: "sk-proj-________________"
  model: "gpt-4"

admin:
  username: "admin"
  password: "________"

deployment:
  mode: "quick"
第六部分：部署流程预览
6.1 部署时间线
总计时间: 30-40分钟

┌─────────────────────────────────────────────────────────┐
│ 阶段1: 环境准备 (10分钟)                                │
├─────────────────────────────────────────────────────────┤
│ ✓ 连接服务器                                            │
│ ✓ 检查系统环境                                          │
│ ✓ 安装Docker和Docker Compose                           │
│ ✓ 配置防火墙规则                                        │
│ ✓ 创建工作目录                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 阶段2: 代码部署 (5分钟)                                 │
├─────────────────────────────────────────────────────────┤
│ ✓ 获取代码(Git克隆或上传)                               │
│ ✓ 配置环境变量(.env文件)                                │
│ ✓ 构建Docker镜像                                        │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 阶段3: 服务启动 (5分钟)                                 │
├─────────────────────────────────────────────────────────┤
│ ✓ 启动PostgreSQL数据库                                  │
│ ✓ 启动Redis缓存                                         │
│ ✓ 运行数据库迁移                                        │
│ ✓ 启动后端API服务                                       │
│ ✓ 启动Celery Worker                                     │
│ ✓ 启动前端服务                                          │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ 阶段4: 配置验证 (10分钟)                                │
├─────────────────────────────────────────────────────────┤
│ ✓ 创建管理员账号                                        │
│ ✓ 配置Nginx反向代理(如需要)                             │
│ ✓ 配置SSL证书(如需要)                                   │
│ ✓ 运行健康检查                                          │
│ ✓ 测试API端点                                           │
│ ✓ 测试前端访问                                          │
│ ✓ 验证数据库连接                                        │
│ ✓ 验证Redis连接                                         │
└─────────────────────────────────────────────────────────┘
6.2 部署后可访问的地址
如果没有域名:

前端界面: http://服务器IP:3000
后端API: http://服务器IP:8000
API文档: http://服务器IP:8000/docs
如果配置了域名和Nginx:

前端界面: https://your-domain.com
后端API: https://your-domain.com/api
API文档: https://your-domain.com/api/docs
6.3 部署模式选择
模式A: 快速体验模式 (推荐新手)

只需要: 服务器信息 + OpenAI密钥
部署时间: 20分钟
可以看到: 基础界面和AI转换功能
后续可以: 逐步添加其他功能
模式B: 完整功能模式

需要: 所有配置信息
部署时间: 40分钟
可以使用: 所有功能(邮件抓取、图片上传、WordPress发布)
适合: 生产环境直接使用
第七部分：检查清单
7.1 部署前最终检查
在开始部署前,请确认以下项目:

必需项 (⭐)

 服务器IP地址和SSH登录信息已准备
 服务器配置满足最低要求(4核8G50GB)
 OpenAI API密钥已准备且有额度
 管理员账号密码已设置
推荐项

 域名已准备并解析(如需要)
 防火墙规则已了解
 备份策略已规划
可选项

 OSS配置已准备(图片上传功能)
 IMAP配置已准备(邮件抓取功能)
 WordPress站点信息已准备(发布功能)
7.2 信息提交方式
方式1: 填写配置文件

复制上面的YAML模板
填写您的信息
保存为deployment-config.yaml
发送给我
方式2: 分步提供

先提供服务器信息和OpenAI密钥
我先完成基础部署
再逐步配置其他功能
方式3: 安全传输

敏感信息可以通过加密方式传输
或者我提供配置模板,您直接在服务器上填写
第八部分：常见问题
Q1: 我没有域名可以部署吗?
A: 可以!使用IP地址访问即可,后期可以随时添加域名。

Q2: 我暂时没有OSS和IMAP配置怎么办?
A: 没关系!可以先部署基础系统,这些功能可以后期通过管理界面配置。

Q3: 服务器配置不够怎么办?
A: 最低4核8G可以运行,但建议升级到8核16G以获得更好性能。

Q4: 部署失败了怎么办?
A: 我会提供详细的错误日志,并协助排查问题。大部分问题都可以快速解决。

Q5: 部署后如何维护?
A: 我会提供维护文档,包括备份、更新、监控等操作指南。

Q6: 数据安全如何保证?
A:

所有敏感配置都加密存储
数据库定期自动备份
支持HTTPS加密传输
可以配置防火墙和访问控制
第九部分：联系和支持
准备好开始部署了吗?
请按以下步骤操作:

填写配置信息

使用上面的模板填写您的信息
至少填写"必需项"
提供服务器访问

SSH登录信息
确保我可以连接到服务器
确认部署模式

快速体验模式 or 完整功能模式
开始部署

我会实时反馈部署进度
遇到问题会及时沟通
部署支持
📧 技术支持: 随时提问
📖 文档参考: 
DEPLOYMENT_GUIDE.md
🔧 故障排查: 提供详细日志分析
🎯 部署后培训: 系统使用指导
准备好了就告诉我,我们开始部署! 🚀

文档版本: v1.0
最后更新: 2024年
适用系统: 荣耀AI审核发布系统


这份清单已经准备好了!您可以:

1. **复制上面的内容**保存为`DEPLOYMENT_CHECKLIST.md`文件
2. **按照清单逐项准备**所需信息
3. **填写配置模板**中的信息
4. **准备好后告诉我**,我们就可以开始部署了

如果您现在就有服务器信息和OpenAI密钥,我们可以立即开始快速部署模式,让您先看到系统运行效果!
Credits used: 1.04
Elapsed time: 4m 31s
