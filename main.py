from flask import Flask, render_template, request
import pandas as pd
import plotly.express as px
from datetime import datetime
import os

app = Flask(__name__)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # ファイルアップロードを処理
        uploaded_file_gantt = request.files['file_gantt']
        uploaded_file_sales = request.files['file_sales']
        
        if uploaded_file_gantt and uploaded_file_sales:
            # ここでファイルを一時的に保存する
            gantt_path = os.path.join('uploads', uploaded_file_gantt.filename)
            sales_path = os.path.join('uploads', uploaded_file_sales.filename)
            uploaded_file_gantt.save(gantt_path)
            uploaded_file_sales.save(sales_path)
            
            # Excelファイルを読み込む
            df_gantt = pd.read_excel(gantt_path, sheet_name='カードプロモーション')
            df_sales = pd.read_excel(sales_path)
            
            # ...（元のStreamlitコードのデータ処理部分をここに移植）...
            # 日付フィルター
            df_gantt['開始日'] = pd.to_datetime(df_gantt['開始日']).dt.date
            df_gantt['終了日'] = pd.to_datetime(df_gantt['終了日']).dt.date
            min_date, max_date = df_gantt['開始日'].min(), df_gantt['終了日'].max()
            start_date = st.date_input('開始日を選択', min_value=min_date, max_value=max_date, value=min_date)
            end_date = st.date_input('終了日を選択', min_value=min_date, max_value=max_date, value=max_date)

            # '全館'カラムで'1'が入力されている場合、'全館'に変換
            df_gantt['全館'] = df_gantt['全館'].apply(lambda x: '全館' if x == 1 else x)

            # 売上データの日付列を日時型に変換し、日付のみを抽出
            df_sales['年月日'] = pd.to_datetime(df_sales['年月日']).dt.date

            # カテゴリを集約する関数
            def aggregate_category(group,input_name):
                # カテゴリ値を結合し、末尾にインプット名を追加
                aggregated_value = '・'.join(group.dropna().unique())
                if aggregated_value:
                    return f"{aggregated_value} {input_name}"
                else:
                    return None

            # カテゴリごとに集約する処理
            df_grouped = pd.DataFrame(columns=('プロモーション情報','プロモーション情報_略','開始日','終了日'))
            categories = ['全館', '4ライン名', 'グループ名', '部門名']
            for category in categories:
                # カテゴリに値がある行のみをフィルタ
                filtered_df = df_gantt.dropna(subset=[category])

                # インプット名、開始日、終了日でグループ化し、カテゴリ値を集約
                grouped = filtered_df.groupby(['インプット名', '開始日', '終了日']).apply(lambda x: aggregate_category(x[category], x['インプット名'].iloc[0])).reset_index(name='プロモーション情報')
                grouped['プロモーション情報_略'] = grouped['プロモーション情報'].apply(lambda x: (x[:10] + '他多数') if len(x) > 10 else x)
                df_grouped = pd.concat([df_grouped,grouped],join='inner')

            # 修正された開始日と終了日の計算
            df_grouped = df_grouped[((df_grouped['開始日'] <= end_date) & (df_grouped['終了日'] >= start_date))]
            df_grouped['修正開始日'] = df_grouped['開始日'].apply(lambda x: max(x, start_date))
            df_grouped['修正終了日'] = df_grouped['終了日'].apply(lambda x: min(x, end_date))

            filtered_df = df_grouped
            # ここにソート処理を追加
            filtered_df = filtered_df.sort_values(by=['修正開始日', '修正終了日'])

            

            # 売上データの折れ線グラフ作成
            filtered_sales = df_sales[(df_sales['年月日'] >= start_date) & (df_sales['年月日'] <= end_date)]
            fig_sales = px.line(filtered_sales, x='年月日', y=['売上高', '予測', '昨年売上高全規模同日', '昨年売上高全規模同曜'],
                                 labels={'value': '売上データ', 'variable': 'カテゴリー'})
            fig_sales.update_layout(width=2000, height=600,margin=dict(l=0, r=0, t=50, b=0))
            
            # Plotlyを使用してガントチャートを作成（修正された日付を使用）
            fig = px.timeline(filtered_df, x_start="修正開始日", x_end="修正終了日", y='プロモーション情報_略', color='プロモーション情報_略', title="プロモーションガントチャート")

            # ガントチャートのX軸の範囲を選択された期間に設定
            fig.update_layout(width=2000, height=600,xaxis_range=[start_date, end_date],margin=dict(l=0, r=0, t=50, b=0))
            fig.update_yaxes(categoryorder="total ascending")

            # PlotlyグラフをJSONとして生成
            fig_sales_json = fig_sales.to_json()
            fig_gantt_json = fig.to_json()

            # HTMLテンプレートにデータを渡す
            return render_template('charts.html', 
                                   gantt_chart=fig_gantt_json, 
                                   sales_chart=fig_sales_json,
                                   gantt_table=filtered_df.to_html(),
                                   sales_table=filtered_sales.to_html())

    # 初期またはファイルがアップロードされていない場合は、アップロードフォームを表示
    return render_template('index.html')

# 他のルートとビュー関数を必要に応じて追加

if __name__ == '__main__':
    app.run(debug=True)
