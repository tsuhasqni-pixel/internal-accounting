# 内部管理会計ツール（標準原価・差異分析・CVP）

**ライブ版（インストール不要）**: https://tsuhasqni-pixel.github.io/internal-accounting/

社内利用向けの**管理会計**ミニアプリ。製品マスタに**標準原価カード**または**簡易予算**を登録し、実際値を入れると**原価差異**と**損益分岐点（CVP）**を自動計算する。

2つの動かし方:

- **ブラウザ版（`docs/`）** — GitHub Pages で配信。JS で計算、データは localStorage に保存。リンクひとつで誰でも開ける。
- **Python 版（`app.py`）** — Flask サーバー。複数端末からの共有や CSV エクスポート拡張など、サーバー側処理が欲しい場合用。

## 主な機能

- **標準原価カード**の登録 — 材料 BOM、労務、製造間接費（OH）の標準値
- **差異分析の自動計算**
  - 詳細モード: 材料2分法（価格・数量）、労務2分法（賃率・時間）、製造間接費3分法（変動予算・能率・固定予算・操業度）
  - 簡易モード: 総差異（建築・受注案件など BOM 展開できないケース）
  - **製品ごとに両モードを切り替え**可能
- **CVP / 段階別損益・損益分岐点分析**
  - 売上明細を**製品別に「販売単価 × 数量」**で入力
  - **単位変動費を標準原価カードから自動取込**（DM + DL + 変動OH）
  - 段階別利益: 売上 → 変動費 → **限界利益** → 個別固定費 → **貢献利益** → 共通固定費 → **営業利益**
  - 全社 blended の **BEP・安全余裕率**
- すべて **HTML UI**（Flask + Jinja2 + Chart.js / GitHub Pages 版は静的SPA）

## 起動

### macOS

```bash
./start.command
```

ダブルクリックでも起動可能。`.venv` を自動作成、依存をインストールし、`http://127.0.0.1:7862` を開く。

### Linux / その他

```bash
./start.sh
```

### Windows

`start.bat` をダブルクリック。

### 手動

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python app.py
```

## 使い方

1. **製品 / 標準原価カード** タブで製品を作成
   - `詳細` モード: 材料・労務・OH の標準値を入力
   - `簡易` モード: 案件全体の予算総額（または材料/労務/経費別）を入力
2. **実績入力** タブで期間ごとの実際値を入力
3. **差異分析**画面に各差異が自動表示される
4. **CVP** タブで売上・変動費・固定費を入力 → BEP が表示
5. CVP 画面で「不利差異を取り込む」製品を選ぶと、**差異を固定費に加算した調整後 BEP** とシフト幅が表示される

## 差異の符号規約

- 値が **正 → 不利（実際 > 標準）**
- 値が **負 → 有利（実際 < 標準）**

教科書通り `実際 − 標準` で統一しているため、ウォーターフォール表示で「コストの増減」として直感的に読める。

## ファイル構成

```
internal-accounting/
├─ app.py                   Flask エントリ
├─ core/
│   ├─ models.py            データクラス定義
│   ├─ storage.py           JSON 永続化（data/ 配下）
│   ├─ variance.py          差異計算（detailed / simple）
│   ├─ cvp.py               CVP・BEP・BEP シフト
│   └─ reports.py           HTML 描画用整形
├─ templates/               Jinja2 テンプレート
├─ static/                  CSS / JS（Chart.js は CDN）
├─ data/                    ユーザーデータ（gitignore）
└─ tests/                   pytest（教科書例題の検算）
```

## テスト

```bash
source .venv/bin/activate
python -m pytest tests/ -v
```

または

```bash
python tests/test_variance.py
python tests/test_cvp.py
```

## ライセンス

社内利用前提のためライセンス未指定。
