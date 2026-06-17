# ソースコードの扱い方

このページは、Controller Mapperをソースコードから起動、開発、テスト、ビルドする人向けです。Release zipを使うだけの場合は [README.md](../README.md) を参照してください。

## 必要環境

- Python 3.11以上
- Windows 11
- vJoyドライバ
- Git

vJoy出力を使わず入力モニタやGUI確認だけを行う場合は、Linux / macOSでも一部機能を確認できます。ただし、配布exeとvJoy出力はWindows向けです。

補足: Python 3.14では通常の `pygame` に対応wheelがないため、このプロジェクトでは互換パッケージの `pygame-ce` を使用します。コード上の `import pygame` はそのまま動作します。

## 開発環境の作成

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -e .
```

テストやビルドも行う場合:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[dev]
```

vJoy出力をソース実行で使う場合:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[vjoy]
```

`requirements.txt` には通常起動に必要な依存のみを記載しています。vJoy出力、テスト、exeビルド用の依存は `pyproject.toml` の optional dependencies に定義しています。

## ソースから起動

```powershell
.\.venv\Scripts\python.exe -m controller_mapper
```

開発インストール後は、環境によって次でも起動できます。

```powershell
controller-mapper
```

`controller-mapper` で次のようなエラーが出る場合は、仮想環境内のコマンドランチャーが古いPythonパスを参照しています。

```text
Fatal error in launcher: Unable to create process using ...
```

プロジェクトフォルダや `.venv` を移動、コピー、リネームしたあとに起きます。現在の仮想環境で再インストールしてください。

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
```

それでも直らない場合は、`.venv` を作り直してから再度インストールしてください。

## プロファイル

プロファイルは `profiles/` ディレクトリにYAMLファイルとして置きます。

同梱サンプル:

```text
profiles\DCS.yaml
```

ソース実行時に `Dashboard` の `プロファイル読み込み` からこのファイルを選ぶと、GUI上で編集できます。

## テスト

```powershell
.\.venv\Scripts\python.exe -m pip install -e .[test]
.\.venv\Scripts\python.exe -m pytest
```

## exeビルド

WindowsでPyInstallerを使ってexeを作成します。

```powershell
.\scripts\build_exe.ps1 -InstallDeps -Clean
```

生成物:

```text
dist\controller-mapper\controller-mapper.exe
```

`profiles\*.yaml` は配布フォルダ内の `_internal\profiles\` に同梱されます。

Release zipを作る場合は、`dist\controller-mapper\` フォルダをzip化します。現在のRelease名は次の形式です。

```text
dist\controller-mapper-v0.1.0-win-x64.zip
```

## ディレクトリ構成

```text
controller-mapper/
  README.md             # Release利用者向け説明
  docs/
    source.md           # ソースコード利用者向け説明
  packaging/            # PyInstaller spec
  scripts/              # ビルド補助スクリプト
  src/controller_mapper/
    app/                # GUIパネル
    core/               # パイプライン・状態管理
    filters/            # デバウンス・デッドゾーン・カーブ等
    transforms/         # 軸/ボタン変換
    input_backends/     # pygame入力
    output_backends/    # vJoy等出力
    config/             # YAMLスキーマ・ローダー
    logging/            # ログ設定
  profiles/             # YAMLプロファイル
  tests/                # 単体テスト
```

## vJoy出力を使う場合

1. vJoyをインストールします。
2. Windowsを再起動します。
3. vJoy Deviceを有効化します。
4. `.\.venv\Scripts\python.exe -m pip install -e .[vjoy]` を実行します。
5. プロファイルの `output.type` を `vjoy`、`output.device_id` を使うvJoy Device番号に設定します。

vJoyが使えない環境では、プロファイルの `output.type` を `null` にするとテストモードとして動かせます。

## 設計メモ

詳細な設計背景は [controller_mapper_design.md](../controller_mapper_design.md) にあります。主な流れは次の通りです。

```text
Input Backend -> Filters -> Transform / Mapping -> Output Backend
```

GUIスレッドとは別にスケジューラが入力取得、変換、出力を行い、GUIは状態キューを読んで表示を更新します。

## 注意事項

- `dist\controller-mapper\_internal` はPyInstallerの実行時依存を含みます。
- Release向けzipには `controller-mapper.exe` 単体ではなく、`controller-mapper` フォルダ全体を含めてください。
- 対戦ゲームでの利用はアンチチートに検出される可能性があります。
- 既存プロファイルのデバイスIDは環境ごとに変わることがあります。`Devices` タブでIDを確認して調整してください。
