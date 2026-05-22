# 技术方案设计文档 v2.0 - 坐姿体态检测DEMO

## 文档信息
- **项目名称**：坐姿体态检测DEMO
- **版本**：v2.0（深度研究后修订版）
- **创建日期**：2025-11-07
- **基于PRD版本**：v1.0

---

## 修订说明

经过深入技术研究，发现原方案存在**重大技术可行性问题**：

### 关键发现
1. **YOLOv8-Pose检测17个关键点**，包括头部5个、上肢6个、下肢6个
2. **坐姿场景下，下肢关键点（髋部、膝盖、脚踝）通常被桌子遮挡**
3. **传统算法（如MediaPipe）依赖髋部关键点计算躯干角度**，不适用于坐姿
4. **必须重新设计算法**，只使用上半身11个关键点

---

## 1. YOLOv8-Pose关键点定义

### 1.1 完整关键点列表（COCO格式）

| 索引 | 名称 | 部位 | 坐姿可见性 |
|------|------|------|-----------|
| 0 | 鼻子 (Nose) | 头部 | ✅ 可见 |
| 1 | 右眼 (Right Eye) | 头部 | ✅ 可见 |
| 2 | 左眼 (Left Eye) | 头部 | ✅ 可见 |
| 3 | 右耳 (Right Ear) | 头部 | ✅ 可见 |
| 4 | 左耳 (Left Ear) | 头部 | ✅ 可见 |
| 5 | 右肩 (Right Shoulder) | 上肢 | ✅ 可见 |
| 6 | 左肩 (Left Shoulder) | 上肢 | ✅ 可见 |
| 7 | 右肘 (Right Elbow) | 上肢 | ⚠️ 可能遮挡 |
| 8 | 左肘 (Left Elbow) | 上肢 | ⚠️ 可能遮挡 |
| 9 | 右手腕 (Right Wrist) | 上肢 | ⚠️ 可能遮挡 |
| 10 | 左手腕 (Left Wrist) | 上肢 | ⚠️ 可能遮挡 |
| 11 | 右髋 (Right Hip) | 下肢 | ❌ 通常遮挡 |
| 12 | 左髋 (Left Hip) | 下肢 | ❌ 通常遮挡 |
| 13 | 右膝 (Right Knee) | 下肢 | ❌ 通常遮挡 |
| 14 | 左膝 (Left Knee) | 下肢 | ❌ 通常遮挡 |
| 15 | 右脚踝 (Right Ankle) | 下肢 | ❌ 通常遮挡 |
| 16 | 左脚踝 (Left Ankle) | 下肢 | ❌ 通常遮挡 |

### 1.2 可用关键点分析

**稳定可见（9个）**：
- 头部：0-鼻子, 1-右眼, 2-左眼, 3-右耳, 4-左耳
- 肩部：5-右肩, 6-左肩

**可能可见（4个）**：
- 手臂：7-右肘, 8-左肘, 9-右手腕, 10-左手腕
- 注意：手放桌面上时可能被遮挡

**通常不可见（6个）**：
- 下肢：11-右髋, 12-左髋, 13-右膝, 14-左膝, 15-右脚踝, 16-左脚踝

---

## 2. 修订后的检测项目

### 2.1 完全可行（优先级P0）

#### ✅ 1. 头部前倾（Forward Head Posture）

**检测原理**：
- 计算肩膀-耳朵连线与垂直轴的夹角
- 头部前倾时，耳朵会明显前移，角度增大

**所需关键点**：
- 左耳（索引4）或右耳（索引3）
- 左肩（索引6）或右肩（索引5）

**算法**：
```python
def detect_forward_head(ear, shoulder):
    """
    ear: (x, y, confidence)
    shoulder: (x, y, confidence)
    """
    # 计算与垂直轴夹角
    delta_x = ear[0] - shoulder[0]
    delta_y = shoulder[1] - ear[1]  # 注意Y轴向下为正
    
    if delta_y < 1:
        return None
    
    angle = math.degrees(math.atan2(abs(delta_x), delta_y))
    
    # 判断严重程度
    if angle < 40:
        return 'normal'
    elif angle < 50:
        return 'mild'
    elif angle < 60:
        return 'moderate'
    else:
        return 'severe'
```

**阈值设置**：
- 正常：< 40度
- 轻度：40-50度
- 中度：50-60度
- 重度：≥ 60度

