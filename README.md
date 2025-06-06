# Markdown 表格转 PDF 工具

一个现代化的 Web 应用程序，可以将 Markdown 格式的表格转换为精美的 PDF 文档。

## ✨ 特性

-   🌐 **现代化 Web 界面**：直观的用户界面，支持在线预览
-   🈵 **完整中文支持**：专门优化的中文字体显示
-   📏 **智能自适应布局**：自动调整表格尺寸以最大化利用 A4 纸张空间
-   🔄 **多种页面方向**：支持竖版、横版和智能自适应选择
-   🎨 **专业 PDF 样式**：简洁的黑白样式，适合正式文档
-   ⚡ **快速转换**：基于 FastAPI 的高性能后端
-   📱 **响应式设计**：支持移动设备和桌面端
-   🐳 **Docker 支持**：一键部署和容器化运行

## 🚀 快速开始

### 本地运行

1. **克隆项目**

    ```bash
    git clone <repository-url>
    cd mdt2pdf
    ```

2. **创建虚拟环境**

    ```bash
    python -m venv .venv
    source .venv/bin/activate  # Linux/Mac
    # 或
    .venv\Scripts\activate     # Windows
    ```

3. **安装依赖**

    ```bash
    pip install -e .
    ```

4. **启动应用**

    ```bash
    python main.py
    ```

    or

    ```bash
    uvicorn main:app --host 127.0.0.1 --port 8000 --reload
    ```

5. **访问应用**

    打开浏览器，访问 http://localhost:8000

### Docker 运行

1. **构建镜像**

    ```bash
    docker build -t mdt2pdf .
    ```

2. **运行容器**

    ```bash
    docker run -p 8000:8000 mdt2pdf
    ```

## 📋 使用方法

### Web 界面

1. 在浏览器中打开应用程序
2. 选择示例模板或输入自定义 Markdown 表格
3. 选择页面方向（推荐使用"自适应"）
4. 点击"预览 PDF"按钮
5. 在右侧面板查看 PDF 预览
6. 点击"下载 PDF"保存文件

### 示例模板

应用内置了多个示例模板：

-   **简单示例**：基础的人员信息表格
-   **员工信息**：包含详细员工数据的表格
-   **宽表格**：多列项目管理表格
-   **财务报表**：月度财务数据表格

### API 接口

#### 健康检查

```bash
GET /health
```

#### 转换表格

```bash
POST /convert
Content-Type: multipart/form-data

参数:
- markdown_content: Markdown表格内容
- orientation: 页面方向 (portrait/landscape/auto)
```

示例：

```bash
curl -X POST \
  -F "markdown_content=| 姓名 | 年龄 | 城市 |
|------|------|------|
| 张三 | 25 | 北京 |
| 李四 | 30 | 上海 |" \
  -F "orientation=auto" \
  http://localhost:8000/convert \
  -o output.pdf
```

## 📊 Markdown 表格格式

支持标准的 Markdown 表格语法：

```markdown
| 列标题 1 | 列标题 2 | 列标题 3 |
| -------- | -------- | -------- |
| 数据 1   | 数据 2   | 数据 3   |
| 数据 4   | 数据 5   | 数据 6   |
```

### 支持的功能

-   ✅ 中文字符完美显示
-   ✅ 数字格式（包括千分位分隔符）
-   ✅ 特殊字符和符号
-   ✅ 长文本自动换行
-   ✅ 表格自动调整大小
-   ✅ 智能分页处理

## 🔧 开发

### 技术栈

-   **后端**: FastAPI, Python 3.9+
-   **PDF 生成**: ReportLab
-   **Markdown 解析**: Python-Markdown
-   **前端**: HTML5, CSS3, JavaScript (Vanilla)
-   **容器化**: Docker, Docker Compose

### 项目结构

```
mdt2pdf/
├── main.py              # 主应用程序
├── templates/           # HTML模板
│   └── index.html      # 前端界面
├── static/             # 静态资源
├── pyproject.toml      # 项目配置
├── Dockerfile          # Docker配置
├── .dockerignore       # Docker忽略文件
└── README.md          # 项目文档
```

### 核心算法

#### 智能布局算法

应用程序包含一个智能布局算法，可以：

1. **分析表格内容**：计算每列的最佳宽度
2. **检测内容长度**：根据文本长度调整列宽
3. **优化页面利用率**：最大化利用 A4 纸张空间
4. **自动选择方向**：根据表格宽度智能选择竖版或横版
5. **字体大小调整**：根据内容密度自动调整字体大小

#### 中文字体支持

-   注册系统中文字体
-   优化中文字符渲染
-   支持中英文混排
-   处理特殊字符和符号

## 🐳 部署

### 生产环境部署

1. **使用 Docker**

    ```bash
    docker build -t mdt2pdf .
    docker run -d -p 8000:8000 --name mdt2pdf-app mdt2pdf
    ```

2. **使用 Docker Compose**

    ```bash
    docker-compose up -d
    ```

3. **反向代理配置** (可选)

    使用 Nginx 或其他反向代理来处理 HTTPS 和负载均衡。

### 环境变量

目前应用程序不需要特殊的环境变量配置，但可以通过以下方式自定义：

-   `PORT`: 应用端口 (默认: 8000)
-   `HOST`: 绑定地址 (默认: 0.0.0.0)

## 📝 示例

### 基础表格

```markdown
| 姓名 | 年龄 | 城市 |
| ---- | ---- | ---- |
| 张三 | 25   | 北京 |
| 李四 | 30   | 上海 |
```

### 财务报表

```markdown
| 月份 | 收入(万元) | 支出(万元) | 净利润(万元) |
| ---- | ---------- | ---------- | ------------ |
| 1 月 | 120.5      | 85.2       | 35.3         |
| 2 月 | 98.7       | 72.1       | 26.6         |
```

### 项目管理

```markdown
| 项目名称 | 负责人   | 开始日期   | 状态   |
| -------- | -------- | ---------- | ------ |
| 网站重构 | 张工程师 | 2023-01-01 | 进行中 |
| 移动应用 | 李产品   | 2023-02-15 | 完成   |
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request 来改进这个项目！

### 开发指南

1. Fork 这个仓库
2. 创建功能分支: `git checkout -b feature/new-feature`
3. 提交更改: `git commit -am 'Add new feature'`
4. 推送分支: `git push origin feature/new-feature`
5. 提交 Pull Request

## 📄 许可证

这个项目使用 MIT 许可证 - 查看[LICENSE](LICENSE)文件了解详情。

## 🆘 支持

如果您遇到任何问题或有功能建议，请：

1. 查看现有的[Issues](../../issues)
2. 创建新的 Issue 描述您的问题
3. 提供详细的复现步骤和环境信息

## 🏆 致谢

-   [FastAPI](https://fastapi.tiangolo.com/) - 现代化的 Python Web 框架
-   [ReportLab](https://www.reportlab.com/) - PDF 生成库
-   [Python-Markdown](https://python-markdown.github.io/) - Markdown 解析器

---

**享受使用 Markdown 表格转 PDF 工具！** 🎉
