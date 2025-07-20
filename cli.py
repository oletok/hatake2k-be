#!/usr/bin/env python3
"""
Hatake CLI - コマンドラインツール
"""
import typer
from typing import Optional
from app.core.database import get_session
from app.services.seed_service import SeedService
from app.services.postal_code_weather_mapping_service import PostalCodeWeatherMappingService
from app.core.logging import get_logger

logger = get_logger("cli")

app = typer.Typer(
    name="hatake",
    help="Hatake API コマンドラインツール",
    add_completion=False
)

@app.command()
def console():
    """
    Rails の console のように、DB やモデルにアクセスできる対話環境。
    """
    try:
        from IPython import embed
    except ImportError:
        typer.echo("❌ IPython がインストールされていません。pip install ipython で対話環境を利用できます。", err=True)
        raise typer.Exit(1)
    
    from app.models.user import User
    from app.models.crop import Crop
    from app.models.weather_area import WeatherArea
    from app.models.postal_code import PostalCode
    from app.models.growing import Growing
    from sqlmodel import select
    
    session = next(get_session())
    
    typer.echo("🚀 Hatake Console を開始します...")
    typer.echo("利用可能なオブジェクト: session, User, Crop, WeatherArea, PostalCode, Growing, select")
    typer.echo("例: session.exec(select(User)).all()")
    
    try:
        embed(user_ns={
            "session": session,
            "User": User,
            "Crop": Crop,
            "WeatherArea": WeatherArea,
            "PostalCode": PostalCode,
            "Growing": Growing,
            "select": select,
        })
    finally:
        session.close()
        typer.echo("👋 Hatake Console を終了しました")

@app.command()
def seed(
    reset: bool = typer.Option(False, "--reset", "-r", help="データをリセットしてから実行"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="詳細ログを表示")
):
    """データベースにシードデータを投入"""
    if verbose:
        typer.echo("🌱 シードデータ投入を開始します...")
    
    session = next(get_session())
    try:
        seed_service = SeedService(session)
        
        if reset:
            typer.echo("⚠️  データベースをリセットします...")
            # ここでリセット処理を追加
        
        result = seed_service.seed_all()
        
        typer.echo("✅ シードデータ投入が完了しました")
        typer.echo(f"📊 結果:")
        typer.echo(f"  - テストユーザー: {result['test_user'].id if hasattr(result['test_user'], 'id') else 'N/A'}")
        typer.echo(f"  - 作物データ: {result['crops']}件")
        typer.echo(f"  - 気象地域: {result['weather_areas']}件")
        typer.echo(f"  - 郵便番号: {result['postal_codes']}件")
        
        if 'postal_code_mapping' in result:
            mapping = result['postal_code_mapping']
            typer.echo(f"  - 郵便番号マッピング: {mapping.get('mapped_count', 0)}件")
        
    except Exception as e:
        typer.echo(f"❌ エラーが発生しました: {e}", err=True)
        raise typer.Exit(1)
    finally:
        session.close()

@app.command()
def mapping():
    """郵便番号と気象地域のマッピングを実行"""
    typer.echo("🔗 郵便番号と気象地域のマッピングを開始します...")
    
    session = next(get_session())
    try:
        mapping_service = PostalCodeWeatherMappingService(session)
        result = mapping_service.map_postal_codes_to_weather_areas()
        
        typer.echo("✅ マッピングが完了しました")
        typer.echo(f"📊 結果:")
        typer.echo(f"  - マッピング済み: {result.get('mapped_count', 0)}件")
        typer.echo(f"  - 見つからず: {result.get('not_found_count', 0)}件")
        typer.echo(f"  - エラー: {result.get('error_count', 0)}件")
        
    except Exception as e:
        typer.echo(f"❌ エラーが発生しました: {e}", err=True)
        raise typer.Exit(1)
    finally:
        session.close()

@app.command()
def db_stats():
    """データベース統計情報を表示"""
    typer.echo("📊 データベース統計情報")
    
    session = next(get_session())
    try:
        from sqlmodel import select, text
        from app.models.user import User
        from app.models.crop import Crop
        from app.models.weather_area import WeatherArea
        from app.models.postal_code import PostalCode
        from app.models.growing import Growing
        
        # 各テーブルの件数を取得
        users_count = len(session.exec(select(User)).all())
        crops_count = len(session.exec(select(Crop)).all())
        weather_areas_count = len(session.exec(select(WeatherArea)).all())
        postal_codes_count = len(session.exec(select(PostalCode)).all())
        growings_count = len(session.exec(select(Growing)).all())
        
        typer.echo(f"👤 ユーザー: {users_count}件")
        typer.echo(f"🌾 作物: {crops_count}件")
        typer.echo(f"🌤️  気象地域: {weather_areas_count}件")
        typer.echo(f"📮 郵便番号: {postal_codes_count}件")
        typer.echo(f"🌱 栽培記録: {growings_count}件")
        
    except Exception as e:
        typer.echo(f"❌ エラーが発生しました: {e}", err=True)
        raise typer.Exit(1)
    finally:
        session.close()

@app.command()
def version():
    """バージョン情報を表示"""
    typer.echo("Hatake CLI v1.0.0")
    typer.echo("🌱 家庭菜園支援システム")

if __name__ == "__main__":
    app()