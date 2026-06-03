# フライトスティック入力補正・変換アプリ 設計書

推奨ファイル名：`controller_mapper_design.md`

作成日：2026-05-30

---

## 1. 目的

本アプリは，フライトスティック，スロットル，ラダーペダル，ゲームパッドなどの物理コントローラ入力を読み取り，ノイズ除去，軸補正，ボタン化，軸化，モード切替などを行った上で，仮想コントローラとしてゲームやシミュレータに出力するGUIアプリである．

特に以下を解決対象とする．

- 押していないボタンが一瞬ONになるチャタリング・ノイズの除去
- 軸入力のデッドゾーン，カーブ，反転，スケーリング
- 軸入力をボタン入力に変換
- ボタン入力を軸入力に変換
- 複数ボタンの組み合わせ，モード切替，レイヤー切替
- 物理デバイスと仮想デバイスの二重入力対策

注意点として，「Pythonプログラムだけで既存のコントローラ入力をゲーム側で直接書き換える」構成は基本的に現実的ではない．実際には，物理デバイスを読み取り，変換後の値をvJoyなどの仮想デバイスに出力し，必要に応じてHidHideで物理デバイスをゲームから隠す構成にするのが堅い．

---

## 2. 想定環境

主対象はWindows 11である．DCS World，Microsoft Flight Simulator，War Thunder，Elite Dangerous，Star Citizenなど，DirectInputまたは仮想ジョイスティック入力を受け取れるソフトを想定する．

GUIはPySide6を採用する．PySide6はQt for Pythonの公式Pythonバインディングであり，Qt6 APIをPythonから利用できる．

入力取得は，MVPでは`pygame.joystick`またはSDL系入力を使う．pygameのジョイスティック機能は，軸，ボタン，Hat/D-padを扱えるため，最初の試作には向いている．

出力は，まずvJoyを第一候補にする．vJoyは仮想ジョイスティックドライバであり，HOTAS用途ではXInputより軸数・ボタン数の面で扱いやすい．ただし，元のvJoyリポジトリはWindows 7からWindows 10 1803までの対応と明記され，新しいWindows向けにはフォークを参照するよう記載されているため，Windows 11環境での動作確認が必要である．

Xbox 360コントローラやDualShock 4として見せたい場合はViGEm系が候補になるが，ViGEmBus本体は2023年11月2日にアーカイブされ，現在は読み取り専用である．したがって，今から新規設計の中核に置くのは避けた方がよい．

---

## 3. 全体構成

```text
[物理コントローラ]
       ↓
[Input Backend]
       ↓
[Raw Input State]
       ↓
[Filter Layer]
  - debounce
  - deadzone
  - smoothing
  - hysteresis
       ↓
[Mapping Engine]
  - button → button
  - axis → axis
  - axis → button
  - button → axis
  - mode / layer
       ↓
[Output Backend]
       ↓
[仮想コントローラ]
       ↓
[ゲーム / シミュレータ]
```

二重入力が起きる場合は以下の構成にする．

```text
[物理コントローラ]
       ↓
[本アプリだけが読む]
       ↓
[変換]
       ↓
[vJoy等の仮想コントローラ]
       ↓
[ゲームが読む]

※ HidHideで物理コントローラをゲームから隠す
```

---

## 4. 機能要件

### 4.1 デバイス検出

アプリ起動時に接続済みデバイスを一覧表示する．

表示項目：

- デバイス名
- GUIDまたはインスタンスID
- 軸数
- ボタン数
- Hat数
- 入力バックエンド名
- 最終入力時刻

接続後のホットプラグ対応はMVPでは必須にしない．最初は「再スキャン」ボタンで十分である．

---

### 4.2 入力モニタ

GUI上で生入力と加工後入力を同時表示する．

例：

```text
Physical Stick
Axis X: raw = 0.034，filtered = 0.000
Axis Y: raw = -0.512，filtered = -0.486
Button 12: raw = OFF，debounced = OFF
Button 13: raw = ON，debounced = ON
Hat 0: UP
```