**参考依据**：
- MediaPipe姿态检测标准
- 医学文献：颈椎角度 < 50度为正常

#### ✅ 2. 高低肩（Uneven Shoulders）

**检测原理**：
- 计算左右肩膀Y坐标差值与肩宽的比例
- 高低肩时，一侧肩膀明显高于另一侧

**所需关键点**：
- 左肩（索引6）
- 右肩（索引5）

**算法**：
```python
def detect_high_low_shoulder(left_shoulder, right_shoulder):
    """
    left_shoulder: (x, y, confidence)
    right_shoulder: (x, y, confidence)
    """
    # 计算高度差和肩宽
    height_diff = abs(left_shoulder[1] - right_shoulder[1])
    shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
    
    if shoulder_width < 1:
        return None
    
    ratio = height_diff / shoulder_width
    
    # 判断严重程度
    if ratio < 0.05:
        return 'normal'
    elif ratio < 0.08:
        return 'mild'
    elif ratio < 0.12:
        return 'moderate'
    else:
        return 'severe'
```

**阈值设置**：
- 正常：< 5%
- 轻度：5-8%
- 中度：8-12%
- 重度：≥ 12%

### 2.2 需要特殊处理（优先级P1）

#### ⚠️ 3. 驼背/含胸（Hunched Back）

**问题**：传统算法需要髋部关键点，但坐姿下不可见

**修订方案**：使用头部-肩膀的相对位置

**方案A：侧面视角 - 肩膀相对鼻子的前后位置**

```python
def detect_hunched_back_side_view(nose, shoulder_mid):
    """
    侧面视角：驼背时肩膀会相对鼻子更靠后
    nose: (x, y, confidence)
    shoulder_mid: (x, y, confidence) - 左右肩中点
    """
    # 计算肩膀相对鼻子的水平距离
    horizontal_offset = abs(nose[0] - shoulder_mid[0])
    
    # 计算头肩垂直距离
    vertical_distance = abs(shoulder_mid[1] - nose[1])
    
    if vertical_distance < 1:
        return None
    
    # 计算前倾比例
    forward_ratio = horizontal_offset / vertical_distance
    
    # 判断严重程度（阈值需要实测调整）
    if forward_ratio < 0.3:
        return 'normal'
    elif forward_ratio < 0.5:
        return 'mild'
    elif forward_ratio < 0.7:
        return 'moderate'
    else:
        return 'severe'
```

**方案B：正面视角 - 通过头部前倾间接判断**

```python
def detect_hunched_back_front_view(neck_angle):
    """
    正面视角：驼背通常伴随头部前倾
    通过头部前倾角度间接判断
    """
    # 头部前倾严重时，通常伴随驼背
    if neck_angle > 50:
        return 'likely_hunched'
    else:
        return 'normal'
```

**推荐**：
- 侧面视角使用方案A
- 正面视角使用方案B（精度较低，仅作参考）

**阈值设置**（需实测调整）：
- 正常：前倾比例 < 0.3
- 轻度：0.3-0.5
- 中度：0.5-0.7
- 重度：≥ 0.7

#### ⚠️ 4. 身体倾斜（Body Tilt）

**问题**：传统算法需要髋部关键点

**修订方案**：使用肩膀-头部中线的倾斜度

```python
def detect_body_tilt(nose, shoulder_mid):
    """
    计算头部-肩膀连线与垂直轴的偏移角度
    """
    delta_x = nose[0] - shoulder_mid[0]
    delta_y = abs(shoulder_mid[1] - nose[1])
    
    if delta_y < 1:
        return None
    
    tilt_angle = abs(math.degrees(math.atan2(delta_x, delta_y)))
    
    # 判断严重程度
    if tilt_angle < 5:
        return 'normal'
    elif tilt_angle < 10:
        return 'mild'
    elif tilt_angle < 15:
        return 'moderate'
    else:
        return 'severe'
```

**阈值设置**：
- 正常：< 5度
- 轻度：5-10度
- 中度：10-15度
- 重度：≥ 15度

### 2.3 依赖条件（优先级P2）

#### ⚠️ 5. 圆肩（Round Shoulders）

**问题**：需要肘部关键点，但手放桌上时可能被遮挡

**检测原理**：
- 肩膀相对肘部的前后位置
- 圆肩时，肩膀会相对肘部更靠前

