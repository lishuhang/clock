/**
 * 智能信息显示终端 - 主脚本
 * 实现时钟、天气、新闻显示功能
 * 兼容旧版本浏览器（ES5/ES6）
 */

// ===========================================
// 全局状态管理
// ===========================================
const AppState = {
    theme: 'light',
    location: null,
    weather: null,
    news: [],
    currentNewsIndex: 0,
    rssConfig: null,
    isNewNewsAvailable: false,
    lastNewsUpdate: 0,
    timers: {
        clock: null,
        news: null,
        newsUpdate: null
    }
};

// ===========================================
// DOM 元素引用
// ===========================================
const DOMElements = {
    // 时钟相关
    clock: null,
    date: null,
    timezone: null,
    
    // 天气相关
    weatherLoading: null,
    weatherContent: null,
    weatherIcon: null,
    temperature: null,
    weatherCondition: null,
    humidity: null,
    windSpeed: null,
    location: null,
    
    // 新闻相关
    newsLoading: null,
    newsContent: null,
    newsTitle: null,
    newsSource: null,
    newsTime: null,
    
    // 控制相关
    themeToggle: null,
    locationModal: null,
    cityInput: null,
    confirmLocation: null,
    cancelLocation: null,
    errorToast: null,
    errorMessage: null
};

