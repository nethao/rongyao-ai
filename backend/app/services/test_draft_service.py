"""
草稿服务单元测试
"""
import pytest
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base
from app.models.submission import Submission
from app.models.draft import Draft, DraftVersion
from app.models.user import User
from app.services.draft_service import DraftService


# 测试数据库配置
TEST_DATABASE_URL = "sqlite+aiosqlite:///:memory:"


@pytest.fixture
async def db_session():
    """创建测试数据库会话"""
    engine = create_async_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )
    
    async with async_session() as session:
        yield session
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    
    await engine.dispose()


@pytest.fixture
async def sample_submission(db_session):
    """创建示例投稿"""
    submission = Submission(
        email_subject="测试邮件",
        email_from="test@example.com",
        email_date=datetime.now(),
        original_content="这是原始内容。我认为这个方案很好。",
        status="completed"
    )
    db_session.add(submission)
    await db_session.commit()
    await db_session.refresh(submission)
    return submission


@pytest.fixture
async def sample_user(db_session):
    """创建示例用户"""
    user = User(
        username="testuser",
        password_hash="hashed_password",
        role="editor"
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.mark.asyncio
class TestDraftService:
    """草稿服务测试类"""
    
    async def test_create_draft_success(self, db_session, sample_submission):
        """测试成功创建草稿"""
        service = DraftService(db_session)
        transformed_content = "这是转换后的内容。他认为这个方案很好。"
        
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content=transformed_content
        )
        
        assert draft.id is not None
        assert draft.submission_id == sample_submission.id
        assert draft.current_content == transformed_content
        assert draft.current_version == 1
        assert draft.status == "draft"
        
        # 验证版本记录已创建
        versions = await service.get_versions(draft.id)
        assert len(versions) == 1
        assert versions[0].version_number == 1
        assert versions[0].content == transformed_content
    
    async def test_create_draft_with_nonexistent_submission(self, db_session):
        """测试为不存在的投稿创建草稿"""
        service = DraftService(db_session)
        
        with pytest.raises(ValueError, match="投稿不存在"):
            await service.create_draft(
                submission_id=99999,
                transformed_content="测试内容"
            )
    
    async def test_create_draft_with_empty_content(self, db_session, sample_submission):
        """测试使用空内容创建草稿"""
        service = DraftService(db_session)
        
        with pytest.raises(ValueError, match="内容不能为空"):
            await service.create_draft(
                submission_id=sample_submission.id,
                transformed_content=""
            )
    
    async def test_update_draft_success(self, db_session, sample_submission):
        """测试成功更新草稿"""
        service = DraftService(db_session)
        
        # 创建草稿
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="初始内容"
        )
        
        # 更新草稿
        new_content = "更新后的内容"
        updated_draft = await service.update_draft(
            draft_id=draft.id,
            content=new_content
        )
        
        assert updated_draft.current_content == new_content
        assert updated_draft.current_version == 2
        
        # 验证版本记录
        versions = await service.get_versions(draft.id)
        assert len(versions) == 2
        assert versions[0].version_number == 2  # 最新版本在前
        assert versions[0].content == new_content
    
    async def test_update_draft_with_same_content(self, db_session, sample_submission):
        """测试使用相同内容更新草稿"""
        service = DraftService(db_session)
        
        content = "测试内容"
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content=content
        )
        
        # 使用相同内容更新
        updated_draft = await service.update_draft(
            draft_id=draft.id,
            content=content
        )
        
        # 版本号不应该增加
        assert updated_draft.current_version == 1
        
        # 版本记录数量不应该增加
        versions = await service.get_versions(draft.id)
        assert len(versions) == 1
    
    async def test_get_draft_success(self, db_session, sample_submission):
        """测试成功获取草稿"""
        service = DraftService(db_session)
        
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="测试内容"
        )
        
        retrieved_draft = await service.get_draft(draft.id)
        
        assert retrieved_draft is not None
        assert retrieved_draft.id == draft.id
        assert retrieved_draft.submission_id == sample_submission.id
    
    async def test_get_draft_not_found(self, db_session):
        """测试获取不存在的草稿"""
        service = DraftService(db_session)
        
        draft = await service.get_draft(99999)
        
        assert draft is None
    
    async def test_get_draft_by_submission(self, db_session, sample_submission):
        """测试根据投稿ID获取草稿"""
        service = DraftService(db_session)
        
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="测试内容"
        )
        
        retrieved_draft = await service.get_draft_by_submission(sample_submission.id)
        
        assert retrieved_draft is not None
        assert retrieved_draft.id == draft.id
    
    async def test_restore_version_success(self, db_session, sample_submission):
        """测试成功恢复版本"""
        service = DraftService(db_session)
        
        # 创建草稿并更新多次
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="版本1内容"
        )
        
        await service.update_draft(draft.id, "版本2内容")
        await service.update_draft(draft.id, "版本3内容")
        
        # 获取版本1
        versions = await service.get_versions(draft.id)
        version_1 = [v for v in versions if v.version_number == 1][0]
        
        # 恢复到版本1
        restored_draft = await service.restore_version(
            draft_id=draft.id,
            version_id=version_1.id
        )
        
        assert restored_draft.current_content == "版本1内容"
        assert restored_draft.current_version == 4  # 恢复操作创建新版本
    
    async def test_restore_ai_version_success(self, db_session, sample_submission):
        """测试成功恢复AI原始版本"""
        service = DraftService(db_session)
        
        # 创建草稿并更新
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="AI转换内容"
        )
        
        await service.update_draft(draft.id, "编辑后内容")
        
        # 恢复AI版本
        restored_draft = await service.restore_ai_version(draft.id)
        
        assert restored_draft.current_content == "AI转换内容"
    
    async def test_list_drafts_all(self, db_session, sample_submission):
        """测试获取所有草稿列表"""
        service = DraftService(db_session)
        
        # 创建多个草稿
        await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="草稿1"
        )
        
        drafts, total = await service.list_drafts()
        
        assert len(drafts) >= 1
        assert total >= 1
    
    async def test_list_drafts_with_status_filter(self, db_session, sample_submission):
        """测试按状态筛选草稿列表"""
        service = DraftService(db_session)
        
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="草稿1"
        )
        
        # 筛选draft状态
        drafts, total = await service.list_drafts(status="draft")
        
        assert len(drafts) >= 1
        assert all(d.status == "draft" for d in drafts)
    
    async def test_mark_as_published(self, db_session, sample_submission):
        """测试标记草稿为已发布"""
        service = DraftService(db_session)
        
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="测试内容"
        )
        
        published_draft = await service.mark_as_published(
            draft_id=draft.id,
            site_id=1,
            wordpress_post_id=123
        )
        
        assert published_draft.status == "published"
        assert published_draft.published_to_site_id == 1
        assert published_draft.wordpress_post_id == 123
        assert published_draft.published_at is not None
    
    async def test_version_cleanup(self, db_session, sample_submission):
        """测试版本清理功能"""
        service = DraftService(db_session)
        
        # 创建草稿
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="初始内容"
        )
        
        # 创建35个版本（超过30个限制）
        for i in range(35):
            await service.update_draft(draft.id, f"内容{i}")
        
        # 验证只保留最近30个版本
        versions = await service.get_versions(draft.id)
        assert len(versions) <= 30
    
    async def test_delete_draft(self, db_session, sample_submission):
        """测试删除草稿"""
        service = DraftService(db_session)
        
        draft = await service.create_draft(
            submission_id=sample_submission.id,
            transformed_content="测试内容"
        )
        
        draft_id = draft.id
        
        await service.delete_draft(draft_id)
        
        # 验证草稿已删除
        deleted_draft = await service.get_draft(draft_id)
        assert deleted_draft is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
