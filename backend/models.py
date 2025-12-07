"""数据库模型和 ORM 操作封装"""
import json
from datetime import datetime
from typing import Dict, List, Optional, Any
from backend.database import get_database


class RecordModel:
    """记录模型"""
    
    @staticmethod
    def create(
        record_id: str,
        title: str,
        topic: str,
        status: str = "draft",
        reference_images: Optional[List[str]] = None
    ) -> str:
        """
        创建记录
        
        Args:
            record_id: 记录 ID (UUID)
            title: 标题（AI 生成的小红书标题）
            topic: 用户输入的主题/需求
            status: 状态 (draft/completed)
            reference_images: 参考图片路径列表
            
        Returns:
            创建的记录 ID
        """
        db = get_database()
        now = datetime.now().isoformat()
        
        reference_images_json = json.dumps(reference_images or [], ensure_ascii=False)
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO records (id, title, topic, status, reference_images_json, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (record_id, title, topic, status, reference_images_json, now, now))
            conn.commit()
        
        return record_id
    
    @staticmethod
    def get(record_id: str) -> Optional[Dict]:
        """
        获取记录
        
        Args:
            record_id: 记录 ID
            
        Returns:
            记录数据字典
        """
        db = get_database()
        record = db.fetchone("SELECT * FROM records WHERE id = ?", (record_id,))
        
        if record:
            # 解析 JSON 字段
            if record.get('reference_images_json'):
                try:
                    record['reference_images'] = json.loads(record['reference_images_json'])
                except:
                    record['reference_images'] = []
            else:
                record['reference_images'] = []
        
        return record
    
    @staticmethod
    def update(
        record_id: str,
        title: Optional[str] = None,
        topic: Optional[str] = None,
        status: Optional[str] = None,
        reference_images: Optional[List[str]] = None
    ) -> bool:
        """
        更新记录
        
        Args:
            record_id: 记录 ID
            title: 标题
            topic: 主题
            status: 状态
            reference_images: 参考图片路径列表
            
        Returns:
            是否更新成功
        """
        db = get_database()
        now = datetime.now().isoformat()
        
        # 构建更新字段
        updates = ["updated_at = ?"]
        params = [now]
        
        if title is not None:
            updates.append("title = ?")
            params.append(title)
        
        if topic is not None:
            updates.append("topic = ?")
            params.append(topic)
        
        if status is not None:
            updates.append("status = ?")
            params.append(status)
        
        if reference_images is not None:
            updates.append("reference_images_json = ?")
            params.append(json.dumps(reference_images, ensure_ascii=False))
        
        params.append(record_id)
        
        query = f"UPDATE records SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, tuple(params))
        
        return True
    
    @staticmethod
    def delete(record_id: str) -> bool:
        """
        删除记录（级联删除相关数据）
        
        Args:
            record_id: 记录 ID
            
        Returns:
            是否删除成功
        """
        db = get_database()
        db.execute("DELETE FROM records WHERE id = ?", (record_id,))
        return True
    
    @staticmethod
    def list(
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
        db = get_database()
        
        # 构建查询条件
        where_clause = ""
        params = []
        
        if status:
            where_clause = "WHERE status = ?"
            params.append(status)
        
        # 查询总数
        count_query = f"SELECT COUNT(*) as count FROM records {where_clause}"
        count_result = db.fetchone(count_query, tuple(params) if params else None)
        total = count_result['count'] if count_result else 0
        
        # 查询分页数据
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        list_query = f"""
            SELECT * FROM records 
            {where_clause}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
        """
        records = db.fetchall(list_query, tuple(params))
        
        # 为每条记录添加 page_count 和 thumbnail
        for record in records:
            # 解析 reference_images
            if record.get('reference_images_json'):
                try:
                    record['reference_images'] = json.loads(record['reference_images_json'])
                except:
                    record['reference_images'] = []
            else:
                record['reference_images'] = []
            
            # 获取 page_count（通过 tone_id -> outline_id）
            # 先获取 tone_id
            tone = db.fetchone(
                "SELECT id FROM tones WHERE record_id = ? ORDER BY created_at DESC LIMIT 1",
                (record['id'],)
            )
            if tone:
                # 再获取 outline_id
                outline = db.fetchone(
                    "SELECT id FROM outlines WHERE tone_id = ? ORDER BY created_at DESC LIMIT 1",
                    (tone['id'],)
                )
                if outline:
                    page_count_result = db.fetchone(
                        "SELECT COUNT(*) as count FROM pages WHERE outline_id = ?",
                        (outline['id'],)
                    )
                    record['page_count'] = page_count_result['count'] if page_count_result else 0
                    
                    # 获取缩略图（从 cover 页面，返回原图文件名，前端通过 thumbnail=true 参数获取缩略图）
                    thumbnail_result = db.fetchone("""
                        SELECT i.filename 
                        FROM pages p
                        LEFT JOIN images i ON p.image_id = i.id
                        WHERE p.outline_id = ? AND p.page_type = 'cover'
                        LIMIT 1
                    """, (outline['id'],))
                    record['thumbnail'] = thumbnail_result['filename'] if thumbnail_result else None
                else:
                    record['page_count'] = 0
                    record['thumbnail'] = None
            else:
                record['page_count'] = 0
                record['thumbnail'] = None
        
        total_pages = (total + page_size - 1) // page_size
        
        return {
            "records": records,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages
        }
    
    @staticmethod
    def search(keyword: str) -> List[Dict]:
        """
        搜索记录
        
        Args:
            keyword: 搜索关键词
            
        Returns:
            记录列表
        """
        db = get_database()
        
        keyword_pattern = f"%{keyword}%"
        records = db.fetchall("""
            SELECT * FROM records 
            WHERE title LIKE ? OR topic LIKE ?
            ORDER BY created_at DESC
        """, (keyword_pattern, keyword_pattern))
        
        # 为每条记录添加额外信息
        for record in records:
            if record.get('reference_images_json'):
                try:
                    record['reference_images'] = json.loads(record['reference_images_json'])
                except:
                    record['reference_images'] = []
            else:
                record['reference_images'] = []
            
            # 获取 page_count（通过 tone_id -> outline_id）
            # 先获取 tone_id
            tone = db.fetchone(
                "SELECT id FROM tones WHERE record_id = ? ORDER BY created_at DESC LIMIT 1",
                (record['id'],)
            )
            if tone:
                # 再获取 outline_id
                outline = db.fetchone(
                    "SELECT id FROM outlines WHERE tone_id = ? ORDER BY created_at DESC LIMIT 1",
                    (tone['id'],)
                )
                if outline:
                    page_count_result = db.fetchone(
                        "SELECT COUNT(*) as count FROM pages WHERE outline_id = ?",
                        (outline['id'],)
                    )
                    record['page_count'] = page_count_result['count'] if page_count_result else 0
                    
                    # 获取缩略图（从 cover 页面，返回原图文件名，前端通过 thumbnail=true 参数获取缩略图）
                    thumbnail_result = db.fetchone("""
                        SELECT i.filename 
                        FROM pages p
                        LEFT JOIN images i ON p.image_id = i.id
                        WHERE p.outline_id = ? AND p.page_type = 'cover'
                        LIMIT 1
                    """, (outline['id'],))
                    record['thumbnail'] = thumbnail_result['filename'] if thumbnail_result else None
                else:
                    record['page_count'] = 0
                    record['thumbnail'] = None
            else:
                record['page_count'] = 0
                record['thumbnail'] = None
        
        return records


class ToneModel:
    """基调模型"""
    
    @staticmethod
    def create(record_id: str, tone_text: str) -> int:
        """
        创建基调
        
        Args:
            record_id: 记录 ID
            tone_text: 基调文本
            
        Returns:
            创建的基调 ID
        """
        db = get_database()
        now = datetime.now().isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tones (record_id, tone_text, created_at)
                VALUES (?, ?, ?)
            """, (record_id, tone_text, now))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_by_record(record_id: str) -> Optional[Dict]:
        """
        获取记录的基调
        
        Args:
            record_id: 记录 ID
            
        Returns:
            基调数据
        """
        db = get_database()
        return db.fetchone(
            "SELECT * FROM tones WHERE record_id = ? ORDER BY created_at DESC LIMIT 1",
            (record_id,)
        )
    
    @staticmethod
    def update(record_id: str, tone_text: str) -> bool:
        """
        更新基调（删除旧的，创建新的）
        
        Args:
            record_id: 记录 ID
            tone_text: 基调文本
            
        Returns:
            是否成功
        """
        db = get_database()
        
        # 删除旧的基调
        db.execute("DELETE FROM tones WHERE record_id = ?", (record_id,))
        
        # 创建新的基调
        ToneModel.create(record_id, tone_text)
        
        return True


class OutlineModel:
    """大纲模型"""
    
    @staticmethod
    def create(
        tone_id: int,
        raw_outline: str,
        metadata_title: Optional[str] = None,
        metadata_content: Optional[str] = None,
        metadata_tags: Optional[str] = None
    ) -> int:
        """
        创建大纲
        
        Args:
            tone_id: 基调 ID
            raw_outline: 原始大纲文本
            metadata_title: 小红书标题
            metadata_content: 小红书正文
            metadata_tags: 小红书标签
            
        Returns:
            创建的大纲 ID
        """
        db = get_database()
        now = datetime.now().isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO outlines (tone_id, raw_outline, metadata_title, metadata_content, metadata_tags, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (tone_id, raw_outline, metadata_title, metadata_content, metadata_tags, now))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_by_tone(tone_id: int) -> Optional[Dict]:
        """
        获取基调的大纲
        
        Args:
            tone_id: 基调 ID
            
        Returns:
            大纲数据
        """
        db = get_database()
        return db.fetchone(
            "SELECT * FROM outlines WHERE tone_id = ? ORDER BY created_at DESC LIMIT 1",
            (tone_id,)
        )
    
    @staticmethod
    def update(
        tone_id: int,
        raw_outline: Optional[str] = None,
        metadata_title: Optional[str] = None,
        metadata_content: Optional[str] = None,
        metadata_tags: Optional[str] = None
    ) -> bool:
        """
        更新大纲（通过 tone_id）
        
        Args:
            tone_id: 基调 ID
            raw_outline: 原始大纲文本
            metadata_title: 小红书标题
            metadata_content: 小红书正文
            metadata_tags: 小红书标签
            
        Returns:
            是否成功
        """
        db = get_database()
        
        # 获取现有大纲（通过 tone_id）
        existing = OutlineModel.get_by_tone(tone_id)
        if not existing:
            return False
        
        # 构建更新字段
        updates = []
        params = []
        
        if raw_outline is not None:
            updates.append("raw_outline = ?")
            params.append(raw_outline)
        
        if metadata_title is not None:
            updates.append("metadata_title = ?")
            params.append(metadata_title)
        
        if metadata_content is not None:
            updates.append("metadata_content = ?")
            params.append(metadata_content)
        
        if metadata_tags is not None:
            updates.append("metadata_tags = ?")
            params.append(metadata_tags)
        
        if not updates:
            return True
        
        params.append(existing['id'])
        
        query = f"UPDATE outlines SET {', '.join(updates)} WHERE id = ?"
        db.execute(query, tuple(params))
        
        return True
    
    @staticmethod
    def delete_by_tone(tone_id: int) -> bool:
        """
        删除基调关联的大纲（同时删除关联的页面）
        
        Args:
            tone_id: 基调 ID
            
        Returns:
            是否成功
        """
        db = get_database()
        
        # 先获取 outline_id
        outline = OutlineModel.get_by_tone(tone_id)
        if outline:
            # 删除关联的页面
            PageModel.delete_by_outline(outline['id'])
            # 删除大纲
            db.execute("DELETE FROM outlines WHERE id = ?", (outline['id'],))
        
        return True


class PageModel:
    """页面模型"""
    
    @staticmethod
    def create(
        outline_id: int,
        page_index: int,
        page_type: str,
        content: str,
        image_id: Optional[int] = None
    ) -> int:
        """
        创建页面
        
        Args:
            outline_id: 大纲 ID
            page_index: 页面索引
            page_type: 页面类型 (cover/content/summary)
            content: 页面内容
            image_id: 关联的图片 ID
            
        Returns:
            创建的页面 ID
        """
        db = get_database()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO pages (outline_id, page_index, page_type, content, image_id)
                VALUES (?, ?, ?, ?, ?)
            """, (outline_id, page_index, page_type, content, image_id))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_by_outline(outline_id: int) -> List[Dict]:
        """
        获取大纲的所有页面（包含关联的图片信息）
        
        Args:
            outline_id: 大纲 ID
            
        Returns:
            页面列表，每个页面包含图片信息（如果有）
        """
        db = get_database()
        pages = db.fetchall("""
            SELECT 
                p.id,
                p.outline_id,
                p.page_index,
                p.page_type,
                p.content,
                p.image_id,
                i.filename as image_filename,
                i.thumbnail_filename as image_thumbnail_filename,
                i.id as image_id_full
            FROM pages p
            LEFT JOIN images i ON p.image_id = i.id
            WHERE p.outline_id = ?
            ORDER BY p.page_index
        """, (outline_id,))
        
        # 整理返回数据，将图片信息整合到页面对象中
        result = []
        for page in pages:
            page_dict = {
                'id': page['id'],
                'outline_id': page['outline_id'],
                'page_index': page['page_index'],
                'page_type': page['page_type'],
                'content': page['content'],
                'image_id': page['image_id']
            }
            
            # 如果有图片信息，添加到页面对象中
            if page['image_filename']:
                page_dict['image'] = {
                    'id': page['image_id_full'],
                    'filename': page['image_filename'],
                    'thumbnail_filename': page['image_thumbnail_filename']
                }
            else:
                page_dict['image'] = None
            
            result.append(page_dict)
        
        return result
    
    @staticmethod
    def get_by_id(page_id: int) -> Optional[Dict]:
        """
        根据页面ID获取页面
        
        Args:
            page_id: 页面 ID
            
        Returns:
            页面数据
        """
        db = get_database()
        return db.fetchone(
            "SELECT * FROM pages WHERE id = ?",
            (page_id,)
        )
    
    @staticmethod
    def get_by_outline_and_index(outline_id: int, page_index: int) -> Optional[Dict]:
        """
        获取指定页面
        
        Args:
            outline_id: 大纲 ID
            page_index: 页面索引
            
        Returns:
            页面数据
        """
        db = get_database()
        return db.fetchone(
            "SELECT * FROM pages WHERE outline_id = ? AND page_index = ?",
            (outline_id, page_index)
        )
    
    @staticmethod
    def update(
        page_id: int,
        page_index: int,
        page_type: str,
        content: str,
        image_id: Optional[int] = None
    ) -> bool:
        """
        更新页面信息
        
        Args:
            page_id: 页面 ID
            page_index: 页面索引
            page_type: 页面类型
            content: 页面内容
            image_id: 关联的图片 ID
            
        Returns:
            是否成功
        """
        db = get_database()
        # 先检查页面是否存在
        existing_page = db.fetchone("SELECT id FROM pages WHERE id = ?", (page_id,))
        if not existing_page:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ 更新页面失败：页面不存在 page_id={page_id}")
            return False
        
        # 执行更新
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE pages 
                SET page_index = ?, page_type = ?, content = ?, image_id = ?
                WHERE id = ?
            """, (page_index, page_type, content, image_id, page_id))
            conn.commit()
            # 检查是否真的更新了行
            rows_affected = cursor.rowcount
            if rows_affected == 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ 更新页面失败：未更新任何行 page_id={page_id}")
                return False
        
        return True
    
    @staticmethod
    def update_image(page_id: int, image_id: int) -> bool:
        """
        更新页面的图片关联
        
        Args:
            page_id: 页面 ID
            image_id: 图片 ID
            
        Returns:
            是否成功
        """
        db = get_database()
        # 先检查页面是否存在
        existing_page = db.fetchone("SELECT id FROM pages WHERE id = ?", (page_id,))
        if not existing_page:
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(f"⚠️ 更新页面图片关联失败：页面不存在 page_id={page_id}, image_id={image_id}")
            return False
        
        # 执行更新
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE pages SET image_id = ? WHERE id = ?", (image_id, page_id))
            conn.commit()
            # 检查是否真的更新了行
            rows_affected = cursor.rowcount
            if rows_affected == 0:
                import logging
                logger = logging.getLogger(__name__)
                logger.warning(f"⚠️ 更新页面图片关联失败：未更新任何行 page_id={page_id}, image_id={image_id}")
                return False
        
        # 验证更新是否成功
        updated_page = db.fetchone("SELECT image_id FROM pages WHERE id = ?", (page_id,))
        if updated_page and updated_page.get('image_id') == image_id:
            return True
        else:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"❌ 更新页面图片关联验证失败：page_id={page_id}, 期望 image_id={image_id}, 实际 image_id={updated_page.get('image_id') if updated_page else None}")
            return False
    
    @staticmethod
    def delete_by_id(page_id: int) -> bool:
        """
        根据页面ID删除页面
        
        Args:
            page_id: 页面 ID
            
        Returns:
            是否成功
        """
        db = get_database()
        db.execute("DELETE FROM pages WHERE id = ?", (page_id,))
        return True
    
    @staticmethod
    def delete_by_outline(outline_id: int) -> bool:
        """
        删除大纲的所有页面
        
        Args:
            outline_id: 大纲 ID
            
        Returns:
            是否成功
        """
        db = get_database()
        db.execute("DELETE FROM pages WHERE outline_id = ?", (outline_id,))
        return True
    
    @staticmethod
    def bulk_create(pages: List[Dict]) -> List[int]:
        """
        批量创建页面
        
        Args:
            pages: 页面列表，每个元素包含 outline_id, page_index, page_type, content
            
        Returns:
            创建的页面 ID 列表
        """
        import logging
        logger = logging.getLogger(__name__)
        
        db = get_database()
        page_ids = []
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            for page in pages:
                cursor.execute("""
                    INSERT INTO pages (outline_id, page_index, page_type, content, image_id)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    page['outline_id'],
                    page['page_index'],
                    page['page_type'],
                    page['content'],
                    page.get('image_id')
                ))
                page_ids.append(cursor.lastrowid)
            conn.commit()
            
            # 🔥 重要：commit 后重新查询实际插入的 id，确保准确性
            if page_ids and pages:
                outline_id = pages[0]['outline_id']
                cursor.execute("""
                    SELECT id FROM pages 
                    WHERE outline_id = ? 
                    ORDER BY page_index
                """, (outline_id,))
                actual_ids = [row[0] for row in cursor.fetchall()]
                
                # 如果实际 id 和 lastrowid 不一致，使用实际 id
                if actual_ids != page_ids:
                    logger.warning(f"⚠️ bulk_create: lastrowid 不一致! lastrowid={page_ids}, 实际={actual_ids}")
                    page_ids = actual_ids
        
        logger.debug(f"📝 bulk_create: 创建了 {len(page_ids)} 个页面, ids={page_ids}")
        return page_ids