// ===========================================
// 工具函数
// ===========================================
const Utils = {
    /**
     * 显示错误提示
     */
    showError: function(message) {
        DOMElements.errorMessage.textContent = message;
        DOMElements.errorToast.style.display = 'block';
        
        setTimeout(function() {
            DOMElements.errorToast.style.display = 'none';
        }, 5000);
    },
    
    /**
     * 格式化时间
     */
    formatTime: function(date) {
        return date.toLocaleTimeString('zh-CN', {
            hour12: false,
            hour: '2-digit',
            minute: '2-digit'
        });
    },
    
    /**
     * 格式化日期
     */
    formatDate: function(date) {
        const options = {
            year: 'numeric',
            month: 'long',
            day: 'numeric',
            weekday: 'long'
        };
        return date.toLocaleDateString('zh-CN', options);
    },
    
    /**
     * 获取相对时间
     */
    getRelativeTime: function(timestamp) {
        const now = Date.now();
        const diff = now - timestamp;
        const minutes = Math.floor(diff / (1000 * 60));
        const hours = Math.floor(diff / (1000 * 60 * 60));
        const days = Math.floor(diff / (1000 * 60 * 60 * 24));
        
        if (minutes < 1) return '刚刚';
        if (minutes < 60) return minutes + '分钟前';
        if (hours < 24) return hours + '小时前';
        return days + '天前';
    },
    
    /**
     * 防抖函数
     */
    debounce: function(func, wait) {
        let timeout;
        return function executedFunction() {
            const later = function() {
                clearTimeout(timeout);
                func.apply(this, arguments);
            }.bind(this);
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    },
    
    /**
     * 数据本地存储
     */
    storage: {
        set: function(key, value) {
            try {
                localStorage.setItem(key, JSON.stringify(value));
            } catch (e) {
                console.warn('本地存储失败:', e);
            }
        },
        
        get: function(key, defaultValue) {
            try {
                const item = localStorage.getItem(key);
                return item ? JSON.parse(item) : defaultValue;
            } catch (e) {
                console.warn('读取本地存储失败:', e);
                return defaultValue;
            }
        }
    }
};

// ===========================================
// 时钟模块
// ===========================================
const Clock = {
    init: function() {
        this.update();
        AppState.timers.clock = setInterval(this.update.bind(this), 1000);
    },
    
    update: function() {
        const now = new Date();
        
        // 更新时间
        DOMElements.clock.textContent = Utils.formatTime(now);
        
        // 更新日期
        DOMElements.date.textContent = Utils.formatDate(now);
        
        // 更新时区信息
        const timeZone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        const timeZoneName = timeZone.split('/').pop().replace('_', ' ');
        DOMElements.timezone.textContent = timeZoneName + ' 时区';
    }
};

// ===========================================
// 天气模块
// ===========================================
const Weather = {
    apiKey: '',
    apiUrl: 'https://api.openweathermap.org/data/2.5/weather',
    
    init: function() {
        this.loadConfig();
        this.getCurrentLocation();
    },
    
    loadConfig: function() {
        // 从配置文件加载 API Key
        if (AppState.rssConfig && AppState.rssConfig.settings.weatherApiKey) {
            this.apiKey = AppState.rssConfig.settings.weatherApiKey;
        }
    },
    
    getCurrentLocation: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                this.onLocationSuccess.bind(this),
                this.onLocationError.bind(this),
                {
                    timeout: 10000,
                    enableHighAccuracy: true,
                    maximumAge: 300000 // 5分钟缓存
                }
            );
        } else {
            this.onLocationError(new Error('浏览器不支持地理位置服务'));
        }
    },
    
    onLocationSuccess: function(position) {
        AppState.location = {
            lat: position.coords.latitude,
            lon: position.coords.longitude,
            name: ''
        };
        this.fetchWeather();
    },
    
    onLocationError: function(error) {
        console.warn('获取位置失败:', error.message);
        
        // 使用默认城市或显示输入框
        const defaultCity = AppState.rssConfig?.settings?.defaultCity || '北京';
        this.showLocationModal(defaultCity);
    },
    
    showLocationModal: function(defaultCity) {
        DOMElements.cityInput.value = defaultCity;
        DOMElements.locationModal.style.display = 'flex';
        DOMElements.cityInput.focus();
    },
    
    hideLocationModal: function() {
        DOMElements.locationModal.style.display = 'none';
    },
    
    setLocationByCity: function(cityName) {
        if (!cityName.trim()) {
            Utils.showError('请输入有效的城市名称');
            return;
        }
        
        AppState.location = {
            lat: null,
            lon: null,
            name: cityName.trim()
        };
        
        this.hideLocationModal();
        this.fetchWeather();
    },
    
    fetchWeather: function() {
        if (!this.apiKey || this.apiKey === 'your_openweather_api_key') {
            // 使用模拟数据
            this.showMockWeather();
            return;
        }
        
        let url = this.apiUrl + '?appid=' + this.apiKey + '&units=metric&lang=zh_cn';
        
        if (AppState.location.lat && AppState.location.lon) {
            url += '&lat=' + AppState.location.lat + '&lon=' + AppState.location.lon;
        } else if (AppState.location.name) {
            url += '&q=' + encodeURIComponent(AppState.location.name);
        }
        
        fetch(url)
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('天气数据获取失败');
                }
                return response.json();
            })
            .then(this.onWeatherSuccess.bind(this))
            .catch(this.onWeatherError.bind(this));
    },
    
    onWeatherSuccess: function(data) {
        AppState.weather = {
            temperature: Math.round(data.main.temp),
            condition: data.weather[0].description,
            humidity: data.main.humidity,
            windSpeed: Math.round(data.wind.speed * 3.6), // 转换为 km/h
            location: data.name,
            icon: data.weather[0].main.toLowerCase()
        };
        
        this.render();
    },
    
    onWeatherError: function(error) {
        console.error('天气数据错误:', error);
        Utils.showError('天气信息加载失败，使用模拟数据');
        this.showMockWeather();
    },
    
    showMockWeather: function() {
        // 模拟天气数据
        AppState.weather = {
            temperature: 22,
            condition: '多云',
            humidity: 65,
            windSpeed: 15,
            location: AppState.location?.name || '北京',
            icon: 'clouds'
        };
        
        this.render();
    },
    
    render: function() {
        if (!AppState.weather) return;
        
        const weather = AppState.weather;
        
        // 隐藏加载状态，显示天气信息
        DOMElements.weatherLoading.style.display = 'none';
        DOMElements.weatherContent.style.display = 'flex';
        
        // 更新天气信息
        DOMElements.temperature.textContent = weather.temperature;
        DOMElements.weatherCondition.textContent = weather.condition;
        DOMElements.humidity.textContent = weather.humidity + '%';
        DOMElements.windSpeed.textContent = weather.windSpeed + ' km/h';
        DOMElements.location.textContent = weather.location;
        
        // 更新天气图标
        this.updateWeatherIcon(weather.icon);
    },
    
    updateWeatherIcon: function(iconCode) {
        let iconPath = 'icons/sunny.svg'; // 默认图标
        
        // 根据天气状态选择图标
        switch (iconCode) {
            case 'clear':
            case 'sun':
                iconPath = 'icons/sunny.svg';
                break;
            case 'clouds':
            case 'cloud':
                iconPath = 'icons/cloudy.svg';
                break;
            case 'rain':
            case 'drizzle':
            case 'thunderstorm':
                iconPath = 'icons/rainy.svg';
                break;
            case 'snow':
                iconPath = 'icons/snowy.svg';
                break;
            default:
                iconPath = 'icons/cloudy.svg';
        }
        
        DOMElements.weatherIcon.src = iconPath;
        DOMElements.weatherIcon.alt = AppState.weather.condition;
    }
};

