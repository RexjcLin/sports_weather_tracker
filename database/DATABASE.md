# 運動天氣追蹤系統 - 資料庫設計文檔

## 📋 目錄
1. [概述](#概述)
2. [資料庫架構](#資料庫架構)
3. [表結構詳解](#表結構詳解)
4. [關鍵設計決策](#關鍵設計決策)
5. [查詢性能優化](#查詢性能優化)
6. [視圖和存儲過程](#視圖和存儲過程)
7. [資料流程](#資料流程)
8. [安裝和使用](#安裝和使用)

---

## 概述

運動天氣追蹤系統是一個整合中央氣象局天氣資料的運動追蹤應用，支援三種運動模式：
- **爬山** - 登山健行
- **健走** - 休閒健走
- **單車** - 自行車騎乘

系統將記錄用戶的實時 GPS 軌跡，並根據天氣條件提供相應的安全建議。

### 技術棧
- **資料庫**：MySQL 8.0+
- **後端**：Python (FastAPI)
- **前端**：Mobile App (Flutter/React Native)
- **字符集**：UTF-8MB4 (支援中文和 emoji)
- **引擎**：InnoDB (支援事務和外鍵)

---

## 資料庫架構

```
┌─────────────────────────────────────────────────────┐
│                  sports_weather_tracker DB           │
└─────────────────────────────────────────────────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────v─────┐      ┌──────v──────┐    ┌──────v──────┐
   │  用戶模塊  │      │  運動模塊    │    │  天氣模塊    │
   └──────────┘      └─────────────┘    └─────────────┘
        │                   │                   │
   • users          • activities         • current_weather
   • favorite_      • gps_points         • weather_forecast
     locations      • activity_          • weather_history
   • weather_        statistics
     alerts
```

### 表清單 (14 張表)

| 模塊 | 表名 | 用途 | 記錄數量預期 |
|-----|------|------|-----------|
| **用戶** | users | 用戶帳號和個人資訊 | 低 (數千) |
| | user_sessions | JWT refresh token session 和撤銷狀態 | 低 (每個登入裝置一筆) |
| | favorite_locations | 用戶最愛位置 | 低 (數百) |
| | weather_alerts | 天氣警告通知 | 中 (數萬) |
| **運動** | sport_modes | 運動模式定義 | 極低 (3筆) |
| | activities | 運動記錄主表 | 中 (數萬) |
| | gps_points | GPS 軌跡點位 | 高 (百萬+) |
| | activity_statistics | 運動統計資料 | 中 (數萬) |
| **天氣** | current_weather | 即時天氣 | 中 (數萬) |
| | weather_forecast | 天氣預報 | 高 (數十萬) |
| | weather_history | 歷史天氣 | 高 (數十萬) |
| | activity_weather_snapshots | 活動-天氣快照 | 高 (百萬+) |
| **建議** | weather_recommendations | 天氣建議 | 中 (數萬) |

---

## 表結構詳解

### 1. users (用戶表)
**用途**：存儲用戶帳號和個人信息

```sql
user_id (PK, INT)              -- 用戶唯一識別符
username (VARCHAR, UNIQUE)     -- 用戶名
email (VARCHAR, UNIQUE)        -- 電子郵件
password_hash (VARCHAR)        -- 加密密碼
first_name / last_name         -- 名字/姓氏
profile_photo_url              -- 頭像URL
bio                           -- 個人簡介
phone / date_of_birth         -- 電話/出生日期
gender / country / city       -- 性別/國家/城市
is_active                     -- 帳號是否啟用
last_login                    -- 最後登入時間
created_at / updated_at       -- 建立/更新時間
```

**索引**：
- `idx_email` - 用於登入
- `idx_username` - 用於搜尋用戶
- `idx_created_at` - 用於列表排序

---

### 2. sport_modes (運動模式表)
**用途**：定義系統支持的運動模式

```sql
mode_id (PK, INT)         -- 運動模式ID
mode_name (VARCHAR)       -- 運動名稱 (爬山/健走/單車)
description               -- 運動描述
icon_url                  -- 運動圖標URL
created_at / updated_at   -- 建立/更新時間
```

**初始數據**：
```
1. 爬山 - 登山健行，需要注意高海拔、低溫和陡坡風險
2. 健走 - 休閒健走，適合各年齡層，需避免高溫和暴雨
3. 單車 - 自行車騎乘，需要注意風力和路面濕度
```

### 3. user_sessions (JWT 登入 session 表)
**用途**：保存 refresh token 的雜湊值，以及登入 session 的效期和撤銷狀態。資料庫不保存 refresh token 明碼。

```text
session_id / user_id             -- session 和使用者識別符
refresh_token_hash               -- refresh token 雜湊值
issued_at / expires_at           -- 發行和到期時間
revoked_at                       -- 登出撤銷時間，可為 NULL
device_info                      -- 裝置資訊，可為 NULL
created_at                       -- 建立時間
```

**索引**：
- `idx_user_id` - 查詢使用者的登入 session
- `idx_refresh_token_hash` - 依 refresh token 雜湊值查詢 session

---

### 4. activities (運動記錄主表)
**用途**：存儲運動記錄的主要信息

```sql
activity_id (PK, BIGINT)           -- 運動記錄唯一識別符
user_id (FK)                       -- 用戶ID
mode_id (FK)                       -- 運動模式ID
title / description                -- 運動標題/描述

-- 時間信息
start_time / end_time              -- 開始/結束時間
duration_seconds                   -- 運動時長

-- 距離和速度
total_distance_meters              -- 總距離 (米)
avg_speed_ms / max_speed_ms        -- 平均/最大速度 (m/s)

-- 海拔數據（爬山專用）
total_elevation_gain_meters        -- 上升海拔
total_elevation_loss_meters        -- 下降海拔
min_elevation_meters / max_elevation_meters  -- 最低/最高海拔

-- 位置信息
start_latitude / start_longitude   -- 起點座標
start_location_name                -- 起點位置名稱
end_latitude / end_longitude       -- 終點座標
end_location_name                  -- 終點位置名稱

-- 狀態
status                             -- 運動狀態 (active/paused/completed/cancelled)
is_public                          -- 是否公開分享

-- 元數據
gps_points_count                   -- GPS 點位數量
created_at / updated_at            -- 建立/更新時間
```

**索引**：
- `idx_user_id` - 查詢用戶的所有活動
- `idx_mode_id` - 按運動模式篩選
- `idx_start_time` - 時間排序
- `idx_location` - 地理位置查詢

---

### 4. gps_points (GPS 軌跡點位表)
**用途**：存儲每個運動的詳細 GPS 軌跡

```sql
point_id (PK, BIGINT)        -- 點位唯一識別符
activity_id (FK, BIGINT)     -- 對應的運動記錄ID
latitude / longitude         -- 座標 (DECIMAL(10,8))
altitude                     -- 海拔高度 (米)
speed_ms                     -- 當前速度 (m/s)
accuracy_meters              -- GPS 精度 (米)
heading                      -- 方向角度 (0-360度)
timestamp                    -- 數據時間戳
sequence_order               -- 序列順序（用於排序軌跡）
created_at                   -- 記錄時間
```

**重要特性**：
- **高頻率寫入**：運動期間每秒可能記錄一個點位
- **大數據量**：一次 1 小時運動可能產生 3,600+ 點位
- **序列重要性**：`sequence_order` 確保軌跡順序正確

**索引**：
- `idx_activity_id` - 查詢單次運動的所有點位
- `idx_sequence` - 按順序排序軌跡
- `idx_location` - 地理位置查詢

---

### 5. current_weather (即時天氣表)
**用途**：存儲各位置的即時天氣數據

```sql
weather_id (PK, BIGINT)           -- 天氣記錄ID
location_name                     -- 位置名稱

-- 地理位置
latitude / longitude              -- 座標

-- 溫度 (°C)
temperature                       -- 當前溫度
feels_like_temp                   -- 體感溫度
temp_min / temp_max               -- 最低/最高溫度

-- 濕度和壓力
humidity                          -- 濕度 (%)
pressure                          -- 氣壓 (hPa)

-- 風力 (m/s)
wind_speed                        -- 風速
wind_direction                    -- 風向 (0-360度)
wind_gust                         -- 陣風速度

-- 降水和能見度
precipitation                     -- 降水量 (mm)
precipitation_probability         -- 降雨機率 (%)
visibility                        -- 能見度 (m)

-- 其他
cloud_coverage                    -- 雲層覆蓋度 (%)
uv_index                          -- 紫外線指數

-- 天氣描述
weather_main                      -- 天氣主分類 (Clear/Rain/Cloud等)
weather_description               -- 詳細描述
weather_icon                      -- 圖標代碼

-- 時間
data_time                         -- 數據時間（來自氣象局）
fetched_at                        -- 數據拉取時間
```

**索引**：
- `idx_location` - 按位置查詢
- `idx_data_time` - 按時間排序
- `idx_fetched_at` - 查詢最新數據

---

### 6. weather_forecast (天氣預報表)
**用途**：存儲 7 天天氣預報

```sql
forecast_id (PK, BIGINT)              -- 預報記錄ID
location_name                         -- 位置名稱
latitude / longitude                  -- 座標
forecast_time                         -- 預報時間
temperature_min / temperature_max     -- 預報溫度範圍
temperature                           -- 預報溫度
humidity                              -- 預報濕度 (%)
wind_speed / wind_direction           -- 預報風力
precipitation_probability             -- 降雨機率 (%)
precipitation_amount                  -- 預報降水量 (mm)
weather_main / weather_description    -- 天氣描述
weather_icon                          -- 圖標代碼
forecast_issued_at                    -- 預報發布時間
fetched_at                            -- 數據拉取時間
```

---

### 7. weather_history (歷史天氣表)
**用途**：存儲歷史天氣數據，用於分析和統計

```sql
history_id (PK, BIGINT)        -- 歷史記錄ID
location_name                  -- 位置名稱
latitude / longitude           -- 座標
weather_date                   -- 天氣日期

-- 溫度統計 (°C)
temp_max / temp_min            -- 最高/最低溫度
avg_temp                       -- 平均溫度

-- 其他統計
humidity                       -- 平均濕度 (%)
wind_speed                     -- 平均風速 (m/s)
wind_direction                 -- 主風向
precipitation                  -- 降水量 (mm)
weather_description            -- 天氣描述
recorded_at                    -- 記錄時間
```

**UNIQUE 索引**：`(latitude, longitude, weather_date)` - 確保每個位置每天只有一筆記錄

---

### 8. activity_weather_snapshots (運動-天氣快照表)
**用途**：記錄運動期間的天氣變化

```sql
snapshot_id (PK, BIGINT)              -- 快照ID
activity_id (FK)                      -- 運動記錄ID
weather_id (FK)                       -- 對應天氣記錄ID

captured_at                           -- 快照捕捉時間

-- 天氣快照（與當時的運動同步）
temperature / feels_like_temp         -- 溫度
humidity                              -- 濕度 (%)
wind_speed / wind_direction           -- 風力
precipitation / precipitation_probability  -- 降水
visibility                            -- 能見度 (m)
uv_index                              -- 紫外線指數
cloud_coverage                        -- 雲層覆蓋度 (%)
weather_description                   -- 天氣描述
created_at                            -- 記錄時間
```

**用途**：
- 記錄運動進行時的實時天氣
- 支持運動-天氣相關性分析
- 用於生成運動報告中的天氣部分

---

### 9. weather_recommendations (天氣建議表)
**用途**：存儲基於天氣的運動安全建議

```sql
recommendation_id (PK, BIGINT)        -- 建議記錄ID
activity_id (FK)                      -- 運動記錄ID
mode_id (FK)                          -- 運動模式ID

-- 建議等級
recommendation_level                  -- ENUM: safe/warning/danger

-- 建議原因和文字
reasons (JSON)                        -- 建議原因陣列
suggestions (TEXT)                    -- 詳細文字建議

-- 各因素狀態
temperature_status                    -- 溫度狀態 (optimal/warning/danger)
humidity_status                       -- 濕度狀態
wind_status                           -- 風力狀態
precipitation_status                  -- 降水狀態
visibility_status                     -- 能見度狀態
uv_status                             -- 紫外線狀態

created_at / updated_at               -- 建立/更新時間
```

**建議等級判定邏輯**（在 Python 後端實現）：
```
🟢 SAFE (安全)
   - 所有因素都在推薦範圍內
   
🟡 WARNING (警告)
   - 一個或多個因素在警告範圍
   - 建議用戶謹慎進行運動
   
🔴 DANGER (危險)
   - 一個或多個因素在危險範圍
   - 不建議進行該運動
```

---

### 10. favorite_locations (用戶最愛位置表)
**用途**：存儲用戶常去的運動地點

```sql
location_id (PK, INT)          -- 位置ID
user_id (FK)                   -- 用戶ID
location_name                  -- 位置名稱（如：陽明山）
latitude / longitude           -- 座標
description                    -- 位置描述
icon_url                       -- 位置圖標URL
visit_count                    -- 訪問次數
created_at / updated_at        -- 建立/更新時間
```

**用途**：
- 快速查詢常去位置的天氣
- 推薦功能
- 分析用戶運動習慣

---

### 11. activity_statistics (活動統計表)
**用途**：預計算用戶的每日/週/月運動統計

```sql
stat_id (PK, BIGINT)                   -- 統計記錄ID
user_id (FK)                           -- 用戶ID
mode_id (FK)                           -- 運動模式ID
stat_date                              -- 統計日期

-- 數量統計
activities_count                       -- 該模式運動次數
total_distance_meters                  -- 總距離 (米)
total_duration_seconds                 -- 總時長 (秒)
avg_speed_ms                           -- 平均速度 (m/s)
total_elevation_gain_meters            -- 總上升海拔 (米)

-- 天氣統計
avg_temperature                        -- 平均溫度 (°C)
avg_humidity                           -- 平均濕度 (%)
avg_wind_speed                         -- 平均風速 (m/s)

created_at / updated_at                -- 建立/更新時間
```

**UNIQUE 索引**：`(user_id, mode_id, stat_date)` - 確保每天每個用戶每種模式只有一筆統計

---

### 12. weather_alerts (天氣警告表)
**用途**：存儲氣象部門發布的警告信息

```sql
alert_id (PK, BIGINT)             -- 警告ID
user_id (FK)                       -- 用戶ID

-- 警告位置
location_name                      -- 位置名稱
latitude / longitude               -- 座標

-- 警告信息
alert_type                         -- 警告類型 (暴雨/寒流/高溫/強風等)
alert_level                        -- 警告等級
alert_description                  -- 警告詳細描述

-- 時間
alert_issued_at                    -- 警告發布時間
alert_expires_at                   -- 警告過期時間

-- 用戶狀態
is_active                          -- 警告是否仍然有效
is_read                            -- 用戶是否已讀
read_at                            -- 用戶閱讀時間
created_at                         -- 記錄時間
```

---

## 關鍵設計決策

### 1. 為什麼使用 BIGINT 作為主鍵？

```sql
activity_id BIGINT AUTO_INCREMENT
gps_points BIGINT AUTO_INCREMENT
```

**原因**：
- GPS 點位數據量大：一年可能產生 1 億+ 筆記錄
- BIGINT 最大值：9,223,372,036,854,775,807 (足夠)
- INT 最大值：4,294,967,295 (不夠)

**計算**：
```
假設：1,000 個活躍用戶
每天平均運動次數：2 次/用戶
每次運動時長：1 小時 (3,600 秒)
每秒記錄 1 個點位：3,600 點位/次

每天總點位數：
1,000 用戶 × 2 次 × 3,600 點位 = 7,200,000 點位/天

年度總點位數：
7,200,000 × 365 天 ≈ 2,628,000,000 點位/年 (~26 億)

BIGINT 可支持 ~3,500 年的數據量 ✓
```

### 2. 為什麼天氣建議存儲在表中？

原本計劃將推薦/警告/危險條件存儲在 `sport_modes` 表中，但後改為存儲建議結果在 `weather_recommendations` 表，原因：

```
舊方案（字段存儲）:
❌ 推薦條件固定在表中，難以調整
❌ 建議邏輯複雜度高，難以維護
❌ 無法記錄建議歷史

新方案（結果存儲）:
✅ 天氣建議邏輯在 Python 後端實現，靈活可調
✅ 記錄每次運動的建議結果，支持分析
✅ 可以隨時優化建議算法
✅ 支持 A/B 測試不同的建議策略
```

### 3. GPS 精度設置

```sql
latitude DECIMAL(10, 8)    -- 最高精度到小數點後 8 位
longitude DECIMAL(11, 8)   -- ≈ 1.1 毫米精度 (過度精確)
```

**解釋**：
- 手機 GPS 實際精度：10-20 米
- DECIMAL(10,8) 可精確到 0.001 毫米（遠超手機能力）
- 採用這個精度是為了未來擴展性（如無人機、專業GPS）

**可選優化**：實際運行中可改為 DECIMAL(10,6) 精確到 0.11 米

### 4. 為什麼需要 activity_weather_snapshots？

不是直接查詢 current_weather，而是快照原因：

```
情境：用戶在 14:00 開始運動，15:00 運動時下雨

情況1（沒有快照）:
- 查詢 current_weather，只能看到運動結束時的天氣
- 無法了解運動期間的天氣變化

情況2（有快照）:
- 每 10 分鐘記錄一次天氣快照
- 完整記錄運動過程中的天氣變化
- 支持"天氣變化分析"功能
- 即使原始天氣記錄被刪除，快照仍保存
```

---

## 查詢性能優化

### 索引策略

#### 複合索引示例

```sql
-- 查詢用戶最近 7 天的運動
SELECT * FROM activities 
WHERE user_id = 1 
AND start_time >= DATE_SUB(NOW(), INTERVAL 7 DAY)
ORDER BY start_time DESC;

-- 對應索引
CREATE INDEX idx_user_activity_time ON activities(user_id, start_time DESC);
```

#### GPS 點位查詢優化

```sql
-- 查詢某次運動的所有軌跡點
SELECT * FROM gps_points 
WHERE activity_id = 12345 
ORDER BY sequence_order ASC;

-- 對應索引
CREATE INDEX idx_sequence ON gps_points(activity_id, sequence_order);
```

### 查詢成本估計

| 查詢類型 | 無索引 | 有索引 | 改善倍數 |
|--------|-------|-------|--------|
| 查詢用戶最近活動 | ~100ms | ~5ms | 20x |
| 查詢 GPS 軌跡 | ~500ms | ~10ms | 50x |
| 按時間查詢天氣 | ~200ms | ~3ms | 67x |

---

## 視圖和存儲過程

### 視圖1：用戶最近活動 (user_recent_activities)

```sql
SELECT 
    a.activity_id,
    u.username,
    a.title,
    sm.mode_name,
    a.start_time,
    a.total_distance_meters,
    a.duration_seconds
FROM activities a
JOIN users u ON a.user_id = u.user_id
JOIN sport_modes sm ON a.mode_id = sm.mode_id
WHERE a.status = 'completed'
ORDER BY a.start_time DESC;
```

**用途**：快速獲取用戶的最近運動列表

### 視圖2：活動天氣統計 (activity_weather_summary)

```sql
SELECT 
    a.activity_id,
    a.title,
    sm.mode_name,
    AVG(aws.temperature) as avg_temp,
    AVG(aws.humidity) as avg_humidity,
    AVG(aws.wind_speed) as avg_wind_speed,
    wr.recommendation_level
FROM activities a
JOIN sport_modes sm ON a.mode_id = sm.mode_id
LEFT JOIN activity_weather_snapshots aws ON a.activity_id = aws.activity_id
LEFT JOIN weather_recommendations wr ON a.activity_id = wr.activity_id
GROUP BY a.activity_id;
```

**用途**：生成運動報告中的天氣統計部分

### 視圖3：用戶運動概覽 (user_activity_summary)

```sql
SELECT 
    u.user_id,
    u.username,
    COUNT(DISTINCT a.activity_id) as total_activities,
    SUM(a.total_distance_meters) as total_distance_meters,
    AVG(a.avg_speed_ms) as avg_speed
FROM users u
LEFT JOIN activities a ON u.user_id = a.user_id
GROUP BY u.user_id;
```

**用途**：用戶個人資料頁的統計摘要

### 存儲過程1：計算運動距離

```sql
CALL calculate_activity_distance(activity_id, @distance);
SELECT @distance as total_distance_meters;
```

**用途**：使用 Haversine 公式計算精確的總距離

### 存儲過程2：更新用戶統計

```sql
CALL update_user_statistics(user_id, mode_id, date);
```

**用途**：計算並更新每日運動統計

---

## 資料流程

### 運動記錄流程

```
1. 用戶開始運動
   ↓
2. 每秒發送 GPS 位置
   → 寫入 gps_points (高頻率)
   ↓
3. 每 10 分鐘擷取一次天氣
   → 寫入 activity_weather_snapshots
   ↓
4. 運動結束
   ↓
5. 計算統計信息 (存儲過程)
   → 更新 activities 表
   → 更新 activity_statistics 表
   ↓
6. 生成天氣建議
   → 寫入 weather_recommendations
   ↓
7. 完成！用戶可查看報告
```

### 天氣資料更新流程

```
1. 後端定時任務 (每 30 分鐘)
   ↓
2. 呼叫中央氣象局 API
   ↓
3. 獲取各位置的即時天氣
   ↓
4. 寫入 current_weather 表
   ↓
5. 關聯到活躍運動
   → 寫入 activity_weather_snapshots (如運動進行中)
   ↓
6. 檢查警告
   → 寫入 weather_alerts (如有發布)
```

---

## 安裝和使用

### 樹梅派部署（MariaDB）

以下做法假設樹梅派是資料庫主機，後端可以在同一台樹梅派或區域網路中的另一台電腦執行。建議使用 MariaDB，與本專案的 MySQL Schema 相容。

#### 1. 在樹梅派安裝並啟動 MariaDB

```bash
sudo apt update
sudo apt install -y mariadb-server
sudo systemctl enable --now mariadb
sudo mariadb-secure-installation
```

查詢樹梅派區域網路 IP，後面會用到：

```bash
hostname -I
```

#### 2. 建立資料庫與網路連線帳號

先在樹梅派執行 Schema：

```bash
mysql -u root -p < database/schema.sql
```

接著登入 MariaDB，將 `<後端主機IP>` 換成執行 FastAPI 的電腦 IP。若後端就在樹梅派，使用 `localhost`：

```sql
CREATE USER 'sports_app'@'<後端主機IP>' IDENTIFIED BY '<強密碼>';
GRANT ALL PRIVILEGES ON sports_weather_tracker.* TO 'sports_app'@'<後端主機IP>';
FLUSH PRIVILEGES;
```

只在同一台樹梅派執行後端時，不需要開放遠端資料庫帳號；可改用：

```sql
CREATE USER 'sports_app'@'localhost' IDENTIFIED BY '<強密碼>';
GRANT ALL PRIVILEGES ON sports_weather_tracker.* TO 'sports_app'@'localhost';
FLUSH PRIVILEGES;
```

#### 3. 允許區域網路連線（僅後端不在樹梅派時）

編輯 MariaDB 設定，將綁定位址改為樹梅派的區域網路介面：

```bash
sudo nano /etc/mysql/mariadb.conf.d/50-server.cnf
```

設定：

```ini
bind-address = 0.0.0.0
```

重啟服務；若啟用了 UFW，只開放後端主機的 3306 連線：

```bash
sudo systemctl restart mariadb
sudo ufw allow from <後端主機IP> to any port 3306 proto tcp
```

#### 4. 設定 FastAPI 後端

在後端主機的 `backend/.env` 設定樹梅派 IP、資料庫帳號和密碼：

```dotenv
DATABASE_URL=mysql+aiomysql://sports_app:<強密碼>@<樹梅派IP>:3306/sports_weather_tracker?charset=utf8mb4
```

密碼包含 `@`、`:`、`/` 或 `#` 時，必須先做 URL encoding；最簡單的方式是使用只含英數字與 `_` 的強密碼。啟動後端：

```bash
cd backend
python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

#### 5. 測試連線

在後端主機測試 TCP 連線：

```bash
nc -vz <樹梅派IP> 3306
```

再啟動 FastAPI。應用程式啟動時會建立 ORM 缺少的表，正式環境仍建議先執行完整的 `schema.sql`，因為它包含索引、外鍵與初始資料。

### 1. 創建資料庫

```bash
# 使用 MySQL 命令行
mysql -u root -p

# 執行 SQL 文件
mysql> source database/schema.sql;

# 確認資料庫建立
mysql> SHOW DATABASES;
mysql> USE sports_weather_tracker;
mysql> SHOW TABLES;
```

### 2. 驗證表結構

```sql
-- 檢查所有表
SHOW TABLES;

-- 檢查表結構
DESCRIBE users;
DESCRIBE activities;
DESCRIBE gps_points;

-- 檢查索引
SHOW INDEX FROM activities;

-- 檢查視圖
SHOW FULL TABLES WHERE TABLE_TYPE = 'VIEW';
```

### 3. 初始化運動模式

```sql
-- 驗證運動模式已插入
SELECT * FROM sport_modes;

-- 應該看到 3 筆記錄:
-- 1. 爬山
-- 2. 健走
-- 3. 單車
```

### 4. 備份資料庫

```bash
# 完整備份
mysqldump -u root -p sports_weather_tracker > backup.sql

# 僅備份結構
mysqldump -u root -p --no-data sports_weather_tracker > schema_only.sql
```

### 5. 還原資料庫

```bash
# 從備份文件還原
mysql -u root -p sports_weather_tracker < backup.sql
```

### 6. 監控資料庫狀態

```sql
-- 查看表的大小
SELECT 
    table_name,
    ROUND(((data_length + index_length) / 1024 / 1024), 2) as size_mb
FROM information_schema.TABLES
WHERE table_schema = 'sports_weather_tracker'
ORDER BY size_mb DESC;

-- 查看表的行數
SELECT 
    table_name,
    table_rows
FROM information_schema.TABLES
WHERE table_schema = 'sports_weather_tracker';
```

---

## 常見查詢示例

### 查詢用戶最近的運動

```sql
SELECT * FROM user_recent_activities
WHERE user_id = 1
LIMIT 10;
```

### 查詢特定運動的 GPS 軌跡

```sql
SELECT 
    latitude, longitude, altitude, 
    speed_ms, timestamp
FROM gps_points
WHERE activity_id = 12345
ORDER BY sequence_order ASC;
```

### 查詢運動期間的天氣變化

```sql
SELECT 
    captured_at,
    temperature,
    humidity,
    wind_speed,
    precipitation_probability
FROM activity_weather_snapshots
WHERE activity_id = 12345
ORDER BY captured_at ASC;
```

### 查詢用戶的運動統計

```sql
SELECT * FROM user_activity_summary
WHERE user_id = 1;
```

### 查詢特定位置的即時天氣

```sql
SELECT *
FROM current_weather
WHERE location_name LIKE '%台北%'
ORDER BY fetched_at DESC
LIMIT 1;
```

### 查詢天氣建議

```sql
SELECT 
    a.title,
    sm.mode_name,
    wr.recommendation_level,
    wr.suggestions,
    wr.temperature_status,
    wr.wind_status,
    wr.precipitation_status
FROM weather_recommendations wr
JOIN activities a ON wr.activity_id = a.activity_id
JOIN sport_modes sm ON wr.mode_id = sm.mode_id
WHERE a.user_id = 1
ORDER BY wr.created_at DESC;
```

---

## 未來擴展

### 可考慮的優化

1. **分表策略**
   - `gps_points` 按日期分表（每月一張表）
   - `weather_history` 按年分表

2. **緩存層**
   - Redis 緩存熱門位置的天氣
   - 快取用戶統計資訊

3. **時序數據庫**
   - 天氣時序數據遷移到 InfluxDB
   - 高頻 GPS 數據遷移到 TimescaleDB

4. **搜尋引擎**
   - Elasticsearch 支援位置名稱搜尋

### 訪問控制和安全

```sql
-- 創建只讀用戶（應用程序讀取）
CREATE USER 'app_reader'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT ON sports_weather_tracker.* TO 'app_reader'@'localhost';

-- 創建讀寫用戶（應用程序寫入）
CREATE USER 'app_writer'@'localhost' IDENTIFIED BY 'password';
GRANT SELECT, INSERT, UPDATE ON sports_weather_tracker.* TO 'app_writer'@'localhost';
```

---

## 聯繫和支持

如有任何問題，請參考：
- [中央氣象局 API 文檔](https://opendata.cwb.gov.tw/)
- [MySQL 官方文檔](https://dev.mysql.com/doc/)
- 項目 GitHub Issues

---

**最後更新**：2025-09-07  
**資料庫版本**：1.0  
**MySQL 版本要求**：8.0+
