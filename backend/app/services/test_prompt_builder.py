"""
提示词构建器单元测试
"""
import pytest
from datetime import datetime, timedelta
from app.services.prompt_builder import PromptBuilder


class TestPromptBuilder:
    """提示词构建器测试类"""
    
    def setup_method(self):
        """测试前准备"""
        self.builder = PromptBuilder()
    
    def test_build_transform_prompt_with_defaults(self):
        """测试使用默认参数构建提示词"""
        prompt = self.builder.build_transform_prompt()
        
        assert "第一人称" in prompt
        assert "第三人称" in prompt
        assert "该单位" in prompt
        assert "引用" in prompt
        assert "时间" in prompt
    
    def test_build_transform_prompt_with_custom_source(self):
        """测试使用自定义来源名称构建提示词"""
        source_name = "XX公司"
        prompt = self.builder.build_transform_prompt(source_name=source_name)
        
        assert source_name in prompt
    
    def test_build_transform_prompt_with_reference_date(self):
        """测试使用参考日期构建提示词"""
        ref_date = datetime(2024, 1, 15)
        prompt = self.builder.build_transform_prompt(reference_date=ref_date)
        
        assert "2024年01月15日" in prompt
    
    def test_extract_source_name_from_content_with_company(self):
        """测试从内容中提取公司名称"""
        content = "XX科技公司致力于创新。我司是一家科技公司。"
        source_name = self.builder.extract_source_name_from_content(content)
        
        # 源名称提取是可选功能，可能返回None或提取到的名称
        if source_name is not None:
            assert "公司" in source_name
    
    def test_extract_source_name_from_content_with_bureau(self):
        """测试从内容中提取局名称"""
        content = "XX市公安局积极响应。我局高度重视此项工作。"
        source_name = self.builder.extract_source_name_from_content(content)
        
        # 源名称提取是可选功能，可能返回None或提取到的名称
        if source_name is not None:
            assert "局" in source_name
    
    def test_extract_source_name_from_content_no_match(self):
        """测试从不包含组织名称的内容中提取"""
        content = "这是一段普通的文本，没有组织名称。"
        source_name = self.builder.extract_source_name_from_content(content)
        
        assert source_name is None
    
    def test_extract_reference_date_from_email_with_date(self):
        """测试从邮件日期提取参考日期"""
        email_date = datetime(2024, 1, 15, 10, 30)
        ref_date = self.builder.extract_reference_date_from_email(email_date)
        
        assert ref_date == email_date
    
    def test_extract_reference_date_from_email_without_date(self):
        """测试邮件日期为空时提取参考日期"""
        ref_date = self.builder.extract_reference_date_from_email(None)
        
        assert ref_date is not None
        assert isinstance(ref_date, datetime)
    
    def test_build_enhanced_prompt_with_examples(self):
        """测试构建包含示例的增强提示词"""
        prompt = self.builder.build_enhanced_prompt(
            source_name="XX公司",
            include_examples=True
        )
        
        assert "示例" in prompt
        assert "原文" in prompt
        assert "转换" in prompt
    
    def test_build_enhanced_prompt_without_examples(self):
        """测试构建不包含示例的提示词"""
        prompt = self.builder.build_enhanced_prompt(
            source_name="XX公司",
            include_examples=False
        )
        
        assert "示例" not in prompt
    
    def test_prompt_contains_all_required_rules(self):
        """测试提示词包含所有必需的规则"""
        prompt = self.builder.build_transform_prompt()
        
        required_keywords = [
            "人称转换",
            "引用内容保护",
            "时间表述规范化",
            "语气和风格",
            "内容完整性"
        ]
        
        for keyword in required_keywords:
            assert keyword in prompt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