この画面は最重要である．入力モニタがないと，変換ルールを作っても，誤動作の原因が物理入力なのか，フィルタなのか，マッピングなのか分からなくなる．

---

### 4.3 ボタンノイズ除去

ボタン入力に対して以下を設定できるようにする．

| 機能 | 内容 |
|---|---|
| デバウンス | 状態が一定時間安定するまでON/OFFを確定しない |
| 最小ON時間 | 短すぎるONパルスを無視する |
| 最小OFF時間 | 短すぎるOFF抜けを無視する |
| 長押し判定 | 一定時間以上押された場合のみON扱い |
| エッジ検出 | 押した瞬間だけ，離した瞬間だけを出力 |
| トグル化 | 押すたびにON/OFF反転 |

推奨初期値：

```text
debounce_ms = 30
minimum_on_ms = 20
minimum_off_ms = 20
```

兵装投下，ギア，フラップなどの誤爆が困る入力は`debounce_ms = 50〜100 ms`でもよい．一方，トリガーや視点操作は遅延が気になるため，重くしすぎない．

---

### 4.4 軸補正

軸入力に対して以下を設定できるようにする．

| 機能 | 内容 |
|---|---|
| キャリブレーション | 最小値，中央値，最大値を保存 |
| デッドゾーン | 中央付近の微小入力を0にする |
| エンドデッドゾーン | 端付近を最大値に張り付ける |
| 反転 | 入力方向を逆にする |
| 感度 | 出力倍率を変える |
| カーブ | 指数カーブ，S字カーブなど |
| スムージング | 急な揺れを少しならす |
| ヒステリシス | 閾値付近のON/OFF振動を防ぐ |
| 飽和 | 出力範囲を制限する |

重要なのは，主操縦軸に強いスムージングをかけすぎないことである．ノイズは減るが，操縦遅れが出る．DCSなどで使うなら，主軸はデッドゾーンとカーブ中心，ボリューム・ダイヤル・スライダー類はスムージング強め，という分け方がよい．

---

## 5. 変換ルール

### 5.1 button → button

物理ボタンを仮想ボタンへ割り当てる．

```yaml
- name: trigger_to_fire
  input:
    device: x56_stick
    type: button
    index: 0
  output:
    device: vjoy1
    type: button
    index: 1
  filters:
    debounce_ms: 20
```

---

### 5.2 axis → axis

物理軸を仮想軸へ割り当てる．

```yaml
- name: stick_x_to_roll
  input:
    device: x56_stick
    type: axis
    index: 0
  output:
    device: vjoy1
    type: axis
    name: x
  filters:
    deadzone: 0.03
    curve: 1.5
    invert: false
```

---

### 5.3 axis → button

軸が一定以上動いたらボタンONにする．

例：スロットルの小さいダイヤルを3ポジションスイッチとして使う．

```yaml
- name: throttle_slider_to_airbrake_extend
  input:
    device: x56_throttle
    type: axis
    index: 3
  output:
    device: vjoy1
    type: button
    index: 20
  transform:
    type: axis_to_button
    on_threshold: 0.65
    off_threshold: 0.50
```

ここでは`on_threshold`と`off_threshold`を分けている．これが重要で，単一閾値だけにすると，0.60付近で入力が振動したときにON/OFFが連打される．この対策がヒステリシスである．

2方向に割り当てる場合：

```yaml
- name: rotary_axis_to_two_buttons
  input:
    device: x56_throttle
    type: axis
    index: 4
  transform:
    type: axis_to_dual_button
    negative:
      output_button: 21
      on_threshold: -0.60
      off_threshold: -0.45
    positive:
      output_button: 22
      on_threshold: 0.60
      off_threshold: 0.45
```

---

### 5.4 button → axis

ボタンを押したら軸値を出す．

用途例：

- ボタンを押している間だけ仮想軸を最大にする
- 2つのボタンで仮想軸を左右に動かす
- ボタンを押している間，徐々に軸値を増やす
- トグルスイッチを仮想スライダーとして扱う

例：ボタンを押したら軸を最大値にする．

