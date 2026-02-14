"""
AI转换提示词构建服务
用于构建第一人称到第三人称转换的提示词

根据设计文档要求：
- 第一人称转第三人称
- 保护引用内容（引号内容）
- 规范化时间表述
- 人称替换逻辑（我局/我司 -> 来源）
"""
import logging
from datetime import datetime, timedelta
from typing import Optional


logger = logging.getLogger(__name__)


class PromptBuilder:
    """提示词构建器"""
    
    def __init__(self):
        """初始化提示词构建器"""
        pass
    
    def build_transform_prompt(
        self,
        source_name: Optional[str] = None,
        reference_date: Optional[datetime] = None
    ) -> str:
        """
        构建第一人称到第三人称转换提示词
        
        Args:
            source_name: 来源名称，用于替换"我局"、"我司"等，如果为None则使用"该单位"
            reference_date: 参考日期，用于规范化相对时间表述，如果为None则使用当前日期
        
        Returns:
            系统提示词字符串
        """
        if source_name is None:
            source_name = "该单位"
        
        if reference_date is None:
            reference_date = datetime.now()
        
        # 格式化参考日期
        ref_date_str = reference_date.strftime("%Y年%m月%d日")
        
        prompt = f"""你是一个专业的内容编辑助手。你的任务是将第一人称叙述转换为第三人称叙述，同时保持内容的准确性和可读性。

**参考信息：**
- 来源单位：{source_name}
- 参考日期：{ref_date_str}（用于计算相对时间）

**转换规则：**

1. **人称转换**
   - 将"我"转换为"他/她"或具体的人名（如果上下文中有提及）
   - 将"我们"转换为"{source_name}"或"他们"
   - 将"我局"、"我司"、"我公司"、"我单位"等转换为"{source_name}"
   - 将"我的"转换为"其"或"该人的"
   - 保持第三人称的客观叙述风格

2. **引用内容保护**
   - 引号内的内容（包括单引号''、双引号""、中文引号「」『』）必须保持原样，不做任何修改
   - 引用的对话、语录、文献内容等必须完整保留

3. **时间表述规范化**
   - 将"今天"转换为具体日期（{ref_date_str}）
   - 将"昨天"转换为具体日期（计算为参考日期的前一天）
   - 将"明天"转换为具体日期（计算为参考日期的后一天）
   - 将"上周"、"本周"、"下周"转换为具体的周期范围
   - 将"上个月"、"本月"、"下个月"转换为具体的月份
   - 保持已有的具体日期格式不变

4. **语气和风格**
   - 保持原文的正式程度和专业性
   - 使用客观、中立的第三人称叙述
   - 不要改变原文的情感色彩和语气强度
   - 保持原文的逻辑结构和论述方式

5. **内容完整性**
   - 不要添加原文中没有的信息
   - 不要删除原文中的重要信息
   - 保持段落结构和格式
   - 保持列表、标题等结构化内容的格式

**输出要求：**
- 直接返回转换后的文本，不要添加任何解释、说明或元信息
- 不要使用"转换后："、"修改为："等前缀
- 不要添加"以上是转换结果"等后缀
- 只返回纯净的转换后文本内容"""
        
        return prompt
    
    def build_quote_protection_examples(self) -> str:
        """
        构建引用内容保护的示例
        
        Returns:
            包含示例的字符串
        """
        examples = """
**引用保护示例：**

原文：我说："这是一个重要的决定。"
转换：他说："这是一个重要的决定。"

原文：我们的口号是"团结就是力量"。
转换：该单位的口号是"团结就是力量"。

原文：我引用了《论语》中的"学而时习之"。
转换：他引用了《论语》中的"学而时习之"。
"""
        return examples
    
    def build_time_normalization_examples(self, reference_date: datetime) -> str:
        """
        构建时间规范化的示例
        
        Args:
            reference_date: 参考日期
        
        Returns:
            包含示例的字符串
        """
        today = reference_date.strftime("%Y年%m月%d日")
        yesterday = (reference_date - timedelta(days=1)).strftime("%Y年%m月%d日")
        tomorrow = (reference_date + timedelta(days=1)).strftime("%Y年%m月%d日")
        
        examples = f"""
**时间规范化示例：**

原文：我今天参加了会议。
转换：他于{today}参加了会议。

原文：我们昨天完成了项目。
转换：该单位于{yesterday}完成了项目。

原文：我明天将出差。
转换：他将于{tomorrow}出差。

原文：我上周提交了报告。
转换：他在上周提交了报告。（如果上下文需要更精确的日期，可以计算具体日期范围）
"""
        return examples
    
    def build_person_replacement_examples(self, source_name: str) -> str:
        """
        构建人称替换的示例
        
        Args:
            source_name: 来源名称
        
        Returns:
            包含示例的字符串
        """
        examples = f"""
**人称替换示例：**

原文：我局高度重视此项工作。
转换：{source_name}高度重视此项工作。

原文：我司致力于技术创新。
转换：{source_name}致力于技术创新。

原文：我们团队完成了任务。
转换：{source_name}团队完成了任务。

原文：我的观点是这样的。
转换：其观点是这样的。

原文：我认为这个方案可行。
转换：他认为这个方案可行。
"""
        return examples
    
    def build_enhanced_prompt(
        self,
        source_name: Optional[str] = None,
        reference_date: Optional[datetime] = None,
        include_examples: bool = True
    ) -> str:
        """
        构建增强版提示词（包含示例）
        
        Args:
            source_name: 来源名称
            reference_date: 参考日期
            include_examples: 是否包含示例
        
        Returns:
            增强版系统提示词
        """
        base_prompt = self.build_transform_prompt(source_name, reference_date)
        
        if not include_examples:
            return base_prompt
        
        if source_name is None:
            source_name = "该单位"
        
        if reference_date is None:
            reference_date = datetime.now()
        
        # 添加示例
        examples = "\n\n" + self.build_quote_protection_examples()
        examples += "\n" + self.build_time_normalization_examples(reference_date)
        examples += "\n" + self.build_person_replacement_examples(source_name)
        
        enhanced_prompt = base_prompt + examples
        
        return enhanced_prompt
    
    def extract_source_name_from_content(self, content: str) -> Optional[str]:
        """
        从内容中提取来源名称
        
        尝试识别内容中的组织名称，如"XX局"、"XX公司"、"XX单位"等
        
        Args:
            content: 原始内容
        
        Returns:
            提取的来源名称，如果无法提取则返回None
        """
        import re
        
        # 常见的组织后缀
        org_suffixes = [
            r'局', r'司', r'公司', r'单位', r'部门', r'处', r'科',
            r'委员会', r'中心', r'院', r'所', r'厅', r'办'
        ]
        
        # 构建正则表达式
        # 匹配"我局"、"我司"等后面可能出现的完整名称
        for suffix in org_suffixes:
            # 尝试匹配"XX局"、"XX公司"等模式
            pattern = rf'([^\s，。！？；：""'']{2,20}{suffix})'
            matches = re.findall(pattern, content)
            
            if matches:
                # 返回第一个匹配的组织名称
                logger.info(f"从内容中提取到来源名称: {matches[0]}")
                return matches[0]
        
        logger.info("无法从内容中提取来源名称，将使用默认值")
        return None
    
    def extract_reference_date_from_email(
        self,
        email_date: Optional[datetime] = None
    ) -> datetime:
        """
        从邮件日期提取参考日期
        
        Args:
            email_date: 邮件日期
        
        Returns:
            参考日期（如果邮件日期为None则返回当前日期）
        """
        if email_date is None:
            logger.info("邮件日期为空，使用当前日期作为参考日期")
            return datetime.now()
        
        logger.info(f"使用邮件日期作为参考日期: {email_date}")
        return email_date


# 全局提示词构建器实例
_prompt_builder: Optional[PromptBuilder] = None


def get_prompt_builder() -> PromptBuilder:
    """
    获取全局提示词构建器实例
    
    Returns:
        提示词构建器实例
    """
    global _prompt_builder
    
    if _prompt_builder is None:
        _prompt_builder = PromptBuilder()
    
    return _prompt_builder
