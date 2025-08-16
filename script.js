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
     * 显示成功提示
     */
    showSuccessMessage: function(message) {
        // 创建成功提示
        const toast = document.createElement('div');
        toast.className = 'success-toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: #10B981;
            color: white;
            padding: 1rem 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            z-index: 1003;
            animation: slideUp 0.3s ease;
            font-weight: 500;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
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
    mode: 'carousel', // 'carousel' 或 'fixed'
    currentCityIndex: 0,
    carouselTimer: null,
    carouselInterval: 30000, // 30秒
    isCarouselRunning: false,
    selectedCity: '北京',
    
    // 全国主要城市列表
    cities: [
        '北京', '哈尔滨', '长春', '沈阳', '天津', '呼和浩特', '乌鲁木齐', '银川', '西宁', '兰州',
        '西安', '拉萨', '成都', '重庆', '贵阳', '昆明', '太原', '石家庄', '济南', '郑州',
        '合肥', '南京', '上海', '武汉', '长沙', '南昌', '杭州', '福州', '台北', '南宁',
        '海口', '广州', '香港', '澳门', '深圳', '厦门', '宁波', '青岛', '大连', '桂林',
        '汕头', '连云港', '秦皇岛', '延安', '赣州', '三亚', '雄安', '高雄', '钓鱼岛', '永兴岛', '永暑礁'
    ],
    
    init: function() {
        this.loadConfig();
        this.loadSavedSettings();
        this.initializeWeatherDisplay();
    },
    
    loadConfig: function() {
        if (AppState.rssConfig && AppState.rssConfig.settings.weatherApiKey) {
            this.apiKey = AppState.rssConfig.settings.weatherApiKey;
        }
    },
    
    loadSavedSettings: function() {
        const savedMode = Utils.storage.get('weatherMode', 'carousel');
        const savedCity = Utils.storage.get('selectedCity', '北京');
        
        this.mode = savedMode;
        this.selectedCity = savedCity;
        
        // 更新UI状态
        this.updateModeIndicator();
    },
    
    initializeWeatherDisplay: function() {
        // 静默尝试获取地理位置，不显示弹框
        this.tryGetCurrentLocation();
    },
    
    tryGetCurrentLocation: function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                this.onLocationSuccess.bind(this),
                this.onLocationError.bind(this),
                {
                    timeout: 5000,
                    enableHighAccuracy: false,
                    maximumAge: 600000 // 10分钟缓存
                }
            );
        } else {
            this.onLocationError(new Error('浏览器不支持地理位置服务'));
        }
    },
    
    onLocationSuccess: function(position) {
        // 成功获取位置，但不立即显示，仅作为备用
        const userLocation = {
            lat: position.coords.latitude,
            lon: position.coords.longitude
        };
        
        // 如果是固定模式且没有选择城市，使用当前位置
        if (this.mode === 'fixed' && !this.selectedCity) {
            this.fetchWeatherByCoords(userLocation.lat, userLocation.lon);
        } else {
            this.startWeatherDisplay();
        }
    },
    
    onLocationError: function(error) {
        console.log('地理位置获取失败，使用默认模式:', error.message);
        this.startWeatherDisplay();
    },
    
    startWeatherDisplay: function() {
        if (this.mode === 'carousel') {
            this.startCarousel();
        } else {
            this.fetchWeatherByCity(this.selectedCity);
        }
    },
    
    startCarousel: function() {
        if (this.isCarouselRunning) return;
        
        this.isCarouselRunning = true;
        this.currentCityIndex = 0;
        
        // 立即显示第一个城市
        this.fetchCurrentCarouselCity();
        
        // 启动定时器
        this.carouselTimer = setInterval(() => {
            this.nextCarouselCity();
        }, this.carouselInterval);
    },
    
    stopCarousel: function() {
        if (this.carouselTimer) {
            clearInterval(this.carouselTimer);
            this.carouselTimer = null;
        }
        this.isCarouselRunning = false;
    },
    
    nextCarouselCity: function() {
        this.currentCityIndex = (this.currentCityIndex + 1) % this.cities.length;
        this.fetchCurrentCarouselCity();
    },
    
    fetchCurrentCarouselCity: function() {
        const city = this.cities[this.currentCityIndex];
        this.fetchWeatherByCity(city, true);
    },
    
    fetchWeatherByCity: function(cityName, isCarousel = false) {
        if (!this.apiKey || this.apiKey === 'your_openweather_api_key') {
            this.showMockWeather(cityName, isCarousel);
            return;
        }
        
        const url = `${this.apiUrl}?q=${encodeURIComponent(cityName)}&appid=${this.apiKey}&units=metric&lang=zh_cn`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('天气数据获取失败');
                }
                return response.json();
            })
            .then(data => this.onWeatherSuccess(data, isCarousel))
            .catch(error => {
                console.error('天气数据错误:', error);
                this.showMockWeather(cityName, isCarousel);
            });
    },
    
    fetchWeatherByCoords: function(lat, lon) {
        if (!this.apiKey || this.apiKey === 'your_openweather_api_key') {
            this.showMockWeather('北京', false);
            return;
        }
        
        const url = `${this.apiUrl}?lat=${lat}&lon=${lon}&appid=${this.apiKey}&units=metric&lang=zh_cn`;
        
        fetch(url)
            .then(response => {
                if (!response.ok) {
                    throw new Error('天气数据获取失败');
                }
                return response.json();
            })
            .then(data => this.onWeatherSuccess(data, false))
            .catch(error => {
                console.error('天气数据错误:', error);
                this.showMockWeather('北京', false);
            });
    },
    
    onWeatherSuccess: function(data, isCarousel = false) {
        AppState.weather = {
            temperature: Math.round(data.main.temp),
            condition: data.weather[0].description,
            humidity: data.main.humidity,
            windSpeed: Math.round(data.wind.speed * 3.6),
            location: data.name,
            icon: data.weather[0].main.toLowerCase(),
            isCarousel: isCarousel
        };
        
        this.render();
    },
    
    showMockWeather: function(cityName, isCarousel = false) {
        // 模拟天气数据
        const mockData = {
            '北京': { temp: 22, condition: '多云', humidity: 65, wind: 15, icon: 'clouds' },
            '上海': { temp: 25, condition: '晴', humidity: 58, wind: 12, icon: 'clear' },
            '广州': { temp: 28, condition: '小雨', humidity: 78, wind: 8, icon: 'rain' },
            '深圳': { temp: 27, condition: '阴', humidity: 72, wind: 10, icon: 'clouds' },
            '成都': { temp: 20, condition: '雾', humidity: 82, wind: 6, icon: 'clouds' },
            '杭州': { temp: 23, condition: '晴', humidity: 61, wind: 14, icon: 'clear' }
        };
        
        const defaultData = { temp: 22, condition: '多云', humidity: 65, wind: 15, icon: 'clouds' };
        const data = mockData[cityName] || defaultData;
        
        AppState.weather = {
            temperature: data.temp,
            condition: data.condition,
            humidity: data.humidity,
            windSpeed: data.wind,
            location: cityName,
            icon: data.icon,
            isCarousel: isCarousel
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
        DOMElements.currentCity.textContent = weather.location;
        
        // 更新天气图标
        this.updateWeatherIcon(weather.icon);
        
        // 更新模式指示器
        this.updateModeIndicator();
    },
    
    updateWeatherIcon: function(iconCode) {
        let iconPath = 'icons/sunny.svg';
        
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
    },
    
    updateModeIndicator: function() {
        const indicator = DOMElements.weatherModeIndicator;
        const modeText = indicator.querySelector('.mode-text');
        
        if (this.mode === 'carousel') {
            modeText.textContent = '轮播模式';
            indicator.className = 'weather-mode-indicator';
        } else {
            modeText.textContent = '固定城市';
            indicator.className = 'weather-mode-indicator fixed-mode';
        }
    },
    
    // 设置模式
    setMode: function(mode, selectedCity = null) {
        this.stopCarousel();
        
        this.mode = mode;
        if (selectedCity) {
            this.selectedCity = selectedCity;
        }
        
        // 保存设置
        Utils.storage.set('weatherMode', this.mode);
        Utils.storage.set('selectedCity', this.selectedCity);
        
        // 重新启动显示
        this.startWeatherDisplay();
    },
    
    // 获取当前设置
    getCurrentSettings: function() {
        return {
            mode: this.mode,
            selectedCity: this.selectedCity,
            cities: this.cities
        };
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
        // 为RSS URL添加防缓存参数
        const timestamp = Date.now();
        const cacheBuster = Math.random().toString(36).substr(2, 9);
        const rssUrlWithCache = `${feed.url}${feed.url.includes('?') ? '&' : '?'}_t=${timestamp}&_cb=${cacheBuster}`;
        const proxiedUrl = this.corsProxy + encodeURIComponent(rssUrlWithCache);
        
        console.log('获取RSS源:', feed.name, '- URL:', feed.url);
        
        return fetch(proxiedUrl, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache'
            },
            cache: 'no-store'
        })
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
// 天气设置模块
// ===========================================
const WeatherSettings = {
    selectedCity: '',
    
    init: function() {
        this.bindEvents();
        this.generateCityGrid();
    },
    
    bindEvents: function() {
        // 打开设置模态框
        DOMElements.weatherSettingsBtn.addEventListener('click', this.openModal.bind(this));
        
        // 关闭模态框
        DOMElements.closeWeatherSettings.addEventListener('click', this.closeModal.bind(this));
        DOMElements.cancelWeatherSettings.addEventListener('click', this.closeModal.bind(this));
        
        // 点击模态框背景关闭
        DOMElements.weatherSettingsModal.addEventListener('click', function(e) {
            if (e.target === DOMElements.weatherSettingsModal) {
                this.closeModal();
            }
        }.bind(this));
        
        // ESC键关闭
        DOMElements.weatherSettingsModal.addEventListener('keydown', function(e) {
            if (e.key === 'Escape') {
                this.closeModal();
            }
        }.bind(this));
        
        // 模式选择
        DOMElements.carouselMode.addEventListener('change', this.onModeChange.bind(this));
        DOMElements.fixedMode.addEventListener('change', this.onModeChange.bind(this));
        
        // 城市搜索
        DOMElements.citySearchInput.addEventListener('input', this.onCitySearch.bind(this));
        
        // 确认设置
        DOMElements.confirmWeatherSettings.addEventListener('click', this.saveSettings.bind(this));
    },
    
    openModal: function() {
        const settings = Weather.getCurrentSettings();
        
        // 设置当前模式
        if (settings.mode === 'carousel') {
            DOMElements.carouselMode.checked = true;
        } else {
            DOMElements.fixedMode.checked = true;
        }
        
        this.selectedCity = settings.selectedCity;
        this.onModeChange();
        this.updateCitySelection();
        
        DOMElements.weatherSettingsModal.style.display = 'flex';
        
        // 获取焦点
        setTimeout(() => {
            if (DOMElements.carouselMode.checked) {
                DOMElements.carouselMode.focus();
            } else {
                DOMElements.fixedMode.focus();
            }
        }, 100);
    },
    
    closeModal: function() {
        DOMElements.weatherSettingsModal.style.display = 'none';
        DOMElements.citySearchInput.value = '';
        this.selectedCity = '';
    },
    
    onModeChange: function() {
        const isFixed = DOMElements.fixedMode.checked;
        
        if (isFixed) {
            DOMElements.citySelectionSection.style.display = 'block';
        } else {
            DOMElements.citySelectionSection.style.display = 'none';
        }
    },
    
    generateCityGrid: function() {
        const cities = Weather.cities;
        const grid = DOMElements.cityGrid;
        
        grid.innerHTML = '';
        
        cities.forEach(city => {
            const cityElement = document.createElement('div');
            cityElement.className = 'city-option';
            cityElement.textContent = city;
            cityElement.dataset.city = city;
            
            cityElement.addEventListener('click', () => {
                this.selectCity(city);
            });
            
            grid.appendChild(cityElement);
        });
    },
    
    selectCity: function(city) {
        this.selectedCity = city;
        this.updateCitySelection();
    },
    
    updateCitySelection: function() {
        const cityOptions = DOMElements.cityGrid.querySelectorAll('.city-option');
        
        cityOptions.forEach(option => {
            if (option.dataset.city === this.selectedCity) {
                option.classList.add('selected');
            } else {
                option.classList.remove('selected');
            }
        });
    },
    
    onCitySearch: function() {
        const searchTerm = DOMElements.citySearchInput.value.toLowerCase();
        const cityOptions = DOMElements.cityGrid.querySelectorAll('.city-option');
        
        cityOptions.forEach(option => {
            const cityName = option.textContent.toLowerCase();
            if (cityName.includes(searchTerm)) {
                option.style.display = 'block';
            } else {
                option.style.display = 'none';
            }
        });
    },
    
    saveSettings: function() {
        const mode = DOMElements.carouselMode.checked ? 'carousel' : 'fixed';
        
        if (mode === 'fixed' && !this.selectedCity) {
            Utils.showError('请选择一个城市');
            return;
        }
        
        // 应用设置
        Weather.setMode(mode, this.selectedCity);
        
        // 关闭模态框
        this.closeModal();
        
        // 显示成功消息
        const modeText = mode === 'carousel' ? '轮播模式' : '固定城市模式';
        const message = mode === 'carousel' ? 
            `已切换到${modeText}` : 
            `已切换到${modeText}：${this.selectedCity}`;
        
        this.showSuccessMessage(message);
    },
    
    showSuccessMessage: function(message) {
        // 创建成功提示
        const toast = document.createElement('div');
        toast.className = 'success-toast';
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            bottom: 2rem;
            left: 50%;
            transform: translateX(-50%);
            background: #10B981;
            color: white;
            padding: 1rem 2rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
            z-index: 1003;
            animation: slideUp 0.3s ease;
            font-weight: 500;
        `;
        
        document.body.appendChild(toast);
        
        setTimeout(() => {
            toast.remove();
        }, 3000);
    }
};

// ===========================================
// 事件处理
// ===========================================
const EventHandlers = {
    init: function() {
        this.bindKeyboardEvents();
        this.bindWindowEvents();
    },
    
    bindKeyboardEvents: function() {
        document.addEventListener('keydown', function(e) {
            // 空格键切换主题
            if (e.code === 'Space' && !e.target.matches('input, textarea, [contenteditable]')) {
                e.preventDefault();
                Theme.toggle();
            }
            
            // 左右箭头切换新闻
            if (e.code === 'ArrowLeft' || e.code === 'ArrowRight') {
                e.preventDefault();
                News.nextNews();
            }
            
            // S键打开天气设置
            if (e.code === 'KeyS' && !e.target.matches('input, textarea, [contenteditable]')) {
                e.preventDefault();
                DOMElements.weatherSettingsBtn.click();
            }
            
            // F5或Ctrl+R强制刷新RSS数据
            if (e.code === 'F5' || (e.ctrlKey && e.code === 'KeyR')) {
                e.preventDefault();
                console.log('强制刷新RSS数据...');
                // 清除本地存储的缓存
                Utils.storage.set('lastNewsUpdate', 0);
                // 重新加载新闻
                News.fetchAllNews();
                Utils.showSuccessMessage('正在刷新RSS数据...');
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
        // 初始化时强制清除缓存
        this.clearAllCaches();
        
        // 初始化DOM元素引用
        this.initDOMElements();
        
        // 加载配置文件
        this.loadConfig();
    },
    
    clearAllCaches: function() {
        try {
            // 清除本地存储的RSS缓存
            Utils.storage.set('lastNewsUpdate', 0);
            
            // 清除Service Worker缓存（如果有）
            if ('serviceWorker' in navigator && 'caches' in window) {
                caches.keys().then(function(cacheNames) {
                    return Promise.all(
                        cacheNames.map(function(cacheName) {
                            return caches.delete(cacheName);
                        })
                    );
                });
            }
            
            console.log('缓存清除完成，强制刷新RSS数据');
        } catch (error) {
            console.warn('清除缓存时出现错误:', error);
        }
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
        DOMElements.currentCity = document.getElementById('current-city');
        DOMElements.weatherModeIndicator = document.getElementById('weather-mode-indicator');
        DOMElements.weatherSettingsBtn = document.getElementById('weather-settings-btn');
        
        // 天气设置模态框
        DOMElements.weatherSettingsModal = document.getElementById('weather-settings-modal');
        DOMElements.closeWeatherSettings = document.getElementById('close-weather-settings');
        DOMElements.carouselMode = document.getElementById('carousel-mode');
        DOMElements.fixedMode = document.getElementById('fixed-mode');
        DOMElements.citySelectionSection = document.getElementById('city-selection-section');
        DOMElements.citySearchInput = document.getElementById('city-search-input');
        DOMElements.cityGrid = document.getElementById('city-grid');
        DOMElements.confirmWeatherSettings = document.getElementById('confirm-weather-settings');
        DOMElements.cancelWeatherSettings = document.getElementById('cancel-weather-settings');
        
        // 新闻相关
        DOMElements.newsLoading = document.getElementById('news-loading');
        DOMElements.newsContent = document.getElementById('news-content');
        DOMElements.newsTitle = document.getElementById('news-title');
        DOMElements.newsSource = document.getElementById('news-source');
        DOMElements.newsTime = document.getElementById('news-time');
        
        // 控制相关
        DOMElements.themeToggle = document.getElementById('theme-toggle');
        DOMElements.errorToast = document.getElementById('error-toast');
        DOMElements.errorMessage = document.getElementById('error-message');
    },
    
    loadConfig: function() {
        // 为 config.json 添加防缓存参数
        const timestamp = Date.now();
        const configUrl = `config.json?v=${timestamp}&_cache_bust=${Math.random().toString(36).substr(2, 9)}`;
        
        fetch(configUrl, {
            method: 'GET',
            headers: {
                'Cache-Control': 'no-cache, no-store, must-revalidate',
                'Pragma': 'no-cache',
                'Expires': '0'
            },
            cache: 'no-store'
        })
            .then(function(response) {
                if (!response.ok) {
                    throw new Error('配置文件加载失败');
                }
                return response.json();
            })
            .then(function(config) {
                AppState.rssConfig = config;
                console.log('配置文件加载成功，包含', config.rssFeeds.length, '个RSS源');
                // 显示加载的RSS源名称
                const sourceNames = config.rssFeeds.map(feed => feed.name).join('、');
                console.log('RSS源：', sourceNames);
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
        WeatherSettings.init();
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