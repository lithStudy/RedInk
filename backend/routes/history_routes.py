"""
历史记录相关 API 路由

包含功能：
- 创建/获取/更新/删除历史记录 (CRUD)
- 搜索历史记录
- 获取统计信息
- 扫描和同步任务图片
- 打包下载图片
"""

import os
import io
import zipfile
import logging
from flask import Blueprint, request, jsonify, send_file
from backend.services.history import get_history_service

logger = logging.getLogger(__name__)


def create_history_blueprint():
    """创建历史记录路由蓝图（工厂函数，支持多次调用）"""
    history_bp = Blueprint('history', __name__)

    # ==================== CRUD 操作 ====================

    @history_bp.route('/history', methods=['POST'])
    def create_history():
        """
        创建历史记录

        请求体：
        - topic: 主题标题（必填）
        - outline: 大纲内容（可选，用于兼容旧代码）
        - record_id: 关联的记录 ID（可选，如果提供则使用该ID）

        返回：
        - success: 是否成功
        - record_id: 新创建的记录 ID
        """
        try:
            data = request.get_json()
            topic = data.get('topic')
            outline = data.get('outline')
            record_id = data.get('record_id')  # 如果提供了 record_id，使用它（用于关联已有记录）

            if not topic:
                return jsonify({
                    "success": False,
                    "error": "参数错误：topic 不能为空。\n请提供主题。"
                }), 400

            history_service = get_history_service()
            # 如果提供了 record_id，直接返回（记录已存在）
            if record_id:
                return jsonify({
                    "success": True,
                    "record_id": record_id
                }), 200
            
            # 否则创建新记录
            record_id = history_service.create_record(topic)

            return jsonify({
                "success": True,
                "record_id": record_id
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"创建历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history', methods=['GET'])
    def list_history():
        """
        获取历史记录列表（分页）

        查询参数：
        - page: 页码（默认 1）
        - page_size: 每页数量（默认 20）
        - status: 状态过滤（可选：all/completed/draft）

        返回：
        - success: 是否成功
        - records: 记录列表
        - total: 总数
        - total_pages: 总页数
        """
        try:
            page = int(request.args.get('page', 1))
            page_size = int(request.args.get('page_size', 20))
            status = request.args.get('status')

            history_service = get_history_service()
            result = history_service.list_records(page, page_size, status)

            return jsonify({
                "success": True,
                **result
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取历史记录列表失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>', methods=['GET'])
    def get_history(record_id):
        """
        获取历史记录详情

        路径参数：
        - record_id: 记录 ID

        返回：
        - success: 是否成功
        - record: 完整的记录数据
        """
        try:
            history_service = get_history_service()
            record = history_service.get_record(record_id)

            if not record:
                return jsonify({
                    "success": False,
                    "error": f"历史记录不存在：{record_id}\n可能原因：记录已被删除或ID错误"
                }), 404

            return jsonify({
                "success": True,
                "record": record
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取历史记录详情失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>', methods=['PUT'])
    def update_history(record_id):
        """
        更新历史记录

        路径参数：
        - record_id: 记录 ID

        请求体（均为可选）：
        - topic: 主题
        - outline: 大纲内容
        - images: 图片信息
        - status: 状态
        - thumbnail: 缩略图文件名

        返回：
        - success: 是否成功
        """
        try:
            data = request.get_json()
            topic = data.get('topic')
            outline = data.get('outline')
            images = data.get('images')
            status = data.get('status')

            history_service = get_history_service()
            success = history_service.update_record(
                record_id,
                topic=topic,
                outline=outline,
                images=images,
                status=status
            )

            if not success:
                return jsonify({
                    "success": False,
                    "error": f"更新历史记录失败：{record_id}\n可能原因：记录不存在或数据格式错误"
                }), 404

            return jsonify({
                "success": True
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"更新历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/<record_id>', methods=['DELETE'])
    def delete_history(record_id):
        """
        删除历史记录

        路径参数：
        - record_id: 记录 ID

        返回：
        - success: 是否成功
        """
        try:
            history_service = get_history_service()
            success = history_service.delete_record(record_id)

            if not success:
                return jsonify({
                    "success": False,
                    "error": f"删除历史记录失败：{record_id}\n可能原因：记录不存在或ID错误"
                }), 404

            return jsonify({
                "success": True
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"删除历史记录失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 搜索和统计 ====================

    @history_bp.route('/history/search', methods=['GET'])
    def search_history():
        """
        搜索历史记录

        查询参数：
        - keyword: 搜索关键词（必填）

        返回：
        - success: 是否成功
        - records: 匹配的记录列表
        """
        try:
            keyword = request.args.get('keyword', '')

            if not keyword:
                return jsonify({
                    "success": False,
                    "error": "参数错误：keyword 不能为空。\n请提供搜索关键词。"
                }), 400

            history_service = get_history_service()
            results = history_service.search_records(keyword)

            return jsonify({
                "success": True,
                "records": results
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"搜索历史记录失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/stats', methods=['GET'])
    def get_history_stats():
        """
        获取历史记录统计信息

        返回：
        - success: 是否成功
        - total: 总记录数
        - by_status: 按状态分组的统计
        """
        try:
            history_service = get_history_service()
            stats = history_service.get_statistics()

            return jsonify({
                "success": True,
                **stats
            }), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"获取历史记录统计失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 扫描和同步 ====================

    @history_bp.route('/history/scan/<record_id>', methods=['GET'])
    def scan_task(record_id):
        """
        扫描单个任务并同步图片列表

        路径参数：
        - record_id: 记录 ID

        返回：
        - success: 是否成功
        - images: 同步后的图片列表
        """
        try:
            history_service = get_history_service()
            result = history_service.scan_and_sync_task_images(record_id)

            if not result.get("success"):
                return jsonify(result), 404

            return jsonify(result), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"扫描任务失败。\n错误详情: {error_msg}"
            }), 500

    @history_bp.route('/history/scan-all', methods=['POST'])
    def scan_all_tasks():
        """
        扫描所有任务并同步图片列表

        返回：
        - success: 是否成功
        - total_tasks: 扫描的任务总数
        - synced: 成功同步的任务数
        - failed: 失败的任务数
        - orphan_tasks: 孤立任务列表（有图片但无记录）
        """
        try:
            history_service = get_history_service()
            result = history_service.scan_all_tasks()

            if not result.get("success"):
                return jsonify(result), 500

            return jsonify(result), 200

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"扫描所有任务失败。\n错误详情: {error_msg}"
            }), 500

    # ==================== 下载功能 ====================

    @history_bp.route('/history/<record_id>/download', methods=['GET'])
    def download_history_zip(record_id):
        """
        下载历史记录的所有图片为 ZIP 文件

        路径参数：
        - record_id: 记录 ID

        返回：
        - 成功：ZIP 文件下载
        - 失败：JSON 错误信息
        """
        try:
            history_service = get_history_service()
            record = history_service.get_record(record_id)

            if not record:
                return jsonify({
                    "success": False,
                    "error": f"历史记录不存在：{record_id}"
                }), 404

            # 使用 record_id 作为任务目录（图片存储在 history/{record_id}/ 目录下）
            record_id_for_dir = record_id

            # 获取任务目录
            task_dir = os.path.join(history_service.history_dir, record_id_for_dir)
            if not os.path.exists(task_dir):
                return jsonify({
                    "success": False,
                    "error": f"任务目录不存在：{record_id_for_dir}"
                }), 404

            # 获取页面顺序（从 outline.pages）
            outline = record.get('outline', {})
            pages = outline.get('pages', [])
            
            # 创建内存中的 ZIP 文件
            zip_buffer = _create_images_zip(task_dir, pages)

            # 生成安全的下载文件名
            title = record.get('title', 'images')
            safe_title = _sanitize_filename(title)
            filename = f"{safe_title}.zip"

            return send_file(
                zip_buffer,
                mimetype='application/zip',
                as_attachment=True,
                download_name=filename
            )

        except Exception as e:
            error_msg = str(e)
            return jsonify({
                "success": False,
                "error": f"下载失败。\n错误详情: {error_msg}"
            }), 500

    return history_bp


def _create_images_zip(task_dir: str, pages: list = None) -> io.BytesIO:
    """
    创建包含所有图片的 ZIP 文件

    Args:
        task_dir: 任务目录路径
        pages: 页面顺序列表（包含 index 字段），用于按照当前显示顺序命名文件

    Returns:
        io.BytesIO: 内存中的 ZIP 文件
    """
    memory_file = io.BytesIO()

    with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zf:
        if pages:
            # 如果提供了页面顺序，按照页面顺序打包
            for display_index, page in enumerate(pages, start=1):
                # 从 page.image.filename 获取图片文件名
                image = page.get('image')
                if image and image.get('filename'):
                    filename = image['filename']
                    file_path = os.path.join(task_dir, filename)
                    
                    # 检查文件是否存在
                    if os.path.exists(file_path):
                        archive_name = f"page_{display_index}.png"
                        zf.write(file_path, archive_name)
        else:
            # 如果没有提供页面顺序，使用原有逻辑（兼容旧代码）
            for filename in os.listdir(task_dir):
                # 跳过缩略图文件
                if filename.startswith('thumb_'):
                    continue

                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    file_path = os.path.join(task_dir, filename)

                    # 生成归档文件名（page_N.png 格式）
                    try:
                        index = int(filename.split('.')[0])
                        archive_name = f"page_{index + 1}.png"
                    except ValueError:
                        archive_name = filename

                    zf.write(file_path, archive_name)

    # 将指针移到开始位置
    memory_file.seek(0)
    return memory_file


def _sanitize_filename(title: str) -> str:
    """
    清理文件名中的非法字符

    Args:
        title: 原始标题

    Returns:
        str: 安全的文件名
    """
    # 只保留字母、数字、空格、连字符和下划线
    safe_title = "".join(
        c for c in title
        if c.isalnum() or c in (' ', '-', '_', '\u4e00-\u9fff')
    ).strip()

    return safe_title if safe_title else 'images'