```yaml
- name: button_to_brake_axis
  input:
    device: x56_stick
    type: button
    index: 5
  output:
    device: vjoy1
    type: axis
    name: rz
  transform:
    type: button_to_axis
    released_value: 0.0
    pressed_value: 1.0
```

例：2ボタンで1軸を操作する．

```yaml
- name: trim_buttons_to_axis
  input:
    device: x56_stick
    type: button_pair
    negative_index: 7
    positive_index: 8
  output:
    device: vjoy1
    type: axis
    name: slider1
  transform:
    type: buttons_to_axis
    mode: ramp
    speed_per_sec: 0.8
    return_to_center: false
```

---

## 6. モード・レイヤー機能

HOTASでは同じボタンをモード別に使いたくなるため，レイヤー機能を入れる．

例：

```text
Mode 0: Navigation
Mode 1: Air-to-Air
Mode 2: Air-to-Ground
Mode 3: UI / VR操作
```

モード切替方式：

- 指定ボタンを押すたびにモード循環
- 指定ボタンを押している間だけ一時レイヤー
- 物理3ポジションスイッチでモード選択
- 軸の位置でモード選択

設計上は，入力イベントに対して現在のモードを付与してからMapping Engineに渡す．

```text
raw_input + current_mode → mapping_rule → virtual_output
```

---

## 7. GUI設計

### 7.1 画面構成

```text
+--------------------------------------------------+
| Device Mapper                                    |
+-------------------+------------------------------+
| Devices           | Live Monitor                  |
| - X56 Stick       | Axis / Button / Hat           |
| - X56 Throttle    | Raw / Filtered / Output       |
| - Pedals          |                              |
+-------------------+------------------------------+
| Profiles          | Mapping Editor                |
| - DCS_F16.yaml    | input → filter → transform    |
| - MSFS.yaml       | output                        |
+-------------------+------------------------------+
| Status: Running / Stopped / vJoy connected       |
+--------------------------------------------------+
```

### 7.2 主要タブ

| タブ | 内容 |
|---|---|
| Dashboard | 接続状態，現在プロファイル，開始・停止 |
| Devices | 物理デバイス一覧，入力モニタ |
| Calibration | 軸の最小・中央・最大の設定 |
| Mapping | 入力と出力の割り当て |
| Filters | デバウンス，デッドゾーン，カーブ |
| Modes | モード・レイヤー設定 |
| Output | vJoyなど仮想デバイスの状態 |
| Logs | エラー，入力検出，プロファイル読み込み結果 |

---

## 8. 内部データ構造

### 8.1 入力状態

```python
@dataclass
class DeviceState:
    axes: dict[int, float]      # -1.0〜1.0
    buttons: dict[int, bool]
    hats: dict[int, tuple[int, int]]

@dataclass
class InputState:
    timestamp: float
    devices: dict[str, DeviceState]
```

### 8.2 加工後状態

```python
@dataclass
class FilteredState:
    timestamp: float
    devices: dict[str, DeviceState]
```

### 8.3 出力状態

```python
@dataclass
class OutputState:
    axes: dict[str, float]
    buttons: dict[int, bool]
    hats: dict[int, tuple[int, int]]
```

---

## 9. 処理周期

目標周期：

```text
入力取得：250〜1000 Hz相当
変換処理：250〜1000 Hz相当
GUI更新：30〜60 Hz
出力更新：250〜1000 Hz相当
```

GUI更新と入力処理を同じスレッドで行うとカクつくため，以下のように分ける．

```text
Main GUI Thread
  - PySide6
  - 設定編集
  - 状態表示

Input Worker Thread
  - 物理入力のポーリング
  - Raw Input State更新

Mapping Worker Thread
  - フィルタ
  - 変換
  - Output State生成

Output Worker Thread
  - vJoy等への書き込み
```

MVPではInput，Mapping，Outputを1つのワーカースレッドにまとめてもよい．ただしGUIスレッドに入れてはいけない．

---

## 10. 推奨技術構成

