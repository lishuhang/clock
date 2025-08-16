# 智能信息显示终端

一个现代简洁的信息显示终端网页应用，可将闲置手机/平板转换为常亮显示屏，用于显示时钟、天气和滚动新闻信息。

## 功能特点

### 🕐 实时时钟
- 大字体数字时钟显示
- 自动获取本地时间和时区
- 日期和星期显示
- 支持多时区显示

### 🌤️ 天气信息
- 自动获取地理位置
- 显示实时天气状况
- 温度、湿度、风速信息
- 直观的天气图标
- 支持手动设置城市

### 📰 新闻滚动
- 支持多个RSS源
- 自动按时间排序
- 每10秒自动切换
- 每10分钟更新内容
- 新内容高亮显示

### 🎨 用户体验
- 响应式设计，适配各种屏幕
- 深色/浅色模式自动切换
- 流畅的动画效果
- 键盘快捷键支持
- 兼容旧版浏览器

## 使用方法

### 1. 直接使用
打开 `index.html` 文件即可使用，应用会使用模拟数据显示基本功能。

### 2. 配置RSS源和API密钥

#### 编辑 `config.json` 文件：

```json
{
  "rssFeeds": [
    {
      "name": "新闻源名称",
      "url": "RSS源地址",
      "category": "新闻分类"
    }
  ],
  "settings": {
    "weatherApiKey": "your_openweather_api_key",
    "corsProxy": "https://api.allorigins.win/raw?url=",
    "newsUpdateInterval": 600000,
    "newsDisplayDuration": 10000,
    "maxNewsItems": 50,
    "defaultCity": "北京"
  }
}
```

#### 获取OpenWeatherMap API密钥：
1. 访问 [OpenWeatherMap](https://openweathermap.org/api)
2. 注册免费账户
3. 获取API Key
4. 将API Key填入 `config.json` 的 `weatherApiKey` 字段

### 3. 本地运行

由于浏览器安全策略，建议使用本地服务器运行：

```bash
# 使用Python
python -m http.server 8000

# 使用Node.js
npx serve .

# 访问 http://localhost:8000
```

### 4. 部署到云平台

支持部署到各种静态托管平台：
- GitHub Pages
- Cloudflare Pages
- Vercel
- Netlify

## 快捷键

- **空格键**: 切换深色/浅色模式
- **左/右箭头**: 手动切换新闻
- **ESC键**: 关闭模态框

## 技术特点

- **纯原生技术**: 仅使用HTML5、CSS3、JavaScript
- **无依赖**: 不需要任何外部框架或库
- **响应式设计**: 适配手机、平板、桌面设备
- **离线友好**: 所有资源本地化存储
- **兼容性强**: 支持2015年后的现代浏览器

## 文件结构

```
info-terminal/
├── index.html          # 主页面
├── style.css           # 样式文件
├── script.js           # JavaScript逻辑
├── config.json         # 配置文件
├── icons/              # 图标文件夹
│   ├── sunny.svg       # 晴天图标
│   ├── cloudy.svg      # 多云图标
│   ├── rainy.svg       # 雨天图标
│   ├── snowy.svg       # 雪天图标
│   ├── sun.svg         # 太阳图标（主题切换）
│   └── moon.svg        # 月亮图标（主题切换）
└── README.md           # 说明文档
```

## 常见问题

### Q: 为什么天气信息显示模拟数据？
A: 需要在 `config.json` 中配置有效的 OpenWeatherMap API密钥。

### Q: 新闻不显示怎么办？
A: 确保RSS源地址有效，或检查CORS代理设置。

### Q: 如何添加更多RSS源？
A: 编辑 `config.json` 文件，在 `rssFeeds` 数组中添加新的RSS源配置。

### Q: 支持哪些设备？
A: 支持所有现代浏览器的设备，包括手机、平板、电脑等。

## 推荐RSS源

以下是一些可用的中文RSS源（需要根据实际情况验证可用性）：

- 新华网: http://www.xinhuanet.com/politics/news_politics.xml
- 人民网: http://www.people.com.cn/rss/politics.xml
- 央视网: http://news.cctv.com/rss/china.xml
- 网易新闻: https://news.163.com/special/0001386F/rss_newstop.xml

**注意**: RSS源地址可能会变化，使用前请验证有效性。

## 开发说明

本应用采用模块化设计，主要模块包括：
- **App**: 主应用初始化
- **Clock**: 时钟功能
- **Weather**: 天气信息
- **News**: 新闻管理
- **Theme**: 主题切换
- **EventHandlers**: 事件处理
- **Utils**: 工具函数

代码结构清晰，易于维护和扩展。

## 许可证

本项目采用 MIT 许可证，可自由使用和修改。