// ===========================================
// 新闻模块
// ===========================================
const News = {
    corsProxy: 'https://api.allorigins.win/raw?url=',
    updateInterval: 600000, // 10分钟
    displayDuration: 10000,  // 10秒
    
    init: function() {
        this.loadConfig();
        this.fetchAllNews();
        this.startUpdateTimer();
    },
    
    loadConfig: function() {
        if (AppState.rssConfig && AppState.rssConfig.settings) {
            const settings = AppState.rssConfig.settings;
            this.corsProxy = settings.corsProxy || this.corsProxy;
            this.updateInterval = settings.newsUpdateInterval || this.updateInterval;
            this.displayDuration = settings.newsDisplayDuration || this.displayDuration;
        }
    },
    
    fetchAllNews: function() {
        if (!AppState.rssConfig || !AppState.rssConfig.rssFeeds) {
            this.showMockNews();
            return;
        }
        
        const feeds = AppState.rssConfig.rssFeeds;
        const promises = feeds.map(this.fetchSingleFeed.bind(this));
        
        Promise.allSettled(promises)
            .then(this.onAllFeedsComplete.bind(this));
    },
    
    fetchSingleFeed: function(feed) {
        return fetch(this.corsProxy + encodeURIComponent(feed.url))
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('HTTP ' + response.status);
                }
                return response.text();
            })
            .then(function(xmlText) {
                return this.parseRSSFeed(xmlText, feed);
            }.bind(this))
            .catch(function(error) {
                console.warn('获取RSS失败:', feed.name, error.message);
                return [];
            });
    },
    
    parseRSSFeed: function(xmlText, feedInfo) {
        try {
            const parser = new DOMParser();
            const xmlDoc = parser.parseFromString(xmlText, 'text/xml');
            
            // 检查解析错误
            if (xmlDoc.querySelector('parsererror')) {
                throw new Error('XML解析错误');
            }
            
            const items = xmlDoc.querySelectorAll('item');
            const news = [];
            
            for (let i = 0; i < items.length && i < 20; i++) {
                const item = items[i];
                const titleEl = item.querySelector('title');
                const linkEl = item.querySelector('link');
                const pubDateEl = item.querySelector('pubDate');
                
                if (titleEl && titleEl.textContent.trim()) {
                    const pubDate = pubDateEl ? new Date(pubDateEl.textContent) : new Date();
                    
                    news.push({
                        title: titleEl.textContent.trim(),
                        link: linkEl ? linkEl.textContent.trim() : '',
                        pubDate: pubDate,
                        timestamp: pubDate.getTime(),
                        source: feedInfo.name,
                        category: feedInfo.category || '新闻',
                        isNew: false
                    });
                }
            }
            
            return news;
        } catch (error) {
            console.error('RSS解析错误:', error);
            return [];
        }
    },
    
    onAllFeedsComplete: function(results) {
        const allNews = [];
        
        results.forEach(function(result) {
            if (result.status === 'fulfilled' && Array.isArray(result.value)) {
                allNews.push.apply(allNews, result.value);
            }
        });
        
        if (allNews.length === 0) {
            this.showMockNews();
            return;
        }
        
        // 按时间排序并限制数量
        allNews.sort(function(a, b) {
            return b.timestamp - a.timestamp;
        });
        
        const maxItems = AppState.rssConfig?.settings?.maxNewsItems || 50;
        const newNews = allNews.slice(0, maxItems);
        
        // 检查是否有新内容
        this.markNewNews(newNews);
        
        AppState.news = newNews;
        AppState.currentNewsIndex = 0;
        AppState.lastNewsUpdate = Date.now();
        
        this.startTicker();
    },
    
    markNewNews: function(newNews) {
        const lastUpdate = Utils.storage.get('lastNewsUpdate', 0);
        const currentTime = Date.now();
        
        AppState.isNewNewsAvailable = false;
        
        newNews.forEach(function(news) {
            if (news.timestamp > lastUpdate) {
                news.isNew = true;
                AppState.isNewNewsAvailable = true;
            }
        });
        
        Utils.storage.set('lastNewsUpdate', currentTime);
    },
    
    showMockNews: function() {
        // 模拟新闻数据
        AppState.news = [
            {
                title: '智能信息显示终端正常运行，欢迎使用！',
                link: '',
                pubDate: new Date(),
                timestamp: Date.now(),
                source: '系统通知',
                category: '系统',
                isNew: true
            },
            {
                title: '请在 config.json 中配置 RSS 源和 API 密钥以获取实时信息',
                link: '',
                pubDate: new Date(Date.now() - 60000),
                timestamp: Date.now() - 60000,
                source: '系统提示',
                category: '配置',
                isNew: false
            }
        ];
        
        AppState.currentNewsIndex = 0;
        this.startTicker();
    },
    
    startTicker: function() {
        if (AppState.news.length === 0) return;
        
        // 隐藏加载状态，显示新闻内容
        DOMElements.newsLoading.style.display = 'none';
        DOMElements.newsContent.style.display = 'flex';
        
        // 显示当前新闻
        this.showCurrentNews();
        
        // 启动定时切换
        this.startNewsRotation();
    },
    
    showCurrentNews: function() {
        if (AppState.news.length === 0) return;
        
        const currentNews = AppState.news[AppState.currentNewsIndex];
        
        // 更新新闻内容
        DOMElements.newsTitle.textContent = currentNews.title;
        DOMElements.newsSource.textContent = currentNews.source;
        DOMElements.newsTime.textContent = Utils.getRelativeTime(currentNews.timestamp);
        
        // 设置新新闻样式
        if (currentNews.isNew) {
            DOMElements.newsTitle.classList.add('new-news');
        } else {
            DOMElements.newsTitle.classList.remove('new-news');
        }
    },
    
    startNewsRotation: function() {
        if (AppState.timers.news) {
            clearInterval(AppState.timers.news);
        }
        
        AppState.timers.news = setInterval(function() {
            this.nextNews();
        }.bind(this), this.displayDuration);
    },
    
    nextNews: function() {
        if (AppState.news.length <= 1) return;
        
        // 添加淡出效果
        DOMElements.newsContent.classList.add('fade-out');
        
        setTimeout(function() {
            // 切换到下一条新闻
            AppState.currentNewsIndex = (AppState.currentNewsIndex + 1) % AppState.news.length;
            this.showCurrentNews();
            
            // 移除淡出效果
            DOMElements.newsContent.classList.remove('fade-out');
        }.bind(this), 250);
    },
    
    startUpdateTimer: function() {
        AppState.timers.newsUpdate = setInterval(function() {
            console.log('更新新闻数据...');
            this.fetchAllNews();
        }.bind(this), this.updateInterval);
    }
};

