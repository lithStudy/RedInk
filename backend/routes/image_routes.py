"""
图片生成相关 API 路由

包含功能：
- 批量生成图片（SSE 流式返回）
- 获取图片
- 重试/重新生成单张图片
- 批量重试失败图片
- 获取任务状态
"""

import os
import json
import base64
import logging
from flask import Blueprint, request, jsonify, Response, send_file
from backend.services.image import get_image_service
from .utils import log_request, log_error

logger = logging.getLogger(__name__)


def create_image_blueprint():
    """创建图片路由蓝图（工厂函数，支持多次调用）"""
    image_bp = Blueprint('image', __name__)

    # ==================== 图片生成 ====================

    @image_bp.route('/generate', methods=['POST'])
    def generate_images():
        """
        批量生成图片（SSE 流式返回）

        请求体：
        - pages: 页面列表（必填）
        - task_id: 任务 ID
        - full_outline: 完整大纲文本
        - user_topic: 用户原始输入主题
        - user_images: base64 编码的用户参考图片列表

        返回：
        SSE 事件流，包含以下事件类型：
        - image: 单张图片生成完成
        - error: 生成错误
        - complete: 全部完成
        """
        try:
            data = request.get_json()
            pages = data.get('pages')
            record_id = data.get('record_id')
            full_outline = data.get('full_outline', '')
            user_topic = data.get('user_topic', '')

            # 解析 base64 格式的用户参考图片
            user_images = _parse_base64_images(data.get('user_images', []))
            reference_mode = data.get('reference_mode', 'cover')

            log_request('/generate', {
                'pages_count': len(pages) if pages else 0,
                'record_id': record_id,
                'user_topic': user_topic[:50] if user_topic else None,
                'user_images': user_images,
                'reference_mode': reference_mode
            })

            if not pages or not record_id:
                logger.warning("图片生成请求缺少必要参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：pages 和 record_id 不能为空。"
                }), 400

            logger.info(f"🖼️  开始图片生成任务: record_id={record_id}, 共 {len(pages)} 页")
            image_service = get_image_service()

            def generate():
                """SSE 事件生成器"""
                for event in image_service.generate_images(
                    pages, record_id, full_outline,
                    user_images=user_images if user_images else None,
                    user_topic=user_topic,
                    reference_mode=reference_mode
                ):
                    event_type = event["event"]
                    event_data = event["data"]

                    # 格式化为 SSE 格式
                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/generate', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"图片生成异常。\n错误详情: {error_msg}\n建议：检查图片生成服务配置和后端日志"
            }), 500

    # ==================== 图片获取 ====================

    @image_bp.route('/images/<task_id>/<filename>', methods=['GET'])
    def get_image(task_id, filename):
        """
        获取图片文件

        路径参数：
        - task_id: 任务 ID
        - filename: 文件名

        查询参数：
        - thumbnail: 是否返回缩略图（默认 true）

        返回：
        - 成功：图片文件
        - 失败：JSON 错误信息
        """
        try:
            logger.debug(f"获取图片: {task_id}/{filename}")

            # 检查是否请求缩略图
            thumbnail = request.args.get('thumbnail', 'true').lower() == 'true'

            # 构建 history 目录路径
            history_root = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                "history"
            )

            if thumbnail:
                # 尝试返回缩略图
                thumb_filename = f"thumb_{filename}"
                thumb_filepath = os.path.join(history_root, task_id, thumb_filename)

                if os.path.exists(thumb_filepath):
                    return send_file(thumb_filepath, mimetype='image/png')

            # 返回原图
            filepath = os.path.join(history_root, task_id, filename)

            if not os.path.exists(filepath):
                return jsonify({
                    "success": False,
                    "error": f"图片不存在：{task_id}/{filename}"
                }), 404

            return send_file(filepath, mimetype='image/png')

        except Exception as e:
            log_error('/images', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取图片失败: {error_msg}"
            }), 500

    # ==================== 重试和重新生成 ====================

    @image_bp.route('/retry', methods=['POST'])
    def retry_single_image():
        """
        重试生成单张失败的图片

        请求体：
        - task_id: 任务 ID（必填）
        - page: 页面信息（必填）
        - use_reference: 是否使用参考图（默认 true）

        返回：
        - success: 是否成功
        - image_url: 新图片 URL
        """
        try:
            data = request.get_json()
            task_id = data.get('task_id')
            page = data.get('page')
            use_reference = data.get('use_reference', True)

            log_request('/retry', {
                'task_id': task_id,
                'page_index': page.get('index') if page else None
            })

            record_id = data.get('record_id')
            
            if not record_id or not page:
                logger.warning("重试请求缺少必要参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：record_id 和 page 不能为空。"
                }), 400

            logger.info(f"🔄 重试生成图片: record={record_id}, page={page.get('index')}")
            image_service = get_image_service()
            result = image_service.retry_single_image(record_id, page, use_reference)

            if result["success"]:
                logger.info(f"✅ 图片重试成功: {result.get('image_url')}")
            else:
                logger.error(f"❌ 图片重试失败: {result.get('error')}")

            return jsonify(result), 200 if result["success"] else 500

        except Exception as e:
            log_error('/retry', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"重试图片生成失败。\n错误详情: {error_msg}"
            }), 500

    @image_bp.route('/retry-failed', methods=['POST'])
    def retry_failed_images():
        """
        批量重试失败的图片（SSE 流式返回）

        请求体：
        - task_id: 任务 ID（必填）
        - pages: 要重试的页面列表（必填）

        返回：
        SSE 事件流
        """
        try:
            data = request.get_json()
            task_id = data.get('task_id')
            pages = data.get('pages')

            log_request('/retry-failed', {
                'task_id': task_id,
                'pages_count': len(pages) if pages else 0
            })

            if not task_id or not pages:
                logger.warning("批量重试请求缺少必要参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：task_id 和 pages 不能为空。\n请提供任务ID和要重试的页面列表。"
                }), 400

            logger.info(f"🔄 批量重试失败图片: task={task_id}, 共 {len(pages)} 页")
            image_service = get_image_service()

            def generate():
                """SSE 事件生成器"""
                for event in image_service.retry_failed_images(task_id, pages):
                    event_type = event["event"]
                    event_data = event["data"]

                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/retry-failed', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"批量重试失败。\n错误详情: {error_msg}"
            }), 500

    @image_bp.route('/regenerate', methods=['POST'])
    def regenerate_image():
        """
        重新生成图片（即使成功的也可以重新生成）

        请求体：
        - record_id: 记录 ID（必填）
        - page: 页面信息（必填）
        - use_reference: 是否使用参考图（默认 true）
        - full_outline: 完整大纲文本（用于上下文）
        - user_topic: 用户原始输入主题
        - reference_mode: 参考图模式（'custom' | 'cover' | 'previous'，默认 'cover'）

        返回：
        - success: 是否成功
        - image_url: 新图片 URL
        """
        try:
            data = request.get_json()
            record_id = data.get('record_id')
            page = data.get('page')
            use_reference = data.get('use_reference', True)
            full_outline = data.get('full_outline', '')
            user_topic = data.get('user_topic', '')
            reference_mode = data.get('reference_mode', 'cover')

            log_request('/regenerate', {
                'record_id': record_id,
                'page_index': page.get('index') if page else None,
                'reference_mode': reference_mode
            })
            
            if not record_id or not page:
                logger.warning("重新生成请求缺少必要参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：record_id 和 page 不能为空。"
                }), 400

            logger.info(f"🔄 重新生成图片: record={record_id}, page={page.get('index')}, mode={reference_mode}")
            image_service = get_image_service()
            result = image_service.regenerate_image(
                record_id, page, use_reference,
                full_outline=full_outline,
                user_topic=user_topic,
                reference_mode=reference_mode
            )

            if result["success"]:
                logger.info(f"✅ 图片重新生成成功: {result.get('image_url')}")
            else:
                logger.error(f"❌ 图片重新生成失败: {result.get('error')}")

            return jsonify(result), 200 if result["success"] else 500

        except Exception as e:
            log_error('/regenerate', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"重新生成图片失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 停止和继续生成 ====================

    @image_bp.route('/stop-generation', methods=['POST'])
    def stop_generation():
        """
        停止图片生成

        请求体：
        - task_id: 任务 ID（必填）

        返回：
        - success: 是否成功
        - message: 操作消息
        """
        try:
            data = request.get_json()
            task_id = data.get('task_id')

            log_request('/stop-generation', {'task_id': task_id})

            if not task_id:
                logger.warning("停止生成请求缺少 task_id 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：task_id 不能为空"
                }), 400

            logger.info(f"⏹️ 请求停止任务: {task_id}")
            image_service = get_image_service()
            image_service.stop_task(task_id)

            return jsonify({
                "success": True,
                "message": "已发送停止信号"
            }), 200

        except Exception as e:
            log_error('/stop-generation', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"停止生成失败: {error_msg}"
            }), 500

    @image_bp.route('/continue-generation', methods=['POST'])
    def continue_generation():
        """
        继续图片生成（SSE 流式返回）
        自动扫描文件夹中的图片，找出未生成的页面

        请求体：
        - record_id: 记录 ID（必填）

        返回：
        SSE 事件流
        """
        try:
            data = request.get_json()
            record_id = data.get('record_id')

            log_request('/continue-generation', {
                'record_id': record_id
            })

            if not record_id:
                logger.warning("继续生成请求缺少 record_id 参数")
                return jsonify({
                    "success": False,
                    "error": "参数错误：record_id 不能为空"
                }), 400
            
            logger.info(f"▶️ 继续任务: record={record_id}")
            image_service = get_image_service()

            def generate():
                """SSE 事件生成器"""
                # 不传入 pages，让服务自动扫描未完成的页面
                for event in image_service.continue_generation(
                    record_id, pages=None, full_outline="", user_topic=""
                ):
                    event_type = event["event"]
                    event_data = event["data"]

                    yield f"event: {event_type}\n"
                    yield f"data: {json.dumps(event_data, ensure_ascii=False)}\n\n"

            return Response(
                generate(),
                mimetype='text/event-stream',
                headers={
                    'Cache-Control': 'no-cache',
                    'X-Accel-Buffering': 'no',
                }
            )

        except Exception as e:
            log_error('/continue-generation', e)
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"继续生成失败: {error_msg}"
            }), 500

    # ==================== 任务状态 ====================

    @image_bp.route('/task/<task_id>', methods=['GET'])
    def get_task_state(task_id):
        """
        获取任务状态

        路径参数：
        - task_id: 任务 ID

        返回：
        - success: 是否成功
        - state: 任务状态
          - generated: 已生成的图片
          - failed: 失败的图片
          - has_cover: 是否有封面图
        """
        try:
            image_service = get_image_service()
            state = image_service.get_task_state(task_id)

            if state is None:
                return jsonify({
                    "success": False,
                    "error": f"任务不存在：{task_id}\n可能原因：\n1. 任务ID错误\n2. 任务已过期或被清理\n3. 服务重启导致状态丢失"
                }), 404

            # 不返回封面图片数据（太大）
            safe_state = {
                "generated": state.get("generated", {}),
                "failed": state.get("failed", {}),
                "has_cover": state.get("cover_image") is not None
            }

            return jsonify({
                "success": True,
                "state": safe_state
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取任务状态失败。\n错误详情: {error_msg}"
            }), 500

    @image_bp.route('/task/<task_id>/images', methods=['GET'])
    def get_task_images(task_id):
        """
        获取任务文件夹中已生成的图片列表（扫描文件系统）

        路径参数：
        - task_id: 任务 ID

        返回：
        - success: 是否成功
        - images: 已生成的图片文件名列表（按索引排序）
        - outline: 大纲信息（如果存在）
        """
        try:
            image_service = get_image_service()
            
            # 扫描已生成的图片
            generated_indices = image_service.scan_generated_images(task_id)
            images = [f"{idx}.png" for idx in sorted(generated_indices)]
            
            # 尝试加载大纲信息
            outline_data = image_service.load_outline_from_task(task_id)
            
            result = {
                "success": True,
                "images": images,
                "generated_indices": sorted(generated_indices)
            }
            
            if outline_data:
                result["outline"] = {
                    "raw": outline_data.get("outline", ""),  # 包含完整的 raw 文本
                    "pages": outline_data.get("pages", []),
                    "topic": outline_data.get("topic", ""),
                    "total": len(outline_data.get("pages", [])),
                    "metadata": outline_data.get("metadata")  # 包含小红书标题、正文和标签
                }
            
            return jsonify(result), 200

        except Exception as e:
            error_msg = str(e)
            logger.error(f"获取任务图片列表失败: {error_msg}")
            return jsonify({
                "success": False,
                "error": f"获取任务图片列表失败: {error_msg}"
            }), 500

    # ==================== 健康检查 ====================

    @image_bp.route('/health', methods=['GET'])
    def health_check():
        """
        健康检查接口

        返回：
        - success: 服务是否正常
        - message: 状态消息
        """
        return jsonify({
            "success": True,
            "message": "服务正常运行"
        }), 200

    return image_bp


# ==================== 辅助函数 ====================

def _parse_base64_images(images_base64: list) -> list:
    """
    解析 base64 编码的图片列表

    Args:
        images_base64: base64 编码的图片字符串列表

    Returns:
        list: 解码后的图片二进制数据列表
    """
    if not images_base64:
        return []

    images = []
    for img_b64 in images_base64:
        # 移除可能的 data URL 前缀（如 data:image/png;base64,）
        if ',' in img_b64:
            img_b64 = img_b64.split(',')[1]
        images.append(base64.b64decode(img_b64))

    return images
