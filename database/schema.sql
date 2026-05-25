-- ============================================
-- 智能坐姿监测系统 - 数据库建表脚本
-- 数据库名: smart_posture
-- ============================================

CREATE DATABASE IF NOT EXISTS smart_posture
  DEFAULT CHARACTER SET utf8mb4
  DEFAULT COLLATE utf8mb4_unicode_ci;

USE smart_posture;

-- ============================================
-- 用户表
-- ============================================
CREATE TABLE IF NOT EXISTS users (
    id            INT           AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)   NOT NULL UNIQUE,
    email         VARCHAR(100)  NOT NULL UNIQUE,
    password_hash VARCHAR(255)  NOT NULL,
    nickname      VARCHAR(50)   DEFAULT NULL,
    phone         VARCHAR(20)   DEFAULT NULL,
    avatar_url    VARCHAR(255)  DEFAULT NULL,
    role          VARCHAR(20)   NOT NULL DEFAULT 'user',
    is_active     BOOLEAN       NOT NULL DEFAULT TRUE,
    created_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_users_email (email),
    INDEX idx_users_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 坐姿记录表（原始数据上传）
-- 对应 ORM: backend/app/db/models.py → PostureRecord
-- ============================================
CREATE TABLE IF NOT EXISTS posture_records (
    id              INT           AUTO_INCREMENT PRIMARY KEY,
    user_id         INT           NOT NULL,
    -- 5项姿态指标的原始测量值
    head_angle      FLOAT         DEFAULT NULL COMMENT '头部前倾角度（度）',
    shoulder_diff   FLOAT         DEFAULT NULL COMMENT '高低肩比例',
    hunchback_score FLOAT         DEFAULT NULL COMMENT '驼背前倾比例',
    body_tilt       FLOAT         DEFAULT NULL COMMENT '身体倾斜角度（度）',
    round_shoulder  FLOAT         DEFAULT NULL COMMENT '圆肩比例',
    -- 综合标签与置信度
    posture_label   VARCHAR(50)   DEFAULT NULL COMMENT '综合坐姿标签',
    confidence      FLOAT         DEFAULT NULL COMMENT '检测置信度',
    created_at      DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_posture_user (user_id),
    INDEX idx_posture_time (created_at),
    INDEX idx_posture_user_time (user_id, created_at),
    CONSTRAINT fk_posture_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 每日统计汇总表（由定时任务聚合生成）
-- ============================================
CREATE TABLE IF NOT EXISTS daily_stats (
    id                      INT           AUTO_INCREMENT PRIMARY KEY,
    user_id                 INT           NOT NULL,
    stat_date               DATE          NOT NULL,
    -- 各项指标的日均值
    avg_head_angle          FLOAT         DEFAULT NULL,
    avg_shoulder_diff       FLOAT         DEFAULT NULL,
    avg_hunchback_score     FLOAT         DEFAULT NULL,
    avg_body_tilt           FLOAT         DEFAULT NULL,
    avg_round_shoulder      FLOAT         DEFAULT NULL,
    -- 统计次数
    record_count            INT           NOT NULL DEFAULT 0,
    -- 不良坐姿时长占比
    bad_posture_ratio       FLOAT         DEFAULT NULL COMMENT '不良坐姿占比（0~1）',
    -- 最严重标签
    worst_label             VARCHAR(50)   DEFAULT NULL,
    created_at              DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_user_date (user_id, stat_date),
    INDEX idx_daily_user (user_id),
    CONSTRAINT fk_daily_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- ============================================
-- 聊天记录表
-- ============================================
CREATE TABLE IF NOT EXISTS chat_history (
    id         INT           AUTO_INCREMENT PRIMARY KEY,
    user_id    INT           NOT NULL,
    role       VARCHAR(20)   NOT NULL COMMENT 'user 或 assistant',
    content    TEXT          NOT NULL,
    created_at DATETIME      NOT NULL DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_chat_user (user_id),
    INDEX idx_chat_time (user_id, created_at),
    CONSTRAINT fk_chat_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
