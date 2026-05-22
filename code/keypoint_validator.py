"""
关键点验证模块
用于验证YOLOv8-Pose检测的关键点是否可用
"""

class KeypointValidator:
    """关键点验证器"""
    
    def __init__(self, confidence_threshold=0.5):
        """
        初始化验证器
        
        Args:
            confidence_threshold: 关键点置信度阈值，默认0.5
        """
        self.confidence_threshold = confidence_threshold
        
        # 定义每种检测所需的关键点索引
        self.required_keypoints = {
            'forward_head': [3, 4, 5, 6],      # 耳朵和肩膀
            'high_low_shoulder': [5, 6],        # 左右肩
            'hunched_back': [0, 5, 6],          # 鼻子和肩膀
            'body_tilt': [0, 5, 6],             # 鼻子和肩膀
            'round_shoulder': [5, 6, 7, 8]      # 肩膀和肘部
        }
    
    def is_visible(self, keypoint):
        """
        判断关键点是否可见
        
        Args:
            keypoint: 关键点数据 (x, y, confidence)
            
        Returns:
            bool: 是否可见
        """
        if keypoint is None:
            return False
        if len(keypoint) < 3:
            return False
        return keypoint[2] > self.confidence_threshold
    
    def get_midpoint(self, kp1, kp2):
        """
        计算两个关键点的中点
        
        Args:
            kp1: 关键点1 (x, y, confidence)
            kp2: 关键点2 (x, y, confidence)
            
        Returns:
            tuple: 中点 (x, y, confidence) 或 None
        """
        if not self.is_visible(kp1) or not self.is_visible(kp2):
            return None
        
        mid_x = (kp1[0] + kp2[0]) / 2
        mid_y = (kp1[1] + kp2[1]) / 2
        mid_conf = min(kp1[2], kp2[2])
        
        return (mid_x, mid_y, mid_conf)
    
    def validate_for_detection(self, keypoints, detection_type):
        """
        验证特定检测所需的关键点是否可用
        
        Args:
            keypoints: 17个关键点列表
            detection_type: 检测类型
            
        Returns:
            bool: 是否可用
        """
        if detection_type not in self.required_keypoints:
            return False
        
        indices = self.required_keypoints[detection_type]
        
        for idx in indices:
            if idx >= len(keypoints):
                return False
            if not self.is_visible(keypoints[idx]):
                return False
        
        return True
    
    def get_available_detections(self, keypoints):
        """
        获取当前关键点可以进行的检测列表
        
        Args:
            keypoints: 17个关键点列表
            
        Returns:
            list: 可用的检测类型列表
        """
        available = []
        
        for detection_type in self.required_keypoints.keys():
            if self.validate_for_detection(keypoints, detection_type):
                available.append(detection_type)
        
        return available
