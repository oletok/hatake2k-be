# Hatake API

農作物管理システムのバックエンドAPI

## 概要

Hatake APIは、農作物、天気エリア、郵便番号、ユーザー情報を管理するための FastAPI ベースのWebAPIです。

## 機能

- 農作物データの管理
- 天気エリア情報の管理
- 郵便番号データの管理
- ユーザー情報の管理
- PostgreSQL データベースとの連携
- データのインポート/エクスポート機能

## 技術スタック

- **フレームワーク**: FastAPI 0.104.1
- **データベース**: PostgreSQL
- **ORM**: SQLModel 0.0.14
- **マイグレーション**: Alembic 1.13.1
- **サーバー**: Uvicorn
- **コンテナ**: Docker & Docker Compose

## セットアップ

### 必要な環境

- Python 3.8+
- Docker & Docker Compose
- PostgreSQL 15

### インストール

1. リポジトリをクローン
```bash
git clone <repository-url>
cd hatake2k/backend
```

2. 仮想環境を作成・アクティベート
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows
```

3. 依存関係をインストール
```bash
pip install -r requirements.txt
```

### Docker を使用した起動

```bash
# コンテナを起動
docker-compose up -d

# ログを確認
docker-compose logs -f api
```

### 直接起動

```bash
# データベースを起動（Docker使用）
docker-compose up -d db

# データベースマイグレーション
alembic upgrade head

# データのシード
python seed.py

# サーバーを起動
uvicorn app.main:app --reload
```

## API エンドポイント

### 基本

- `GET /` - ルートエンドポイント
- `GET /health` - ヘルスチェック
- `GET /docs` - API ドキュメント（Swagger UI）

### 農作物

- `GET /crops` - 農作物一覧取得
- `GET /crops/{crop_id}` - 農作物詳細取得

### 天気エリア

- `GET /weather-areas` - 天気エリア一覧取得
- `GET /weather-areas/{area_id}` - 天気エリア詳細取得

### 郵便番号

- `GET /postal-codes` - 郵便番号一覧取得
- `GET /postal-codes/{postal_code}` - 郵便番号詳細取得

## 開発

### データベースマイグレーション

```bash
# マイグレーションファイルを作成
alembic revision --autogenerate -m "description"

# マイグレーションを適用
alembic upgrade head

# マイグレーションを元に戻す
alembic downgrade -1
```

### データのシード

```bash
python seed.py
```

## 設定

環境変数または `.env` ファイルで設定を変更できます：

```env
DATABASE_URL=postgresql://hatake_user:hatake_password@localhost:5432/hatake
HOST=0.0.0.0
PORT=8000
DEBUG=false
LOG_LEVEL=INFO
```

## プロジェクト構成

```
backend/
├── app/
│   ├── api/           # API エンドポイント
│   ├── core/          # 設定・データベース・ログ
│   ├── models/        # データモデル
│   ├── services/      # ビジネスロジック
│   └── utils/         # ユーティリティ
├── alembic/           # データベースマイグレーション
├── _data/             # CSVデータファイル
├── docker-compose.yml # Docker設定
├── requirements.txt   # Python依存関係
└── README.md         # このファイル
```

## サービス

### Web管理画面

pgAdmin4にアクセスして PostgreSQL を管理できます：

- URL: http://localhost:5050
- Email: admin@example.com
- Password: admin

### API ドキュメント

サーバー起動後、以下のURLでAPI ドキュメントにアクセスできます：

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## ライセンス

このプロジェクトは MIT ライセンスの下で公開されています。