-- =====================================================
-- 運動天氣追蹤系統 - MySQL 資料庫設計
-- =====================================================
-- 建立日期: 2025-09-07
-- 資料庫名稱: sports_weather_tracker
-- =====================================================

-- =====================================================
-- 1. 創建資料庫
-- =====================================================
CREATE DATABASE IF NOT EXISTS sports_weather_tracker
CHARACTER SET utf8mb4
COLLATE utf8mb4_unicode_ci;

USE sports_weather_tracker;

-- =====================================================
-- 2. 用戶表 (users)
-- =====================================================
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(50) UNIQUE NOT NULL COMMENT '用戶名',
    email VARCHAR(100) UNIQUE NOT NULL COMMENT '電子郵件',
    password_hash VARCHAR(255) NOT NULL COMMENT '密碼雜湊值',
    first_name VARCHAR(50) COMMENT '名字',
    last_name VARCHAR(50) COMMENT '姓氏',
    profile_photo_url VARCHAR(500) COMMENT '個人頭像URL',
    bio TEXT COMMENT '個人簡介',
    phone VARCHAR(20) COMMENT '電話號碼',
    date_of_birth DATE COMMENT '出生日期',
    gender ENUM('male', 'female', 'other') COMMENT '性別',
    country VARCHAR(50) COMMENT '國家',
    city VARCHAR(50) COMMENT '城市',
    is_active BOOLEAN DEFAULT TRUE COMMENT '帳號是否啟用',
    last_login DATETIME COMMENT '最後登入時間',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '建立時間',
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新時間',
    INDEX idx_email (email),
    INDEX idx_username (username),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用戶信息表';

