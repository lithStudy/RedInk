"""
大纲生成相关 API 路由

包含功能：
- 生成基调
- 生成大纲（支持图片上传和基调）
"""

import time
import base64
import logging
from flask import Blueprint, request, jsonify
from backend.services.outline import get_outline_service
from .utils import log_request, log_error

logger = logging.getLogger(__name__)


def create_outline_blueprint():
    """创建大纲路由蓝图（工厂函数，支持多次调用）"""
    outline_bp = Blueprint('outline', __name__)

    @outline_bp.route('/tone', methods=['POST'])
    def generate_tone():
        """
        生成内容基调

        请求格式：application/json
        - topic: 主题文本（必填）
        - record_id: 记录ID（可选，如果提供则更新现有记录，否则创建新记录）

        返回：
        - success: 是否成功
        - tone: 基调文本
        - record_id: 记录ID
        """
        start_time = time.time()

        try:
            data = request.get_json()
            topic = data.get('topic') if data else None
            record_id = data.get('record_id') if data else None

            log_request('/tone', {'topic': topic, 'record_id': record_id})

            # 验证必填参数
            if not topic:
                logger.warning("基调生成请求缺少 topic 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供要生成基调的主题内容。"
                }), 400

            # 如果提供了 record_id，使用现有记录；否则创建新记录
            from backend.services.history import get_history_service
            history_service = get_history_service()
            
            if record_id:
                # 使用现有记录，更新主题
                logger.info(f"🔄 使用现有记录更新基调: record_id={record_id}")
                # 更新记录的主题
                from backend.models import RecordModel
                RecordModel.update(record_id=record_id, topic=topic)
            else:
                # 创建新记录
                record_id = history_service.create_record(topic=topic, title="", status="draft")
                logger.info(f"✅ 创建新记录: record_id={record_id}")
            
            # 调用基调生成服务
            logger.info(f"🔄 开始生成基调，主题: {topic[:50]}...")
            outline_service = get_outline_service()
            result = outline_service.generate_tone(topic, record_id)
            
            # 在返回结果中添加 record_id
            if result["success"]:
                result["record_id"] = record_id

            # 记录结果
            elapsed = time.time() - start_time
            if result["success"]:
                logger.info(f"✅ 基调生成成功，耗时 {elapsed:.2f}s")
                return jsonify(result), 200
            else:
                logger.error(f"❌ 基调生成失败: {result.get('error', '未知错误')}")
                return jsonify(result), 500

        except Exception as e:
            log_error('/tone', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"基调生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    @outline_bp.route('/outline', methods=['POST'])
    def generate_outline():
        """
        生成大纲（支持图片上传）

        请求格式：
        1. multipart/form-data（带图片文件）
           - topic: 主题文本
           - images: 图片文件列表

        2. application/json（无图片或 base64 图片）
           - topic: 主题文本
           - images: base64 编码的图片数组（可选）

        返回：
        - success: 是否成功
        - outline: 原始大纲文本
        - pages: 解析后的页面列表
        """
        start_time = time.time()

        try:
            # 解析请求数据
            topic, images, tone, record_id = _parse_outline_request()

            log_request('/outline', {'topic': topic, 'images': images, 'tone': '已提供' if tone else '未提供', 'record_id': record_id})

            # 验证必填参数
            if not topic:
                logger.warning("大纲生成请求缺少 topic 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供要生成图文的主题内容。"
                }), 400

            # 如果没有 record_id，先创建记录
            from backend.services.history import get_history_service
            if not record_id:
                history_service = get_history_service()
                record_id = history_service.create_record(topic=topic, title="", status="draft")
                logger.info(f"✅ 创建记录: record_id={record_id}")

            # 调用大纲生成服务
            logger.info(f"🔄 开始生成大纲，主题: {topic[:50]}..., record_id={record_id}")
            outline_service = get_outline_service()
            result = outline_service.generate_outline(topic, record_id, images if images else None, tone)
            
            # 在返回结果中添加 record_id
            if result["success"]:
                result["record_id"] = record_id

            # 记录结果
            elapsed = time.time() - start_time
            if result["success"]:
                logger.info(f"✅ 大纲生成成功，耗时 {elapsed:.2f}s，共 {len(result.get('pages', []))} 页")
                return jsonify(result), 200
            else:
                logger.error(f"❌ 大纲生成失败: {result.get('error', '未知错误')}")
                return jsonify(result), 500

        except Exception as e:
            log_error('/outline', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"大纲生成异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    @outline_bp.route('/tone/<record_id>', methods=['GET'])
    def get_tone(record_id: str):
        """
        获取记录关联的基调

        路径参数：
        - record_id: 记录ID

        返回：
        - success: 是否成功
        - tone: 基调文本
        """
        try:
            logger.info(f"🔄 读取基调，记录ID: {record_id}")
            outline_service = get_outline_service()
            result = outline_service.get_tone(record_id)

            if result["success"]:
                logger.info("✅ 读取基调成功")
                return jsonify(result), 200
            else:
                logger.warning(f"⚠️ 读取基调失败: {result.get('error', '未知错误')}")
                return jsonify(result), 404

        except Exception as e:
            log_error('/tone/<task_id>', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"读取基调异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    @outline_bp.route('/tone/<record_id>', methods=['PUT'])
    def update_tone(record_id: str):
        """
        更新记录关联的基调

        路径参数：
        - record_id: 记录ID

        请求体：
        - tone: 基调文本

        返回：
        - success: 是否成功
        """
        try:
            data = request.get_json()
            tone_text = data.get('tone') if data else None

            if not tone_text:
                logger.warning("更新基调请求缺少 tone 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：tone 不能为空。"
                }), 400

            logger.info(f"🔄 更新基调，记录ID: {record_id}")
            outline_service = get_outline_service()
            result = outline_service.update_tone(record_id, tone_text)

            if result["success"]:
                logger.info("✅ 更新基调成功")
                return jsonify(result), 200
            else:
                logger.warning(f"⚠️ 更新基调失败: {result.get('error', '未知错误')}")
                return jsonify(result), 400

        except Exception as e:
            log_error('/tone/<task_id>', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"更新基调异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    @outline_bp.route('/outline/<record_id>', methods=['PUT'])
    def update_outline_route(record_id: str):
        """
        更新记录的大纲（例如删除页面后）

        路径参数：
        - record_id: 记录ID

        请求体：
        - pages: 新的页面列表

        返回：
        - success: 是否成功
        """
        try:
            data = request.get_json()
            pages = data.get('pages') if data else None

            if not pages:
                logger.warning("更新大纲请求缺少 pages 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：pages 不能为空。"
                }), 400

            logger.info(f"🔄 更新大纲，记录ID: {record_id}, 页面数: {len(pages)}")
            outline_service = get_outline_service()
            result = outline_service.update_outline(record_id, pages)

            if result["success"]:
                logger.info("✅ 更新大纲成功")
                return jsonify(result), 200
            else:
                logger.warning(f"⚠️ 更新大纲失败: {result.get('error', '未知错误')}")
                return jsonify(result), 400

        except Exception as e:
            log_error('/outline/<task_id>', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"更新大纲异常。\n错误详情: {error_msg}\n建议：检查后端日志获取更多信息"
            }), 500

    return outline_bp


