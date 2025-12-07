import os
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pathlib import Path
from backend.models import RecordModel, ToneModel, OutlineModel, PageModel, ImageModel


class HistoryService:
    def __init__(self):
        self.history_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_dir, exist_ok=True)

    def create_record(
        self,
        topic: str,
        title: str = "",
        status: str = "draft"
    ) -> str:
        """
        创建记录
        
        Args:
            topic: 用户输入的主题/需求
            title: AI 生成的标题（可选，大纲生成后会更新）
            status: 状态
            
        Returns:
            记录 ID
        """
        record_id = str(uuid.uuid4())
        RecordModel.create(
            record_id=record_id,
            title=title,
            topic=topic,
            status=status,
            reference_images=None
        )
        return record_id

    def get_record(self, record_id: str) -> Optional[Dict]:
        """
        获取完整记录信息（包含 outline、pages 等，图片信息整合在 pages 中）
        
        Args:
            record_id: 记录 ID
            
        Returns:
            完整记录数据
        """
        record = RecordModel.get(record_id)
        if not record:
            return None
        
        # 获取大纲信息（通过 tone_id）
        tone = ToneModel.get_by_record(record_id)
        outline = None
        if tone:
            outline = OutlineModel.get_by_tone(tone['id'])
        if outline:
            record['outline'] = {
                'raw': outline['raw_outline'],
                'metadata': {
                    'title': outline['metadata_title'],
                    'content': outline['metadata_content'],
                    'tags': outline['metadata_tags']
                }
            }
            
            # 获取页面列表（已包含图片信息）
            pages = PageModel.get_by_outline(outline['id'])
            record['outline']['pages'] = [
                {
                    'id': p['id'],  # 包含页面ID，用于匹配图片关联
                    'index': p['page_index'],
                    'type': p['page_type'],
                    'content': p['content'],
                    'image': p.get('image')  # 图片信息（如果有）
                }
                for p in pages
            ]
            
            # 获取缩略图（从 cover 页面的图片）
            thumbnail = None
            for page in pages:
                if page['page_type'] == 'cover' and page.get('image'):
                    thumbnail = page['image']['filename']
                    break
            
            # 如果没找到 cover 图片，使用第一张有图片的页面
            if not thumbnail:
                for page in pages:
                    if page.get('image'):
                        thumbnail = page['image']['filename']
                        break
            
            record['thumbnail'] = thumbnail
        else:
            record['thumbnail'] = None
        
        return record

    def update_record(
        self,
        record_id: str,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        status: Optional[str] = None,
        outline: Optional[Dict] = None,
        images: Optional[Dict] = None
    ) -> bool:
        """
        更新记录
        
        Args:
            record_id: 记录 ID
            title: 标题
            topic: 主题
            status: 状态
            outline: 大纲数据（包含 raw, metadata, pages）
            images: 图片数据（暂时保留兼容性，实际图片通过 ImageModel 管理）
            
        Returns:
            是否成功
        """
        # 更新基本信息
        RecordModel.update(
            record_id=record_id,
            title=title,
            topic=topic,
            status=status
        )
        
        # 更新大纲
        if outline:
            metadata = outline.get('metadata', {})
            # 先获取 tone_id
            tone = ToneModel.get_by_record(record_id)
            if tone:
                OutlineModel.update(
                    tone_id=tone['id'],
                    raw_outline=outline.get('raw'),
                    metadata_title=metadata.get('title'),
                    metadata_content=metadata.get('content'),
                    metadata_tags=metadata.get('tags')
                )
            
            # 更新页面（只更新内容，保持页面ID不变）
            if 'pages' in outline:
                # 获取 outline_id（通过 tone_id）
                tone = ToneModel.get_by_record(record_id)
                if tone:
                    outline_obj = OutlineModel.get_by_tone(tone['id'])
                    if outline_obj:
                        # 获取现有页面
                        existing_pages = PageModel.get_by_outline(outline_obj['id'])
                        existing_page_ids = {p['id'] for p in existing_pages}
                        existing_pages_by_id = {p['id']: p for p in existing_pages}
                        
                        # 收集传入的页面 ID
                        incoming_page_ids = {p.get('id') for p in outline['pages'] if p.get('id')}
                        
                        # 更新或创建页面
                        for page in outline['pages']:
                            page_id = page.get('id')
                            
                            # 确定 image_id
                            image_id = None
                            if page_id and page_id in existing_pages_by_id:
                                # 保留现有的 image_id
                                image_id = existing_pages_by_id[page_id].get('image_id')
                            
                            # 如果前端传递了 image.id，优先使用
                            if isinstance(page.get('image'), dict) and page['image'].get('id'):
                                image_id = page['image']['id']
                            
                            if page_id and page_id in existing_page_ids:
                                # 🔥 更新现有页面（保持ID不变）
                                PageModel.update(
                                    page_id=page_id,
                                    page_index=page['index'],
                                    page_type=page['type'],
                                    content=page['content'],
                                    image_id=image_id
                                )
                            else:
                                # 创建新页面（没有ID的页面）
                                PageModel.create(
                                    outline_id=outline_obj['id'],
                                    page_index=page['index'],
                                    page_type=page['type'],
                                    content=page['content'],
                                    image_id=image_id
                                )
                        
                        # 删除不在新列表中的页面
                        pages_to_delete = existing_page_ids - incoming_page_ids
                        for page_id in pages_to_delete:
                            PageModel.delete_by_id(page_id)
        
        return True

    def delete_record(self, record_id: str) -> bool:
        """
        删除记录及其关联的所有数据和文件
        
        Args:
            record_id: 记录 ID
            
        Returns:
            是否成功
        """
        record = RecordModel.get(record_id)
        if not record:
            return False
        
        # 获取所有图片文件名，用于删除文件
        images = ImageModel.get_by_record(record_id)
        
        # 删除数据库记录（级联删除）
        RecordModel.delete(record_id)
        
        # 删除图片文件
        # 注意：图片存储在 history/{record_id}/ 目录下
        # 图片文件名格式：{record_id}_{timestamp}_{random}.png
        for img in images:
            # 删除原图
            img_path = self._find_image_path(img['filename'])
            if img_path and os.path.exists(img_path):
                try:
                    os.remove(img_path)
                except Exception as e:
                    print(f"删除图片失败: {img_path}, {e}")
            
            # 删除缩略图
            if img['thumbnail_filename']:
                thumb_path = self._find_image_path(img['thumbnail_filename'])
                if thumb_path and os.path.exists(thumb_path):
                    try:
                        os.remove(thumb_path)
                    except Exception as e:
                        print(f"删除缩略图失败: {thumb_path}, {e}")
        
        return True

    def _find_image_path(self, filename: str) -> Optional[str]:
        """
        在 history 目录中查找图片文件
        
        Args:
            filename: 文件名
            
        Returns:
            完整路径
        """
        # 遍历 history 目录下的所有 task_ 文件夹
        for item in os.listdir(self.history_dir):
            if item.startswith('task_'):
                task_dir = os.path.join(self.history_dir, item)
                img_path = os.path.join(task_dir, filename)
                if os.path.exists(img_path):
                    return img_path
        return None

    def list_records(
        self,
        page: int = 1,
        page_size: int = 20,
        status: Optional[str] = None
    ) -> Dict:
        """
        列出记录
        
        Args:
            page: 页码
            page_size: 每页数量
            status: 状态筛选
            
        Returns:
            包含 records, total, page, page_size, total_pages 的字典
        """
        return RecordModel.list(page=page, page_size=page_size, status=status)

    def search_records(self, keyword: str) -> List[Dict]:
        """
        搜索记录
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            记录列表
        """
        return RecordModel.search(keyword)

    def get_statistics(self) -> Dict:
        """
        获取统计信息
        
        Returns:
            统计数据
        """
        # 获取所有记录
        all_records = RecordModel.list(page=1, page_size=10000)
        
        total = all_records['total']
        status_count = {}
        
        for record in all_records['records']:
            status = record.get('status', 'draft')
            status_count[status] = status_count.get(status, 0) + 1
        
        return {
            "total": total,
            "by_status": status_count
        }

    def scan_and_sync_task_images(self, record_id: str) -> Dict[str, Any]:
        """
        扫描任务文件夹，同步图片列表（兼容迁移前的数据）
        
        Args:
            record_id: 记录ID
            
        Returns:
            扫描结果
        """
        task_dir = os.path.join(self.history_dir, record_id)

        if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
            return {
                "success": False,
                "error": f"任务目录不存在: {record_id}"
            }

        try:
            # 扫描目录下所有图片文件（排除缩略图）
            image_files = []
            for filename in os.listdir(task_dir):
                # 跳过缩略图文件（以 thumb_ 开头）
                if filename.startswith('thumb_'):
                    continue
                if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                    image_files.append(filename)

            # 按文件名排序
            image_files.sort()

            return {
                "success": True,
                "record_id": record_id,
                "images_count": len(image_files),
                "images": image_files
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"扫描任务失败: {str(e)}"
            }

    def scan_all_tasks(self) -> Dict[str, Any]:
        """
        扫描所有任务文件夹，同步图片列表（兼容迁移前的数据）
        
        Returns:
            扫描结果统计
        """
        if not os.path.exists(self.history_dir):
            return {
                "success": False,
                "error": "历史记录目录不存在"
            }

        try:
            synced_count = 0
            failed_count = 0
            results = []

            # 遍历 history 目录
            for item in os.listdir(self.history_dir):
                item_path = os.path.join(self.history_dir, item)

                # 只处理目录（任务文件夹）
                if not os.path.isdir(item_path):
                    continue

                # 假设任务文件夹名就是 record_id
                record_id = item

                # 扫描并同步
                result = self.scan_and_sync_task_images(record_id)
                results.append(result)

                if result.get("success"):
                    synced_count += 1
                else:
                    failed_count += 1

            return {
                "success": True,
                "total_tasks": len(results),
                "synced": synced_count,
                "failed": failed_count,
                "results": results
            }

        except Exception as e:
            return {
                "success": False,
                "error": f"扫描所有任务失败: {str(e)}"
            }


_service_instance = None


def get_history_service() -> HistoryService:
    global _service_instance
    if _service_instance is None:
        _service_instance = HistoryService()
    return _service_instance