-- =====================================================
-- 3. 運動模式表 (sport_modes)
-- =====================================================
CREATE TABLE sport_modes (
    mode_id INT AUTO_INCREMENT PRIMARY KEY,
    mode_name VARCHAR(50) UNIQUE NOT NULL COMMENT '運動模式名稱 (爬山/健走/單車)',
    description VARCHAR(500) COMMENT '運動模式描述',
    icon_url VARCHAR(500) COMMENT '運動模式圖標URL',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='運動模式表';

-- =====================================================
-- 4. 運動記錄主表 (activities)
-- =====================================================
CREATE TABLE activities (
    activity_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用戶ID',
    mode_id INT NOT NULL COMMENT '運動模式ID',
    title VARCHAR(200) NOT NULL COMMENT '運動標題',
    description TEXT COMMENT '運動描述',
    start_time DATETIME NOT NULL COMMENT '開始時間',
    end_time DATETIME NOT NULL COMMENT '結束時間',
    duration_seconds INT NOT NULL COMMENT '運動時長 (秒)',
    
    -- 距離和速度
    total_distance_meters DECIMAL(10, 2) NOT NULL COMMENT '總距離 (米)',
    avg_speed_ms DECIMAL(6, 2) COMMENT '平均速度 (m/s)',
    max_speed_ms DECIMAL(6, 2) COMMENT '最大速度 (m/s)',
    
    -- 海拔數據 (僅適用於爬山)
    total_elevation_gain_meters DECIMAL(8, 2) COMMENT '上升海拔 (米)',
    total_elevation_loss_meters DECIMAL(8, 2) COMMENT '下降海拔 (米)',
    min_elevation_meters DECIMAL(8, 2) COMMENT '最低海拔 (米)',
    max_elevation_meters DECIMAL(8, 2) COMMENT '最高海拔 (米)',
    
    -- 起點和終點
    start_latitude DECIMAL(10, 8) NOT NULL COMMENT '起點緯度',
    start_longitude DECIMAL(11, 8) NOT NULL COMMENT '起點經度',
    start_location_name VARCHAR(200) COMMENT '起點位置名稱',
    end_latitude DECIMAL(10, 8) NOT NULL COMMENT '終點緯度',
    end_longitude DECIMAL(11, 8) NOT NULL COMMENT '終點經度',
    end_location_name VARCHAR(200) COMMENT '終點位置名稱',
    
    -- 運動狀態
    status ENUM('active', 'paused', 'completed', 'cancelled') DEFAULT 'completed' COMMENT '運動狀態',
    is_public BOOLEAN DEFAULT FALSE COMMENT '是否公開',
    
    -- 元數據
    gps_points_count INT DEFAULT 0 COMMENT 'GPS 點位數量',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (mode_id) REFERENCES sport_modes(mode_id),
    INDEX idx_user_id (user_id),
    INDEX idx_mode_id (mode_id),
    INDEX idx_start_time (start_time),
    INDEX idx_status (status),
    INDEX idx_location (start_latitude, start_longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='運動記錄主表';

-- =====================================================
-- 5. GPS 軌跡點位表 (gps_points)
-- =====================================================
CREATE TABLE gps_points (
    point_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT '運動記錄ID',
    latitude DECIMAL(10, 8) NOT NULL COMMENT '緯度',
    longitude DECIMAL(11, 8) NOT NULL COMMENT '經度',
    altitude DECIMAL(8, 2) COMMENT '海拔高度 (米)',
    speed_ms DECIMAL(6, 2) COMMENT '當前速度 (m/s)',
    accuracy_meters INT COMMENT 'GPS 精度 (米)',
    heading DECIMAL(5, 2) COMMENT '方向角度 (0-360度)',
    timestamp DATETIME NOT NULL COMMENT '數據時間戳',
    sequence_order INT NOT NULL COMMENT '序列順序',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id) ON DELETE CASCADE,
    INDEX idx_activity_id (activity_id),
    INDEX idx_timestamp (timestamp),
    INDEX idx_sequence (activity_id, sequence_order),
    INDEX idx_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='GPS軌跡點位表';

-- =====================================================
-- 6. 即時天氣表 (current_weather)
-- =====================================================
CREATE TABLE current_weather (
    weather_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(200) NOT NULL COMMENT '位置名稱',
    latitude DECIMAL(10, 8) NOT NULL COMMENT '緯度',
    longitude DECIMAL(11, 8) NOT NULL COMMENT '經度',
    
    -- 溫度數據
    temperature DECIMAL(5, 2) NOT NULL COMMENT '溫度 (°C)',
    feels_like_temp DECIMAL(5, 2) COMMENT '體感溫度 (°C)',
    temp_min DECIMAL(5, 2) COMMENT '最低溫度 (°C)',
    temp_max DECIMAL(5, 2) COMMENT '最高溫度 (°C)',
    
    -- 濕度和壓力
    humidity INT NOT NULL COMMENT '濕度 (%)',
    pressure INT COMMENT '氣壓 (hPa)',
    
    -- 風力數據
    wind_speed DECIMAL(5, 2) NOT NULL COMMENT '風速 (m/s)',
    wind_direction INT COMMENT '風向 (0-360度)',
    wind_direction_description VARCHAR(20) COMMENT '風向文字描述',
    wind_gust DECIMAL(5, 2) COMMENT '陣風速度 (m/s)',
    
    -- 降水和能見度
    precipitation DECIMAL(6, 2) COMMENT '降水量 (mm)',
    precipitation_probability INT COMMENT '降雨機率 (%)',
    visibility INT COMMENT '能見度 (m)',
    
    -- 雲層和紫外線
    cloud_coverage INT COMMENT '雲層覆蓋度 (%)',
    uv_index INT COMMENT '紫外線指數',
    
    -- 天氣描述
    weather_main VARCHAR(50) COMMENT '天氣主分類',
    weather_description VARCHAR(200) COMMENT '天氣詳細描述',
    weather_icon VARCHAR(50) COMMENT '天氣圖標代碼',
    
    -- 數據時間
    data_time DATETIME NOT NULL COMMENT '數據時間 (來自氣象局)',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '數據拉取時間',
    
    -- 索引
    INDEX idx_location (latitude, longitude),
    INDEX idx_data_time (data_time),
    INDEX idx_fetched_at (fetched_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='即時天氣表';

-- =====================================================
-- 7. 天氣預報表 (weather_forecast)
-- =====================================================
CREATE TABLE weather_forecast (
    forecast_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(200) NOT NULL COMMENT '位置名稱',
    latitude DECIMAL(10, 8) NOT NULL COMMENT '緯度',
    longitude DECIMAL(11, 8) NOT NULL COMMENT '經度',
    
    -- 預報時間段
    forecast_time DATETIME NOT NULL COMMENT '預報時間',
    
    -- 溫度數據
    temperature_min DECIMAL(5, 2) COMMENT '預報最低溫度 (°C)',
    temperature_max DECIMAL(5, 2) COMMENT '預報最高溫度 (°C)',
    temperature DECIMAL(5, 2) COMMENT '預報溫度 (°C)',
    
    -- 濕度和風力
    humidity INT COMMENT '預報濕度 (%)',
    wind_speed DECIMAL(5, 2) COMMENT '預報風速 (m/s)',
    wind_direction INT COMMENT '預報風向 (0-360度)',
    wind_direction_description VARCHAR(20) COMMENT '預報風向文字描述',
    
    -- 降水
    precipitation_probability INT COMMENT '降雨機率 (%)',
    precipitation_amount DECIMAL(6, 2) COMMENT '預報降水量 (mm)',
    
    -- 天氣描述
    weather_main VARCHAR(50) COMMENT '天氣主分類',
    weather_description VARCHAR(200) COMMENT '天氣詳細描述',
    weather_icon VARCHAR(50) COMMENT '天氣圖標代碼',
    
    -- 數據時間
    forecast_issued_at DATETIME NOT NULL COMMENT '預報發布時間',
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '數據拉取時間',
    
    -- 索引
    INDEX idx_location (latitude, longitude),
    INDEX idx_forecast_time (forecast_time),
    INDEX idx_issued_at (forecast_issued_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天氣預報表';

-- =====================================================
-- 8. 歷史天氣表 (weather_history)
-- =====================================================
CREATE TABLE weather_history (
    history_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    location_name VARCHAR(200) NOT NULL COMMENT '位置名稱',
    latitude DECIMAL(10, 8) NOT NULL COMMENT '緯度',
    longitude DECIMAL(11, 8) NOT NULL COMMENT '經度',
    
    -- 日期
    weather_date DATE NOT NULL COMMENT '天氣日期',
    
    -- 溫度數據
    temp_max DECIMAL(5, 2) COMMENT '當日最高溫度 (°C)',
    temp_min DECIMAL(5, 2) COMMENT '當日最低溫度 (°C)',
    avg_temp DECIMAL(5, 2) COMMENT '平均溫度 (°C)',
    
    -- 濕度和風力
    humidity INT COMMENT '平均濕度 (%)',
    wind_speed DECIMAL(5, 2) COMMENT '平均風速 (m/s)',
    wind_direction INT COMMENT '主風向',
    wind_direction_description VARCHAR(20) COMMENT '主風向文字描述',
    
    -- 降水
    precipitation DECIMAL(6, 2) COMMENT '降水量 (mm)',
    
    -- 天氣描述
    weather_description VARCHAR(200) COMMENT '天氣描述',
    
    -- 數據時間
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '記錄時間',
    
    -- 索引
    UNIQUE INDEX idx_location_date (latitude, longitude, weather_date),
    INDEX idx_weather_date (weather_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='歷史天氣表';

-- =====================================================
-- 9. 運動-天氣快照表 (activity_weather_snapshots)
-- =====================================================
CREATE TABLE activity_weather_snapshots (
    snapshot_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT '運動記錄ID',
    weather_id BIGINT COMMENT '對應的即時天氣ID',
    
    -- 快照時間
    captured_at DATETIME NOT NULL COMMENT '快照捕捉時間',
    
    -- 天氣快照數據
    temperature DECIMAL(5, 2) COMMENT '溫度快照 (°C)',
    feels_like_temp DECIMAL(5, 2) COMMENT '體感溫度快照 (°C)',
    humidity INT COMMENT '濕度快照 (%)',
    wind_speed DECIMAL(5, 2) COMMENT '風速快照 (m/s)',
    wind_direction INT COMMENT '風向快照',
    wind_direction_description VARCHAR(20) COMMENT '風向文字快照',
    precipitation DECIMAL(6, 2) COMMENT '降水量快照 (mm)',
    precipitation_probability INT COMMENT '降雨機率快照 (%)',
    visibility INT COMMENT '能見度快照 (m)',
    uv_index INT COMMENT '紫外線指數快照',
    cloud_coverage INT COMMENT '雲層覆蓋度快照 (%)',
    
    -- 天氣描述
    weather_description VARCHAR(200) COMMENT '天氣描述',
    
    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id) ON DELETE CASCADE,
    FOREIGN KEY (weather_id) REFERENCES current_weather(weather_id) ON DELETE SET NULL,
    INDEX idx_activity_id (activity_id),
    INDEX idx_captured_at (captured_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='運動-天氣快照表';

-- =====================================================
-- 10. 天氣建議表 (weather_recommendations)
-- =====================================================
CREATE TABLE weather_recommendations (
    recommendation_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    activity_id BIGINT NOT NULL COMMENT '運動記錄ID',
    mode_id INT NOT NULL COMMENT '運動模式ID',
    
    -- 建議等級
    recommendation_level ENUM('safe', 'warning', 'danger') DEFAULT 'safe' COMMENT '建議等級 (安全/警告/危險)',
    
    -- 建議原因 (可能有多個)
    reasons JSON COMMENT '建議原因 JSON 陣列',
    
    -- 建議文字
    suggestions TEXT COMMENT '詳細建議',
    
    -- 天氣因素詳情
    temperature_status VARCHAR(50) COMMENT '溫度狀態 (optimal/warning/danger)',
    humidity_status VARCHAR(50) COMMENT '濕度狀態',
    wind_status VARCHAR(50) COMMENT '風力狀態',
    precipitation_status VARCHAR(50) COMMENT '降水狀態',
    visibility_status VARCHAR(50) COMMENT '能見度狀態',
    uv_status VARCHAR(50) COMMENT '紫外線狀態',
    
    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (activity_id) REFERENCES activities(activity_id) ON DELETE CASCADE,
    FOREIGN KEY (mode_id) REFERENCES sport_modes(mode_id),
    INDEX idx_activity_id (activity_id),
    INDEX idx_recommendation_level (recommendation_level)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天氣建議表';

-- =====================================================
-- 11. 用戶最愛位置表 (favorite_locations)
-- =====================================================
CREATE TABLE favorite_locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用戶ID',
    location_name VARCHAR(200) NOT NULL COMMENT '位置名稱',
    latitude DECIMAL(10, 8) NOT NULL COMMENT '緯度',
    longitude DECIMAL(11, 8) NOT NULL COMMENT '經度',
    description VARCHAR(500) COMMENT '位置描述',
    icon_url VARCHAR(500) COMMENT '位置圖標URL',
    visit_count INT DEFAULT 0 COMMENT '訪問次數',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_location (latitude, longitude)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用戶最愛位置表';

-- =====================================================
-- 12. 活動統計表 (activity_statistics)
-- =====================================================
CREATE TABLE activity_statistics (
    stat_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用戶ID',
    mode_id INT NOT NULL COMMENT '運動模式ID',
    stat_date DATE NOT NULL COMMENT '統計日期',
    
    -- 統計數據
    activities_count INT DEFAULT 0 COMMENT '運動次數',
    total_distance_meters DECIMAL(15, 2) DEFAULT 0 COMMENT '總距離 (米)',
    total_duration_seconds INT DEFAULT 0 COMMENT '總時長 (秒)',
    avg_speed_ms DECIMAL(6, 2) COMMENT '平均速度 (m/s)',
    total_elevation_gain_meters DECIMAL(8, 2) DEFAULT 0 COMMENT '總上升海拔 (米)',
    
    -- 天氣統計
    avg_temperature DECIMAL(5, 2) COMMENT '平均溫度 (°C)',
    avg_humidity INT COMMENT '平均濕度 (%)',
    avg_wind_speed DECIMAL(5, 2) COMMENT '平均風速 (m/s)',
    
    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    FOREIGN KEY (mode_id) REFERENCES sport_modes(mode_id),
    UNIQUE INDEX idx_user_mode_date (user_id, mode_id, stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='活動統計表';

-- =====================================================
-- 13. 天氣警告表 (weather_alerts)
-- =====================================================
CREATE TABLE weather_alerts (
    alert_id BIGINT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL COMMENT '用戶ID',
    location_name VARCHAR(200) NOT NULL COMMENT '位置名稱',
    latitude DECIMAL(10, 8) NOT NULL COMMENT '緯度',
    longitude DECIMAL(11, 8) NOT NULL COMMENT '經度',
    
    -- 警告信息
    alert_type VARCHAR(100) NOT NULL COMMENT '警告類型 (暴雨/寒流/高溫/強風等)',
    alert_level VARCHAR(50) COMMENT '警告等級',
    alert_description TEXT COMMENT '警告描述',
    
    -- 時間信息
    alert_issued_at DATETIME NOT NULL COMMENT '警告發布時間',
    alert_expires_at DATETIME COMMENT '警告過期時間',
    
    -- 用戶狀態
    is_active BOOLEAN DEFAULT TRUE COMMENT '警告是否激活',
    is_read BOOLEAN DEFAULT FALSE COMMENT '用戶是否已讀',
    read_at DATETIME COMMENT '用戶閱讀時間',
    
    -- 時間戳
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- 外鍵和索引
    FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),
    INDEX idx_is_active (is_active),
    INDEX idx_is_read (is_read)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='天氣警告表';

-- =====================================================
-- 14. 創建初始運動模式數據
-- =====================================================
INSERT INTO sport_modes (
    mode_name, description, icon_url
) VALUES
('爬山', '登山健行，需要注意高海拔、低溫和陡坡風險', 'icon_mountaineering.png'),
('健走', '休閒健走，適合各年齡層，需避免高溫和暴雨', 'icon_walking.png'),
('單車', '自行車騎乘，需要注意風力和路面濕度', 'icon_cycling.png');

-- =====================================================
-- 15. 創建必要的索引以提升查詢性能
-- =====================================================

-- 複合索引：用戶的活動查詢
CREATE INDEX idx_user_activity_time ON activities(user_id, start_time DESC);

-- 複合索引：特定模式的活動
CREATE INDEX idx_mode_time ON activities(mode_id, start_time DESC);

-- GPS點位查詢優化
CREATE INDEX idx_activity_sequence ON gps_points(activity_id, sequence_order);

-- 天氣數據查詢優化
CREATE INDEX idx_weather_location_time ON current_weather(location_name, data_time DESC);
CREATE INDEX idx_forecast_location_time ON weather_forecast(location_name, forecast_time);

-- 統計數據查詢優化
CREATE INDEX idx_stat_user_date ON activity_statistics(user_id, stat_date DESC);

-- 警告查詢優化
CREATE INDEX idx_alert_user_active ON weather_alerts(user_id, is_active, alert_issued_at DESC);

-- =====================================================
-- 16. 創建視圖以簡化常見查詢
-- =====================================================

-- 視圖1: 用戶最近的活動
CREATE VIEW user_recent_activities AS
SELECT 
    a.activity_id,
    a.user_id,
    u.username,
    a.title,
    sm.mode_name,
    a.start_time,
    a.end_time,
    a.total_distance_meters,
    a.duration_seconds,
    a.total_elevation_gain_meters,
    a.status,
    a.created_at
FROM activities a
JOIN users u ON a.user_id = u.user_id
JOIN sport_modes sm ON a.mode_id = sm.mode_id
WHERE a.status = 'completed'
ORDER BY a.start_time DESC;

-- 視圖2: 活動天氣統計
CREATE VIEW activity_weather_summary AS
SELECT 
    a.activity_id,
    a.user_id,
    a.title,
    sm.mode_name,
    a.start_time,
    a.end_time,
    AVG(aws.temperature) as avg_temp,
    AVG(aws.humidity) as avg_humidity,
    AVG(aws.wind_speed) as avg_wind_speed,
    MAX(aws.precipitation_probability) as max_precipitation_prob,
    wr.recommendation_level
FROM activities a
JOIN sport_modes sm ON a.mode_id = sm.mode_id
LEFT JOIN activity_weather_snapshots aws ON a.activity_id = aws.activity_id
LEFT JOIN weather_recommendations wr ON a.activity_id = wr.activity_id
GROUP BY a.activity_id, a.user_id, a.title, sm.mode_name;

-- 視圖3: 用戶運動統計概覽
CREATE VIEW user_activity_summary AS
SELECT 
    u.user_id,
    u.username,
    COUNT(DISTINCT a.activity_id) as total_activities,
    SUM(a.total_distance_meters) as total_distance_meters,
    SUM(a.duration_seconds) as total_duration_seconds,
    AVG(a.avg_speed_ms) as avg_overall_speed,
    SUM(a.total_elevation_gain_meters) as total_elevation_gain_meters,
    MAX(a.start_time) as last_activity_date
FROM users u
LEFT JOIN activities a ON u.user_id = a.user_id AND a.status = 'completed'
GROUP BY u.user_id, u.username;

-- =====================================================
-- 17. 創建存儲過程
-- =====================================================

-- 存儲過程1: 計算運動距離（使用 Haversine 公式）
DELIMITER $$

CREATE PROCEDURE calculate_activity_distance(
    IN p_activity_id BIGINT,
    OUT p_total_distance DECIMAL(10, 2)
)
BEGIN
    DECLARE v_lat1, v_lon1, v_lat2, v_lon2 DECIMAL(10, 8);
    DECLARE v_distance DECIMAL(10, 2);
    DECLARE done INT DEFAULT FALSE;
    DECLARE activity_cursor CURSOR FOR 
        SELECT latitude, longitude FROM gps_points 
        WHERE activity_id = p_activity_id 
        ORDER BY sequence_order ASC;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = TRUE;
    
    SET p_total_distance = 0;
    
    OPEN activity_cursor;
    
    read_loop: LOOP
        FETCH activity_cursor INTO v_lat2, v_lon2;
        IF done THEN
            LEAVE read_loop;
        END IF;
        
        IF v_lat1 IS NOT NULL AND v_lon1 IS NOT NULL THEN
            SET v_distance = ST_Distance_Sphere(
                POINT(v_lon1, v_lat1),
                POINT(v_lon2, v_lat2)
            );
            SET p_total_distance = p_total_distance + v_distance;
        END IF;
        
        SET v_lat1 = v_lat2;
        SET v_lon1 = v_lon2;
    END LOOP;
    
    CLOSE activity_cursor;
END$$

DELIMITER ;

-- 存儲過程2: 更新用戶統計
DELIMITER $$

CREATE PROCEDURE update_user_statistics(
    IN p_user_id INT,
    IN p_mode_id INT,
    IN p_stat_date DATE
)
BEGIN
    INSERT INTO activity_statistics (
        user_id, mode_id, stat_date,
        activities_count, total_distance_meters,
        total_duration_seconds, avg_speed_ms,
        total_elevation_gain_meters
    )
    SELECT 
        p_user_id,
        p_mode_id,
        p_stat_date,
        COUNT(*),
        COALESCE(SUM(total_distance_meters), 0),
        COALESCE(SUM(duration_seconds), 0),
        COALESCE(AVG(avg_speed_ms), 0),
        COALESCE(SUM(total_elevation_gain_meters), 0)
    FROM activities
    WHERE user_id = p_user_id
    AND mode_id = p_mode_id
    AND DATE(start_time) = p_stat_date
    AND status = 'completed'
    ON DUPLICATE KEY UPDATE
        activities_count = VALUES(activities_count),
        total_distance_meters = VALUES(total_distance_meters),
        total_duration_seconds = VALUES(total_duration_seconds),
        avg_speed_ms = VALUES(avg_speed_ms),
        total_elevation_gain_meters = VALUES(total_elevation_gain_meters),
        updated_at = CURRENT_TIMESTAMP;
END$$

DELIMITER ;

-- =====================================================
-- 18. 創建觸發器以自動更新時間戳
-- =====================================================

-- 觸發器：更新 activity 表的 updated_at
DELIMITER $$

CREATE TRIGGER activity_update_timestamp
BEFORE UPDATE ON activities
FOR EACH ROW
BEGIN
    SET NEW.updated_at = CURRENT_TIMESTAMP;
END$$

DELIMITER ;

-- 觸發器：當添加 GPS 點位時，自動更新活動的 GPS 點位計數
DELIMITER $$

CREATE TRIGGER update_gps_points_count
AFTER INSERT ON gps_points
FOR EACH ROW
BEGIN
    UPDATE activities
    SET gps_points_count = gps_points_count + 1
    WHERE activity_id = NEW.activity_id;
END$$

DELIMITER ;

-- =====================================================
-- 完成：資料庫架構設置
-- =====================================================
-- 所有表、索引、視圖和存儲過程已成功創建
-- 請確認數據庫已準備好用於應用程序開發