// ===========================================
// 主题切换模块
// ===========================================
const Theme = {
    init: function() {
        // 读取本地存储的主题设置
        const savedTheme = Utils.storage.get('theme', null);
        
        if (savedTheme) {
            AppState.theme = savedTheme;
        } else {
            // 根据系统偏好设置默认主题
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                AppState.theme = 'dark';
            } else {
                AppState.theme = 'light';
            }
        }
        
        this.apply();
        this.bindEvents();
    },
    
    apply: function() {
        document.documentElement.setAttribute('data-theme', AppState.theme);
        this.updateToggleButton();
    },
    
    updateToggleButton: function() {
        const ariaLabel = AppState.theme === 'light' ? '切换到深色模式' : '切换到浅色模式';
        DOMElements.themeToggle.setAttribute('aria-label', ariaLabel);
    },
    
    toggle: function() {
        AppState.theme = AppState.theme === 'light' ? 'dark' : 'light';
        this.apply();
        Utils.storage.set('theme', AppState.theme);
    },
    
    bindEvents: function() {
        DOMElements.themeToggle.addEventListener('click', this.toggle.bind(this));
        
        // 监听系统主题变化
        if (window.matchMedia) {
            const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
            mediaQuery.addEventListener('change', this.onSystemThemeChange.bind(this));
        }
    },
    
    onSystemThemeChange: function(e) {
        // 只有在用户没有手动设置主题时才跟随系统
        const savedTheme = Utils.storage.get('theme', null);
        if (!savedTheme) {
            AppState.theme = e.matches ? 'dark' : 'light';
            this.apply();
        }
    }
};

