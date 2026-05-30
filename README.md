# Controller Mapper

フライトスティック入力補正・変換アプリ

## 概要

物理コントローラ（フライトスティック、スロットル、ラダーペダルなど）の入力を読み取り、
ノイズ除去・軸補正・変換を行ったうえで仮想コントローラ（vJoy）へ出力するGUIアプリです。

## 必要環境

- Python 3.11 以上
- Windows 11（vJoy出力を使う場合） または Linux / macOS（モニタのみ）
- vJoyドライバ（仮想コントローラ出力を使う場合）

## インストール

```bash
# 依存ライブラリのインストール
pip install -r requirements.txt

# 開発インストール
pip install -e .
```

## 起動

```bash
python -m controller_mapper
# または
controller-mapper
```

## vJoy出力を使う場合（Windows）

1. [vJoy](https://github.com/shauleiz/vJoy) をインストール
2. `pip install pyvjoy` を実行
3. `requirements.txt` の `# pyvjoy` 行のコメントアウトを解除

## プロファイル

`profiles/` ディレクトリにYAMLファイルを配置します。
サンプル：`profiles/dcs_f16_x56.yaml`

## ディレクトリ構成

```
controller-mapper/
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

```bash
pytest tests/ -v
```

## 注意事項

- vJoyはWindows 10/11向けフォーク版の使用を推奨します
- 対戦ゲームでの使用はアンチチートに検出される可能性があります
- シミュレータ（DCS、MSFS等）での使用を主対象としています
