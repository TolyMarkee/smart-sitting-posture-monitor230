-- 初始化测试数据
-- 仅在数据库为空时执行

USE smart_posture;

-- 测试用户（密码 123456 的 bcrypt 哈希）
INSERT IGNORE INTO users (username, email, password_hash) VALUES
('test', 'test@example.com', '$2b$12$LJ3m4ys3LC0fSGw6kPQXKeVLSg8DJ8xcZMNx3XwqvBxw2wfvJn5.q'),
('demo', 'demo@example.com', '$2b$12$LJ3m4ys3LC0fSGw6kPQXKeVLSg8DJ8xcZMNx3XwqvBxw2wfvJn5.q');
