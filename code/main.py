"""
坐姿体态检测DEMO - 主程序
基于庐山派K230开发板和YOLOv8-Pose模型
"""

from libs.PipeLine import PipeLine, ScopedTiming
from libs.AIBase import AIBase
from libs.AI2D import Ai2d
import os
import ujson
from media.media import *
from time import *
import nncase_runtime as nn
import ulab.numpy as np
import time
import utime
import image
import random
import gc
import sys
import aidemo
import math

# 导入自定义模块
from posture_analyzer import PostureAnalyzer
from keypoint_validator import KeypointValidator


class PersonKeyPointApp(AIBase):
    """人体关键点检测和体态分析应用"""
    
    def __init__(self, kmodel_path, model_input_size, confidence_threshold=0.2,
                 nms_threshold=0.5, rgb888p_size=[1280, 720], display_size=[1920, 1080],
                 debug_mode=0):
        """
        初始化应用
        
        Args:
            kmodel_path: 模型文件路径
            model_input_size: 模型输入尺寸
            confidence_threshold: 检测置信度阈值
            nms_threshold: NMS阈值
            rgb888p_size: 摄像头输入尺寸
            display_size: 显示输出尺寸
            debug_mode: 调试模式
        """
        super().__init__(kmodel_path, model_input_size, rgb888p_size, debug_mode)
        
        self.kmodel_path = kmodel_path
        self.model_input_size = model_input_size
        self.confidence_threshold = confidence_threshold
        self.nms_threshold = nms_threshold
        self.rgb888p_size = [ALIGN_UP(rgb888p_size[0], 16), rgb888p_size[1]]
        self.display_size = [ALIGN_UP(display_size[0], 16), display_size[1]]
        self.debug_mode = debug_mode
        
        # 骨骼连接关系（用于绘制）
        self.SKELETON = [
            (16, 14), (14, 12), (17, 15), (15, 13), (12, 13),
            (6, 12), (7, 13), (6, 7), (6, 8), (7, 9),
            (8, 10), (9, 11), (2, 3), (1, 2), (1, 3),
            (2, 4), (3, 5), (4, 6), (5, 7)
        ]
        
        # 肢体颜色
        self.LIMB_COLORS = [
            (255, 51, 153, 255), (255, 51, 153, 255), (255, 51, 153, 255),
            (255, 51, 153, 255), (255, 255, 51, 255), (255, 255, 51, 255),
            (255, 255, 51, 255), (255, 255, 128, 0), (255, 255, 128, 0),
            (255, 255, 128, 0), (255, 255, 128, 0), (255, 255, 128, 0),
            (255, 0, 255, 0), (255, 0, 255, 0), (255, 0, 255, 0),
            (255, 0, 255, 0), (255, 0, 255, 0), (255, 0, 255, 0),
            (255, 0, 255, 0)
        ]
        
        # 关键点颜色
        self.KPS_COLORS = [
            (255, 0, 255, 0), (255, 0, 255, 0), (255, 0, 255, 0),
            (255, 0, 255, 0), (255, 0, 255, 0), (255, 255, 128, 0),
            (255, 255, 128, 0), (255, 255, 128, 0), (255, 255, 128, 0),
            (255, 255, 128, 0), (255, 255, 128, 0), (255, 51, 153, 255),
            (255, 51, 153, 255), (255, 51, 153, 255), (255, 51, 153, 255),
            (255, 51, 153, 255), (255, 51, 153, 255)
        ]
        
        # 初始化体态分析器和关键点验证器
        self.posture_analyzer = PostureAnalyzer()
        self.keypoint_validator = KeypointValidator(confidence_threshold=0.5)
        
        # Ai2d实例
        self.ai2d = Ai2d(debug_mode)
        self.ai2d.set_ai2d_dtype(nn.ai2d_format.NCHW_FMT, nn.ai2d_format.NCHW_FMT,
                                  np.uint8, np.uint8)
    
    def config_preprocess(self, input_image_size=None):
        """配置预处理"""
        with ScopedTiming("set preprocess config", self.debug_mode > 0):
            ai2d_input_size = input_image_size if input_image_size else self.rgb888p_size
            top, bottom, left, right = self.get_padding_param()
            self.ai2d.pad([0, 0, 0, 0, top, bottom, left, right], 0, [0, 0, 0])
            self.ai2d.resize(nn.interp_method.tf_bilinear, nn.interp_mode.half_pixel)
            self.ai2d.build([1, 3, ai2d_input_size[1], ai2d_input_size[0]],
                           [1, 3, self.model_input_size[1], self.model_input_size[0]])
    
    def postprocess(self, results):
        """后处理AI推理结果"""
        with ScopedTiming("postprocess", self.debug_mode > 0):
            results = aidemo.person_kp_postprocess(
                results[0],
                [self.rgb888p_size[1], self.rgb888p_size[0]],
                self.model_input_size,
                self.confidence_threshold,
                self.nms_threshold
            )
            return results
    
    def draw_result(self, pl, res):
        """
        绘制检测结果
        
        Args:
            pl: PipeLine实例
            res: 检测结果
        """
        with ScopedTiming("display_draw", self.debug_mode > 0):
            if res[0]:
                pl.osd_img.clear()
                kpses = res[1]
                
                for i in range(len(res[0])):
                    # 绘制关键点和骨架
                    self.draw_skeleton(pl, kpses[i])
                    
                    # 体态分析
                    issues = self.posture_analyzer.analyze(kpses[i])
                    
                    # 显示体态问题
                    self.draw_posture_issues(pl, issues)
                    
                    gc.collect()
            else:
                pl.osd_img.clear()
                # 未检测到人体
                pl.osd_img.draw_string_advanced(10, 30, 32, "未检测到人体", (255, 255, 0, 255))
    
    def draw_skeleton(self, pl, kps):
        """
        绘制人体骨架
        
        Args:
            pl: PipeLine实例
            kps: 关键点数据
        """
        # 绘制关键点
        for k in range(17):
            kps_x, kps_y, kps_s = round(kps[k][0]), round(kps[k][1]), kps[k][2]
            kps_x1 = int(float(kps_x) * self.display_size[0] // self.rgb888p_size[0])
            kps_y1 = int(float(kps_y) * self.display_size[1] // self.rgb888p_size[1])
            if kps_s > 0:
                pl.osd_img.draw_circle(kps_x1, kps_y1, 5, self.KPS_COLORS[k], 4)
        
        # 绘制骨架连线
        for k in range(len(self.SKELETON)):
            ske = self.SKELETON[k]
            pos1_x, pos1_y = round(kps[ske[0]-1][0]), round(kps[ske[0]-1][1])
            pos1_x_ = int(float(pos1_x) * self.display_size[0] // self.rgb888p_size[0])
            pos1_y_ = int(float(pos1_y) * self.display_size[1] // self.rgb888p_size[1])
            
            pos2_x, pos2_y = round(kps[(ske[1]-1)][0]), round(kps[(ske[1]-1)][1])
            pos2_x_ = int(float(pos2_x) * self.display_size[0] // self.rgb888p_size[0])
            pos2_y_ = int(float(pos2_y) * self.display_size[1] // self.rgb888p_size[1])
            
            pos1_s, pos2_s = kps[(ske[0]-1)][2], kps[(ske[1]-1)][2]
            if pos1_s > 0.0 and pos2_s > 0.0:
                pl.osd_img.draw_line(pos1_x_, pos1_y_, pos2_x_, pos2_y_,
                                    self.LIMB_COLORS[k], 4)
    
    def draw_posture_issues(self, pl, issues):
        """
        显示体态问题
        
        Args:
            pl: PipeLine实例
            issues: 体态问题列表
        """
        if issues:
            y_offset = 30
            for issue in issues:
                # 获取严重程度对应的颜色
                color = self.posture_analyzer.get_severity_color(issue['severity'])
                
                # 显示问题名称和描述
                text = f"{issue['name']}: {issue['description']}"
                pl.osd_img.draw_string_advanced(10, y_offset, 32, text, color)
                y_offset += 40
        else:
            # 坐姿良好
            pl.osd_img.draw_string_advanced(10, 30, 32, "坐姿良好", (0, 255, 0, 255))
    
    def get_padding_param(self):
        """计算padding参数"""
        dst_w = self.model_input_size[0]
        dst_h = self.model_input_size[1]
        input_width = self.rgb888p_size[0]
        input_high = self.rgb888p_size[1]
        ratio_w = dst_w / input_width
        ratio_h = dst_h / input_high
        ratio = min(ratio_w, ratio_h)
        new_w = int(ratio * input_width)
        new_h = int(ratio * input_high)
        dw = (dst_w - new_w) / 2
        dh = (dst_h - new_h) / 2
        top = int(round(dh - 0.1))
        bottom = int(round(dh + 0.1))
        left = int(round(dw - 0.1))
        right = int(round(dw - 0.1))
        return top, bottom, left, right


if __name__ == "__main__":
    # 显示模式，默认"lcd"，可以选择"hdmi"和"lcd"
    display_mode = "lcd"
    
    # k230保持不变，k230d可调整为[640,360]
    rgb888p_size = [1920, 1080]
    
    if display_mode == "hdmi":
        display_size = [1920, 1080]
    else:
        display_size = [800, 480]
    
    # 模型路径
    kmodel_path = "/sdcard/examples/kmodel/yolov8n-pose.kmodel"
    
    # 其它参数设置
    confidence_threshold = 0.2
    nms_threshold = 0.5
    
    # 初始化PipeLine
    pl = PipeLine(rgb888p_size=rgb888p_size, display_size=display_size, display_mode=display_mode)
    pl.create()
    
    # 初始化人体关键点检测和体态分析实例
    person_kp = PersonKeyPointApp(
        kmodel_path,
        model_input_size=[320, 320],
        confidence_threshold=confidence_threshold,
        nms_threshold=nms_threshold,
        rgb888p_size=rgb888p_size,
        display_size=display_size,
        debug_mode=0
    )
    person_kp.config_preprocess()
    
    try:
        print("坐姿体态检测DEMO启动")
        print("建议摄像头位置：侧面45度角，距离1-2米")
        print("按Ctrl+C退出")
        
        while True:
            os.exitpoint()
            with ScopedTiming("total", 1):
                # 获取当前帧数据
                img = pl.get_frame()
                # 推理当前帧
                res = person_kp.run(img)
                # 绘制结果到PipeLine的osd图像
                person_kp.draw_result(pl, res)
                # 显示当前的绘制结果
                pl.show_image()
                gc.collect()
                
    except Exception as e:
        sys.print_exception(e)
    finally:
        person_kp.deinit()
        pl.destroy()
        print("程序已退出")
