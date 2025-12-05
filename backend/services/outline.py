import logging
import os
import re
import yaml
import uuid
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from backend.utils.text_client import get_text_chat_client

logger = logging.getLogger(__name__)


class OutlineService:
    def __init__(self):
        logger.debug("初始化 OutlineService...")
        self.text_config = self._load_text_config()
        self.client = self._get_client()
        self.prompt_template = self._load_prompt_template()
        
        # 历史记录根目录（与图片服务使用相同的目录）
        self.history_root_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "history"
        )
        os.makedirs(self.history_root_dir, exist_ok=True)
        
        logger.info(f"OutlineService 初始化完成，使用服务商: {self.text_config.get('active_provider')}")

    def _load_text_config(self) -> dict:
        """加载文本生成配置"""
        config_path = Path(__file__).parent.parent.parent / 'text_providers.yaml'
        logger.debug(f"加载文本配置: {config_path}")

        if config_path.exists():
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    config = yaml.safe_load(f) or {}
                logger.debug(f"文本配置加载成功: active={config.get('active_provider')}")
                return config
            except yaml.YAMLError as e:
                logger.error(f"文本配置 YAML 解析失败: {e}")
                raise ValueError(
                    f"文本配置文件格式错误: text_providers.yaml\n"
                    f"YAML 解析错误: {e}\n"
                    "解决方案：检查 YAML 缩进和语法"
                )

        logger.warning("text_providers.yaml 不存在，使用默认配置")
        # 默认配置
        return {
            'active_provider': 'google_gemini',
            'providers': {
                'google_gemini': {
                    'type': 'google_gemini',
                    'model': 'gemini-2.0-flash-exp',
                    'temperature': 1.0,
                    'max_output_tokens': 8000
                }
            }
        }

    def _get_client(self):
        """根据配置获取客户端"""
        active_provider = self.text_config.get('active_provider', 'google_gemini')
        providers = self.text_config.get('providers', {})

        if not providers:
            logger.error("未找到任何文本生成服务商配置")
            raise ValueError(
                "未找到任何文本生成服务商配置。\n"
                "解决方案：\n"
                "1. 在系统设置页面添加文本生成服务商\n"
                "2. 或手动编辑 text_providers.yaml 文件"
            )

        if active_provider not in providers:
            available = ', '.join(providers.keys())
            logger.error(f"文本服务商 [{active_provider}] 不存在，可用: {available}")
            raise ValueError(
                f"未找到文本生成服务商配置: {active_provider}\n"
                f"可用的服务商: {available}\n"
                "解决方案：在系统设置中选择一个可用的服务商"
            )

        provider_config = providers.get(active_provider, {})

        if not provider_config.get('api_key'):
            logger.error(f"文本服务商 [{active_provider}] 未配置 API Key")
            raise ValueError(
                f"文本服务商 {active_provider} 未配置 API Key\n"
                "解决方案：在系统设置页面编辑该服务商，填写 API Key"
            )

        logger.info(f"使用文本服务商: {active_provider} (type={provider_config.get('type')})")
        return get_text_chat_client(provider_config)

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "outline_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _load_tone_prompt_template(self) -> str:
        prompt_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "prompts",
            "tone_prompt.txt"
        )
        with open(prompt_path, "r", encoding="utf-8") as f:
            return f.read()

    def _parse_outline(self, outline_text: str) -> tuple[List[Dict[str, Any]], Dict[str, str]]:
        """
        解析大纲文本，提取标题、正文、标签和页面内容
        
        返回:
            tuple: (pages, metadata)
            - pages: 页面列表
            - metadata: 包含 title, content, tags 的字典
        """
        metadata = {
            "title": "",
            "content": "",
            "tags": ""
        }
        
        # 提取小红书标题、正文和标签
        title_match = re.search(r'【小红书标题】\s*\n+(.*?)(?=\n+【|<page>|\Z)', outline_text, re.DOTALL)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
            logger.debug(f"提取到标题: {metadata['title'][:50]}...")
        else:
            logger.warning("未找到【小红书标题】标记")
        
        content_match = re.search(r'【小红书正文】\s*\n+(.*?)(?=\n+【|<page>|\Z)', outline_text, re.DOTALL)
        if content_match:
            metadata["content"] = content_match.group(1).strip()
            logger.debug(f"提取到正文: {len(metadata['content'])} 字符")
        else:
            logger.warning("未找到【小红书正文】标记")
        
        tags_match = re.search(r'【小红书标签】\s*\n+(.*?)(?=\n+【|<page>|\Z)', outline_text, re.DOTALL)
        if tags_match:
            metadata["tags"] = tags_match.group(1).strip()
            logger.debug(f"提取到标签: {metadata['tags']}")
        else:
            logger.warning("未找到【小红书标签】标记")
        
        # 按 <page> 分割页面（兼容旧的 --- 分隔符）
        if '<page>' in outline_text:
            pages_raw = re.split(r'<page>', outline_text, flags=re.IGNORECASE)
        else:
            # 向后兼容：如果没有 <page> 则使用 ---
            pages_raw = outline_text.split("---")

        pages = []

        for index, page_text in enumerate(pages_raw):
            page_text = page_text.strip()
            if not page_text:
                continue
            
            # 如果页面文本包含【小红书标题】等标记，说明这是元数据部分，跳过
            if '【小红书标题】' in page_text or '【小红书正文】' in page_text or '【小红书标签】' in page_text:
                continue

            page_type = "content"
            type_match = re.match(r"\[(\S+)\]", page_text)
            if type_match:
                type_cn = type_match.group(1)
                type_mapping = {
                    "封面": "cover",
                    "内容": "content",
                    "总结": "summary",
                }
                page_type = type_mapping.get(type_cn, "content")

            pages.append({
                "index": index,
                "type": page_type,
                "content": page_text
            })

        return pages, metadata

    def generate_tone(self, topic: str) -> Dict[str, Any]:
        """生成内容基调"""
        try:
            logger.info(f"开始生成基调: topic={topic[:50]}...")
            tone_prompt_template = self._load_tone_prompt_template()
            prompt = tone_prompt_template.format(topic=topic)

            # 从配置中获取模型参数
            active_provider = self.text_config.get('active_provider', 'google_gemini')
            providers = self.text_config.get('providers', {})
            provider_config = providers.get(active_provider, {})

            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            logger.info(f"调用文本生成 API 生成基调: model={model}, temperature={temperature}")
            tone_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=None
            )

            logger.debug(f"基调生成完成，文本长度: {len(tone_text)} 字符")
            
            # 创建 taskId 和文件夹
            task_id = f"task_{uuid.uuid4().hex[:8]}"
            task_dir = os.path.join(self.history_root_dir, task_id)
            os.makedirs(task_dir, exist_ok=True)
            logger.info(f"创建任务目录: {task_dir}")

            # 保存基调到文件
            tone_file = os.path.join(task_dir, "tone.txt")
            with open(tone_file, "w", encoding="utf-8") as f:
                f.write(tone_text)
            logger.info(f"基调已保存到: {tone_file}")

            logger.info("基调生成成功")

            return {
                "success": True,
                "tone": tone_text,
                "task_id": task_id
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"基调生成失败: {error_msg}")

            # 根据错误类型提供更详细的错误信息
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 模型名称不正确\n"
                    "2. 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 网络连接不稳定\n"
                    "2. API 服务暂时不可用\n"
                    "3. Base URL 配置错误\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API 调用次数超限\n"
                    "2. 账户配额用尽\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"基调生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. Text API 配置错误或密钥无效\n"
                    "2. 网络连接问题\n"
                    "3. 模型无法访问或不存在\n"
                    "建议：检查配置文件 text_providers.yaml"
                )

            return {
                "success": False,
                "error": detailed_error
            }

    def generate_outline(
        self,
        topic: str,
        images: Optional[List[bytes]] = None,
        tone: Optional[str] = None,
        task_id: Optional[str] = None
    ) -> Dict[str, Any]:
        try:
            logger.info(f"开始生成大纲: topic={topic[:50]}..., images={len(images) if images else 0}, tone={'已提供' if tone else '未提供'}")
            
            # 格式化提示词（包含基调）
            prompt = self.prompt_template.format(
                tone=tone if tone else "未提供内容基调，请使用通用小红书风格",
                topic=topic
            )
            logger.debug("已将基调添加到提示词")

            if images and len(images) > 0:
                prompt += f"\n\n注意：用户提供了 {len(images)} 张参考图片，请在生成大纲时考虑这些图片的内容和风格。这些图片可能是产品图、个人照片或场景图，请根据图片内容来优化大纲，使生成的内容与图片相关联。"
                logger.debug(f"添加了 {len(images)} 张参考图片到提示词")

            # 从配置中获取模型参数
            active_provider = self.text_config.get('active_provider', 'google_gemini')
            providers = self.text_config.get('providers', {})
            provider_config = providers.get(active_provider, {})

            model = provider_config.get('model', 'gemini-2.0-flash-exp')
            temperature = provider_config.get('temperature', 1.0)
            max_output_tokens = provider_config.get('max_output_tokens', 8000)

            logger.info(f"调用文本生成 API: model={model}, temperature={temperature}")
            outline_text = self.client.generate_text(
                prompt=prompt,
                model=model,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                images=images
            )

            logger.debug(f"API 返回文本长度: {len(outline_text)} 字符")
            pages, metadata = self._parse_outline(outline_text)
            logger.info(f"大纲解析完成，共 {len(pages)} 页")
            logger.info(f"提取元数据: 标题={metadata.get('title', '')[:20]}..., 正文长度={len(metadata.get('content', ''))} 字符, 标签数={len(metadata.get('tags', '').split())}")

            # 创建 taskId 和文件夹（如果未提供 task_id，则创建新的）
            if not task_id:
                task_id = f"task_{uuid.uuid4().hex[:8]}"
            
            task_dir = os.path.join(self.history_root_dir, task_id)
            
            # 如果提供了 task_id 且目录已存在（说明是重新生成），清除旧的图片文件
            if task_id and os.path.exists(task_dir):
                self._clear_task_images(task_dir)
                logger.info(f"已清除任务目录中的旧图片: {task_dir}")
            
            os.makedirs(task_dir, exist_ok=True)
            logger.info(f"使用任务目录: {task_dir}")

            # 如果提供了基调，保存基调到文件
            if tone:
                tone_file = os.path.join(task_dir, "tone.txt")
                with open(tone_file, "w", encoding="utf-8") as f:
                    f.write(tone)
                logger.info(f"基调已保存到: {tone_file}")

            # 保存大纲内容到文件夹
            outline_data = {
                "topic": topic,
                "outline": outline_text,
                "pages": pages,
                "has_images": images is not None and len(images) > 0,
                "metadata": metadata  # 保存元数据
            }
            outline_file = os.path.join(task_dir, "outline.json")
            with open(outline_file, "w", encoding="utf-8") as f:
                json.dump(outline_data, f, ensure_ascii=False, indent=2)
            logger.info(f"大纲已保存到: {outline_file}")

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages,
                "has_images": images is not None and len(images) > 0,
                "task_id": task_id,
                "metadata": metadata  # 返回元数据
            }

        except Exception as e:
            error_msg = str(e)
            logger.error(f"大纲生成失败: {error_msg}")

            # 根据错误类型提供更详细的错误信息
            if "api_key" in error_msg.lower() or "unauthorized" in error_msg.lower() or "401" in error_msg:
                detailed_error = (
                    f"API 认证失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API Key 无效或已过期\n"
                    "2. API Key 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查并更新 API Key"
                )
            elif "model" in error_msg.lower() or "404" in error_msg:
                detailed_error = (
                    f"模型访问失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 模型名称不正确\n"
                    "2. 没有访问该模型的权限\n"
                    "解决方案：在系统设置页面检查模型名称配置"
                )
            elif "timeout" in error_msg.lower() or "连接" in error_msg:
                detailed_error = (
                    f"网络连接失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. 网络连接不稳定\n"
                    "2. API 服务暂时不可用\n"
                    "3. Base URL 配置错误\n"
                    "解决方案：检查网络连接，稍后重试"
                )
            elif "rate" in error_msg.lower() or "429" in error_msg or "quota" in error_msg.lower():
                detailed_error = (
                    f"API 配额限制。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. API 调用次数超限\n"
                    "2. 账户配额用尽\n"
                    "解决方案：等待配额重置，或升级 API 套餐"
                )
            else:
                detailed_error = (
                    f"大纲生成失败。\n"
                    f"错误详情: {error_msg}\n"
                    "可能原因：\n"
                    "1. Text API 配置错误或密钥无效\n"
                    "2. 网络连接问题\n"
                    "3. 模型无法访问或不存在\n"
                    "建议：检查配置文件 text_providers.yaml"
                )

            return {
                "success": False,
                "error": detailed_error
            }

    def get_tone(self, task_id: str) -> Dict[str, Any]:
        """从任务目录读取基调"""
        try:
            task_dir = os.path.join(self.history_root_dir, task_id)
            tone_file = os.path.join(task_dir, "tone.txt")
            
            if not os.path.exists(tone_file):
                logger.warning(f"基调文件不存在: {tone_file}")
                return {
                    "success": False,
                    "error": "基调文件不存在"
                }
            
            with open(tone_file, "r", encoding="utf-8") as f:
                tone_text = f.read()
            
            logger.info(f"成功读取基调: {tone_file}")
            return {
                "success": True,
                "tone": tone_text
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"读取基调失败: {error_msg}")
            return {
                "success": False,
                "error": f"读取基调失败: {error_msg}"
            }

    def update_tone(self, task_id: str, tone: str) -> Dict[str, Any]:
        """更新任务目录中的基调"""
        try:
            task_dir = os.path.join(self.history_root_dir, task_id)
            
            if not os.path.exists(task_dir):
                logger.warning(f"任务目录不存在: {task_dir}")
                return {
                    "success": False,
                    "error": "任务目录不存在"
                }
            
            tone_file = os.path.join(task_dir, "tone.txt")
            with open(tone_file, "w", encoding="utf-8") as f:
                f.write(tone)
            
            logger.info(f"成功更新基调: {tone_file}")
            return {
                "success": True
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"更新基调失败: {error_msg}")
            return {
                "success": False,
                "error": f"更新基调失败: {error_msg}"
            }

    def _clear_task_images(self, task_dir: str):
        """
        清除任务目录中的图片文件（包括原图和缩略图）
        
        Args:
            task_dir: 任务目录路径
        """
        try:
            if not os.path.exists(task_dir):
                return
            
            # 遍历目录中的所有文件
            for filename in os.listdir(task_dir):
                file_path = os.path.join(task_dir, filename)
                
                # 只删除图片文件（包括缩略图），保留其他文件（如 outline.json, tone.txt）
                if filename.endswith(('.png', '.jpg', '.jpeg')):
                    try:
                        os.remove(file_path)
                        logger.debug(f"已删除图片文件: {filename}")
                    except Exception as e:
                        logger.warning(f"删除图片文件失败: {filename}, {e}")
        except Exception as e:
            logger.error(f"清除任务图片失败: {task_dir}, {e}")

    def update_outline(self, task_id: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        更新任务的大纲（例如删除页面后）
        
        该方法会：
        1. 更新 outline.json 文件
        2. 重命名现有的图片文件以匹配新的页面索引
        
        Args:
            task_id: 任务ID
            pages: 新的页面列表
        
        Returns:
            操作结果字典
        """
        try:
            task_dir = os.path.join(self.history_root_dir, task_id)
            
            if not os.path.exists(task_dir):
                logger.warning(f"任务目录不存在: {task_dir}")
                return {
                    "success": False,
                    "error": "任务目录不存在"
                }
            
            outline_file = os.path.join(task_dir, "outline.json")
            
            if not os.path.exists(outline_file):
                logger.warning(f"大纲文件不存在: {outline_file}")
                return {
                    "success": False,
                    "error": "大纲文件不存在"
                }
            
            # 读取现有的大纲文件
            with open(outline_file, "r", encoding="utf-8") as f:
                outline_data = json.load(f)
            
            # 保存旧的页面索引映射（oldIndex -> newIndex）
            old_pages = outline_data.get("pages", [])
            old_to_new_index = {}
            
            # 创建旧索引集合
            old_indices = {p["index"] for p in old_pages}
            new_indices = {p["index"] for p in pages}
            
            # 找出被删除的页面索引
            deleted_indices = old_indices - new_indices
            
            # 构建索引映射
            for new_page in pages:
                new_index = new_page["index"]
                # 在旧页面中找到相同内容的页面
                for old_page in old_pages:
                    if old_page["content"] == new_page["content"] and old_page["type"] == new_page["type"]:
                        old_to_new_index[old_page["index"]] = new_index
                        break
            
            logger.info(f"页面索引映射: {old_to_new_index}")
            logger.info(f"删除的页面索引: {deleted_indices}")
            
            # 重命名图片文件
            # 先将需要重命名的文件移动到临时名称，避免冲突
            temp_renames = []
            for old_index, new_index in old_to_new_index.items():
                if old_index != new_index:
                    # 处理原图
                    old_file = os.path.join(task_dir, f"{old_index}.png")
                    if os.path.exists(old_file):
                        temp_file = os.path.join(task_dir, f"temp_{old_index}.png")
                        os.rename(old_file, temp_file)
                        temp_renames.append((temp_file, os.path.join(task_dir, f"{new_index}.png")))
                        logger.debug(f"重命名图片: {old_index}.png -> temp_{old_index}.png")
                    
                    # 处理缩略图
                    old_thumb = os.path.join(task_dir, f"thumb_{old_index}.png")
                    if os.path.exists(old_thumb):
                        temp_thumb = os.path.join(task_dir, f"temp_thumb_{old_index}.png")
                        os.rename(old_thumb, temp_thumb)
                        temp_renames.append((temp_thumb, os.path.join(task_dir, f"thumb_{new_index}.png")))
                        logger.debug(f"重命名缩略图: thumb_{old_index}.png -> temp_thumb_{old_index}.png")
            
            # 执行最终重命名
            for temp_file, final_file in temp_renames:
                os.rename(temp_file, final_file)
                logger.debug(f"完成重命名: {os.path.basename(temp_file)} -> {os.path.basename(final_file)}")
            
            # 删除被删除页面的图片文件
            for deleted_index in deleted_indices:
                deleted_file = os.path.join(task_dir, f"{deleted_index}.png")
                if os.path.exists(deleted_file):
                    os.remove(deleted_file)
                    logger.info(f"删除图片: {deleted_index}.png")
                
                deleted_thumb = os.path.join(task_dir, f"thumb_{deleted_index}.png")
                if os.path.exists(deleted_thumb):
                    os.remove(deleted_thumb)
                    logger.info(f"删除缩略图: thumb_{deleted_index}.png")
            
            # 更新大纲数据
            outline_data["pages"] = pages
            
            # 重新生成 outline 文本
            outline_text = "\n\n<page>\n\n".join([page["content"] for page in pages])
            outline_data["outline"] = outline_text
            
            # 保存更新后的大纲文件
            with open(outline_file, "w", encoding="utf-8") as f:
                json.dump(outline_data, f, ensure_ascii=False, indent=2)
            
            logger.info(f"成功更新大纲: {outline_file}")
            return {
                "success": True
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"更新大纲失败: {error_msg}")
            return {
                "success": False,
                "error": f"更新大纲失败: {error_msg}"
            }


def get_outline_service() -> OutlineService:
    """
    获取大纲生成服务实例
    每次调用都创建新实例以确保配置是最新的
    """
    return OutlineService()
