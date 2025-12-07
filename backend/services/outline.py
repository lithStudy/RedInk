import logging
import os
import re
import yaml
import uuid
import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from backend.utils.text_client import get_text_chat_client
from backend.models import RecordModel, ToneModel, OutlineModel, PageModel

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

    def generate_tone(self, topic: str, record_id: str) -> Dict[str, Any]:
        """
        生成内容基调并保存到数据库
        
        Args:
            topic: 用户输入的主题
            record_id: 记录 ID
            
        Returns:
            生成结果
        """
        try:
            logger.info(f"开始生成基调: topic={topic[:50]}..., record_id={record_id}")
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
            
            # 保存基调到数据库
            ToneModel.create(record_id=record_id, tone_text=tone_text)
            logger.info(f"基调已保存到数据库: record_id={record_id}")

            return {
                "success": True,
                "tone": tone_text
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
        record_id: str,
        images: Optional[List[bytes]] = None,
        tone: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        生成大纲并保存到数据库
        
        Args:
            topic: 用户输入的主题
            record_id: 记录 ID
            images: 参考图片列表
            tone: 内容基调
            
        Returns:
            生成结果
        """
        try:
            logger.info(f"开始生成大纲: topic={topic[:50]}..., record_id={record_id}, images={len(images) if images else 0}")
            
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
            logger.info(f"提取元数据: 标题={metadata.get('title', '')[:20]}..., 正文长度={len(metadata.get('content', ''))} 字符")

            # 创建 record_id 文件夹（用于存放图片）
            record_dir = os.path.join(self.history_root_dir, record_id)
            os.makedirs(record_dir, exist_ok=True)
            logger.info(f"创建记录目录: {record_dir}")

            # 获取或创建 tone
            tone_obj = ToneModel.get_by_record(record_id)
            if not tone_obj:
                # 如果没有 tone，需要先创建（如果提供了 tone 参数）
                if tone:
                    tone_id = ToneModel.create(record_id=record_id, tone_text=tone)
                    logger.info(f"基调已保存到数据库: record_id={record_id}, tone_id={tone_id}")
                else:
                    # 如果没有提供 tone，创建一个空的 tone
                    tone_id = ToneModel.create(record_id=record_id, tone_text="")
                    logger.info(f"创建空基调: record_id={record_id}, tone_id={tone_id}")
            else:
                tone_id = tone_obj['id']
                
                # 🔥 重要：先删除旧的大纲和页面（在更新 tone 之前）
                existing_outline = OutlineModel.get_by_tone(tone_id)
                if existing_outline:
                    logger.info(f"🗑️ 删除旧的大纲和页面: outline_id={existing_outline['id']}")
                    OutlineModel.delete_by_tone(tone_id)
                
                # 如果提供了新的 tone，更新它
                if tone and tone != tone_obj['tone_text']:
                    ToneModel.update(record_id=record_id, tone_text=tone)
                    # 🔥 重要：ToneModel.update 会删除旧 tone 并创建新 tone，需要重新获取 tone_id
                    tone_obj = ToneModel.get_by_record(record_id)
                    tone_id = tone_obj['id']
                    logger.info(f"更新基调: record_id={record_id}, new_tone_id={tone_id}")
            
            # 保存大纲到数据库（使用 tone_id）
            outline_id = OutlineModel.create(
                tone_id=tone_id,
                raw_outline=outline_text,
                metadata_title=metadata.get('title'),
                metadata_content=metadata.get('content'),
                metadata_tags=metadata.get('tags')
            )
            logger.info(f"大纲已保存到数据库: tone_id={tone_id}, outline_id={outline_id}")
            
            # 保存页面到数据库
            pages_data = [
                {
                    'outline_id': outline_id,
                    'page_index': page['index'],
                    'page_type': page['type'],
                    'content': page['content'],
                    'image_id': None
                }
                for page in pages
            ]
            page_ids = PageModel.bulk_create(pages_data)
            logger.info(f"页面已保存到数据库: {len(pages)} 页, page_ids={page_ids}")
            
            # 将数据库ID映射到对应的页面
            pages_with_ids = []
            for i, page in enumerate(pages):
                page_with_id = page.copy()
                page_with_id['id'] = page_ids[i] if i < len(page_ids) else None
                pages_with_ids.append(page_with_id)
            
            logger.info(f"✅ 返回给前端的 page_ids: {[p.get('id') for p in pages_with_ids]}")
            
            # 更新 record 的 title
            RecordModel.update(record_id=record_id, title=metadata.get('title'))

            return {
                "success": True,
                "outline": outline_text,
                "pages": pages_with_ids,
                "has_images": images is not None and len(images) > 0,
                "metadata": metadata
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

    def get_tone(self, record_id: str) -> Dict[str, Any]:
        """
        从数据库读取基调
        
        Args:
            record_id: 记录 ID
            
        Returns:
            基调数据
        """
        try:
            tone = ToneModel.get_by_record(record_id)
            
            if not tone:
                logger.warning(f"基调不存在: record_id={record_id}")
                return {
                    "success": False,
                    "error": "基调不存在"
                }
            
            logger.info(f"成功读取基调: record_id={record_id}")
            return {
                "success": True,
                "tone": tone['tone_text']
            }
        except Exception as e:
            error_msg = str(e)
            logger.error(f"读取基调失败: {error_msg}")
            return {
                "success": False,
                "error": f"读取基调失败: {error_msg}"
            }

    def update_tone(self, record_id: str, tone: str) -> Dict[str, Any]:
        """
        更新数据库中的基调
        
        Args:
            record_id: 记录 ID
            tone: 基调文本
            
        Returns:
            更新结果
        """
        try:
            ToneModel.update(record_id=record_id, tone_text=tone)
            logger.info(f"成功更新基调: record_id={record_id}")
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

    def update_outline(self, record_id: str, pages: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        更新数据库中的大纲页面
        
        Args:
            record_id: 记录 ID
            pages: 新的页面列表
            
        Returns:
            操作结果字典
        """
        try:
            # 获取 outline_id（通过 tone_id）
            tone = ToneModel.get_by_record(record_id)
            if not tone:
                return {
                    "success": False,
                    "error": "基调不存在"
                }
            outline = OutlineModel.get_by_tone(tone['id'])
            if not outline:
                return {
                    "success": False,
                    "error": "大纲不存在"
                }
            outline_id = outline['id']
            
            # 获取现有页面列表
            existing_pages = PageModel.get_by_outline(outline_id)
            existing_page_ids = {page['id'] for page in existing_pages}
            existing_page_by_id = {page['id']: page for page in existing_pages}
            
            # 收集新页面列表中的页面ID
            new_page_ids = set()
            for page in pages:
                if page.get('id'):
                    new_page_ids.add(page['id'])
            
            # 更新或创建页面
            for page in pages:
                page_id = page.get('id')
                image_id = None
                
                # 确定 image_id
                if page_id and page_id in existing_page_by_id:
                    # 如果页面已存在，保留原有的 image_id
                    image_id = existing_page_by_id[page_id].get('image_id')
                
                # 如果前端传递了 image.id，优先使用（用于更新图片关联）
                if isinstance(page.get('image'), dict) and page['image'].get('id'):
                    image_id = page['image']['id']
                
                if page_id and page_id in existing_page_ids:
                    # 更新现有页面
                    PageModel.update(
                        page_id=page_id,
                        page_index=page['index'],
                        page_type=page['type'],
                        content=page['content'],
                        image_id=image_id
                    )
                else:
                    # 创建新页面
                    PageModel.create(
                        outline_id=outline_id,
                        page_index=page['index'],
                        page_type=page['type'],
                        content=page['content'],
                        image_id=image_id
                    )
            
            # 删除不在新列表中的页面
            pages_to_delete = existing_page_ids - new_page_ids
            for page_id in pages_to_delete:
                PageModel.delete_by_id(page_id)
            
            # 重新生成 outline 文本
            outline_text = "\n\n<page>\n\n".join([page['content'] for page in pages])
            # 通过 outline 获取 tone_id
            tone_id = outline['tone_id']
            OutlineModel.update(tone_id=tone_id, raw_outline=outline_text)
            
            logger.info(f"成功更新大纲: record_id={record_id}")
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