def _parse_outline_request():
    """
    解析大纲生成请求

    支持两种格式：
    1. multipart/form-data - 用于文件上传
    2. application/json - 用于 base64 图片和基调

    返回：
        tuple: (topic, images, tone, record_id) - 主题、图片列表、基调和记录ID
    """
    tone = None
    record_id = None
    
    # 检查是否是 multipart/form-data（带图片文件）
    if request.content_type and 'multipart/form-data' in request.content_type:
        topic = request.form.get('topic')
        tone = request.form.get('tone')  # 支持从 form 中获取基调
        record_id = request.form.get('record_id')  # 支持从 form 中获取记录ID
        images = []

        # 获取上传的图片文件
        if 'images' in request.files:
            files = request.files.getlist('images')
            for file in files:
                if file and file.filename:
                    image_data = file.read()
                    images.append(image_data)

        return topic, images, tone, record_id

    # JSON 请求（无图片或 base64 图片）
    data = request.get_json()
    topic = data.get('topic')
    tone = data.get('tone')  # 从 JSON 中获取基调
    record_id = data.get('record_id')  # 从 JSON 中获取记录ID
    images = []

    # 支持 base64 格式的图片
    images_base64 = data.get('images', [])
    if images_base64:
        for img_b64 in images_base64:
            # 移除可能的 data URL 前缀
            if ',' in img_b64:
                img_b64 = img_b64.split(',')[1]
            images.append(base64.b64decode(img_b64))

    return topic, images, tone, record_id
