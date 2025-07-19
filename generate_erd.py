#!/usr/bin/env python3
"""
動的ER図生成スクリプト
modelsディレクトリをスキャンしてSQLModelクラスを解析し、自動でMermaid形式のER図を生成
"""

import ast
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any, Optional


class ModelAnalyzer:
    """SQLModelクラスを解析するクラス"""
    
    def __init__(self, models_dir: Path):
        self.models_dir = models_dir
        self.tables: Dict[str, Dict] = {}
        self.relationships: List[Dict] = []
        
    def analyze_models(self) -> None:
        """modelsディレクトリ内の全Pythonファイルを解析"""
        for py_file in self.models_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            self._analyze_file(py_file)
    
    def _analyze_file(self, file_path: Path) -> None:
        """単一ファイルを解析"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef):
                    self._analyze_class(node, file_path.stem)
        except Exception as e:
            print(f"⚠️  ファイル解析エラー {file_path}: {e}")
    
    def _analyze_class(self, class_node: ast.ClassDef, module_name: str) -> None:
        """クラス定義を解析"""
        # SQLModelのテーブルクラスかチェック
        if not self._is_table_class(class_node):
            return
            
        table_name = self._get_table_name(class_node)
        if not table_name:
            return
            
        # フィールド解析
        fields = self._analyze_fields(class_node)
        
        # テーブル情報を保存
        self.tables[table_name] = {
            "class_name": class_node.name,
            "module": module_name,
            "fields": fields,
            "relationships": []
        }
        
        # リレーション解析
        self._analyze_relationships(class_node, table_name)
    
    def _is_table_class(self, class_node: ast.ClassDef) -> bool:
        """SQLModelのテーブルクラスかどうか判定"""
        # クラス定義の文字列表現を確認してtable=Trueがあるかチェック
        class_line = f"class {class_node.name}("
        
        # 基底クラスを確認
        base_names = []
        for base in class_node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
        
        # キーワード引数を確認
        for keyword in class_node.keywords:
            if keyword.arg == "table" and isinstance(keyword.value, ast.Constant):
                if keyword.value.value is True:
                    return "SQLModel" in base_names or any("Base" in name for name in base_names)
        
        return False
    
    def _get_table_name(self, class_node: ast.ClassDef) -> Optional[str]:
        """テーブル名を取得"""
        # __tablename__属性を探す
        for stmt in class_node.body:
            if isinstance(stmt, ast.Assign):
                for target in stmt.targets:
                    if (isinstance(target, ast.Name) and 
                        target.id == "__tablename__"):
                        if isinstance(stmt.value, ast.Constant):
                            return stmt.value.value
        
        # __tablename__がない場合はクラス名をスネークケースに変換
        return self._to_snake_case(class_node.name)
    
    def _to_snake_case(self, name: str) -> str:
        """CamelCaseをsnake_caseに変換"""
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()
    
    def _analyze_fields(self, class_node: ast.ClassDef) -> List[Dict]:
        """クラスのフィールドを解析（継承されたフィールドも含む）"""
        fields = []
        
        # 基底クラスからフィールドを収集
        for base in class_node.bases:
            if isinstance(base, ast.Name) and base.id.endswith("Base"):
                base_fields = self._get_base_class_fields(base.id)
                fields.extend(base_fields)
        
        # 現在のクラスのフィールドを解析
        for stmt in class_node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                field_info = self._analyze_field_annotation(stmt, field_name)
                if field_info:
                    fields.append(field_info)
        
        return fields
    
    def _get_base_class_fields(self, base_class_name: str) -> List[Dict]:
        """基底クラスのフィールドを取得"""
        # 既に解析済みのテーブルから基底クラスのフィールドを探す
        for table_name, table_info in self.tables.items():
            if table_info["class_name"] == base_class_name:
                return table_info["fields"]
        
        # 基底クラスを新たに解析
        for py_file in self.models_dir.glob("*.py"):
            if py_file.name.startswith("__"):
                continue
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                tree = ast.parse(content)
                for node in ast.walk(tree):
                    if (isinstance(node, ast.ClassDef) and 
                        node.name == base_class_name):
                        fields = []
                        for stmt in node.body:
                            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                                field_name = stmt.target.id
                                field_info = self._analyze_field_annotation(stmt, field_name)
                                if field_info:
                                    fields.append(field_info)
                        return fields
            except:
                continue
        
        return []
    
    def _analyze_field_annotation(self, stmt: ast.AnnAssign, field_name: str) -> Optional[Dict]:
        """フィールドアノテーションを解析"""
        # 型情報の取得
        field_type = self._extract_type(stmt.annotation)
        
        # Relationshipフィールドは除外
        if stmt.value and isinstance(stmt.value, ast.Call):
            if (isinstance(stmt.value.func, ast.Name) and 
                stmt.value.func.id == "Relationship"):
                return None
        
        # Field()の設定を解析
        field_props = {"name": field_name, "type": field_type}
        
        if stmt.value and isinstance(stmt.value, ast.Call):
            if (isinstance(stmt.value.func, ast.Name) and 
                stmt.value.func.id == "Field"):
                field_props.update(self._analyze_field_call(stmt.value))
        
        return field_props
    
    def _extract_type(self, annotation) -> str:
        """型アノテーションから型名を抽出"""
        if isinstance(annotation, ast.Name):
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            if isinstance(annotation.value, ast.Name):
                base_type = annotation.value.id
                if base_type in ["Optional", "List"]:
                    inner_type = self._extract_type(annotation.slice)
                    return f"{base_type}[{inner_type}]"
                return base_type
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        return "Unknown"
    
    def _analyze_field_call(self, call_node: ast.Call) -> Dict:
        """Field()関数呼び出しを解析"""
        props = {}
        
        # キーワード引数を解析
        for keyword in call_node.keywords:
            if keyword.arg == "primary_key" and isinstance(keyword.value, ast.Constant):
                if keyword.value.value:
                    props["primary_key"] = True
            elif keyword.arg == "foreign_key" and isinstance(keyword.value, ast.Constant):
                props["foreign_key"] = keyword.value.value
            elif keyword.arg == "unique" and isinstance(keyword.value, ast.Constant):
                if keyword.value.value:
                    props["unique"] = True
            elif keyword.arg == "index" and isinstance(keyword.value, ast.Constant):
                if keyword.value.value:
                    props["index"] = True
            elif keyword.arg == "description" and isinstance(keyword.value, ast.Constant):
                props["description"] = keyword.value.value
        
        return props
    
    def _analyze_relationships(self, class_node: ast.ClassDef, table_name: str) -> None:
        """リレーションシップを解析"""
        for stmt in class_node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                field_name = stmt.target.id
                
                # Relationshipフィールドを探す
                if (stmt.value and isinstance(stmt.value, ast.Call) and
                    isinstance(stmt.value.func, ast.Name) and
                    stmt.value.func.id == "Relationship"):
                    
                    # 型アノテーションから関連テーブルを推定
                    related_table = self._extract_related_table(stmt.annotation)
                    if related_table:
                        rel_info = {
                            "from_table": table_name,
                            "to_table": related_table,
                            "field_name": field_name,
                            "type": "one_to_many" if "List" in self._extract_type(stmt.annotation) else "many_to_one"
                        }
                        self.relationships.append(rel_info)
    
    def _extract_related_table(self, annotation) -> Optional[str]:
        """型アノテーションから関連テーブル名を抽出"""
        type_str = self._extract_type(annotation)
        
        # Optional[TableName]やList[TableName]から TableName を抽出
        if "[" in type_str and "]" in type_str:
            inner = type_str.split("[")[1].split("]")[0]
            if inner.startswith('"') and inner.endswith('"'):
                inner = inner[1:-1]  # クォートを除去
            table_name = self._to_snake_case(inner)
            # 単数形から複数形に変換
            return self._to_plural_table_name(table_name)
        elif type_str.startswith('"') and type_str.endswith('"'):
            table_name = self._to_snake_case(type_str[1:-1])
            # 単数形から複数形に変換
            return self._to_plural_table_name(table_name)
        
        return None
    
    def _to_plural_table_name(self, table_name: str) -> str:
        """テーブル名を複数形に変換"""
        # 既知のテーブル名マッピング
        plural_mapping = {
            "crop": "crops",
            "weather_area": "weather_areas", 
            "postal_code": "postal_codes",
            "crop_weather_area": "crop_weather_areas",
            "user": "users"
        }
        
        return plural_mapping.get(table_name, table_name + "s")


class MermaidGenerator:
    """Mermaid ER図生成クラス"""
    
    def __init__(self, analyzer: ModelAnalyzer):
        self.analyzer = analyzer
    
    def generate(self) -> str:
        """Mermaid形式のER図を生成"""
        lines = [
            "erDiagram",
            f"    %% 自動生成されたER図 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            ""
        ]
        
        # テーブル定義
        for table_name, table_info in self.analyzer.tables.items():
            lines.append(f"    {table_name} {{")
            
            # フィールドをソート（PKを最初に、その他は名前順）
            sorted_fields = self._sort_fields(table_info["fields"])
            
            for field in sorted_fields:
                field_line = self._format_field(field)
                lines.append(f"        {field_line}")
            
            lines.append("    }")
            lines.append("")
        
        # リレーション（重複除去）
        if self.analyzer.relationships:
            lines.append("    %% Relations")
            unique_relations = self._deduplicate_relationships(self.analyzer.relationships)
            for rel in unique_relations:
                relation_line = self._format_relationship(rel)
                lines.append(f"    {relation_line}")
        
        return "\n".join(lines)
    
    def _format_field(self, field: Dict) -> str:
        """フィールド定義をフォーマット"""
        name = field["name"]
        field_type = self._map_python_type_to_db(field["type"])
        description = field.get("description", "")
        
        # 基本的なフィールド説明を追加
        if not description:
            description = self._get_default_description(name, field_type)
        
        # Mermaid ER図の正しい構文に従う
        base_field = ""
        if field.get("primary_key"):
            base_field = f"{field_type} {name} PK"
        elif field.get("foreign_key"):
            base_field = f"{field_type} {name} FK"
        elif field.get("unique"):
            base_field = f"{field_type} {name} UK"
        else:
            base_field = f"{field_type} {name}"
        
        # 説明があれば追加
        if description:
            return f"{base_field} \"{description}\""
        return base_field
    
    def _get_default_description(self, field_name: str, field_type: str) -> str:
        """フィールド名から推測される説明を生成"""
        descriptions = {
            "id": "主キー",
            "code": "コード",
            "category": "カテゴリ",
            "name": "名前",
            "aliases": "別名・異名リスト",
            "difficulty": "難易度",
            "difficulty_reasons": "難易度の理由",
            "created_at": "作成日時",
            "updated_at": "更新日時",
            "last_login_at": "最終ログイン日時",
            "firebase_uid": "Firebase UID",
            "email": "メールアドレス",
            "display_name": "表示名",
            "photo_url": "プロフィール画像URL",
            "bio": "自己紹介",
            "is_active": "アクティブフラグ",
            "prefecture": "都道府県",
            "region": "地方・区分",
            "data_version": "データバージョン",
            "postal_code": "郵便番号",
            "city": "市区町村",
            "town": "町域",
            "weather_area_id": "気象地域ID",
            "crop_id": "農作物ID",
            "total_processed": "処理総数",
            "errors": "エラー数",
            "import_time": "インポート時刻"
        }
        
        return descriptions.get(field_name, "")
    
    def _map_python_type_to_db(self, python_type: str) -> str:
        """Python型をDB型にマッピング"""
        type_mapping = {
            "int": "int",
            "str": "string",
            "bool": "boolean", 
            "datetime": "datetime",
            "Optional[int]": "int",
            "Optional[str]": "string",
            "Optional[datetime]": "datetime",
            "List[str]": "jsonb",
            "List[Dict]": "jsonb",
        }
        
        return type_mapping.get(python_type, python_type.lower())
    
    def _format_relationship(self, rel: Dict) -> str:
        """リレーション定義をフォーマット"""
        from_table = rel["from_table"]
        to_table = rel["to_table"]
        
        # リレーションタイプに応じて矢印を決定
        if rel["type"] == "one_to_many":
            arrow = "||--o{"
        else:  # many_to_one
            arrow = "}o--||"
        
        return f"{from_table} {arrow} {to_table} : \"{rel['field_name']}\""
    
    def _sort_fields(self, fields: List[Dict]) -> List[Dict]:
        """フィールドをソート（PKを最初に、その他は元の順番）"""
        pk_fields = []
        other_fields = []
        
        for field in fields:
            if field.get("primary_key"):
                pk_fields.append(field)
            else:
                other_fields.append(field)
        
        # PKを最初に、その他は元の順番のまま
        return pk_fields + other_fields
    
    def _deduplicate_relationships(self, relationships: List[Dict]) -> List[Dict]:
        """重複するリレーションを除去"""
        unique_relations = []
        seen_pairs = set()
        
        for rel in relationships:
            from_table = rel["from_table"]
            to_table = rel["to_table"]
            
            # テーブルペアを正規化（アルファベット順でソート）
            # users/user のような単複の違いも考慮
            normalized_from = from_table.rstrip('s') if from_table.endswith('s') else from_table
            normalized_to = to_table.rstrip('s') if to_table.endswith('s') else to_table
            
            pair = tuple(sorted([normalized_from, normalized_to]))
            
            if pair not in seen_pairs:
                seen_pairs.add(pair)
                unique_relations.append(rel)
        
        return unique_relations


def main():
    """メイン処理"""
    try:
        # プロジェクトパス設定
        project_root = Path(__file__).parent
        models_dir = project_root / "app" / "models"
        
        if not models_dir.exists():
            print(f"❌ modelsディレクトリが見つかりません: {models_dir}")
            return
        
        print(f"🔍 modelsディレクトリをスキャン中: {models_dir}")
        
        # モデル解析
        analyzer = ModelAnalyzer(models_dir)
        analyzer.analyze_models()
        
        print(f"📊 発見されたテーブル: {len(analyzer.tables)}")
        for table_name in analyzer.tables.keys():
            print(f"   - {table_name}")
        
        print(f"🔗 発見されたリレーション: {len(analyzer.relationships)}")
        for rel in analyzer.relationships:
            print(f"   - {rel['from_table']} -> {rel['to_table']} ({rel['field_name']})")
        
        # Mermaid図生成
        generator = MermaidGenerator(analyzer)
        erd_content = generator.generate()
        
        # ファイル出力
        output_path = project_root / "ERD.mermaid"
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(erd_content)
        
        print(f"✅ ER図を生成しました: {output_path}")
        print(f"📁 ファイルサイズ: {len(erd_content)} bytes")
        
    except Exception as e:
        print(f"❌ エラーが発生しました: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()