class ImageModel:
    """图片模型"""
    
    @staticmethod
    def create(
        record_id: str,
        filename: str,
        thumbnail_filename: str
    ) -> int:
        """
        创建图片记录
        
        Args:
            record_id: 记录 ID
            filename: 文件名
            thumbnail_filename: 缩略图文件名
            
        Returns:
            创建的图片 ID
        """
        db = get_database()
        now = datetime.now().isoformat()
        
        with db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO images (record_id, filename, thumbnail_filename, created_at)
                VALUES (?, ?, ?, ?)
            """, (record_id, filename, thumbnail_filename, now))
            conn.commit()
            return cursor.lastrowid
    
    @staticmethod
    def get_by_record(record_id: str) -> List[Dict]:
        """
        获取记录的所有图片
        
        Args:
            record_id: 记录 ID
            
        Returns:
            图片列表
        """
        db = get_database()
        return db.fetchall(
            "SELECT * FROM images WHERE record_id = ? ORDER BY created_at",
            (record_id,)
        )
    
    @staticmethod
    def get_by_filename(filename: str) -> Optional[Dict]:
        """
        通过文件名获取图片
        
        Args:
            filename: 文件名
            
        Returns:
            图片数据
        """
        db = get_database()
        return db.fetchone(
            "SELECT * FROM images WHERE filename = ?",
            (filename,)
        )
    
    @staticmethod
    def delete_by_record(record_id: str) -> bool:
        """
        删除记录的所有图片
        
        Args:
            record_id: 记录 ID
            
        Returns:
            是否成功
        """
        db = get_database()
        db.execute("DELETE FROM images WHERE record_id = ?", (record_id,))
        return True

