import streamlit as st
import pandas as pd
import json
import base64
import requests
from datetime import datetime

# ページ設定
st.set_page_config(page_title="SADASAPO eBay物販アシスタント", layout="wide")

st.title("🛍️ メルカリ → eBay 利益計算 & GitHub同期ツール")
st.markdown("メルカリのURLを入力し、eBay向けの英語翻訳と利益率（目標15%以上）を自動計算してGitHubへ保存します。")

# GitHub設定（必要に応じてStreamlitのSecretsや入力欄で管理）
st.sidebar.header("⚙️ GitHub連携設定")
github_token = st.sidebar.text_input("GitHub Personal Access Token", type="password")
repo_name = st.sidebar.text_input("リポジトリ名", value="Neo403zz/mercari-selestpro")
file_path = st.sidebar.text_input("保存先ファイルパス", value="data/sourced_products.json")

# 入力フォーム
st.header("1. メルカリ商品情報の入力")
mercari_url = st.text_input("メルカリの商品URLを入力してください", placeholder="https://jp.mercari.com/item/mXXXXXXXXX")

col1, col2 = st.columns(2)

with col1:
    item_title_jp = st.text_input("商品タイトル（日本語）", value="【チェンソーマン】ねんどろいど デンジ フィギュア")
    purchase_price = st.number_input("国内仕入価格 (JPY)", min_value=0, value=1800, step=100)
    
with col2:
    item_category = st.selectbox("カテゴリ・仕様", ["ねんどろいど (Nendoroid)", "一番くじ (MASTERLISE)", "プライズ・その他フィギュア"])
    box_size = st.selectbox("箱・サイズ区分", ["60サイズ (小型軽量・箱なし等)", "80サイズ (標準フィギュア箱あり)", "100サイズ以上 (大型)"])

# 翻訳・計算ロジック
st.header("2. 自動翻訳 & 利益計算シミュレーション")

if st.button("🔄 計算・翻訳を実行する", type="primary"):
    # 簡易翻訳ロジック（フィギュア特化型）
    translated_title = ""
    if "ねんどろいど" in item_category:
        translated_title = f"Nendoroid {item_title_jp.replace('【チェンソーマン】', 'Chainsaw Man ').replace('ねんどろいど', '').strip()} Good Smile Company Japan"
    elif "一番くじ" in item_category:
        translated_title = f"Ichiban Kuji MASTERLISE {item_title_jp.replace('一番くじ', '').strip()} Figure Japan"
    else:
        translated_title = f"Anime Figure {item_title_jp} Authentic Japan"

    # 送料設定
    shipping_jpy = 3000 if "60サイズ" in box_size else (3600 if "80サイズ" in box_size else 5000)
    shipping_usd = shipping_jpy / 150.0

    # 想定eBay販売価格の自動提案（仕入 + 送料から逆算、または目安$110）
    suggested_ebay_usd = 110.0
    exchange_rate = 150.0
    sales_jpy = suggested_ebay_usd * exchange_rate
    
    # 手数料計算 (eBay 13.5% + Payoneer 2.0% = 15.5%)
    ebay_fee_jpy = sales_jpy * 0.135
    payoneer_fee_jpy = sales_jpy * 0.02
    
    # 純利益・利益率
    net_profit_jpy = sales_jpy - (purchase_price + shipping_jpy + ebay_fee_jpy + payoneer_fee_jpy)
    profit_margin = (net_profit_jpy / sales_jpy) * 100
    
    # セッション状態に保存
    st.session_state['result'] = {
        "mercari_url": mercari_url,
        "title_jp": item_title_jp,
        "title_en": translated_title,
        "purchase_price": purchase_price,
        "ebay_usd": suggested_ebay_usd,
        "sales_jpy": sales_jpy,
        "shipping_jpy": shipping_jpy,
        "net_profit_jpy": int(net_profit_jpy),
        "profit_margin": round(profit_margin, 1),
        "status": "OK" if profit_margin >= 15.0 else "NG",
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    st.success("計算と英語翻訳が完了しました！")

# 結果表示と保存
if 'result' in st.session_state:
    res = st.session_state['result']
    
    st.markdown("---")
    st.subheader("📊 シミュレーション結果確認")
    
    col_a, col_b, col_c = st.columns(3)
    col_a.metric("想定eBay売価", f"${res['ebay_usd']:.2f} (約¥{res['sales_jpy']:,.0f})")
    col_b.metric("見込み純利益", f"¥{res['net_profit_jpy']:,}支持")
    col_c.metric("利益率", f"{res['profit_margin']}%", "目標15%以上" if res['status']=="OK" else "基準未満")
    
    st.text_input("【eBay用】英語翻訳タイトル", value=res['title_en'])
    
    if res['status'] == "OK":
        st.success("✅ 利益基準（15%以上）をクリアしています。「GitHubに保存」ボタンを押してください。")
    else:
        st.warning("⚠️ 利益率が15%未満です。仕入価格や販売価格を見直してください。")

    # GitHubへ保存する処理
    if st.button("💾 GitHub（Neo403zz/mercari-selestpro）に保存する", type="secondary"):
        if not github_token:
            st.error("左側のサイドバーにGitHubの Personal Access Token を入力してください。")
        else:
            try:
                headers = {
                    "Authorization": f"Bearer {github_token}",
                    "Accept": "application/vnd.github+json"
                }
                api_url = f"https://api.github.com/repos/{repo_name}/contents/{file_path}"
                
                # 既存ファイルの取得を試みる
                existing_data = []
                sha = None
                get_res = requests.get(api_url, headers=headers)
                if get_res.status_code == 200:
                    file_info = get_res.json()
                    sha = file_info['sha']
                    file_content = base64.b64decode(file_info['content']).decode('utf-8')
                    existing_data = json.loads(file_content)
                
                # 新規データを追加
                existing_data.append(res)
                updated_content = json.dumps(existing_data, ensure_ascii=False, indent=2)
                encoded_content = base64.b64encode(updated_content.encode('utf-8')).decode('utf-8')
                
                # GitHubへプッシュ（コミット）
                payload = {
                    "message": f"Add sourced product: {res['title_jp']} (Profit: {res['net_profit_jpy']} JPY)",
                    "content": encoded_content,
                    "sha": sha if sha else None
                }
                
                put_res = requests.put(api_url, headers=headers, data=json.dumps(payload))
                if put_res.status_code in [200, 201]:
                    st.success(f"🚀 データのGitHub（{repo_name}）への保存が成功しました！")
                else:
                    st.error(f"GitHub保存エラー: {put_res.status_code} - {put_res.text}")
                    
            except Exception as e:
                st.error(f"エラーが発生しました: {e}")
