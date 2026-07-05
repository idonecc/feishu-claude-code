"""
智能错误追踪系统
为每个错误生成唯一ID，便于快速诊断
"""

import json
import os
import time
import traceback
from datetime import datetime
from pathlib import Path
import hashlib


class ErrorTracker:
    """错误追踪器"""

    def __init__(self, log_dir=None):
        if log_dir is None:
            log_dir = os.path.expanduser("~/.feishu-claude/errors")
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)

        # 每日错误日志文件
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_log = self.log_dir / f"errors-{today}.jsonl"

    def generate_error_id(self, error_type: str, message: str) -> str:
        """
        生成错误ID: ERR-YYYYMMDD-HASH6
        例: ERR-20260705-a3b4c5
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")

        # 用错误类型和消息生成短哈希
        content = f"{error_type}:{message}:{timestamp}"
        hash_obj = hashlib.md5(content.encode())
        short_hash = hash_obj.hexdigest()[:6]

        error_id = f"ERR-{datetime.now().strftime('%Y%m%d')}-{short_hash}"
        return error_id

    def log_error(
        self,
        error: Exception,
        context: dict = None,
        user_id: str = None,
        chat_id: str = None,
        session_id: str = None,
    ) -> str:
        """
        记录错误并返回错误ID

        Args:
            error: 异常对象
            context: 额外上下文信息
            user_id: 用户ID
            chat_id: 会话ID
            session_id: Claude session ID

        Returns:
            错误ID字符串
        """
        error_type = type(error).__name__
        error_msg = str(error)

        # 生成错误ID
        error_id = self.generate_error_id(error_type, error_msg)

        # 完整错误记录
        error_record = {
            "error_id": error_id,
            "timestamp": datetime.now().isoformat(),
            "error_type": error_type,
            "error_message": error_msg,
            "traceback": traceback.format_exc(),
            "user_id": user_id,
            "chat_id": chat_id,
            "session_id": session_id,
            "context": context or {},
        }

        # 写入每日日志文件（JSONL格式）
        with open(self.daily_log, 'a', encoding='utf-8') as f:
            f.write(json.dumps(error_record, ensure_ascii=False) + '\n')

        # 同时写入独立的错误文件（便于单独查看）
        error_file = self.log_dir / f"{error_id}.json"
        with open(error_file, 'w', encoding='utf-8') as f:
            json.dump(error_record, f, ensure_ascii=False, indent=2)

        return error_id

    def get_error(self, error_id: str) -> dict:
        """根据错误ID获取完整错误信息"""
        error_file = self.log_dir / f"{error_id}.json"

        if not error_file.exists():
            # 如果独立文件不存在，搜索每日日志
            return self._search_in_daily_logs(error_id)

        with open(error_file, 'r', encoding='utf-8') as f:
            return json.load(f)

    def _search_in_daily_logs(self, error_id: str) -> dict:
        """在每日日志中搜索错误ID"""
        # 从错误ID提取日期
        parts = error_id.split('-')
        if len(parts) >= 2:
            date_str = parts[1]  # YYYYMMDD
            # 转换为 YYYY-MM-DD
            log_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
            log_file = self.log_dir / f"errors-{log_date}.jsonl"

            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        record = json.loads(line)
                        if record.get('error_id') == error_id:
                            return record

        return None

    def format_error_for_display(self, error_id: str) -> str:
        """格式化错误信息用于显示给用户"""
        error_record = self.get_error(error_id)

        if not error_record:
            return f"❌ 错误ID {error_id} 未找到"

        lines = [
            f"🔍 **错误详情** `{error_id}`",
            f"",
            f"**时间**: {error_record['timestamp']}",
            f"**类型**: `{error_record['error_type']}`",
            f"**消息**: {error_record['error_message']}",
        ]

        if error_record.get('session_id'):
            lines.append(f"**Session**: `{error_record['session_id'][:16]}...`")

        if error_record.get('user_id'):
            lines.append(f"**用户**: `{error_record['user_id'][:12]}...`")

        # 截取关键的traceback部分（最后10行）
        tb_lines = error_record.get('traceback', '').strip().split('\n')
        if len(tb_lines) > 10:
            tb_lines = ['...'] + tb_lines[-10:]

        lines.append(f"\n**调用栈**:")
        lines.append("```")
        lines.extend(tb_lines)
        lines.append("```")

        if error_record.get('context'):
            lines.append(f"\n**上下文**: {json.dumps(error_record['context'], ensure_ascii=False, indent=2)}")

        return '\n'.join(lines)


# 全局实例
_tracker = ErrorTracker()


def log_error(
    error: Exception,
    context: dict = None,
    user_id: str = None,
    chat_id: str = None,
    session_id: str = None,
) -> str:
    """便捷函数：记录错误并返回错误ID"""
    return _tracker.log_error(error, context, user_id, chat_id, session_id)


def get_error(error_id: str) -> dict:
    """便捷函数：获取错误详情"""
    return _tracker.get_error(error_id)


def format_error(error_id: str) -> str:
    """便捷函数：格式化错误信息"""
    return _tracker.format_error_for_display(error_id)
