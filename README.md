# Controller Mapper

フライトスティック入力補正・変換アプリ

## 概要

物理コントローラ（フライトスティック、スロットル、ラダーペダルなど）の入力を読み取り、
ノイズ除去・軸補正・変換を行ったうえで仮想コントローラ（vJoy）へ出力するGUIアプリです。

使用するだけなら、[vJoy](https://github.com/jshafer817/vJoy) をインスト―ルしたのち、releaseからzipファイルをダウンロードして、exeファイルを起動するだけで使用できます。

## 必要環境

- Python 3.11 以上
- Windows 11（vJoy出力を使う場合） または Linux / macOS（モニタのみ）
- vJoyドライバ（仮想コントローラ出力を使う場合）

補足: Python 3.14 では通常の `pygame` に対応wheelがないため、
このプロジェクトでは互換パッケージの `pygame-ce` を使用します。
コード上の `import pygame` はそのまま動作します。

## インストール

```powershell
# 仮想環境の作成例
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip

# 開発インストール
.\.venv\Scripts\python.exe -m pip install -e .

# テストやビルドも行う開発環境
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

`requirements.txt` には通常起動に必要な依存のみを記載しています。
vJoy出力やexeビルド用の依存は optional dependencies として `pyproject.toml` に定義しています。

## 起動

```powershell
.\.venv\Scripts\python.exe -m controller_mapper
# または
controller-mapper
```

## exe化（Windows）

```powershell
# ビルド用依存のインストール込みでexeを作成
.\scripts\build_exe.ps1 -InstallDeps -Clean
```

生成物は `dist\controller-mapper\controller-mapper.exe` です。
`profiles\*.yaml` は配布フォルダ内の `_internal\profiles\` に同梱されます。
配布するときは `controller-mapper.exe` 単体ではなく、`dist\controller-mapper\` フォルダ一式をコピーしてください。

## vJoy出力を使う場合（Windows）

1. [vJoy](https://github.com/jshafer817/vJoy) をインストール
2. `.\.venv\Scripts\python.exe -m pip install -e .[vjoy]` を実行
3. プロファイルの `output.type` を `vjoy` に設定

## プロファイル

`profiles/` ディレクトリにYAMLファイルを配置します。
サンプル：`profiles/DCS.yaml`

## ディレクトリ構成

```
controller-mapper/
  packaging/      # PyInstaller spec
  scripts/        # ビルド補助スクリプト
  src/controller_mapper/
    app/          # GUIパネル
    core/         # パイプライン・状態管理
    filters/      # デバウンス・デッドゾーン・カーブ等
    transforms/   # 軸↔ボタン変換
    input_backends/   # pygame入力
    output_backends/  # vJoy等出力
    config/       # YAMLスキーマ・ローダー
  profiles/       # YAMLプロファイル
  tests/          # 単体テスト
```

## テスト

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest
```

## 注意事項

- vJoyはWindows 10/11向けフォーク版の使用を推奨します
- 対戦ゲームでの使用はアンチチートに検出される可能性があります
- シミュレータ（DCS、MSFS等）での使用を主対象としています