**算法**：
```python
def detect_round_shoulders(left_shoulder, right_shoulder, 
                           left_elbow, right_elbow):
    """
    需要检查肘部置信度
    """
    # 检查肘部是否可见
    if left_elbow[2] < 0.5 or right_elbow[2] < 0.5:
        return None  # 肘部不可见，跳过检测
    
    # 计算肩膀和肘部中点
    shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
    elbow_mid_x = (left_elbow[0] + right_elbow[0]) / 2
    
    # 计算肩宽
    shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
    
    if shoulder_width < 1:
        return None
    
    # 计算前移距离
    forward_offset = abs(shoulder_mid_x - elbow_mid_x)
    ratio = forward_offset / shoulder_width
    
    # 判断严重程度
    if ratio < 0.2:
        return 'normal'
    elif ratio < 0.3:
        return 'mild'
    elif ratio < 0.5:
        return 'moderate'
    else:
        return 'severe'
```

**阈值设置**：
- 正常：< 0.2
- 轻度：0.2-0.3
- 中度：0.3-0.5
- 重度：≥ 0.5

**注意**：
- 必须检查肘部置信度 > 0.5
- 如果肘部不可见，跳过该项检测

---

## 3. 拍摄角度建议

### 3.1 侧面视角（推荐）

**优点**：
- 可以准确检测头部前倾
- 可以检测驼背（肩膀-鼻子位置）
- 效果最好

**缺点**：
- 无法检测高低肩
- 无法检测身体左右倾斜

**适合检测**：
- ✅ 头部前倾
- ✅ 驼背
- ❌ 高低肩
- ❌ 身体倾斜
- ⚠️ 圆肩（部分）

### 3.2 正面视角

**优点**：
- 可以检测高低肩
- 可以检测身体倾斜
- 更自然的使用场景

**缺点**：
- 驼背检测精度较低
- 头部前倾检测精度较低

**适合检测**：
- ⚠️ 头部前倾（精度较低）
- ❌ 驼背（精度很低）
- ✅ 高低肩
- ✅ 身体倾斜
- ⚠️ 圆肩（部分）

### 3.3 推荐方案

**方案1：侧面45度角**
- 兼顾侧面和正面优点
- 可以检测大部分问题
- **推荐用于办公/学习场景**

**方案2：双摄像头**
- 一个侧面，一个正面
- 检测最全面
- 成本较高，复杂度增加

**方案3：用户自选角度**
- 根据角度自动选择检测项目
- 灵活性最高
- 需要角度识别算法

---

## 4. 修订后的整体架构

```
┌─────────────────────────────────────────────────────────┐
│                     应用层 (Application)                  │
│  ┌──────────────────────────────────────────────────┐   │
│  │         PersonKeyPointApp (主程序)                │   │
│  │  - 视频流获取                                      │   │
│  │  - 关键点检测调度                                  │   │
│  │  - 体态分析调度                                    │   │
│  │  - 结果显示                                        │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   业务逻辑层 (Business Logic)             │
│  ┌──────────────────────┐  ┌──────────────────────┐    │
│  │  PostureAnalyzer     │  │  KeypointValidator   │    │
│  │  (体态分析器)         │  │  (关键点验证器)       │    │
│  │  - 头部前倾检测       │  │  - 置信度过滤         │    │
│  │  - 高低肩检测         │  │  - 可见性判断         │    │
│  │  - 驼背检测(修订)     │  │  - 中点计算           │    │
│  │  - 身体倾斜检测(修订) │  └──────────────────────┘    │
│  │  - 圆肩检测(条件)     │                              │
│  └──────────────────────┘                              │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    AI推理层 (AI Inference)                │
│  ┌──────────────────────────────────────────────────┐   │
│  │         YOLOv8-Pose Model                         │   │
│  │  - 17个关键点检测                                  │   │
│  │  - 上半身11个通常可见                              │   │
│  │  - 下半身6个通常不可见                             │   │
│  └──────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
```

---

## 5. 关键点验证模块

### 5.1 KeypointValidator类设计