| 用途 | 第一候補 | 備考 |
|---|---|---|
| GUI | PySide6 | 公式Qt for Python．見た目と保守性がよい |
| 入力取得 | pygame.joystick | 試作しやすい．軸・ボタン・Hatを扱える |
| 詳細HID入力 | hidapi系 | デバイス固有処理が必要になったら検討 |
| 仮想ジョイスティック出力 | vJoy + pyvjoy系 | HOTAS向き．Windows 11では動作確認必須 |
| 仮想Xbox出力 | ViGEm系 | 便利だがプロジェクト終了済みなので中核にはしない |
| 物理デバイス隠蔽 | HidHide | 二重入力対策 |
| 設定ファイル | YAML | 手編集しやすい |
| ログ | Python logging | バグ解析に必須 |
| 配布 | PyInstaller | exe化候補 |

---

## 11. プロファイル形式案

```yaml
profile:
  name: DCS_F16_X56
  version: 1

devices:
  x56_stick:
    match:
      name_contains: "X56"
      role: stick

  x56_throttle:
    match:
      name_contains: "X56"
      role: throttle

output:
  type: vjoy
  device_id: 1

global:
  update_rate_hz: 500
  gui_rate_hz: 30

modes:
  default: nav
  definitions:
    - nav
    - aa
    - ag

rules:
  - name: roll
    mode: "*"
    input:
      device: x56_stick
      type: axis
      index: 0
    filters:
      deadzone: 0.03
      curve: 1.3
      invert: false
    output:
      type: axis
      name: x

  - name: pitch
    mode: "*"
    input:
      device: x56_stick
      type: axis
      index: 1
    filters:
      deadzone: 0.03
      curve: 1.4
      invert: true
    output:
      type: axis
      name: y

  - name: noisy_button_fix
    mode: "*"
    input:
      device: x56_throttle
      type: button
      index: 12
    filters:
      debounce_ms: 50
      minimum_on_ms: 30
    output:
      type: button
      index: 12

  - name: slider_to_speedbrake
    mode: "*"
    input:
      device: x56_throttle
      type: axis
      index: 3
    transform:
      type: axis_to_button
      on_threshold: 0.65
      off_threshold: 0.50
    output:
      type: button
      index: 20
```

---

## 12. モジュール設計

推奨ディレクトリ構成：

```text
controller-mapper/
  README.md
  pyproject.toml
  requirements.txt

  src/
    controller_mapper/
      __init__.py
      main.py

      app/
        main_window.py
        device_panel.py
        monitor_panel.py
        mapping_editor.py
        calibration_panel.py
        log_panel.py

      core/
        state.py
        pipeline.py
        scheduler.py
        profile.py
        errors.py

      input_backends/
        base.py
        pygame_backend.py
        hid_backend.py

      output_backends/
        base.py
        vjoy_backend.py
        vigem_backend.py

      filters/
        debounce.py
        deadzone.py
        smoothing.py
        hysteresis.py
        curve.py

      transforms/
        button_to_button.py
        axis_to_axis.py
        axis_to_button.py
        button_to_axis.py
        mode_switch.py

      config/
        schema.py
        loader.py
        validator.py

      logging/
        log_config.py

  profiles/
    dcs_f16_x56.yaml
    msfs_general.yaml

  tests/
    test_debounce.py
    test_axis_to_button.py
    test_button_to_axis.py
    test_deadzone.py
```

---

## 13. MVP実装範囲

最初から全部作ると破綻しやすいので，MVPは絞るべきである．

### MVP 1：入力確認アプリ

- 物理コントローラ一覧表示
- 軸・ボタン・Hatのリアルタイム表示
- ログ表示
- プロファイル保存なし

ここで入力が安定して読めるか確認する．

### MVP 2：ボタンノイズ除去

- ボタンのデバウンス
- 最小ON時間
- 最小OFF時間
- 加工後状態の表示

### MVP 3：vJoy出力

- button → button
- axis → axis
- vJoyへの出力
- ゲーム側で認識確認

### MVP 4：軸・ボタン相互変換

- axis → button
- button → axis
- ヒステリシス
- YAMLプロファイル読み込み

### MVP 5：GUIマッピングエディタ

