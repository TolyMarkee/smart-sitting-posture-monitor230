"""
配置文件
所有可调整的参数集中在此文件中
"""

# 模型配置
MODEL_CONFIG = {
    # 模型文件路径
    'kmodel_path': '/sdcard/examples/kmodel/yolov8n-pose.kmodel',
    
    # 模型输入尺寸
    'input_size': [320, 320],
    
    # 检测置信度阈值
    'confidence_threshold': 0.2,
    
    # NMS阈值
    'nms_threshold': 0.5
}

# 显示配置
DISPLAY_CONFIG = {
    # 显示模式：'lcd' 或 'hdmi'
    'mode': 'lcd',
    
    # 摄像头输入分辨率
    'rgb888p_size': [1920, 1080],
    
    # LCD显示分辨率
    'lcd_size': [800, 480],
    
    # HDMI显示分辨率
    'hdmi_size': [1920, 1080]
}

# 关键点配置
KEYPOINT_CONFIG = {
    # 关键点置信度阈值（用于判断关键点是否可见）
    'confidence_threshold': 0.5,
    
    # 每种检测必需的关键点索引
    'required_keypoints': {
        'forward_head': [3, 4, 5, 6],      # 耳朵和肩膀
        'high_low_shoulder': [5, 6],        # 左右肩
        'hunched_back': [0, 5, 6],          # 鼻子和肩膀
        'body_tilt': [0, 5, 6],             # 鼻子和肩膀
        'round_shoulder': [5, 6, 7, 8]      # 肩膀和肘部
    }
}

# 体态检测阈值
POSTURE_THRESHOLDS = {
    # 头部前倾（角度，度）
    # P0优先级，准确率目标 ≥ 80%
    'forward_head': {
        'normal': 40,      # < 40度为正常
        'mild': 50,        # 40-50度为轻度
        'moderate': 60     # 50-60度为中度，≥60度为重度
    },
    
    # 高低肩（比例）
    # P0优先级，准确率目标 ≥ 80%
    'high_low_shoulder': {
        'normal': 0.05,    # < 5%为正常
        'mild': 0.08,      # 5-8%为轻度
        'moderate': 0.12   # 8-12%为中度，≥12%为重度
    },
    
    # 驼背（前倾比例）
    # P1优先级，准确率目标 ≥ 70%
    # 注意：此为修订算法，阈值需要实测调整
    'hunched_back': {
        'normal': 0.3,     # < 0.3为正常
        'mild': 0.5,       # 0.3-0.5为轻度
        'moderate': 0.7    # 0.5-0.7为中度，≥0.7为重度
    },
    
    # 身体倾斜（角度，度）
    # P1优先级，准确率目标 ≥ 70%
    'body_tilt': {
        'normal': 5,       # < 5度为正常
        'mild': 10,        # 5-10度为轻度
        'moderate': 15     # 10-15度为中度，≥15度为重度
    },
    
    # 圆肩（比例）
    # P2优先级，依赖肘部可见性
    'round_shoulder': {
        'normal': 0.2,     # < 0.2为正常
        'mild': 0.3,       # 0.2-0.3为轻度
        'moderate': 0.5    # 0.3-0.5为中度，≥0.5为重度
    }
}

# 颜色配置
COLOR_CONFIG = {
    'normal': (0, 255, 0, 255),      # 绿色
    'mild': (255, 255, 0, 255),      # 黄色
    'moderate': (255, 165, 0, 255),  # 橙色
    'severe': (255, 0, 0, 255)       # 红色
}

# 调试配置
DEBUG_CONFIG = {
    # 是否启用调试模式
    'enabled': False,
    
    # 是否显示FPS
    'show_fps': True,
    
    # 是否显示关键点索引
    'show_keypoint_indices': False,
    
    # 是否打印检测结果
    'print_results': False
}

# 使用建议
USAGE_TIPS = """
坐姿体态检测DEMO使用建议：

1. 摄像头位置：
   - 建议角度：侧面45度
   - 建议距离：1-2米
   - 确保上半身在画面中

2. 环境要求：
   - 光线充足
   - 背景简洁
   - 避免逆光

3. 检测项目：
   - P0（必须）：头部前倾、高低肩
   - P1（应该）：驼背、身体倾斜
   - P2（可选）：圆肩（需要肘部可见）

4. 阈值调整：
   - 如果检测过于敏感，可以适当提高阈值
   - 如果检测不够敏感，可以适当降低阈值
   - 修改 POSTURE_THRESHOLDS 中的值

5. 注意事项：
   - 检测结果仅供参考
   - 不能替代专业医学诊断
   - 长期体态问题请咨询医生
"""