// ===========================================
// 事件处理
// ===========================================
const EventHandlers = {
    init: function() {
        this.bindLocationModal();
        this.bindKeyboardEvents();
        this.bindWindowEvents();
    },
    
    bindLocationModal: function() {
        // 确认位置
        DOMElements.confirmLocation.addEventListener('click', function() {
            const cityName = DOMElements.cityInput.value;
            Weather.setLocationByCity(cityName);
        });
        
        // 取消位置设置
        DOMElements.cancelLocation.addEventListener('click', function() {
            Weather.hideLocationModal();
            Weather.showMockWeather();
        });
        
        // 回车键确认
        DOMElements.cityInput.addEventListener('keypress', function(e) {
            if (e.key === 'Enter') {
                const cityName = DOMElements.cityInput.value;
                Weather.setLocationByCity(cityName);
            }
        });
        
        // ESC键关闭
        DOMElements.locationModal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                Weather.hideLocationModal();
                Weather.showMockWeather();
            }
        });
    },
    
    bindKeyboardEvents: function() {
        document.addEventListener('keydown', function(e) {
            // 空格键切换主题
            if (e.code === 'Space' && !e.target.matches('input')) {
                e.preventDefault();
                Theme.toggle();
            }
            
            // 左右箭头切换新闻
            if (e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
                e.preventDefault();
                News.nextNews();
            }
        });
    },
    
    bindWindowEvents: function() {
        // 窗口获取/失去焦点时暂停/恢复动画
        document.addEventListener('visibilitychange', function() {
            if (document.hidden) {
                // 暂停所有定时器
                Object.keys(AppState.timers).forEach(function(key) {
                    if (AppState.timers[key]) {
                        clearInterval(AppState.timers[key]);
                    }
                });
            } else {
                // 恢复所有功能
                Clock.init();
                News.startNewsRotation();
                News.startUpdateTimer();
            }
        });
        
        // 窗口大小变化时的处理
        window.addEventListener('resize', Utils.debounce(function() {
            // 在移动设备上隐藏地址栏
            if (window.innerHeight < 500) {
                document.body.style.height = '100vh';
            }
        }, 250));
    }
};

// ===========================================
// 主应用初始化
// ===========================================
const App = {
    init: function() {
        // 初始化DOM元素引用
        this.initDOMElements();
        
        // 加载配置文件
        this.loadConfig();
    },
    
    initDOMElements: function() {
        // 时钟相关
        DOMElements.clock = document.getElementById('clock');
        DOMElements.date = document.getElementById('date');
        DOMElements.timezone = document.getElementById('timezone');
        
        // 天气相关
        DOMElements.weatherLoading = document.getElementById('weather-loading');
        DOMElements.weatherContent = document.getElementById('weather-content');
        DOMElements.weatherIcon = document.getElementById('weather-icon');
        DOMElements.temperature = document.getElementById('temperature');
        DOMElements.weatherCondition = document.getElementById('weather-condition');
        DOMElements.humidity = document.getElementById('humidity');
        DOMElements.windSpeed = document.getElementById('wind-speed');
        DOMElements.location = document.getElementById('location');
        
        // 新闻相关
        DOMElements.newsLoading = document.getElementById('news-loading');
        DOMElements.newsContent = document.getElementById('news-content');
        DOMElements.newsTitle = document.getElementById('news-title');
        DOMElements.newsSource = document.getElementById('news-source');
        DOMElements.newsTime = document.getElementById('news-time');
        
        // 控制相关
        DOMElements.themeToggle = document.getElementById('theme-toggle');
        DOMElements.locationModal = document.getElementById('location-modal');
        DOMElements.cityInput = document.getElementById('city-input');
        DOMElements.confirmLocation = document.getElementById('confirm-location');
        DOMElements.cancelLocation = document.getElementById('cancel-location');
        DOMElements.errorToast = document.getElementById('error-toast');
        DOMElements.errorMessage = document.getElementById('error-message');
    },
    
    loadConfig: function() {
        fetch('config.json')
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('配置文件加载失败');
                }
                return response.json();
            })
            .then(function(config) {
                AppState.rssConfig = config;
                this.startApp();
            }.bind(this))
            .catch(function(error) {
                console.error('加载配置失败:', error);
                Utils.showError('配置文件加载失败，使用默认设置');
                this.startApp();
            }.bind(this));
    },
    
    startApp: function() {
        // 初始化所有模块
        Theme.init();
        Clock.init();
        Weather.init();
        News.init();
        EventHandlers.init();
        
        console.log('智能信息显示终端启动完成！');
    }
};

// 等待DOM加载完成后启动应用
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', App.init.bind(App));
} else {
    App.init();
}