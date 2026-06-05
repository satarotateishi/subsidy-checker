# 補助金・助成金 新着チェッカー（amu株式会社用）

毎週月曜日に補助金・助成金サイトを自動巡回し、新着情報をメールで通知します。

## 監視対象

| サイト | URL |
|---|---|
| ミラサポplus | https://mirasapo-plus.go.jp/subsidy/ |
| J-Net21 | https://j-net21.smrj.go.jp/headline/ |
| 宮城県 中小企業支援 | https://www.pref.miyagi.jp/soshiki/chusho/ |
| 仙台市 産業振興 | https://www.city.sendai.jp/keizai-sogyo/index.html |

---

## セットアップ手順

### 1. このリポジトリを作成する

1. GitHubで「New repository」をクリック
2. リポジトリ名を `subsidy-checker` などにする（Private推奨）
3. 以下のファイルをアップロード：
   - `checker.py`
   - `.github/workflows/weekly.yml`

### 2. Gmailのアプリパスワードを取得する

1. Googleアカウント → セキュリティ → 2段階認証をON
2. 「アプリパスワード」で16桁のパスワードを生成
3. メモしておく

### 3. GitHub Secretsを設定する

リポジトリの「Settings」→「Secrets and variables」→「Actions」→「New repository secret」で以下を登録：

| Secret名 | 値 |
|---|---|
| `ANTHROPIC_API_KEY` | AnthropicコンソールのAPIキー |
| `GMAIL_ADDRESS` | 送信元のGmailアドレス（例: you@gmail.com） |
| `GMAIL_APP_PASSWORD` | 手順2で取得した16桁のパスワード |
| `NOTIFY_TO` | 通知を受け取るメールアドレス |

### 4. 動作確認

リポジトリの「Actions」タブ → 「補助金 週次チェック」→「Run workflow」で手動実行できます。

---

## 実行スケジュール

- **自動**: 毎週月曜 午前9時（JST）
- **手動**: ActionsタブからRun workflowをクリック

## カスタマイズ

`checker.py` の `KEYWORDS` リストを編集すると、検知するキーワードを変更できます。

```python
KEYWORDS = [
    "補助金", "助成金", "公募", ...  # ← ここに追加・削除
]
```
