import os
import sys
from pathlib import Path

# 改进：从模块中直接导入主函数，避免 init_demo_data.main() 的长调用
# 同时添加类型提示支持（Python 3.5+）
try:
    from init_demo_data import main as init_database_main
except ImportError as e:
    print(f"❌ 无法导入 init_demo_data 模块: {e}")
    print("请确保 init_demo_data.py 文件在当前目录")
    sys.exit(1)


def reset_database(data_dir: str = ".", verbose: bool = True) -> bool:
    """
    重置所有数据库文件并重新初始化示例数据

    Args:
        data_dir: 数据库文件所在目录，默认为当前目录
        verbose: 是否打印详细日志
    """
    db_files = [
        'data/email.db',
        'data/detection_history.db',
        'data/chat_history.db',
        'data/comments.db',
        'data/knowledge_base.db'
    ]

    deleted_count = 0
    data_path = Path(data_dir)

    # 删除旧数据库
    for db_file in db_files:
        file_path = data_path / db_file
        if file_path.exists():
            try:
                file_path.unlink()
                if verbose:
                    print(f"✓ 已删除: {db_file}")
                deleted_count += 1
            except OSError as e:
                print(f"⚠️ 无法删除 {db_file}: {e}")
                return False

    if deleted_count == 0 and verbose:
        print("ℹ️ 未发现现有数据库文件，将直接创建新数据库")

    # 重新初始化
    try:
        init_database_main()
        if verbose:
            print("\n✅ 数据库已重置并导入示例数据！")
        return True
    except Exception as e:
        print(f"\n❌ 数据库初始化失败: {e}")
        return False


if __name__ == "__main__":
    # 支持命令行参数指定目录
    target_dir = sys.argv[1] if len(sys.argv) > 1 else "."
    success = reset_database(target_dir)
    sys.exit(0 if success else 1)