- GUIからルール追加
- GUIから閾値編集
- プロファイル保存
- 入力を動かして「この入力を割り当て」機能

---

## 14. テスト方針

### 14.1 単体テスト

特に以下はテスト必須．

- デバウンス処理
- ヒステリシス処理
- デッドゾーン処理
- カーブ処理
- axis → button変換
- button → axis変換
- モード切替

例：ボタンノイズテスト

```text
入力：
OFF, OFF, ON(5ms), OFF, OFF

期待：
ずっとOFF
```

例：ヒステリシステスト

```text
on_threshold = 0.65
off_threshold = 0.50

入力：
0.60 → 0.66 → 0.62 → 0.51 → 0.49

期待：
OFF → ON → ON → ON → OFF
```

---

## 15. リスクと注意点

### 15.1 二重入力問題

ゲームが物理デバイスと仮想デバイスの両方を認識すると，同じ操作が二重に入る．この場合はHidHideを使って物理デバイスをゲームから隠す設計にする．

### 15.2 vJoyの保守状況

vJoyはHOTAS用途では便利だが，元リポジトリはWindows 10 1803までを対象としている．Windows 11で安定運用するには，実際に使うvJoyビルド，署名済みドライバ，pyvjoy互換性を先に検証する必要がある．

### 15.3 ViGEm依存

ViGEmBusはXbox 360コントローラやDualShock 4のエミュレーションに向くが，リポジトリがアーカイブ済みであるため，今から依存度を高くするのは危険である．使うなら「対応ゲームがXInputしか受けない場合の追加出力」として扱う方がよい．

### 15.4 アンチチート

一部ゲームでは仮想入力，ドライバ，入力変換ツールがアンチチートに嫌われる可能性がある．DCSやMSFSのようなシミュレータ用途を主対象にし，対戦ゲーム向けのマクロ・自動化機能は避けるべきである．

### 15.5 遅延

入力補正を増やすほど遅延が増える．特に操縦桿のpitch/roll/yawには重いスムージングをかけない方がよい．一方，スロットルのロータリーダイヤルやモードスイッチには多少の遅延があっても問題になりにくい．

---

## 16. 最初に作るべきプロトタイプ

最初に作るべき最小構成はこれである．

```text
PySide6 GUI
  ↓
pygame.joystickで入力取得
  ↓
入力モニタ表示
  ↓
ボタンにdebounce_msを適用
  ↓
axis → button変換を1つ実装
  ↓
vJoyへ出力
```

最初からHidHide連携やViGEm出力まで入れると，ドライバ問題とGUI問題と変換ロジック問題が同時に来る．まずは「入力が読める」「変換できる」「仮想デバイスへ出せる」の3点だけを固めるのがよい．

---

## 17. 参考資料

- Qt for Python / PySide6公式ドキュメント  
  https://doc.qt.io/qtforpython-6/index.html

- pygame.joystick公式ドキュメント  
  https://www.pygame.org/docs/ref/joystick.html

- vJoy GitHub  
  https://github.com/shauleiz/vJoy

- pyvjoy GitHub  
  https://github.com/tidzo/pyvjoy

- HidHide GitHub  
  https://github.com/nefarius/HidHide

- ViGEmBus GitHub  
  https://github.com/nefarius/ViGEmBus

- Microsoft XInput Game Controller APIs  
  https://learn.microsoft.com/en-us/windows/win32/xinput/xinput-game-controller-apis-portal

- PyInstaller Manual  
  https://www.pyinstaller.org/

---

## 18. 補足：この設計の実装上の優先順位

1. 入力モニタを作る
2. ボタンのデバウンスを実装する
3. 軸のデッドゾーンとカーブを実装する
4. axis → buttonを実装する
5. button → axisを実装する
6. vJoy出力を実装する
7. YAMLプロファイルを読み込む
8. GUIでマッピングを編集できるようにする
9. HidHideを使った二重入力対策を手順化する
10. PyInstallerで配布可能にする

この順番を守るべきである．特に，GUIマッピングエディタを先に作ると，見た目は進むが肝心の入力処理が固まらず，後から作り直しになりやすい．
