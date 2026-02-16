"""
IMAP邮件抓取服务
"""
import re
from typing import List, Optional, Tuple
from datetime import datetime
from imap_tools import MailBox, AND
from email.header import decode_header
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class EmailData:
    """邮件数据结构"""
    def __init__(
        self,
        subject: str,
        from_addr: str,
        date: datetime,
        body: str,
        attachments: List[Tuple[str, bytes]]
    ):
        self.subject = subject
        self.from_addr = from_addr
        self.date = date
        self.body = body
        self.attachments = attachments
        
        # 解析邮件标题中的站点和来源信息
        self.target_site = None
        self.source = None
        self._parse_subject()
    
    def _parse_subject(self):
        """
        解析邮件标题
        格式: 投递到（{站点}）站，来自（{来源}）的稿件
        """
        pattern = r'投递到[（(](.+?)[）)]站.*来自[（(](.+?)[）)]'
        match = re.search(pattern, self.subject)
        
        if match:
            self.target_site = match.group(1).strip()
            self.source = match.group(2).strip()
            logger.info(f"解析邮件标题: 站点={self.target_site}, 来源={self.source}")
        else:
            logger.warning(f"无法解析邮件标题格式: {self.subject}")


class IMAPFetcher:
    """IMAP邮件抓取器"""
    
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_ssl: bool = True
    ):
        """
        初始化IMAP抓取器
        
        Args:
            host: IMAP服务器地址
            port: IMAP端口
            username: 用户名
            password: 密码
            use_ssl: 是否使用SSL
        """
        self.host = host or settings.IMAP_HOST
        self.port = port or settings.IMAP_PORT
        self.username = username or settings.IMAP_USER
        self.password = password or settings.IMAP_PASSWORD
        self.use_ssl = use_ssl if use_ssl is not None else settings.IMAP_USE_SSL
        
        if not all([self.host, self.username, self.password]):
            raise ValueError("IMAP配置不完整，请检查环境变量")
    
    def connect(self) -> MailBox:
        """
        连接到IMAP服务器
        
        Returns:
            MailBox: 邮箱连接对象
        """
        try:
            mailbox = MailBox(self.host, self.port)
            mailbox.login(self.username, self.password, initial_folder='INBOX')
            logger.info(f"成功连接到IMAP服务器: {self.host}")
            return mailbox
        except Exception as e:
            logger.error(f"连接IMAP服务器失败: {str(e)}")
            raise
    
    def fetch_unread_emails(
        self,
        limit: int = 10,
        mark_as_read: bool = False,
        fallback_recent_limit: int = 5
    ) -> List[EmailData]:
        """
        获取未读邮件；若未读为 0 则按 fallback_recent_limit 抓取最近几封（避免因已读而一直抓不到）。
        
        Args:
            limit: 最多获取的未读邮件数量
            mark_as_read: 是否在提取后标记为已读
            fallback_recent_limit: 未读为 0 时，抓取最近多少封邮件（0 表示不 fallback）
        
        Returns:
            List[EmailData]: 邮件数据列表
        """
        emails = []
        
        try:
            with self.connect() as mailbox:
                # 必须传 mark_seen=False，否则 imap_tools 在 fetch 时就会把邮件标为已读，下次就抓不到未读了
                messages = list(mailbox.fetch(
                    criteria=AND(seen=False),
                    limit=limit,
                    reverse=True,
                    mark_seen=False
                ))
                
                # 未读为 0 且允许 fallback 时，抓取最近几封（可能已被其他客户端标为已读）
                if len(messages) == 0 and fallback_recent_limit and fallback_recent_limit > 0:
                    logger.info(f"未读邮件为 0，尝试抓取最近 {fallback_recent_limit} 封邮件")
                    messages = list(mailbox.fetch(
                        criteria='ALL',
                        limit=fallback_recent_limit,
                        reverse=True,
                        mark_seen=False
                    ))
                
                for msg in messages:
                    try:
                        email_data = self._extract_email_data(msg)
                        emails.append(email_data)
                        if mark_as_read:
                            mailbox.flag(msg.uid, ['\\Seen'], True)
                        logger.info(f"成功提取邮件: {email_data.subject}")
                    except Exception as e:
                        logger.error(f"提取邮件失败: {str(e)}")
                        continue
        
        except Exception as e:
            logger.error(f"获取未读邮件失败: {str(e)}")
            raise
        
        return emails
    
    def _extract_email_data(self, msg) -> EmailData:
        """
        从邮件消息中提取数据
        
        Args:
            msg: imap_tools消息对象
        
        Returns:
            EmailData: 邮件数据对象
        """
        # 解码主题
        subject = self._decode_header(msg.subject)
        
        # 获取发件人
        from_addr = msg.from_
        
        # 获取日期
        date = msg.date
        
        # 获取邮件正文（优先HTML，否则纯文本）
        body = msg.html or msg.text or ""
        
        # 提取附件
        attachments = []
        for att in msg.attachments:
            filename = self._decode_header(att.filename)
            content = att.payload
            attachments.append((filename, content))
        
        return EmailData(
            subject=subject,
            from_addr=from_addr,
            date=date,
            body=body,
            attachments=attachments
        )
    
    def _decode_header(self, header: str) -> str:
        """
        解码邮件头部（处理编码问题）
        
        Args:
            header: 邮件头部字符串
        
        Returns:
            str: 解码后的字符串
        """
        if not header:
            return ""
        
        try:
            decoded_parts = decode_header(header)
            result = []
            
            for part, encoding in decoded_parts:
                if isinstance(part, bytes):
                    if encoding:
                        result.append(part.decode(encoding))
                    else:
                        result.append(part.decode('utf-8', errors='ignore'))
                else:
                    result.append(str(part))
            
            return ''.join(result)
        except Exception as e:
            logger.warning(f"解码邮件头部失败: {str(e)}")
            return str(header)
    
    def test_connection(self) -> bool:
        """
        测试IMAP连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            with self.connect() as mailbox:
                # 尝试获取邮箱信息
                mailbox.folder.status()
                logger.info("IMAP连接测试成功")
                return True
        except Exception as e:
            logger.error(f"IMAP连接测试失败: {str(e)}")
            return False
