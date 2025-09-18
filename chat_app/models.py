from django.db import models

# Create your models here.
class Conversation(models.Model):
    """会话模型，代表一次完整的聊天会话"""
    title = models.CharField(max_length=200, default="新会话")  # 会话标题
    created_at = models.DateTimeField(auto_now_add=True)  # 创建时间
    updated_at = models.DateTimeField(auto_now=True)  # 更新时间

    class Meta:
        ordering = ['-updated_at']  # 按更新时间倒序排列，最近的会话在前面
        verbose_name = "会话"
        verbose_name_plural = "会话"

    def __str__(self):
        return self.title or f"会话 {self.id}"

    def title_user_message(self):
        """从会话中用户发送的第一条消息更新标题"""
        # 查找当前会话中用户发送的第一条消息
        first_user_msg = self.messages.filter(sender='user').order_by('time').first()

        if first_user_msg:
            # 截取前30个字符作为标题，超过则加省略号
            self.title = first_user_msg.content[:30] + ("..." if len(first_user_msg.content) > 30 else "")
            self.save(update_fields=['title'])  # 只更新title字段，提高效率


class Message(models.Model):
    """消息模型，代表会话中的一条消息"""
    SENDER_CHOICES = (
        ('user', '用户'),
        ('ai', 'AI'),
    )

    conversation = models.ForeignKey(
        Conversation,
        on_delete=models.CASCADE,
        related_name="messages"
    )

    content = models.TextField()  # 消息内容
    sender = models.CharField(max_length=10, choices=SENDER_CHOICES)  # 发送者
    time = models.DateTimeField(auto_now_add=True)  # 发送时间


    class Meta:
        ordering = ['time']  # 按时间顺序排列消息
        verbose_name = "消息"
        verbose_name_plural = "消息"

    def __str__(self):
        return f"{self.get_sender_display()}: {self.content[:20]}"
