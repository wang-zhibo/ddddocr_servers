# ddddocr 验证码识别平台

🦉 基于 FastAPI + ddddocr 的极简验证码识别平台，支持用户注册、登录、充值、API Key 管理、验证码识别、API 调用示例，UI 极简科技感。

## 主要功能
- 用户注册/登录/充值/余额管理
- API Key 管理与调用
- 验证码图片识别（ddddocr）
- 识别扣费、余额不足提示
- Web端演示与美化
- API 调用示例（curl/Python/JS）

## 安装依赖
```bash
pip install -r requirements.txt
```

## 启动服务
```bash
python main.py
```
默认端口：8000

## 主要页面
- `/` 首页
- `/register` 注册
- `/login` 登录
- `/me` 个人中心（余额、API Key、充值）
- `/ocr_page` 验证码识别演示
- `/api_demo` API 调用示例

## API 说明
- `POST /ocr`  
  - Header: `x-api-key: <你的API_KEY>`
  - FormData: `file` (图片文件)
  - 返回：`{"result": "识别结果", "balance": 余额}`

## 管理员账号
- 启动自动创建：用户名 `admin`，密码 `admin`

## 演示截图
> ![screenshot](screenshot.png)

---
基于 FastAPI & ddddocr，适合自部署、二次开发。 