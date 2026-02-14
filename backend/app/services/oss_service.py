"""
阿里云OSS存储服务
"""
import os
import oss2
from typing import Optional, Tuple
from datetime import datetime
import hashlib
import logging
from app.config import settings

logger = logging.getLogger(__name__)


class OSSService:
    """阿里云OSS服务"""
    
    def __init__(
        self,
        access_key_id: Optional[str] = None,
        access_key_secret: Optional[str] = None,
        endpoint: Optional[str] = None,
        bucket_name: Optional[str] = None
    ):
        """
        初始化OSS服务
        
        Args:
            access_key_id: 访问密钥ID
            access_key_secret: 访问密钥Secret
            endpoint: OSS端点
            bucket_name: 存储桶名称
        """
        self.access_key_id = access_key_id or settings.OSS_ACCESS_KEY_ID
        self.access_key_secret = access_key_secret or settings.OSS_ACCESS_KEY_SECRET
        self.endpoint = endpoint or settings.OSS_ENDPOINT
        self.bucket_name = bucket_name or settings.OSS_BUCKET_NAME
        
        if not all([self.access_key_id, self.access_key_secret, self.endpoint, self.bucket_name]):
            raise ValueError("OSS配置不完整，请检查环境变量")
        
        # 创建认证对象
        self.auth = oss2.Auth(self.access_key_id, self.access_key_secret)
        
        # 创建Bucket对象
        self.bucket = oss2.Bucket(self.auth, self.endpoint, self.bucket_name)
        
        logger.info(f"OSS服务初始化成功: {self.bucket_name}")
    
    def upload_file(
        self,
        file_data: bytes,
        filename: str,
        folder: str = "images",
        max_retries: int = 3
    ) -> Tuple[str, str]:
        """
        上传文件到OSS
        
        Args:
            file_data: 文件数据
            filename: 文件名
            folder: 存储文件夹
            max_retries: 最大重试次数
        
        Returns:
            Tuple[str, str]: (OSS URL, OSS Key)
        
        Raises:
            RuntimeError: 上传失败时抛出
        """
        # 生成唯一的文件名（使用时间戳和哈希）
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_hash = hashlib.md5(file_data).hexdigest()[:8]
        ext = os.path.splitext(filename)[1]
        unique_filename = f"{timestamp}_{file_hash}{ext}"
        
        # 构建OSS key
        oss_key = f"{folder}/{unique_filename}"
        
        # 重试上传
        last_error = None
        for attempt in range(max_retries):
            try:
                logger.info(f"上传文件到OSS (尝试 {attempt + 1}/{max_retries}): {oss_key}")
                
                # 上传文件
                result = self.bucket.put_object(oss_key, file_data)
                
                if result.status == 200:
                    # 构建访问URL
                    oss_url = f"https://{self.bucket_name}.{self.endpoint}/{oss_key}"
                    logger.info(f"文件上传成功: {oss_url}")
                    return oss_url, oss_key
                else:
                    last_error = f"上传失败，状态码: {result.status}"
                    logger.warning(last_error)
            
            except Exception as e:
                last_error = str(e)
                logger.error(f"上传异常 (尝试 {attempt + 1}/{max_retries}): {last_error}")
                
                if attempt < max_retries - 1:
                    continue
        
        # 所有重试都失败
        error_msg = f"文件上传失败，已重试{max_retries}次: {last_error}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)
    
    def delete_file(self, oss_key: str) -> bool:
        """
        删除OSS文件
        
        Args:
            oss_key: OSS文件key
        
        Returns:
            bool: 是否删除成功
        """
        try:
            self.bucket.delete_object(oss_key)
            logger.info(f"文件删除成功: {oss_key}")
            return True
        except Exception as e:
            logger.error(f"文件删除失败: {str(e)}")
            return False
    
    def file_exists(self, oss_key: str) -> bool:
        """
        检查文件是否存在
        
        Args:
            oss_key: OSS文件key
        
        Returns:
            bool: 文件是否存在
        """
        try:
            return self.bucket.object_exists(oss_key)
        except Exception as e:
            logger.error(f"检查文件存在性失败: {str(e)}")
            return False
    
    def get_file_url(self, oss_key: str, expires: int = 3600) -> str:
        """
        获取文件的签名URL（用于私有bucket）
        
        Args:
            oss_key: OSS文件key
            expires: 过期时间（秒）
        
        Returns:
            str: 签名URL
        """
        try:
            url = self.bucket.sign_url('GET', oss_key, expires)
            return url
        except Exception as e:
            logger.error(f"生成签名URL失败: {str(e)}")
            raise
    
    def compress_image(
        self,
        oss_key: str,
        quality: int = 60
    ) -> bool:
        """
        压缩OSS上的图片
        
        Args:
            oss_key: OSS文件key
            quality: 压缩质量（1-100）
        
        Returns:
            bool: 是否压缩成功
        """
        try:
            # 下载原图
            result = self.bucket.get_object(oss_key)
            original_data = result.read()
            
            # 使用OSS图片处理服务压缩
            # 格式: image/quality,q_<quality>
            process = f"image/quality,q_{quality}"
            
            # 上传压缩后的图片（覆盖原图）
            self.bucket.put_object(oss_key, original_data, headers={'x-oss-process': process})
            
            logger.info(f"图片压缩成功: {oss_key}, 质量: {quality}")
            return True
        
        except Exception as e:
            logger.error(f"图片压缩失败: {str(e)}")
            return False
    
    def test_connection(self) -> bool:
        """
        测试OSS连接
        
        Returns:
            bool: 连接是否成功
        """
        try:
            # 尝试列出bucket信息
            self.bucket.get_bucket_info()
            logger.info("OSS连接测试成功")
            return True
        except Exception as e:
            logger.error(f"OSS连接测试失败: {str(e)}")
            return False
