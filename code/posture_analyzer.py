"""
坐姿体态分析器模块
基于YOLOv8-Pose的17个关键点进行体态分析
只使用上半身关键点，适用于坐姿场景
"""

import math

class PostureAnalyzer:
    """坐姿体态分析器"""
    
    def __init__(self):
        """初始化分析器，设置阈值"""
        
        # 体态检测阈值配置
        self.thresholds = {
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
            # 驼背（前倾比例）
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
        
        # 关键点索引定义（COCO格式）
        self.keypoint_indices = {
            'nose': 0,
            'right_eye': 1,
            'left_eye': 2,
            'right_ear': 3,
            'left_ear': 4,
            'right_shoulder': 5,
            'left_shoulder': 6,
            'right_elbow': 7,
            'left_elbow': 8,
            'right_wrist': 9,
            'left_wrist': 10,
            'right_hip': 11,
            'left_hip': 12,
            'right_knee': 13,
            'left_knee': 14,
            'right_ankle': 15,
            'left_ankle': 16
        }
    
    def calculate_angle_with_vertical(self, point1, point2):
        """
        计算两点连线与垂直轴的夹角
        
        Args:
            point1: 基准点（下方点）(x, y)
            point2: 目标点（上方点）(x, y)
            
        Returns:
            float: 角度（度）或 None
        """
        try:
            x1, y1 = point1[0], point1[1]
            x2, y2 = point2[0], point2[1]
            
            delta_x = x2 - x1
            delta_y = y1 - y2  # 注意：图像坐标系Y轴向下为正，需要反转
            
            if abs(delta_y) < 1e-6:
                return 90.0
            
            # 使用atan2计算角度
            angle_rad = math.atan2(abs(delta_x), abs(delta_y))
            angle_deg = math.degrees(angle_rad)
            
            return angle_deg
        except Exception as e:
            print(f"角度计算错误: {e}")
            return None
    
    def classify_severity(self, value, thresholds):
        """
        根据阈值分类严重程度
        
        Args:
            value: 测量值
            thresholds: 阈值字典 {'normal': x, 'mild': y, 'moderate': z}
            
        Returns:
            str: 'normal', 'mild', 'moderate', 'severe'
        """
        if value < thresholds['normal']:
            return 'normal'
        elif value < thresholds['mild']:
            return 'mild'
        elif value < thresholds['moderate']:
            return 'moderate'
        else:
            return 'severe'
    
    def detect_forward_head(self, keypoints):
        """
        检测头部前倾（P0优先级）
        
        Args:
            keypoints: 17个关键点列表
            
        Returns:
            dict: 检测结果或 None
        """
        try:
            # 获取耳朵和肩膀关键点
            left_ear = keypoints[self.keypoint_indices['left_ear']]
            right_ear = keypoints[self.keypoint_indices['right_ear']]
            left_shoulder = keypoints[self.keypoint_indices['left_shoulder']]
            right_shoulder = keypoints[self.keypoint_indices['right_shoulder']]
            
            # 计算中点
            ear_mid_x = (left_ear[0] + right_ear[0]) / 2
            ear_mid_y = (left_ear[1] + right_ear[1]) / 2
            
            shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_mid_y = (left_shoulder[1] + right_shoulder[1]) / 2
            
            # 计算颈部倾斜角度
            neck_angle = self.calculate_angle_with_vertical(
                (shoulder_mid_x, shoulder_mid_y),
                (ear_mid_x, ear_mid_y)
            )
            
            if neck_angle is None:
                return None
            
            # 判断严重程度
            severity = self.classify_severity(
                neck_angle,
                self.thresholds['forward_head']
            )
            
            if severity == 'normal':
                return None
            
            return {
                'type': 'forward_head',
                'name': '头部前倾',
                'severity': severity,
                'value': neck_angle,
                'description': f'颈部倾斜{int(neck_angle)}度'
            }
            
        except Exception as e:
            print(f"头部前倾检测错误: {e}")
            return None
    
    def detect_high_low_shoulder(self, keypoints):
        """
        检测高低肩（P0优先级）
        
        Args:
            keypoints: 17个关键点列表
            
        Returns:
            dict: 检测结果或 None
        """
        try:
            left_shoulder = keypoints[self.keypoint_indices['left_shoulder']]
            right_shoulder = keypoints[self.keypoint_indices['right_shoulder']]
            
            # 计算高度差和肩宽
            height_diff = abs(left_shoulder[1] - right_shoulder[1])
            shoulder_width = abs(left_shoulder[0] - right_shoulder[0])
            
            if shoulder_width < 1:
                return None
            
            # 计算比例
            ratio = height_diff / shoulder_width
            
            # 判断严重程度
            severity = self.classify_severity(
                ratio,
                self.thresholds['high_low_shoulder']
            )
            
            if severity == 'normal':
                return None
            
            # 判断哪侧肩膀更高
            higher_side = 'left' if left_shoulder[1] < right_shoulder[1] else 'right'
            higher_side_cn = '左' if higher_side == 'left' else '右'
            
            return {
                'type': 'high_low_shoulder',
                'name': '高低肩',
                'severity': severity,
                'value': ratio,
                'description': f'{higher_side_cn}肩较高'
            }
            
        except Exception as e:
            print(f"高低肩检测错误: {e}")
            return None
    
    def detect_hunched_back(self, keypoints):
        """
        检测驼背（P1优先级，修订算法）
        使用肩膀相对鼻子的位置关系
        
        Args:
            keypoints: 17个关键点列表
            
        Returns:
            dict: 检测结果或 None
        """
        try:
            nose = keypoints[self.keypoint_indices['nose']]
            left_shoulder = keypoints[self.keypoint_indices['left_shoulder']]
            right_shoulder = keypoints[self.keypoint_indices['right_shoulder']]
            
            # 计算肩膀中点
            shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_mid_y = (left_shoulder[1] + right_shoulder[1]) / 2
            
            # 计算水平偏移和垂直距离
            horizontal_offset = abs(nose[0] - shoulder_mid_x)
            vertical_distance = abs(shoulder_mid_y - nose[1])
            
            if vertical_distance < 1:
                return None
            
            # 计算前倾比例
            forward_ratio = horizontal_offset / vertical_distance
            
            # 判断严重程度
            severity = self.classify_severity(
                forward_ratio,
                self.thresholds['hunched_back']
            )
            
            if severity == 'normal':
                return None
            
            return {
                'type': 'hunched_back',
                'name': '驼背含胸',
                'severity': severity,
                'value': forward_ratio,
                'description': f'上半身前倾'
            }
            
        except Exception as e:
            print(f"驼背检测错误: {e}")
            return None
    
    def detect_body_tilt(self, keypoints):
        """
        检测身体倾斜（P1优先级，修订算法）
        使用肩膀-鼻子连线与垂直轴的偏移
        
        Args:
            keypoints: 17个关键点列表
            
        Returns:
            dict: 检测结果或 None
        """
        try:
            nose = keypoints[self.keypoint_indices['nose']]
            left_shoulder = keypoints[self.keypoint_indices['left_shoulder']]
            right_shoulder = keypoints[self.keypoint_indices['right_shoulder']]
            
            # 计算肩膀中点
            shoulder_mid_x = (left_shoulder[0] + right_shoulder[0]) / 2
            shoulder_mid_y = (left_shoulder[1] + right_shoulder[1]) / 2
            
            # 计算倾斜角度
            delta_x = nose[0] - shoulder_mid_x
            delta_y = abs(shoulder_mid_y - nose[1])
            
            if delta_y < 1:
                return None
            
            tilt_angle = abs(math.degrees(math.atan2(delta_x, delta_y)))
            
            # 判断严重程度
            severity = self.classify_severity(
                tilt_angle,
                self.thresholds['body_tilt']
            )
            
            if severity == 'normal':
                return None
            
            # 判断倾斜方向
            tilt_direction = 'left' if delta_x < 0 else 'right'
            tilt_direction_cn = '左' if tilt_direction == 'left' else '右'
            
            return {
                'type': 'body_tilt',
                'name': '身体倾斜',
                'severity': severity,
                'value': tilt_angle,
                'description': f'向{tilt_direction_cn}倾斜{int(tilt_angle)}度'
            }
            
        except Exception as e:
            print(f"身体倾斜检测错误: {e}")
            return None
    
    def detect_round_shoulders(self, keypoints):
        """
        检测圆肩（P2优先级，依赖肘部可见性）
        
        Args:
            keypoints: 17个关键点列表
            
        Returns:
            dict: 检测结果或 None
        """
        try:
            left_shoulder = keypoints[self.keypoint_indices['left_shoulder']]
            right_shoulder = keypoints[self.keypoint_indices['right_shoulder']]
            left_elbow = keypoints[self.keypoint_indices['left_elbow']]
            right_elbow = keypoints[self.keypoint_indices['right_elbow']]
            
            # 检查肘部置信度（必须可见）
            if left_elbow[2] < 0.5 or right_elbow[2] < 0.5:
                return None
            
            # 计算中点
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
            severity = self.classify_severity(
                ratio,
                self.thresholds['round_shoulder']
            )
            
            if severity == 'normal':
                return None
            
            return {
                'type': 'round_shoulder',
                'name': '圆肩',
                'severity': severity,
                'value': ratio,
                'description': '肩部过度前倾'
            }
            
        except Exception as e:
            print(f"圆肩检测错误: {e}")
            return None
    
    def analyze(self, keypoints):
        """
        综合分析坐姿体态
        
        Args:
            keypoints: 17个关键点列表 [(x, y, confidence), ...]
            
        Returns:
            list: 体态问题列表
        """
        issues = []
        
        try:
            # P0优先级：头部前倾
            result = self.detect_forward_head(keypoints)
            if result:
                issues.append(result)
            
            # P0优先级：高低肩
            result = self.detect_high_low_shoulder(keypoints)
            if result:
                issues.append(result)
            
            # P1优先级：驼背
            result = self.detect_hunched_back(keypoints)
            if result:
                issues.append(result)
            
            # P1优先级：身体倾斜
            result = self.detect_body_tilt(keypoints)
            if result:
                issues.append(result)
            
            # P2优先级：圆肩（依赖肘部可见性）
            result = self.detect_round_shoulders(keypoints)
            if result:
                issues.append(result)
            
        except Exception as e:
            print(f"体态分析错误: {e}")
        
        return issues
    
    def get_severity_color(self, severity):
        """
        获取严重程度对应的颜色
        
        Args:
            severity: 严重程度 'normal', 'mild', 'moderate', 'severe'
            
        Returns:
            tuple: RGBA颜色
        """
        color_map = {
            'normal': (0, 255, 0, 255),      # 绿色
            'mild': (255, 255, 0, 255),      # 黄色
            'moderate': (255, 165, 0, 255),  # 橙色
            'severe': (255, 0, 0, 255)       # 红色
        }
        return color_map.get(severity, (255, 255, 255, 255))
    
    def get_severity_name_cn(self, severity):
        """
        获取严重程度的中文名称
        
        Args:
            severity: 严重程度
            
        Returns:
            str: 中文名称
        """
        name_map = {
            'normal': '正常',
            'mild': '轻度',
            'moderate': '中度',
            'severe': '重度'
        }
        return name_map.get(severity, '未知')
