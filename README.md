# X (Twitter) 互动数据采集系统

这是一个基于 Flask 开发的 X (Twitter) 互动数据采集系统，用于自动采集和存储指定媒体账号(media_acocunt)的互动数据。

## 功能特点

- 支持采集多种互动类型数据：
  - 转发并评论（quote）
  - 仅转发（retweet）
  - 仅评论（reply）
  
- 支持定时自动采集更新
- 支持自定义采集频率（支持秒、分钟、小时、天、周）
- 提供 RESTful API 接口
- 数据持久化存储

## 技术栈

- Flask：Web 框架
- Flask-SQLAlchemy：ORM 框架
- Flask-APScheduler：任务调度
- Tweepy：Twitter API 客户端
- Mysql：数据存储

## 环境要求

- Python 3.x
- Mysql 数据库
- Twitter API 密钥

## 安装配置

1. 克隆项目并安装依赖：
```bash
git clone [项目地址]
cd [项目目录]
pip install -r requirements.txt
```

2. 配置环境变量：
在用户目录下创建 `.twitter_relay/.env` 文件，添加以下配置：
```bash
API_KEY=example
API_SECRET=example
ACCESS_TOKEN=example
ACCESS_SECRET=example
BEARER_TOKEN=example
DATABASE_URL=mysql+pymysql://useranme:password@addr/dbname
NOSTR_SECRET=nsecxxxxexample
```

3. 初始化数据库：

执行 `./flaskr/schema.sql` 中所有sql语句进行table初始化以及api key初始化。

## API 接口定义

参考 `https://kxx0hmk42lx.feishu.cn/docx/JO9Rd2g58oTCr5xeNSicCOPnnNh`

## 运行项目
进入项目根目录执行：
```bash
python run.py
```

## 测试

可以查看`test_utils.py`中的构建请求的函数。

项目包含完整的测试用例，可以通过运行以下命令执行测试：

```bash
python -m tests.api_test
```
以及
```bash
python -m tests.admin_test
```

## 注意事项

1. 请确保 Twitter API 密钥配置正确
2. 注意 Twitter API 的访问频率限制，参考：https://docs.x.com/x-api/fundamentals/rate-limits
3. 建议根据实际需求调整数据采集频率
4. 数据库索引已针对查询进行优化