```python
class KeypointValidator:
    """关键点验证器"""
    
    def __init__(self, confidence_threshold=0.5):
        self.confidence_threshold = confidence_threshold
    
    def is_visible(self, keypoint):
        """判断关键点是否可见"""
        if keypoint is None:
            return False
        if len(keypoint) < 3:
            return False
        return keypoint[2] > self.confidence_threshold
    
    def get_midpoint(self, kp1, kp2):
        """计算两个关键点的中点"""
        if not self.is_visible(kp1) or not self.is_visible(kp2):
            return None
        mid_x = (kp1[0] + kp2[0]) / 2
        mid_y = (kp1[1] + kp2[1]) / 2
        mid_conf = min(kp1[2], kp2[2])
        return (mid_x, mid_y, mid_conf)
    
    def validate_keypoints_for_detection(self, keypoints, detection_type):
        """验证特定检测所需的关键点是否可用"""
        required_indices = {
            'forward_head': [3, 4, 5, 6],  # 耳朵和肩膀
            'high_low_shoulder': [5, 6],    # 左右肩
            'hunched_back': [0, 5, 6],      # 鼻子和肩膀
            'body_tilt': [0, 5, 6],         # 鼻子和肩膀
            'round_shoulder': [5, 6, 7, 8]  # 肩膀和肘部
        }
        
        indices = required_indices.get(detection_type, [])
        for idx in indices:
            if not self.is_visible(keypoints[idx]):
                return False
        return True
```

---

## 6. 配置参数设计

```python
# 模型配置
MODEL_CONFIG = {
    'kmodel_path': '/sdcard/examples/kmodel/yolov8n-pose.kmodel',
    'input_size': [320, 320],
    'confidence_threshold': 0.2,  # 模型检测阈值
    'nms_threshold': 0.5
}

# 显示配置
DISPLAY_CONFIG = {
    'mode': 'lcd',  # 'lcd' or 'hdmi'
    'rgb888p_size': [1920, 1080],
    'lcd_size': [800, 480],
    'hdmi_size': [1920, 1080]
}

# 关键点置信度阈值
KEYPOINT_CONFIG = {
    'confidence_threshold': 0.5,  # 关键点可见性阈值
    'required_keypoints': {
        # 每种检测必需的关键点索引
        'forward_head': [3, 4, 5, 6],
        'high_low_shoulder': [5, 6],
        'hunched_back': [0, 5, 6],
        'body_tilt': [0, 5, 6],
        'round_shoulder': [5, 6, 7, 8]
    }
}

# 体态检测阈值（修订版）
POSTURE_THRESHOLDS = {
    # 头部前倾（角度，度）
    'forward_head': {
        'normal': 40,
        'mild': 50,
        'moderate': 60
    },
    # 高低肩（比例）
    'high_low_shoulder': {
        'normal': 0.05,
        'mild': 0.08,
        'moderate': 0.12
    },
    # 驼背（前倾比例，需实测调整）
    'hunched_back': {
        'normal': 0.3,
        'mild': 0.5,
        'moderate': 0.7
    },
    # 身体倾斜（角度，度）
    'body_tilt': {
        'normal': 5,
        'mild': 10,
        'moderate': 15
    },
    # 圆肩（比例）
    'round_shoulder': {
        'normal': 0.2,
        'mild': 0.3,
        'moderate': 0.5
    }
}

# 颜色配置
COLOR_CONFIG = {
    'normal': (0, 255, 0, 255),      # 绿色
    'mild': (255, 255, 0, 255),      # 黄色
    'moderate': (255, 165, 0, 255),  # 橙色
    'severe': (255, 0, 0, 255)       # 红色
}
```

---

## 7. 测试方案（修订版）

### 7.1 关键点可见性测试

| 测试项 | 测试方法 | 预期结果 |
|-------|---------|---------|
| 头部关键点 | 正常坐姿 | 鼻子、眼睛、耳朵置信度 > 0.5 |
| 肩部关键点 | 正常坐姿 | 左右肩膀置信度 > 0.5 |
| 肘部关键点 | 手放桌上 | 肘部可能不可见 |
| 肘部关键点 | 手臂自然下垂 | 肘部置信度 > 0.5 |
| 髋部关键点 | 坐在桌前 | 髋部置信度 < 0.5（被遮挡） |

### 7.2 算法功能测试

| 测试项 | 测试方法 | 预期结果 |
|-------|---------|---------|
| 头部前倾 | 头部向前伸 | 识别为头部前倾 |
| 正常坐姿 | 保持正确坐姿 | 显示"坐姿良好" |
| 高低肩 | 抬高一侧肩膀 | 识别为高低肩 |
| 驼背 | 弯腰驼背（侧面） | 识别为驼背 |
| 身体倾斜 | 身体向一侧倾斜 | 识别为身体倾斜 |
| 圆肩 | 肩部内旋（肘部可见时） | 识别为圆肩 |
| 肘部遮挡 | 手放桌上 | 跳过圆肩检测，不崩溃 |

