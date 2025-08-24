import warnings
import sys
from io import StringIO

# 警告をキャプチャするためのバッファ
warning_buffer = StringIO()

def capture_warnings():
    """警告をキャプチャして詳細情報を収集"""
    warnings.resetwarnings()
    
    # カスタム警告フィルター
    def custom_warning_handler(message, category, filename, lineno, file=None, line=None):
        warning_info = {
            'message': str(message),
            'category': category.__name__,
            'filename': filename,
            'lineno': lineno,
            'line': line
        }
        
        print("=" * 60)
        print("🚨 警告が検出されました")
        print("=" * 60)
        for key, value in warning_info.items():
            print(f"{key:12}: {value}")
        
        # スタックトレースを表示
        import traceback
        print("\nスタックトレース:")
        traceback.print_stack()
        print("=" * 60)
        
        return warning_info
    
    warnings.showwarning = custom_warning_handler
    warnings.simplefilter("always")  # すべての警告を表示
    
    return custom_warning_handler

def minimal_test():
    """最小限のテストで警告を確認"""
    print("最小限のOpenAIテストを実行...")
    
    try:
        from openai import OpenAI
        print("✓ OpenAIライブラリのインポート完了")
        
        # APIキーが設定されている場合のみテスト実行
        try:
            client = OpenAI()  # 環境変数からAPIキーを取得
            print("✓ クライアント作成完了")
            
            # 簡単なファイル作成とアップロードテスト
            with open("../documents/loganpark.pdf", "w") as f:
                f.write("test content")
            
            print("ファイルアップロードテスト開始...")
            with open("../documents/loganpark.pdf", "rb") as f:
                file_obj = client.files.create(file=f, purpose="assistants")
                print(f"✓ ファイルアップロード完了: {file_obj.id}")
                
                # クリーンアップ
                client.files.delete(file_obj.id)
                print("✓ ファイル削除完了")
                
        except Exception as api_error:
            print(f"⚠ API操作でエラー: {api_error}")
            print("（APIキーが設定されていない可能性があります）")
            
    except ImportError as import_error:
        print(f"❌ インポートエラー: {import_error}")
    except Exception as e:
        print(f"❌ 予期しないエラー: {e}")

if __name__ == "__main__":
    # 警告キャプチャを開始
    warning_handler = capture_warnings()
    
    print("警告監視を開始しました...")
    print("OpenAI関連の操作をテストします...")
    
    # テスト実行
    minimal_test()
    
    print("\nテスト完了。警告が発生した場合は上記に詳細が表示されます。")