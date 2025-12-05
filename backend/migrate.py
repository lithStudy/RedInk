"""数据迁移脚本 - 将 JSON 数据迁移到 SQLite 数据库"""
import os
import json
import time
import random
import shutil
from pathlib import Path
from typing import Dict, List
from backend.database import get_database
from backend.models import RecordModel, ToneModel, OutlineModel, PageModel, ImageModel

def migrate_data():
    """执行数据迁移"""
    print("="*60)
    print("数据迁移脚本")
    print("将 JSON 文件数据迁移到 SQLite 数据库")
    print("="*60)
    print()
    
    # 获取 history 目录
    history_dir = Path(__file__).parent.parent / "history"
    if not history_dir.exists():
        print(f"❌ 历史记录目录不存在: {history_dir}")
        return
    
    # 初始化数据库
    print("📊 初始化数据库...")
    db = get_database()
    print("✅ 数据库初始化完成")
    print()
    
    # 读取 index.json
    index_file = history_dir / "index.json"
    if not index_file.exists():
        print(f"❌ index.json 不存在: {index_file}")
        return
    
    with open(index_file, 'r', encoding='utf-8') as f:
        index_data = json.load(f)
    
    records = index_data.get('records', [])
    print(f"📋 找到 {len(records)} 条记录")
    print()
    
    migrated_count = 0
    error_count = 0
    
    for record in records:
        record_id = record['id']
        task_id = record.get('task_id')
        
        print(f"处理记录: {record_id}")
        print(f"  标题: {record['title']}")
        print(f"  任务ID: {task_id}")
        
        try:
            # 读取记录详情 JSON
            record_file = history_dir / f"{record_id}.json"
            if not record_file.exists():
                print(f"  ⚠️  记录文件不存在: {record_file}")
                error_count += 1
                continue
            
            with open(record_file, 'r', encoding='utf-8') as f:
                record_detail = json.load(f)
            
            # 1. 创建 record
            outline_data = record_detail.get('outline', {})
            metadata = outline_data.get('metadata', {})
            
            RecordModel.create(
                record_id=record_id,
                title=record['title'],
                topic=outline_data.get('topic', record['title']),
                status=record.get('status', 'completed'),
                reference_images=None  # 旧数据没有参考图片记录
            )
            print(f"  ✅ 创建 record")
            
            # 2. 迁移 tone
            tone_id = None
            if task_id:
                task_dir = history_dir / task_id
                tone_file = task_dir / "tone.txt"
                if tone_file.exists():
                    with open(tone_file, 'r', encoding='utf-8') as f:
                        tone_text = f.read()
                    tone_id = ToneModel.create(record_id=record_id, tone_text=tone_text)
                    print(f"  ✅ 迁移 tone, tone_id={tone_id}")
            
            # 如果没有 tone，创建一个空的
            if not tone_id:
                tone_id = ToneModel.create(record_id=record_id, tone_text="")
                print(f"  ✅ 创建空 tone, tone_id={tone_id}")
            
            # 3. 迁移 outline（使用 tone_id）
            outline_id = OutlineModel.create(
                tone_id=tone_id,
                raw_outline=outline_data.get('raw', ''),
                metadata_title=metadata.get('title'),
                metadata_content=metadata.get('content'),
                metadata_tags=metadata.get('tags')
            )
            print(f"  ✅ 迁移 outline, tone_id={tone_id}, outline_id={outline_id}")
            
            # 4. 迁移 pages
            pages = outline_data.get('pages', [])
            for page in pages:
                PageModel.create(
                    outline_id=outline_id,
                    page_index=page['index'],
                    page_type=page['type'],
                    content=page['content'],
                    image_id=None  # 先创建，后面关联图片
                )
            print(f"  ✅ 迁移 {len(pages)} 个页面")
            
            # 5. 迁移并重命名图片
            if task_id:
                task_dir = history_dir / task_id
                if task_dir.exists() and task_dir.is_dir():
                    images_data = record_detail.get('images', {})
                    generated_images = images_data.get('generated', [])
                    
                    # 按文件名中的索引排序
                    def get_image_index(filename):
                        try:
                            return int(filename.split('.')[0])
                        except:
                            return 999
                    
                    generated_images.sort(key=get_image_index)
                    
                    for old_filename in generated_images:
                        old_path = task_dir / old_filename
                        if not old_path.exists():
                            continue
                        
                        # 提取页面索引
                        try:
                            page_index = int(old_filename.split('.')[0])
                        except:
                            print(f"    ⚠️  无法解析图片索引: {old_filename}")
                            continue
                        
                        # 生成新文件名
                        timestamp = int(time.time())
                        random_num = random.randint(1000, 9999)
                        new_filename = f"{record_id}_{timestamp}_{random_num}.png"
                        new_path = task_dir / new_filename
                        
                        # 重命名原图
                        shutil.move(str(old_path), str(new_path))
                        
                        # 重命名缩略图
                        old_thumb = task_dir / f"thumb_{old_filename}"
                        new_thumb_filename = f"thumb_{new_filename}"
                        new_thumb = task_dir / new_thumb_filename
                        if old_thumb.exists():
                            shutil.move(str(old_thumb), str(new_thumb))
                        
                        # 创建图片记录
                        image_id = ImageModel.create(
                            record_id=record_id,
                            filename=new_filename,
                            thumbnail_filename=new_thumb_filename
                        )
                        
                        # 更新 page 的 image_id
                        page = PageModel.get_by_outline_and_index(outline_id, page_index)
                        if page:
                            PageModel.update_image(page['id'], image_id)
                        
                        print(f"    ✅ 迁移图片: {old_filename} -> {new_filename}")
                    
                    print(f"  ✅ 迁移 {len(generated_images)} 张图片")
            
            # 6. 删除 JSON 文件
            record_file.unlink()
            print(f"  ✅ 删除 {record_file.name}")
            
            # 7. 删除 tone.txt 和 outline.json
            if task_id:
                task_dir = history_dir / task_id
                tone_file = task_dir / "tone.txt"
                if tone_file.exists():
                    tone_file.unlink()
                    print(f"  ✅ 删除 tone.txt")
                
                outline_file = task_dir / "outline.json"
                if outline_file.exists():
                    outline_file.unlink()
                    print(f"  ✅ 删除 outline.json")
            
            migrated_count += 1
            print(f"  ✅ 记录迁移完成")
            print()
            
        except Exception as e:
            print(f"  ❌ 迁移失败: {e}")
            error_count += 1
            print()
            continue
    
    # 删除 index.json
    try:
        index_file.unlink()
        print(f"✅ 删除 index.json")
    except Exception as e:
        print(f"⚠️  删除 index.json 失败: {e}")
    
    # 删除记录 ID 命名的 JSON 文件
    for json_file in history_dir.glob("*.json"):
        if json_file.name != "index.json":
            try:
                json_file.unlink()
                print(f"✅ 删除 {json_file.name}")
            except Exception as e:
                print(f"⚠️  删除 {json_file.name} 失败: {e}")
    
    print()
    print("="*60)
    print(f"迁移完成！")
    print(f"  成功: {migrated_count} 条")
    print(f"  失败: {error_count} 条")
    print("="*60)


if __name__ == "__main__":
    migrate_data()

