# NPB歴代オーダー編成 — Netlify自動更新版

現在のサイト、選手データ、画像保存、X共有などを含む静的サイト一式です。
GitHub Actionsが毎日06:20（日本時間）に選手データを更新・検査し、成功した場合だけ指定したNetlifyサイトへ公開します。

## 自動更新する情報

- NPB現役選手の在籍・現役／OB判定
- 支配下／育成登録
- 球団公式の登録ポジション
- 当年の一軍・二軍で実際に就いた守備位置
- 生年月日、投打、読み仮名
- NPB通算打撃・投手成績
- MLB経験者のMLB通算打撃・投手成績
- 新しく公式名簿へ追加された選手

過去の所属球団、既存のOB選手データ、手動補正済みデータは保持します。更新元の取得失敗、選手数の異常、ID重複などを検知すると公開処理は停止し、Netlify上の正常な旧版を残します。

## 最初に一度だけ行う設定

### 1. GitHubへ登録

1. GitHubで新しい Private repository を作成します。
2. このZIPを端末で展開します。
3. 展開したフォルダーの中身を、フォルダー構成を維持したままリポジトリへ登録します。
4. GitHubの Settings → Actions → General → Workflow permissions で Read and write permissions を選び、保存します。

重要: ZIPそのものをGitHubへ置くだけでは動きません。.github/workflows/daily-player-update.yml がリポジトリ内に存在する状態にしてください。

### 2. Netlifyの値を確認

既存のNetlifyサイトで次を確認します。

- NETLIFY_SITE_ID: Site configuration（または Project configuration）→ General → Site details の Site ID
- NETLIFY_AUTH_TOKEN: User settings → Applications → Personal access tokens で新規発行

トークンはパスワードと同様の秘密情報です。画面共有や投稿をしないでください。

### 3. GitHubへ秘密情報を登録

GitHubリポジトリの Settings → Secrets and variables → Actions → New repository secret から、次の2件を登録します。

| Name | Secret |
|---|---|
| NETLIFY_SITE_ID | Netlifyで確認したSite ID |
| NETLIFY_AUTH_TOKEN | Netlifyで発行したPersonal access token |

### 4. 初回実行

GitHubの Actions → Daily player data update → Run workflow を押します。
緑のチェックが付けば、同じNetlifyサイトのURLへ更新版が公開されています。以後は毎日自動実行されます。

## 独自ドメイン

Netlifyの Domain management → Add a domain から設定できます。ただし npb-order-builder.sscp.com を使うには、sscp.com の所有者がDNSレコードを変更できることが必要です。

## 手動実行と障害確認

- すぐ更新したい場合: GitHubの Actions 画面から Run workflow
- 失敗した場合: 赤い実行履歴を開き、失敗したステップを確認
- 更新元のページ構造が変わった場合: automation/update_daily.py の解析処理を修正

## 構成

- dist/: Netlifyで公開するサイト
- automation/update_daily.py: NPB名簿・守備・通算成績の更新
- automation/update_mlb.py: MLB通算成績の更新
- automation/validate_database.py: 公開前の安全検査
- .github/workflows/daily-player-update.yml: 毎日の実行とNetlify公開
- netlify.toml: Netlify設定

## 注意

外部サイトのメンテナンスや仕様変更により自動取得が失敗することはあります。その場合は誤ったデータを公開せず停止する設計ですが、完全な無人運用を永久に保証するものではありません。月に一度程度、GitHub Actionsの実行結果を確認してください。
