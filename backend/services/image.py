"""图片生成服务"""
import logging
import os
import uuid
import time
import random
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, Any, Generator, List, Optional, Tuple
from backend.config import Config
from backend.generators.factory import ImageGeneratorFactory
from backend.utils.image_compressor import compress_image
from backend.models import ToneModel, OutlineModel, PageModel, ImageModel, RecordModel

logger = logging.getLogger(__name__)


class ImageService:
    """图片生成服务类"""

    # 并发配置
    MAX_CONCURRENT = 15  # 最大并发数
    AUTO_RETRY_COUNT = 3  # 自动重试次数

    # 任务停止标志
    _stop_flags: Dict[str, bool] = {}

    def __init__(self, provider_name: str = None):
        """
        初始化图片生成服务

        Args:
            provider_name: 服务商名称，如果为None则使用配置文件中的激活服务商
        """
        logger.debug("初始化 ImageService...")

        # 获取服务商配置
        if provider_name is None:
            provider_name = Config.get_active_image_provider()

        logger.info(f"使用图片服务商: {provider_name}")
        provider_config = Config.get_image_provider_config(provider_name)

        # 创建生成器实例
        provider_type = provider_config.get('type', provider_name)
        logger.debug(f"创建生成器: type={provider_type}")
        self.generator = ImageGeneratorFactory.create(provider_type, provider_config)

        # 保存配置信息
        self.provider_name = provider_name
        self.provider_config = provider_config

        # 检查是否启用短 prompt 模式
        self.use_short_prompt = provider_config.get('short_prompt', False)

        # 加载提示词模板
        self.prompt_template = self._load_prompt_template()
        self.prompt_template_short = self._load_prompt_template(short=True)

        # 历史记录根目录
        self.history_root_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_root_dir, exist_ok=True)

        # 当前任务的输出目录（每个任务一个子文件夹）
        self.current_task_dir = None

        # 存储任务状态（用于重试）
        self._task_states: Dict[str, Dict] = {}

        logger.info(f"ImageService 初始化完成: provider={provider_name}, type={provider_type}")

    def _load_prompt_template(self, short: bool = False) -> str:
        """加载 Prompt 模板"""
        filename = "image_prompt_short.txt" if short else "image_prompt.txt"
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            filename
        )
        if not os.path.exists(prompt_path):
            # 如果短模板不存在，返回空字符串
            return ""
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_tone_from_record(self, record_id: str) -> Optional[str]:
        """从数据库加载内容基调"""
        try:
            tone = ToneModel.get_by_record(record_id)
            if tone:
                logger.info(f"成功加载基调: record_id={record_id}")
                return tone['tone_text']
            logger.debug(f"基调不存在: record_id={record_id}")
            return None
        except Exception as e:
            logger.warning(f"加载基调失败: {e}")
            return None

    def _save_image(self, image_data: bytes, record_id: str, page_index: int, task_dir: str = None) -> Tuple[str, str, int]:
        """
        保存图片到本地并写入数据库，同时生成缩略图
        
        Args:
            image_data: 图片二进制数据
            record_id: 记录 ID
            page_index: 页面索引
            task_dir: 任务目录（如果为None则使用当前任务目录）
            
        Returns:
            (文件路径, 文件名, 图片ID)
        """
        if task_dir is None:
            task_dir = self.current_task_dir

        if task_dir is None:
            raise ValueError("任务目录未设置")

        # 生成新的文件名：{record_id}_{timestamp}_{random}.png
        timestamp = int(time.time())
        random_num = random.randint(1000, 9999)
        filename = f"{record_id}_{timestamp}_{random_num}.png"
        thumbnail_filename = f"thumb_{filename}"

        # 保存原图
        filepath = os.path.join(task_dir, filename)
        with open(filepath, "wb") as f:
            f.write(image_data)

        # 生成缩略图（50KB左右）
        thumbnail_data = compress_image(image_data, max_size_kb=50)
        thumbnail_path = os.path.join(task_dir, thumbnail_filename)
        with open(thumbnail_path, "wb") as f:
            f.write(thumbnail_data)
        
        # 保存到数据库
        image_id = ImageModel.create(
            record_id=record_id,
            filename=filename,
            thumbnail_filename=thumbnail_filename
        )
        
        # 更新 page 的 image_id
        # 先获取 tone_id，再获取 outline_id
        tone = ToneModel.get_by_record(record_id)
        if tone:
            outline = OutlineModel.get_by_tone(tone['id'])
            if outline:
                page = PageModel.get_by_outline_and_index(outline['id'], page_index)
                if page:
                    PageModel.update_image(page['id'], image_id)
        
        logger.info(f"图片已保存: filename={filename}, image_id={image_id}")

        return filepath, filename, image_id

    def _generate_single_image(
        self,
        page: Dict,
        record_id: str,
        reference_image: Optional[bytes] = None,
        retry_count: int = 0,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = "",
        tone: Optional[str] = None
    ) -> Tuple[int, bool, Optional[str], Optional[str]]:
        """
        生成单张图片（带自动重试）

        Args:
            page: 页面数据
            record_id: 记录ID
            reference_image: 参考图片（封面图）
            retry_count: 当前重试次数
            full_outline: 完整的大纲文本
            user_images: 用户上传的参考图片列表
            user_topic: 用户原始输入

        Returns:
            (index, success, filename, error_message)
        """
        index = page["index"]
        page_type = page["type"]
        page_content = page["content"]

        max_retries = self.AUTO_RETRY_COUNT

        for attempt in range(max_retries):
            try:
                logger.debug(f"生成图片 [{index}]: type={page_type}, attempt={attempt + 1}/{max_retries}")

                # 根据配置选择模板（短 prompt 或完整 prompt）
                if self.use_short_prompt and self.prompt_template_short:
                    # 短 prompt 模式：只包含页面类型和内容
                    prompt = self.prompt_template_short.format(
                        page_content=page_content,
                        page_type=page_type
                    )
                    logger.debug(f"  使用短 prompt 模式 ({len(prompt)} 字符)")
                else:
                    # 完整 prompt 模式：包含基调、大纲和用户需求
                    prompt = self.prompt_template.format(
                        tone=tone if tone else "未提供内容基调，请使用通用小红书风格",
                        page_content=page_content,
                        page_type=page_type,
                        full_outline=full_outline,
                        user_topic=user_topic if user_topic else "未提供"
                    )

                # 调用生成器生成图片
                if self.provider_config.get('type') == 'google_genai':
                    logger.debug(f"  使用 Google GenAI 生成器")
                    image_data = self.generator.generate_image(
                        prompt=prompt,
                        aspect_ratio=self.provider_config.get('default_aspect_ratio', '3:4'),
                        temperature=self.provider_config.get('temperature', 1.0),
                        model=self.provider_config.get('model', 'gemini-3-pro-image-preview'),
                        reference_image=reference_image,
                    )
                elif self.provider_config.get('type') == 'image_api':
                    logger.debug(f"  使用 Image API 生成器")
                    # Image API 支持多张参考图片
                    # 根据参考图模式组合参考图片
                    reference_images = []
                    # 如果提供了 reference_image，使用它（cover 或 previous 模式）
                    if reference_image:
                        reference_images.append(reference_image)
                    # 如果提供了 user_images，也添加它们（custom 模式或作为补充）
                    if user_images:
                        reference_images.extend(user_images)

                    image_data = self.generator.generate_image(
                        prompt=prompt,
                        aspect_ratio=self.provider_config.get('default_aspect_ratio', '3:4'),
                        temperature=self.provider_config.get('temperature', 1.0),
                        model=self.provider_config.get('model', 'nano-banana-2'),
                        reference_images=reference_images if reference_images else None,
                    )
                else:
                    logger.debug(f"  使用 OpenAI 兼容生成器")
                    image_data = self.generator.generate_image(
                        prompt=prompt,
                        size=self.provider_config.get('default_size', '1024x1024'),
                        model=self.provider_config.get('model'),
                        quality=self.provider_config.get('quality', 'standard'),
                    )

                # 保存图片（使用当前任务目录）并写入数据库
                filepath, filename, image_id = self._save_image(image_data, record_id, index, self.current_task_dir)
                logger.info(f"✅ 图片 [{index}] 生成成功: {filename}, image_id={image_id}")

                return (index, True, filename, None)

            except Exception as e:
                error_msg = str(e)
                logger.warning(f"图片 [{index}] 生成失败 (尝试 {attempt + 1}/{max_retries}): {error_msg[:200]}")

                if attempt < max_retries - 1:
                    # 等待后重试
                    wait_time = 2 ** attempt
                    logger.debug(f"  等待 {wait_time} 秒后重试...")
                    time.sleep(wait_time)
                    continue

                logger.error(f"❌ 图片 [{index}] 生成失败，已达最大重试次数")
                return (index, False, None, error_msg)

        return (index, False, None, "超过最大重试次数")

    def generate_images(
        self,
        pages: list,
        record_id: str,
        full_outline: str = "",
        user_images: Optional[List[bytes]] = None,
        user_topic: str = "",
        reference_mode: str = "cover"
    ) -> Generator[Dict[str, Any], None, None]:
        """
        生成图片（生成器，支持 SSE 流式返回）
        优化版本：先生成封面，然后并发生成其他页面

        Args:
            pages: 页面列表
            record_id: 记录 ID（必填，同时用作文件夹路径）
            full_outline: 完整的大纲文本（用于保持风格一致）
            user_images: 用户上传的参考图片列表（可选）
            user_topic: 用户原始输入（用于保持意图一致）
            reference_mode: 参考图模式 (cover/previous/custom)

        Yields:
            进度事件字典
        """
        logger.info(f"开始图片生成任务: record_id={record_id}, pages={len(pages)}")

        # 创建记录专属目录
        self.current_task_dir = os.path.join(self.history_root_dir, record_id)
        os.makedirs(self.current_task_dir, exist_ok=True)
        logger.debug(f"记录目录: {self.current_task_dir}")

        # 加载内容基调
        tone = self._load_tone_from_record(record_id)
        if tone:
            logger.info("✅ 已加载内容基调，将应用于图片生成")
        else:
            logger.info("⚠️ 未找到内容基调，将使用默认风格")

        total = len(pages)
        generated_images = []
        failed_pages = []
        cover_image_data = None

        # 压缩用户上传的参考图到200KB以内（减少内存和传输开销）
        compressed_user_images = None
        if user_images:
            compressed_user_images = [compress_image(img, max_size_kb=200) for img in user_images]

        # 初始化任务状态
        self._task_states[record_id] = {
            "pages": pages,
            "generated": {},
            "failed": {},
            "cover_image": None,
            "full_outline": full_outline,
            "user_images": compressed_user_images,
            "user_topic": user_topic
        }

        # ==================== 第一阶段：生成封面 ====================
        cover_page = None
        other_pages = []

        for page in pages:
            if page["type"] == "cover":
                cover_page = page
            else:
                other_pages.append(page)

        # 如果没有封面，使用第一页作为封面
        if cover_page is None and len(pages) > 0:
            cover_page = pages[0]
            other_pages = pages[1:]

        if cover_page:
            # 发送封面生成进度（包含 record_id，让前端可以立即使用）
            yield {
                "event": "progress",
                                "data": {
                                    "index": cover_page["index"],
                                    "status": "generating",
                                    "message": "正在生成封面...",
                                    "current": 1,
                                    "total": total,
                                    "phase": "cover",
                                    "record_id": record_id
                                }
            }

            # 生成封面（使用用户上传的图片作为参考）
            index, success, filename, error = self._generate_single_image(
                cover_page, record_id, reference_image=None, full_outline=full_outline,
                user_images=compressed_user_images, user_topic=user_topic, tone=tone
            )

            if success:
                generated_images.append(filename)
                self._task_states[record_id]["generated"][index] = filename

                # 读取封面图片作为参考，并立即压缩到200KB以内
                cover_path = os.path.join(self.current_task_dir, filename)
                with open(cover_path, "rb") as f:
                    cover_image_data = f.read()

                # 压缩封面图（减少内存占用和后续传输开销）
                cover_image_data = compress_image(cover_image_data, max_size_kb=200)
                self._task_states[record_id]["cover_image"] = cover_image_data

                yield {
                        "event": "complete",
                        "data": {
                            "index": index,
                            "status": "done",
                            "image_url": f"/api/images/{record_id}/{filename}",
                            "phase": "cover"
                        }
                }
            else:
                failed_pages.append(cover_page)
                self._task_states[record_id]["failed"][index] = error

                yield {
                    "event": "error",
                    "data": {
                        "index": index,
                        "status": "error",
                        "message": error,
                        "retryable": True,
                        "phase": "cover"
                    }
                }

        # ==================== 第二阶段：生成其他页面 ====================
        if other_pages:
            # 检查是否被停止
            if self.is_task_stopped(record_id):
                yield {
                    "event": "stopped",
                    "data": {
                        "record_id": record_id,
                        "message": "生成已停止",
                        "completed": len(generated_images),
                        "pending": len(other_pages)
                    }
                }
                return

            # 检查是否启用高并发模式
            high_concurrency = self.provider_config.get('high_concurrency', False)

            if high_concurrency:
                # 高并发模式：并行生成
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始并发生成 {len(other_pages)} 页内容...",
                        "current": len(generated_images),
                        "total": total,
                        "phase": "content",
                        "record_id": record_id
                    }
                }

                # 使用线程池并发生成
                with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
                    # 提交所有任务
                    def get_ref_for_page(page_idx: int) -> Optional[bytes]:
                        """根据参考图模式获取当前页面的参考图"""
                        if reference_mode == 'custom':
                            # 使用自定义参考图（用户上传的图片）
                            if compressed_user_images and len(compressed_user_images) > 0:
                                return compressed_user_images[0]
                            return None
                        elif reference_mode == 'cover':
                            # 使用封面参考
                            return cover_image_data
                        elif reference_mode == 'previous':
                            # 使用上一张参考（当前页面的前一张已生成的图片）
                            prev_idx = page_idx - 1
                            while prev_idx >= 0:
                                prev_path = os.path.join(self.current_task_dir, f"{prev_idx}.png")
                                if os.path.exists(prev_path):
                                    with open(prev_path, "rb") as f:
                                        prev_data = f.read()
                                    return compress_image(prev_data, max_size_kb=200)
                                prev_idx -= 1
                            # 如果没有找到前一张，回退到封面
                            return cover_image_data
                        else:
                            return cover_image_data

                future_to_page = {
                    executor.submit(
                        self._generate_single_image,
                        page,
                        record_id,
                        get_ref_for_page(page["index"]),  # 根据模式获取参考图
                        0,  # retry_count
                        full_outline,  # 传入完整大纲
                        compressed_user_images if reference_mode == 'custom' else None,  # 只在custom模式传递user_images
                        user_topic,  # 用户原始输入
                        tone  # 内容基调
                    ): page
                    for page in other_pages
                }

                # 发送每个页面的进度
                for page in other_pages:
                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "current": len(generated_images) + 1,
                            "total": total,
                            "phase": "content"
                        }
                    }

                # 收集结果
                for future in as_completed(future_to_page):
                        # 检查是否被停止
                        if self.is_task_stopped(record_id):
                            # 取消剩余任务
                            for f in future_to_page:
                                f.cancel()
                            yield {
                                "event": "stopped",
                                "data": {
                                    "record_id": record_id,
                                    "message": "生成已停止",
                                    "completed": len(generated_images),
                                    "pending": total - len(generated_images)
                                }
                            }
                            return

                        page = future_to_page[future]
                        try:
                            index, success, filename, error = future.result()

                            if success:
                                generated_images.append(filename)
                                self._task_states[record_id]["generated"][index] = filename

                                yield {
                                    "event": "complete",
                                    "data": {
                                        "index": index,
                                        "status": "done",
                                        "image_url": f"/api/images/{record_id}/{filename}",
                                        "phase": "content"
                                    }
                                }
                            else:
                                failed_pages.append(page)
                                self._task_states[record_id]["failed"][index] = error

                                yield {
                                    "event": "error",
                                    "data": {
                                        "index": index,
                                        "status": "error",
                                        "message": error,
                                        "retryable": True,
                                        "phase": "content"
                                    }
                                }

                        except Exception as e:
                            failed_pages.append(page)
                            error_msg = str(e)
                            self._task_states[record_id]["failed"][page["index"]] = error_msg

                            yield {
                                "event": "error",
                                "data": {
                                    "index": page["index"],
                                    "status": "error",
                                    "message": error_msg,
                                    "retryable": True,
                                    "phase": "content"
                                }
                            }
            else:
                # 顺序模式：逐个生成
                yield {
                    "event": "progress",
                    "data": {
                        "status": "batch_start",
                        "message": f"开始顺序生成 {len(other_pages)} 页内容...",
                        "current": len(generated_images),
                        "total": total,
                        "phase": "content",
                        "task_id": record_id
                    }
                }

                for page in other_pages:
                    # 检查是否被停止
                    if self.is_task_stopped(record_id):
                        yield {
                            "event": "stopped",
                            "data": {
                                "record_id": record_id,
                                "message": "生成已停止",
                                "completed": len(generated_images),
                                "pending": total - len(generated_images)
                            }
                        }
                        return

                    # 发送生成进度
                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "current": len(generated_images) + 1,
                            "total": total,
                            "phase": "content"
                        }
                    }

                    # 根据参考图模式获取参考图
                    def get_ref_for_page(page_idx: int) -> Optional[bytes]:
                        """根据参考图模式获取当前页面的参考图"""
                        if reference_mode == 'custom':
                            # 使用自定义参考图（用户上传的图片）
                            if compressed_user_images and len(compressed_user_images) > 0:
                                return compressed_user_images[0]
                            return None
                        elif reference_mode == 'cover':
                            # 使用封面参考
                            return cover_image_data
                        elif reference_mode == 'previous':
                            # 使用上一张参考（当前页面的前一张已生成的图片）
                            prev_idx = page_idx - 1
                            while prev_idx >= 0:
                                prev_path = os.path.join(self.current_task_dir, f"{prev_idx}.png")
                                if os.path.exists(prev_path):
                                    with open(prev_path, "rb") as f:
                                        prev_data = f.read()
                                    return compress_image(prev_data, max_size_kb=200)
                                prev_idx -= 1
                            # 如果没有找到前一张，回退到封面
                            return cover_image_data
                        else:
                            return cover_image_data

                    # 生成单张图片
                    index, success, filename, error = self._generate_single_image(
                        page,
                        record_id,
                        get_ref_for_page(page["index"]),  # 根据模式获取参考图
                        0,
                        full_outline,
                        compressed_user_images if reference_mode == 'custom' else None,  # 只在custom模式传递user_images
                        user_topic,
                        tone  # 内容基调
                    )

                    if success:
                        generated_images.append(filename)
                        self._task_states[record_id]["generated"][index] = filename

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{record_id}/{filename}",
                                "phase": "content"
                            }
                        }
                    else:
                        failed_pages.append(page)
                        self._task_states[record_id]["failed"][index] = error

                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True,
                                "phase": "content"
                            }
                        }

        # ==================== 完成 ====================
        yield {
            "event": "finish",
            "data": {
                "success": len(failed_pages) == 0,
                "record_id": record_id,
                "images": generated_images,
                "total": total,
                "completed": len(generated_images),
                "failed": len(failed_pages),
                "failed_indices": [p["index"] for p in failed_pages]
            }
        }

    def _get_reference_image_by_mode(
        self,
        record_id: str,
        page_index: int,
        reference_mode: str,
        task_state: Optional[Dict] = None
    ) -> Optional[bytes]:
        """
        根据参考图模式获取参考图片

        Args:
            record_id: 记录ID
            page_index: 当前页面索引
            reference_mode: 参考图模式（'custom' | 'cover' | 'previous'）
            task_state: 任务状态（可选）

        Returns:
            参考图片的二进制数据，如果没有则返回 None
        """
        if reference_mode == 'custom':
            # 使用自定义参考图（用户上传的图片）
            if task_state:
                user_images = task_state.get("user_images")
                if user_images and len(user_images) > 0:
                    # 返回第一张用户上传的图片
                    return user_images[0]
            return None

        elif reference_mode == 'cover':
            # 使用封面参考
            if task_state:
                cover_image = task_state.get("cover_image")
                if cover_image:
                    return cover_image

            # 从文件系统加载封面图
            cover_path = os.path.join(self.current_task_dir, "0.png")
            if os.path.exists(cover_path):
                with open(cover_path, "rb") as f:
                    cover_data = f.read()
                return compress_image(cover_data, max_size_kb=200)
            return None

        elif reference_mode == 'previous':
            # 使用上一张参考（当前页面的前一张已生成的图片）
            # 查找前一张已生成的图片
            prev_index = page_index - 1
            while prev_index >= 0:
                prev_image_path = os.path.join(self.current_task_dir, f"{prev_index}.png")
                if os.path.exists(prev_image_path):
                    with open(prev_image_path, "rb") as f:
                        prev_data = f.read()
                    return compress_image(prev_data, max_size_kb=200)
                prev_index -= 1

            # 如果没有找到前一张，回退到封面
            cover_path = os.path.join(self.current_task_dir, "0.png")
            if os.path.exists(cover_path):
                with open(cover_path, "rb") as f:
                    cover_data = f.read()
                return compress_image(cover_data, max_size_kb=200)
            return None

        else:
            # 默认使用封面
            return self._get_reference_image_by_mode(record_id, page_index, 'cover', task_state)

    def retry_single_image(
        self,
        record_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        reference_mode: str = "cover"
    ) -> Dict[str, Any]:
        """
        重试生成单张图片

        Args:
            record_id: 记录ID
            page: 页面数据
            use_reference: 是否使用参考图
            full_outline: 完整大纲文本（从前端传入）
            user_topic: 用户原始输入（从前端传入）
            reference_mode: 参考图模式（'custom' | 'cover' | 'previous'）

        Returns:
            生成结果
        """
        self.current_task_dir = os.path.join(self.history_root_dir, record_id)
        os.makedirs(self.current_task_dir, exist_ok=True)

        reference_image = None
        user_images = None
        task_state = None

        # 加载内容基调
        tone_data = self._load_tone_from_record(record_id)

        # 首先尝试从任务状态中获取上下文
        if record_id in self._task_states:
            task_state = self._task_states[record_id]
            # 如果没有传入上下文，则使用任务状态中的
            if not full_outline:
                full_outline = task_state.get("full_outline", "")
            if not user_topic:
                user_topic = task_state.get("user_topic", "")
            user_images = task_state.get("user_images")

        # 根据模式获取参考图
        if use_reference:
            reference_image = self._get_reference_image_by_mode(
                record_id, page["index"], reference_mode, task_state
            )

        index, success, filename, error = self._generate_single_image(
            page,
            record_id,
            reference_image,
            0,
            full_outline,
            user_images,
            user_topic,
            tone_data
        )

        if success:
            if record_id in self._task_states:
                self._task_states[record_id]["generated"][index] = filename
                if index in self._task_states[record_id]["failed"]:
                    del self._task_states[record_id]["failed"][index]

            return {
                "success": True,
                "index": index,
                "image_url": f"/api/images/{record_id}/{filename}"
            }
        else:
            return {
                "success": False,
                "index": index,
                "error": error,
                "retryable": True
            }

    def retry_failed_images(
        self,
        record_id: str,
        pages: List[Dict]
    ) -> Generator[Dict[str, Any], None, None]:
        """
        批量重试失败的图片

        Args:
            record_id: 记录ID
            pages: 需要重试的页面列表

        Yields:
            进度事件
        """
        # 获取参考图
        reference_image = None
        if record_id in self._task_states:
            reference_image = self._task_states[record_id].get("cover_image")

        total = len(pages)
        success_count = 0
        failed_count = 0

        yield {
            "event": "retry_start",
            "data": {
                "total": total,
                "message": f"开始重试 {total} 张失败的图片"
            }
        }

        # 并发重试
        # 从任务状态中获取完整大纲
        full_outline = ""
        user_topic = ""
        if record_id in self._task_states:
            full_outline = self._task_states[record_id].get("full_outline", "")
            user_topic = self._task_states[record_id].get("user_topic", "")

        # 加载内容基调
        tone = self._load_tone_from_record(record_id)

        with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
            future_to_page = {
                executor.submit(
                    self._generate_single_image,
                    page,
                    record_id,
                    reference_image,
                    0,  # retry_count
                    full_outline,  # 传入完整大纲
                    None,  # user_images
                    user_topic,  # 用户原始输入
                    tone  # 内容基调
                ): page
                for page in pages
            }

            for future in as_completed(future_to_page):
                page = future_to_page[future]
                try:
                    index, success, filename, error = future.result()

                    if success:
                        success_count += 1
                        if record_id in self._task_states:
                            self._task_states[record_id]["generated"][index] = filename
                            if index in self._task_states[record_id]["failed"]:
                                del self._task_states[record_id]["failed"][index]

                        yield {
                            "event": "complete",
                            "data": {
                                "index": index,
                                "status": "done",
                                "image_url": f"/api/images/{record_id}/{filename}"
                            }
                        }
                    else:
                        failed_count += 1
                        yield {
                            "event": "error",
                            "data": {
                                "index": index,
                                "status": "error",
                                "message": error,
                                "retryable": True
                            }
                        }

                except Exception as e:
                    failed_count += 1
                    yield {
                        "event": "error",
                        "data": {
                            "index": page["index"],
                            "status": "error",
                            "message": str(e),
                            "retryable": True
                        }
                    }

        yield {
            "event": "retry_finish",
            "data": {
                "success": failed_count == 0,
                "total": total,
                "completed": success_count,
                "failed": failed_count
            }
        }

    def regenerate_image(
        self,
        record_id: str,
        page: Dict,
        use_reference: bool = True,
        full_outline: str = "",
        user_topic: str = "",
        reference_mode: str = "cover"
    ) -> Dict[str, Any]:
        """
        重新生成图片（用户手动触发，即使成功的也可以重新生成）

        Args:
            record_id: 记录ID
            page: 页面数据
            use_reference: 是否使用封面作为参考
            full_outline: 完整大纲文本
            user_topic: 用户原始输入
            reference_mode: 参考图模式（'custom' | 'cover' | 'previous'）

        Returns:
            生成结果
        """
        return self.retry_single_image(
            record_id, page, use_reference,
            full_outline=full_outline,
            user_topic=user_topic,
            reference_mode=reference_mode
        )

    def get_image_path(self, record_id: str, filename: str) -> str:
        """
        获取图片完整路径

        Args:
            record_id: 记录ID
            filename: 文件名

        Returns:
            完整路径
        """
        record_dir = os.path.join(self.history_root_dir, record_id)
        return os.path.join(record_dir, filename)

    def get_task_state(self, record_id: str) -> Optional[Dict]:
        """获取任务状态"""
        return self._task_states.get(record_id)

    def cleanup_task(self, record_id: str):
        """清理任务状态（释放内存）"""
        if record_id in self._task_states:
            del self._task_states[record_id]

    def stop_task(self, record_id: str) -> bool:
        """
        停止指定记录的图片生成

        Args:
            record_id: 记录ID

        Returns:
            是否成功设置停止标志
        """
        ImageService._stop_flags[record_id] = True
        logger.info(f"⏹️ 记录 {record_id} 已请求停止")
        return True

    def is_task_stopped(self, record_id: str) -> bool:
        """检查记录是否被停止"""
        return ImageService._stop_flags.get(record_id, False)

    def clear_stop_flag(self, record_id: str):
        """清除停止标志"""
        if record_id in ImageService._stop_flags:
            del ImageService._stop_flags[record_id]

    def load_outline_from_record(self, record_id: str) -> Optional[Dict]:
        """
        从数据库加载大纲信息

        Args:
            record_id: 记录ID

        Returns:
            大纲数据字典，包含 topic, outline, pages 等
        """
        try:
            # 先获取 tone_id，再获取 outline
            tone = ToneModel.get_by_record(record_id)
            if not tone:
                logger.warning(f"基调不存在: record_id={record_id}")
                return None
            
            outline = OutlineModel.get_by_tone(tone['id'])
            if not outline:
                logger.warning(f"大纲不存在: record_id={record_id}")
                return None
            
            # 获取页面（通过 outline_id）
            pages = PageModel.get_by_outline(outline['id'])
            
            # 获取记录信息
            record = RecordModel.get(record_id)
            
            outline_data = {
                'topic': record['topic'] if record else '',
                'outline': outline['raw_outline'],
                'pages': [
                    {
                        'index': p['page_index'],
                        'type': p['page_type'],
                        'content': p['content']
                    }
                    for p in pages
                ],
                'has_images': bool(record and record.get('reference_images')),
                'metadata': {
                    'title': outline['metadata_title'],
                    'content': outline['metadata_content'],
                    'tags': outline['metadata_tags']
                }
            }
            
            logger.info(f"成功加载大纲: record_id={record_id}")
            return outline_data
        except Exception as e:
            logger.error(f"加载大纲失败: {e}")
            return None

    def scan_generated_images(self, task_id: str) -> set:
        """
        扫描任务文件夹中已生成的图片

        Args:
            task_id: 任务ID

        Returns:
            已生成的图片索引集合
        """
        task_dir = os.path.join(self.history_root_dir, task_id)
        if not os.path.exists(task_dir):
            return set()

        generated_indices = set()
        for filename in os.listdir(task_dir):
            # 跳过非图片文件和缩略图
            if filename.startswith('thumb_') or filename == 'outline.json':
                continue
            if filename.endswith('.png') or filename.endswith('.jpg') or filename.endswith('.jpeg'):
                # 提取索引（文件名格式：{index}.png）
                try:
                    index = int(filename.split('.')[0])
                    generated_indices.add(index)
                except ValueError:
                    continue

        return generated_indices

    def get_pending_pages(self, task_id: str) -> List[Dict]:
        """
        获取未完成的页面列表（从文件夹扫描）

        Args:
            task_id: 任务ID

        Returns:
            未完成的页面列表
        """
        # 加载大纲（task_id 和 record_id 相同）
        outline_data = self.load_outline_from_record(task_id)
        if not outline_data:
            logger.warning(f"无法加载大纲，task_id: {task_id}")
            return []

        all_pages = outline_data.get("pages", [])
        if not all_pages:
            return []

        # 扫描已生成的图片
        generated_indices = self.scan_generated_images(task_id)
        logger.info(f"任务 {task_id} 已生成图片索引: {generated_indices}")

        # 返回未生成的页面
        pending_pages = [p for p in all_pages if p["index"] not in generated_indices]
        logger.info(f"任务 {task_id} 待生成页面数: {len(pending_pages)}")
        return pending_pages

    def continue_generation(
        self,
        record_id: str,
        pages: List[Dict] = None,
        full_outline: str = "",
        user_topic: str = ""
    ) -> Generator[Dict[str, Any], None, None]:
        """
        继续生成图片（从未完成的页面继续）

        Args:
            record_id: 记录ID
            pages: 要生成的页面列表（如果为空则自动获取未完成的页面）
            full_outline: 完整大纲文本
            user_topic: 用户原始输入

        Yields:
            进度事件字典
        """
        # 清除停止标志
        self.clear_stop_flag(record_id)

        # 设置记录目录
        self.current_task_dir = os.path.join(self.history_root_dir, record_id)
        os.makedirs(self.current_task_dir, exist_ok=True)

        # 从数据库加载大纲信息
        outline_data = self.load_outline_from_record(record_id)
        if not outline_data:
            yield {
                "event": "error",
                "data": {
                    "message": f"无法加载记录大纲，record_id: {record_id}",
                    "retryable": False
                }
            }
            return

        # 如果没有传入页面，自动扫描未完成的页面
        if pages is None or len(pages) == 0:
            pages = self.get_pending_pages(record_id)

        if len(pages) == 0:
            # 扫描已生成的图片列表
            generated_indices = self.scan_generated_images(record_id)
            generated_images = [f"{idx}.png" for idx in sorted(generated_indices)]
            
            yield {
                "event": "finish",
                "data": {
                    "success": True,
                    "task_id": record_id,
                    "images": generated_images,
                    "total": len(outline_data.get("pages", [])),
                    "completed": len(generated_indices),
                    "failed": 0,
                    "failed_indices": [],
                    "message": "没有需要生成的页面"
                }
            }
            return

        logger.info(f"▶️ 继续任务 {record_id}，待生成 {len(pages)} 页")

        # 从大纲数据中获取上下文
        if not full_outline:
            full_outline = outline_data.get("outline", "")
        if not user_topic:
            user_topic = outline_data.get("topic", "")

        # 加载内容基调
        tone = self._load_tone_from_record(record_id)
        if tone:
            logger.info("✅ 已加载内容基调，将应用于图片生成")
        else:
            logger.info("⚠️ 未找到内容基调，将使用默认风格")

        # 获取参考图片（从文件系统加载封面图）
        reference_image = None
        cover_path = os.path.join(self.current_task_dir, "0.png")
        if os.path.exists(cover_path):
            with open(cover_path, "rb") as f:
                cover_data = f.read()
            reference_image = compress_image(cover_data, max_size_kb=200)
        
        # 用户上传的图片暂时不支持从文件恢复（需要前端传入）
        user_images = None

        # 获取总页数和已生成数量
        all_pages = outline_data.get("pages", [])
        total_pages = len(all_pages)
        generated_indices = self.scan_generated_images(record_id)
        generated_count = len(generated_indices)

        # 如果没有封面图，尝试从文件系统加载
        if reference_image is None:
            cover_path = os.path.join(self.current_task_dir, "0.png")
            if os.path.exists(cover_path):
                with open(cover_path, "rb") as f:
                    cover_data = f.read()
                reference_image = compress_image(cover_data, max_size_kb=200)
                # 保存到任务状态
                if record_id in self._task_states:
                    self._task_states[record_id]["cover_image"] = reference_image

        failed_pages = []

        yield {
            "event": "continue_start",
            "data": {
                "task_id": record_id,
                "pending_count": len(pages),
                "total": total_pages,
                "completed": generated_count,
                "message": f"继续生成 {len(pages)} 张图片"
            }
        }

        # 检查是否启用高并发模式
        high_concurrency = self.provider_config.get('high_concurrency', False)

        if high_concurrency:
            # 高并发模式
            with ThreadPoolExecutor(max_workers=self.MAX_CONCURRENT) as executor:
                future_to_page = {
                    executor.submit(
                        self._generate_single_image,
                        page,
                        record_id,
                        reference_image,
                        0,
                        full_outline,
                        user_images,
                        user_topic,
                        tone
                    ): page
                    for page in pages
                }

                # 发送每个页面的进度
                for page in pages:
                    yield {
                        "event": "progress",
                        "data": {
                            "index": page["index"],
                            "status": "generating",
                            "current": generated_count + 1,
                            "total": total_pages,
                            "phase": "continue"
                        }
                    }

                for future in as_completed(future_to_page):
                    # 检查是否被停止
                    if self.is_task_stopped(record_id):
                        # 取消剩余任务
                        for f in future_to_page:
                            f.cancel()
                        # 重新扫描已生成的图片
                        current_generated = self.scan_generated_images(record_id)
                        yield {
                            "event": "stopped",
                            "data": {
                                "task_id": record_id,
                                "message": "生成已停止",
                                "completed": len(current_generated),
                                "pending": total_pages - len(current_generated)
                            }
                        }
                        return

                    page = future_to_page[future]
                    try:
                        index, success, filename, error = future.result()

                        if success:
                            generated_count += 1
                            if record_id in self._task_states:
                                self._task_states[record_id]["generated"][index] = filename

                            yield {
                                "event": "complete",
                                "data": {
                                    "index": index,
                                    "status": "done",
                                    "image_url": f"/api/images/{record_id}/{filename}",
                                    "phase": "continue"
                                }
                            }
                        else:
                            failed_pages.append(page)
                            if record_id in self._task_states:
                                self._task_states[record_id]["failed"][index] = error

                            yield {
                                "event": "error",
                                "data": {
                                    "index": index,
                                    "status": "error",
                                    "message": error,
                                    "retryable": True,
                                    "phase": "continue"
                                }
                            }

                    except Exception as e:
                        failed_pages.append(page)
                        error_msg = str(e)
                        if record_id in self._task_states:
                            self._task_states[record_id]["failed"][page["index"]] = error_msg

                        yield {
                            "event": "error",
                            "data": {
                                "index": page["index"],
                                "status": "error",
                                "message": error_msg,
                                "retryable": True,
                                "phase": "continue"
                            }
                        }
        else:
            # 顺序模式
            for page in pages:
                # 检查是否被停止
                if self.is_task_stopped(record_id):
                    # 重新扫描已生成的图片
                    current_generated = self.scan_generated_images(record_id)
                    yield {
                        "event": "stopped",
                        "data": {
                            "task_id": record_id,
                            "message": "生成已停止",
                            "completed": len(current_generated),
                            "pending": total_pages - len(current_generated)
                        }
                    }
                    return

                yield {
                    "event": "progress",
                    "data": {
                        "index": page["index"],
                        "status": "generating",
                        "current": generated_count + 1,
                        "total": total_pages,
                        "phase": "continue"
                    }
                }

                index, success, filename, error = self._generate_single_image(
                    page,
                    record_id,
                    reference_image,
                    0,
                    full_outline,
                    user_images,
                    user_topic,
                    tone
                )

                if success:
                    generated_count += 1
                    if record_id in self._task_states:
                        self._task_states[record_id]["generated"][index] = filename

                    yield {
                        "event": "complete",
                        "data": {
                            "index": index,
                            "status": "done",
                            "image_url": f"/api/images/{record_id}/{filename}",
                            "phase": "continue"
                        }
                    }
                else:
                    failed_pages.append(page)
                    if record_id in self._task_states:
                        self._task_states[record_id]["failed"][index] = error

                    yield {
                        "event": "error",
                        "data": {
                            "index": index,
                            "status": "error",
                            "message": error,
                            "retryable": True,
                            "phase": "continue"
                        }
                    }

        # 完成 - 从文件夹扫描所有已生成的图片
        final_generated_indices = self.scan_generated_images(record_id)
        all_generated = [f"{idx}.png" for idx in sorted(final_generated_indices)]
        
        yield {
            "event": "finish",
            "data": {
                "success": len(failed_pages) == 0,
                "task_id": record_id,
                "images": all_generated,
                "total": total_pages,
                "completed": len(all_generated),
                "failed": len(failed_pages),
                "failed_indices": [p["index"] for p in failed_pages]
            }
        }


# 全局服务实例
_service_instance = None

def get_image_service() -> ImageService:
    """获取全局图片生成服务实例"""
    global _service_instance
    if _service_instance is None:
        _service_instance = ImageService()
    return _service_instance

def reset_image_service():
    """重置全局服务实例（配置更新后调用）"""
    global _service_instance
    _service_instance = None