### 7.3 性能测试

| 测试项 | 目标值 | 测试方法 |
|-------|-------|---------|
| 帧率 | ≥ 10 FPS | 运行时统计 |
| 延迟 | < 200ms | 改变姿势到显示更新 |
| 准确率 | ≥ 80% | 10种姿势各测试10次 |
| 稳定性 | ≥ 1小时 | 长时间运行 |

### 7.4 边界测试

| 测试项 | 测试方法 | 预期结果 |
|-------|---------|---------|
| 无人 | 画面中无人 | 不崩溃，显示提示 |
| 侧身 | 侧面90度 | 部分检测有效 |
| 背面 | 背对摄像头 | 检测失败，不崩溃 |
| 肘部遮挡 | 手放桌上 | 跳过圆肩检测 |
| 弱光 | 光线不足 | 精度下降但不崩溃 |

---

## 8. 风险评估与应对（修订版）

### 8.1 技术风险

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 肘部检测率低 | 高 | 中 | 圆肩检测设为可选项 |
| 驼背检测精度不足 | 中 | 中 | 实测调整阈值，或降低优先级 |
| 正面视角效果差 | 中 | 中 | 建议用户使用侧面视角 |
| 阈值不适用 | 高 | 中 | 提供可配置参数 |

### 8.2 实施风险

| 风险 | 概率 | 影响 | 应对措施 |
|-----|------|------|---------|
| 实际测试不通过 | 中 | 高 | 在实际硬件上充分测试 |
| 用户使用角度不当 | 高 | 中 | 提供摄像头摆放指南 |
| 检测项目减少 | 低 | 中 | 优先实现高优先级项目 |

---

## 9. 实施计划（修订版）

### 9.1 阶段划分

**阶段1：核心功能实现（P0）**
- 实现头部前倾检测
- 实现高低肩检测
- 实现关键点验证模块
- 预计时间：2小时

**阶段2：扩展功能实现（P1）**
- 实现驼背检测（修订算法）
- 实现身体倾斜检测（修订算法）
- 预计时间：1小时

**阶段3：可选功能实现（P2）**
- 实现圆肩检测（带条件判断）
- 预计时间：30分钟

**阶段4：测试与调优**
- 关键点可见性测试
- 算法功能测试
- 阈值调整
- 预计时间：2小时

### 9.2 验收标准（修订版）

**必须实现（P0）**：
- ✅ 头部前倾检测准确率 ≥ 80%
- ✅ 高低肩检测准确率 ≥ 80%
- ✅ 帧率 ≥ 10 FPS
- ✅ 连续运行 ≥ 1小时不崩溃

**应该实现（P1）**：
- ⚠️ 驼背检测准确率 ≥ 70%（精度要求降低）
- ⚠️ 身体倾斜检测准确率 ≥ 70%

**可以实现（P2）**：
- ⚠️ 圆肩检测（肘部可见时）

---

## 10. 关键结论

### 10.1 技术可行性

1. **YOLOv8-Pose在坐姿场景下只能检测上半身11个关键点**
2. **传统算法依赖髋部，必须重新设计**
3. **头部前倾和高低肩检测完全可行**
4. **驼背和身体倾斜需要修订算法，精度可能降低**
5. **圆肩检测依赖肘部可见性**

### 10.2 方案调整

1. **优先实现头部前倾和高低肩**（P0）
2. **驼背和身体倾斜使用修订算法**（P1）
3. **圆肩检测设为可选**（P2）
4. **建议用户使用侧面45度角拍摄**
5. **所有阈值需要实际测试后调整**

### 10.3 与PRD的差异

| PRD要求 | 技术方案 | 差异说明 |
|---------|---------|---------|
| 5种体态问题 | 5种（算法修订） | 驼背和身体倾斜算法需修订 |
| 准确率 ≥ 80% | P0项 ≥ 80%，P1项 ≥ 70% | 部分检测精度降低 |
| 所有问题必须实现 | P0必须，P1应该，P2可选 | 优先级调整 |

---

**请您审阅修订后的技术方案，确认是否可以接受这些技术限制和调整。确认后我们将进入代码实现阶段。**
